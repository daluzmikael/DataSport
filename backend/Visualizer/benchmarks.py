"""Ceilings that put radar axes on a shared 0-100 scale.

These are PLAYER per-game ceilings, carried over from Team45's `STAT_BENCHMARKS`
(DashboardBackend/dashboardInterpreter.py). They are deliberately NOT the
`RADAR_BENCHMARKS` in frontend/home-prototype/src/data/schema/charts.ts — those are
team *game totals* (PTS: 120), and normalising a player's 27 points against them would
flatten every axis to near zero.

There is NO fallback for a column without an entry here, and that is the point. The
fallback used to be "normalise against the largest value in the frame", which is
degenerate for the case radars are mostly used in: a solo profile's frame is ONE row, so
the frame max is that player's own value and the axis reads exactly 100 every time.
Kobe Bryant's 2005-06 profile came back with seven of twelve axes pegged at 100.0 —
a polygon that is a circle, and says nothing. An axis that cannot be placed on a shared
scale is dropped instead.
"""
from __future__ import annotations

RADAR_BENCHMARKS: dict[str, float] = {
    "PTS": 35.0,
    "AST": 11.0,
    "REB": 14.0,
    "OREB": 5.0,
    "DREB": 11.0,
    "STL": 2.5,
    "BLK": 2.5,
    "FGM": 12.0,
    "FGA": 25.0,
    "FG3M": 5.0,
    "FG3A": 13.0,
    "FTM": 9.0,
    "FTA": 11.0,
    "MIN": 38.0,
    "TOV": 5.0,
    "PF": 4.0,
    "PLUS_MINUS": 12.0,
    # Fractions in the vault, so the ceiling is a fraction too.
    "FG_PCT": 0.65,
    "FG3_PCT": 0.45,
    "FT_PCT": 0.95,
    "TS_PCT": 0.70,
    "EFG_PCT": 0.65,
    "USG_PCT": 0.36,
    "AST_PCT": 0.50,
    "REB_PCT": 0.25,
    "OREB_PCT": 0.15,
    "DREB_PCT": 0.35,
    "PIE": 0.20,
    "OFF_RATING": 125.0,
    "DEF_RATING": 125.0,
    "NET_RATING": 15.0,
}

# Lower is better, so a raw ratio would reward the worst defender on the chart.
INVERTED: frozenset[str] = frozenset({"DEF_RATING", "TOV", "PF"})


def has_benchmark(column: str) -> bool:
    return (column or "").upper() in RADAR_BENCHMARKS


def benchmark_for(column: str) -> float | None:
    return RADAR_BENCHMARKS.get((column or "").upper())


def is_inverted(column: str) -> bool:
    return (column or "").upper() in INVERTED


def normalize(value: float, column: str) -> float | None:
    """Map a raw stat onto 0-100 against its ceiling, clamped.

    Returns None when the column has no ceiling — the caller drops the axis rather than
    inventing a scale for it.
    """
    ceiling = benchmark_for(column)
    if not ceiling:
        return None
    pct = (float(value) / ceiling) * 100.0
    if is_inverted(column):
        pct = 100.0 - pct
    return round(max(0.0, min(100.0, pct)), 1)
