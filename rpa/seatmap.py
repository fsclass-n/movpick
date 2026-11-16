"""극장 좌석 배치도 생성 · 명당 자리 산출 · 잔여석 변동 시뮬레이션."""

import random
import string

import numpy as np

PRIME_RATIO = 0.18
MAX_ROWS, MAX_COLS = 26, 30


def seat_id(row: int, col: int) -> str:
    return f"{string.ascii_uppercase[row]}{col + 1}"


def _dims(total: int) -> tuple[int, int, int]:
    total = int(np.clip(total or 120, 30, MAX_ROWS * MAX_COLS))
    cols = int(np.clip(round(np.sqrt(total * 1.6)), 8, MAX_COLS))
    rows = int(np.clip(int(np.ceil(total / cols)), 4, MAX_ROWS))
    return rows, cols, total


def prime_scores(rows: int, cols: int) -> np.ndarray:
    """스크린 기준 약 62% 깊이 · 중앙 열일수록 높은 점수 (0~1)."""
    r = np.arange(rows)[:, None]
    c = np.arange(cols)[None, :]
    r0, c0 = (rows - 1) * 0.62, (cols - 1) / 2
    dr = np.abs(r - r0) / max(rows - 1, 1)
    dc = np.abs(c - c0) / max(cols - 1, 1)
    return np.clip(1 - (dr * 1.6 + dc * 1.4) ** 1.2, 0, 1)


def _blocked(rows: int, cols: int, excess: int) -> list[str]:
    """정원을 맞추기 위해 뒷줄 양 끝 좌석부터 제거."""
    out: list[str] = []
    for r in range(rows - 1, -1, -1):
        left, right = 0, cols - 1
        while left <= right and len(out) < excess:
            out.append(seat_id(r, left))
            if len(out) < excess and left != right:
                out.append(seat_id(r, right))
            left, right = left + 1, right - 1
        if len(out) >= excess:
            break
    return out


def _weighted_sample(rng: random.Random, seats: list[str], scores: dict[str, float], k: int) -> set[str]:
    """명당 자리가 먼저 팔리는 현실적 분포로 점유 좌석을 샘플링."""
    pool = list(seats)
    chosen: set[str] = set()
    for _ in range(max(0, min(k, len(pool)))):
        pick = rng.choices(pool, weights=[(0.35 + scores[s]) ** 3 for s in pool], k=1)[0]
        chosen.add(pick)
        pool.remove(pick)
    return chosen


def build_layout(total_seats: int, available_seats: int, seed: str) -> dict:
    rng = random.Random(seed)
    rows, cols, total = _dims(total_seats)
    blocked = set(_blocked(rows, cols, rows * cols - total))
    grid = prime_scores(rows, cols)
    scores = {
        seat_id(r, c): round(float(grid[r, c]), 3)
        for r in range(rows)
        for c in range(cols)
        if seat_id(r, c) not in blocked
    }
    threshold = float(np.quantile(list(scores.values()), 1 - PRIME_RATIO))
    available = max(0, min(available_seats, total))
    taken = _weighted_sample(rng, list(scores), scores, total - available)
    return {
        "rows": rows,
        "cols": cols,
        "aisles": [c for c in (round(cols * 0.22), round(cols * 0.78)) if 0 < c < cols],
        "blocked": sorted(blocked),
        "prime": sorted(s for s, v in scores.items() if v >= threshold),
        "taken": sorted(taken),
        "scores": scores,
    }


def capacity(layout: dict) -> int:
    return len(layout["scores"])


def available_count(layout: dict) -> int:
    return capacity(layout) - len(layout["taken"])


def free_seats(layout: dict) -> set[str]:
    return set(layout["scores"]) - set(layout["taken"])


def reconcile(layout: dict, available_seats: int, seed: str) -> dict:
    """실제 크롤링된 잔여석 수에 맞춰 기존 배치도를 최소 변경으로 보정."""
    rng = random.Random(seed)
    taken = set(layout["taken"])
    target = capacity(layout) - max(0, min(available_seats, capacity(layout)))
    if len(taken) < target:
        taken |= _weighted_sample(rng, sorted(free_seats(layout)), layout["scores"], target - len(taken))
    elif len(taken) > target:
        taken -= set(rng.sample(sorted(taken), len(taken) - target))
    return {**layout, "taken": sorted(taken)}


def simulate_tick(
    layout: dict, rng: random.Random | None = None, cancel_rate: float = 0.03, book_rate: float = 0.02
) -> tuple[dict, list[str], list[str]]:
    """취소표 발생/신규 예매를 시뮬레이션. (새 레이아웃, 새로 비워진 좌석, 새로 예매된 좌석)"""
    rng = rng or random.Random()
    prime = set(layout["prime"])
    taken = set(layout["taken"])
    freed = [s for s in sorted(taken) if rng.random() < cancel_rate * (1.5 if s in prime else 1)]
    booked = [s for s in sorted(free_seats(layout)) if rng.random() < book_rate * (0.5 + layout["scores"][s])]
    return {**layout, "taken": sorted((taken - set(freed)) | set(booked))}, freed, booked
