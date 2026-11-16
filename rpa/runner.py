"""RPA 단독 실행 CLI.

    python -m rpa.runner --chain all --mode auto --date 2026-11-16 [--json out.json] [--headed]
"""

import argparse
import json
from datetime import date

import pandas as pd

from .service import CHAINS, crawl_chain


def main() -> None:
    ap = argparse.ArgumentParser(description="movpick 상영 시간표 · 잔여석 RPA 수집기")
    ap.add_argument("--chain", default="all", choices=["all", *CHAINS])
    ap.add_argument("--mode", default="auto", choices=["auto", "real", "mock"])
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--headed", action="store_true", help="브라우저 창을 띄워서 실행")
    ap.add_argument("--json", help="결과를 JSON 파일로 저장")
    args = ap.parse_args()

    day = date.fromisoformat(args.date)
    rows = []
    for chain in CHAINS if args.chain == "all" else [args.chain]:
        r = crawl_chain(chain, day, args.mode, args.timeout, headless=not args.headed)
        print(f"[{chain:8}] ok={r.ok} source={r.source} items={len(r.items)} {r.duration_ms}ms - {r.message}")
        rows += [s.to_dict() for s in r.items]

    if rows:
        df = pd.DataFrame(rows)
        df["booking_rate"] = (1 - df.available_seats / df.total_seats.clip(lower=1)).round(3)
        summary = df.groupby(["chain", "movie_title"]).agg(
            showtimes=("external_id", "count"), avg_booking_rate=("booking_rate", "mean")
        )
        print(summary.round(3).to_string())
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
