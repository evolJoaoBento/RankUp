from __future__ import annotations

# Chess-style Elo. K=32 (standard for provisional/club play).
K = 32
START_RATING = 1000


def expected(ra: int, rb: int) -> float:
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def update(ra: int, rb: int, score_a: float) -> tuple[int, int]:
    """score_a: 1.0 win, 0.5 draw, 0.0 loss (for player A). Returns (new_a, new_b)."""
    ea = expected(ra, rb)
    na = round(ra + K * (score_a - ea))
    nb = round(rb + K * ((1.0 - score_a) - (1.0 - ea)))
    return na, nb
