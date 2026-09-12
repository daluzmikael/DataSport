"""Vault column -> broadcast name, unit and precision.

`Analyzer.query_analyzer._DISPLAY_COLUMN_RENAMES` is the nearest existing map but holds
exactly two entries, both for PIE, so it could not carry axis labels. This is the fuller
version, seeded from the two frontend maps that already existed —
`TREND_STAT_LABELS` (src/api/playerTrendData.ts) and `LEADERBOARD_STAT_LABELS`
(src/api/playerLeaderboardData.ts) — so the axis and the sentence use the same words.
"""
from __future__ import annotations

from Visualizer.chart_spec import FieldSpec, Unit

# Base name, with no per-mode wording. `label_for` adds "per game" / "total" itself so
# a Totals leaderboard never says "per game".
_BASE_LABELS: dict[str, str] = {
    "PTS": "Points",
    "AST": "Assists",
    "REB": "Rebounds",
    "OREB": "Offensive rebounds",
    "DREB": "Defensive rebounds",
    "STL": "Steals",
    "BLK": "Blocks",
    "BLKA": "Blocked attempts",
    "TOV": "Turnovers",
    "PF": "Fouls",
    "PFD": "Fouls drawn",
    "MIN": "Minutes",
    "GP": "Games played",
    "W": "Wins",
    "L": "Losses",
    "FGM": "Field goals made",
    "FGA": "Field goals attempted",
    "FG3M": "3-pointers made",
    "FG3A": "3-pointers attempted",
    "FTM": "Free throws made",
    "FTA": "Free throws attempted",
    "PLUS_MINUS": "Plus/minus",
    "DD2": "Double-doubles",
    "TD3": "Triple-doubles",
    "NBA_FANTASY_PTS": "Fantasy points",
    # Percentages — stored as fractions in the vault.
    "FG_PCT": "FG%",
    "FG3_PCT": "3P%",
    "FT_PCT": "FT%",
    "TS_PCT": "True shooting %",
    "EFG_PCT": "Effective FG%",
    "USG_PCT": "Usage %",
    "AST_PCT": "Assist %",
    "REB_PCT": "Rebound %",
    "OREB_PCT": "Offensive rebound %",
    "DREB_PCT": "Defensive rebound %",
    "TM_TOV_PCT": "Turnover %",
    "W_PCT": "Win %",
    # Ratings and rates.
    "OFF_RATING": "Offensive rating",
    "DEF_RATING": "Defensive rating",
    "NET_RATING": "Net rating",
    "E_OFF_RATING": "Est. offensive rating",
    "E_DEF_RATING": "Est. defensive rating",
    "E_NET_RATING": "Est. net rating",
    "PACE": "Pace",
    "POSS": "Possessions",
    "PIE": "PIE (PER equivalent)",
    "AST_TO": "Assist/turnover",
    "AST_RATIO": "Assist ratio",
}

# Counting stats that read as a rate under a PerGame plan and as a total otherwise.
_COUNTING: frozenset[str] = frozenset(
    {
        "PTS", "AST", "REB", "OREB", "DREB", "STL", "BLK", "BLKA", "TOV",
        "PF", "PFD", "MIN", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
        "NBA_FANTASY_PTS",
    }
)

# Never a total or a per-game figure, whatever the plan's per_mode says.
_ALWAYS_ABSOLUTE: frozenset[str] = frozenset({"GP", "W", "L", "DD2", "TD3", "POSS"})

_RATING_SUFFIXES = ("_RATING",)


def base_label(column: str) -> str:
    """Broadcast name with no per-mode wording."""
    key = (column or "").upper()
    if key in _BASE_LABELS:
        return _BASE_LABELS[key]
    # Unknown column: title-case it rather than showing a raw identifier.
    return (column or "").replace("_", " ").strip().title() or "Value"


def unit_for(column: str) -> Unit | None:
    key = (column or "").upper()
    if key.endswith("_PCT"):
        return "pct"
    if key.endswith(_RATING_SUFFIXES) or key == "PACE":
        return "rating"
    if key in _ALWAYS_ABSOLUTE:
        return "count"
    if key in _COUNTING:
        return "per_game"
    return None


def precision_for(column: str) -> int:
    key = (column or "").upper()
    if key.endswith("_PCT"):
        return 1  # rendered as a percentage, so one decimal is plenty
    if key in _ALWAYS_ABSOLUTE:
        return 0
    return 1


def label_for(column: str, per_mode: str | None = None) -> str:
    """Broadcast name, qualified by per_mode where that changes the meaning."""
    key = (column or "").upper()
    label = base_label(column)
    if key in _ALWAYS_ABSOLUTE or key.endswith("_PCT") or unit_for(key) == "rating":
        return label
    if key not in _COUNTING:
        return label
    mode = (per_mode or "").lower()
    if mode == "pergame":
        return f"{label} per game"
    if mode == "totals":
        return f"Total {label.lower()}"
    return label


def field(column: str, per_mode: str | None = None) -> FieldSpec:
    return FieldSpec(
        column=column,
        label=label_for(column, per_mode),
        unit=unit_for(column),
        precision=precision_for(column),
    )
