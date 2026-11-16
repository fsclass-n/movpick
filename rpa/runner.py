"""RPA 단독 실행 CLI / 원격 수집기.

    # 수집 결과 확인
    python -m rpa.runner --chain all --mode auto --date 2026-11-16 [--json out.json] [--headed]

    # 원격 수집기: 국내 PC에서 CGV를 수집해 백엔드로 전송 (RPA_INGEST_TOKEN 필요)
    python -m rpa.runner --chain cgv --mode real --days 2 --push https://movpick-api.onrender.com
"""

import argparse
import json
import os
import socket
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from .service import CHAINS, crawl_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def push(api: str, token: str, result) -> str:
    body = {
        "chain": result.chain,
        "date": result.day.isoformat(),
        "items": [{k: v for k, v in s.to_dict().items() if k not in ("chain", "source", "extra")} for s in result.items],
        "duration_ms": result.duration_ms,
        "collector": socket.gethostname()[:50],
    }
    res = requests.post(f"{api.rstrip('/')}/api/rpa/ingest", json=body, headers={"X-RPA-Token": token}, timeout=120)
    if not res.ok:
        raise RuntimeError(f"push 실패 HTTP {res.status_code}: {res.text[:200]}")
    return f"push {res.json()['saved']}건 저장"


def main() -> None:
    ap = argparse.ArgumentParser(description="movpick 상영 시간표 · 잔여석 RPA 수집기")
    ap.add_argument("--chain", default="all", choices=["all", *CHAINS])
    ap.add_argument("--mode", default="auto", choices=["auto", "real", "mock"])
    ap.add_argument("--date", default=date.today().isoformat(), help="시작 일자 (YYYY-MM-DD)")
    ap.add_argument("--days", type=int, default=1, help="시작 일자부터 수집할 일수")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--headed", action="store_true", help="브라우저 창을 띄워서 실행")
    ap.add_argument("--proxy", default=os.getenv("RPA_PROXY_URL") or None, help="http://user:pass@host:port")
    ap.add_argument("--json", help="결과를 JSON 파일로 저장")
    ap.add_argument("--push", metavar="API_URL", help="실데이터를 백엔드 /api/rpa/ingest 로 전송")
    ap.add_argument("--token", default=os.getenv("RPA_INGEST_TOKEN", ""), help="기본값: 환경변수 RPA_INGEST_TOKEN")
    args = ap.parse_args()
    if args.push and not args.token:
        ap.error("--push 에는 --token 또는 RPA_INGEST_TOKEN 환경변수가 필요합니다.")

    start = date.fromisoformat(args.date)
    rows, failed = [], 0
    for chain in CHAINS if args.chain == "all" else [args.chain]:
        for day in (start + timedelta(days=i) for i in range(max(1, args.days))):
            r = crawl_chain(chain, day, args.mode, args.timeout, headless=not args.headed, proxy=args.proxy)
            note = ""
            if args.push and r.source == "real" and r.items:
                try:
                    note = " | " + push(args.push, args.token, r)
                except Exception as e:  # noqa: BLE001
                    note, failed = f" | {e}", failed + 1
            elif args.push:
                note = " | 실데이터가 아니므로 전송 생략"
            failed += 0 if r.ok else 1
            if os.getenv("GITHUB_ACTIONS") and not r.ok:
                print(f"::error title={chain} {day}::{r.message}{note}")
            print(f"[{chain:8}] {day} ok={r.ok} source={r.source} items={len(r.items)} {r.duration_ms}ms - {r.message}{note}")
            rows += [s.to_dict() for s in r.items]

    if rows and not args.push:
        df = pd.DataFrame(rows)
        df["booking_rate"] = (1 - df.available_seats / df.total_seats.clip(lower=1)).round(3)
        summary = df.groupby(["chain", "movie_title"]).agg(
            showtimes=("external_id", "count"), avg_booking_rate=("booking_rate", "mean")
        )
        print(summary.round(3).to_string())
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
