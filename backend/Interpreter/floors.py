"""Minimum-volume floors for leaderboard questions.

Without a floor, "who was the best isolation scorer in 2023-24" answers
*Zion Williamson, 2.048 points per possession* — on 21 possessions. The number is
correct and the answer is useless; the intended answer is Kawhi Leonard at 1.198 on
252 possessions. The same happens on every rate stat: on/off net rating hands back a
player with 8 games, field-goal percentage hands back a centre with 12 attempts.

Three rules, in precedence order:

1. **The user always wins.** "minimum 50 games", "at least 100 possessions",
   "including everyone" — whatever they say replaces or removes the default.
   Detection is done in Python with a regex rather than left to the model, because a
   silently-dropped override is worse than no override at all.
2. **A default applies to ranking questions only.** A question about a NAMED player
   must never filter them out: "what did Jordan Walsh average" has to answer even at
   9 games.
3. **A floor that empties the result is dropped.** Returning nothing is worse than
   returning noisy rows.

Whatever ends up applied is recorded on the plan so the analyst can state it — an
unstated filter is an invisible lie about what "best" meant.
"""
from __future__ import annotations

import os

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Floor:
    column: str
    value: float
    label: str                 # human phrase: "games played", "possessions"
    source: str = "default"    # "default" | "user"

    def phrase(self) -> str:
        """How the analyst should say it."""
        v = int(self.value) if float(self.value).is_integer() else self.value
        return f"minimum {v} {self.label}"

    def as_row_filter(self) -> dict:
        return {"column": self.column, "op": "gte", "value": self.value}


# Per-table defaults. Chosen to cut noise without cutting real contributors: 20 games
# is roughly a quarter season, 100 possessions is a real play-type sample.
# Team tables get no floor — all 30 teams play a full schedule.
FLOOR_DEFAULTS: dict[str, Floor] = {
    "player_season_stats": Floor("GP", 20, "games played"),
    "player_estimated_metrics": Floor("GP", 20, "games played"),
    "player_on_off": Floor("GP", 20, "games played"),
    "player_synergy": Floor("POSS", 100, "possessions"),
    "player_tracking": Floor("GP", 20, "games played"),
    "player_shot_zones": Floor("GP", 20, "games played"),
    "lineups": Floor("MIN", 100, "minutes together"),
}

# A playoff run is at most 4 rounds. "Who led the 2022-23 playoffs in scoring" with the
# regular-season 20-game default kept 22 of 217 players — effectively "who led among
# the two finalists". The right games floor for a postseason is one full series.
PLAYOFF_GAMES_FLOOR = 5


def _postseason(plan) -> bool:
    return str(getattr(plan, "season_type", "") or "") == "Playoffs"


# Percentage columns are ratios, and a ratio with an empty denominator beats every real
# performance: "best three-point shooter in 2023-24" answered *Drew Eubanks, 100%* — on
# zero attempts. A games-played floor cannot fix that, because Eubanks played 75 games.
# The floor has to sit on the DENOMINATOR. Thresholds mirror the NBA's own qualifying
# rules (300 FGM / 82 3PM / 125 FTM a season), expressed in the units of each per_mode.
_RATE_DENOMINATORS: dict[str, tuple[str, str, float, float]] = {
    #  order_by column -> (denominator column, label, PerGame min, Totals min)
    "FG_PCT":   ("FGA",  "field goal attempts",   5.0, 300),
    "FG3_PCT":  ("FG3A", "three-point attempts",  2.0, 100),
    "FT_PCT":   ("FTA",  "free throw attempts",   2.0, 125),
    "TS_PCT":   ("FGA",  "field goal attempts",   5.0, 300),
    "EFG_PCT":  ("FGA",  "field goal attempts",   5.0, 300),
}


# Impact and efficiency ratings have no denominator column to floor — NET_RATING is
# already per-100-possessions, so there is nothing to divide by. Their noise comes from
# sample size instead, and the games default is too weak to catch it: the 2023-24
# NET_RATING leader was Neemias Queta, who played 28 games and cleared a 20-game floor
# comfortably. Above him sat Malcolm Cazalon at +83.3 in ONE game and 2.6 minutes.
#
# Minutes are the honest gate for these. 15 mpg over a qualifying season is roughly the
# rotation cutoff, and in Totals rows the equivalent season minutes.
_RATING_COLUMNS: frozenset[str] = frozenset({
    "NET_RATING", "OFF_RATING", "DEF_RATING", "E_NET_RATING", "E_OFF_RATING",
    "E_DEF_RATING", "PIE", "PACE", "E_PACE", "PLUS_MINUS", "USG_PCT", "E_USG_PCT",
    "AST_PCT", "AST_RATIO", "AST_TO", "OREB_PCT", "DREB_PCT", "REB_PCT",
    "TM_TOV_PCT", "E_TOV_PCT", "PPP", "PERCENTILE",
})

RATING_MIN_MPG = float(os.getenv("FLOOR_RATING_MIN_MPG", "15"))
RATING_MIN_TOTAL_MIN = float(os.getenv("FLOOR_RATING_MIN_TOTAL_MIN", "900"))


def rating_floor_for(order_by: str | None, per_mode: str) -> Floor | None:
    """Minutes floor implied by ranking on a rating/impact column."""
    if str(order_by or "").upper() not in _RATING_COLUMNS:
        return None
    if per_mode == "Totals":
        return Floor("MIN", RATING_MIN_TOTAL_MIN, "total minutes")
    return Floor("MIN", RATING_MIN_MPG, "minutes per game")


def rate_floor_for(order_by: str | None, per_mode: str) -> Floor | None:
    """Denominator floor implied by ranking on a percentage column."""
    key = str(order_by or "").upper()
    spec = _RATE_DENOMINATORS.get(key)
    if not spec:
        return None
    column, label, per_game_min, totals_min = spec
    if per_mode == "Totals":
        return Floor(column, totals_min, label)
    return Floor(column, per_game_min, f"{label} per game")

# Units the user might name, mapped to the column that measures them.
_UNIT_COLUMNS: dict[str, tuple[str, str]] = {
    "game": ("GP", "games played"),
    "games": ("GP", "games played"),
    "gp": ("GP", "games played"),
    "minute": ("MIN", "minutes"),
    "minutes": ("MIN", "minutes"),
    "min": ("MIN", "minutes"),
    "possession": ("POSS", "possessions"),
    "possessions": ("POSS", "possessions"),
    "poss": ("POSS", "possessions"),
    "attempt": ("FGA", "attempts"),
    "attempts": ("FGA", "attempts"),
    "shot": ("FGA", "attempts"),
    "shots": ("FGA", "attempts"),
}

_UNIT_ALT = "|".join(sorted(_UNIT_COLUMNS, key=len, reverse=True))

# "at least 50 games", "minimum of 20 games", "min 100 possessions", "50+ games",
# "30 games or more"
_MIN_PATTERNS = (
    r"(?:at\s+least|minimum(?:\s+of)?|min\.?|no\s+fewer\s+than)\s+(\d+)\s*(" + _UNIT_ALT + r")\b",
    r"(\d+)\s*\+\s*(" + _UNIT_ALT + r")\b",
    r"(\d+)\s*(" + _UNIT_ALT + r")\s+or\s+more\b",
)

# Phrases that mean "do not filter anyone out".
_NO_FLOOR_PATTERNS = (
    r"\bno\s+(?:minimum|floor|cutoff|threshold)\b",
    r"\b(?:include|including)\s+(?:everyone|everybody|all\s+players)\b",
    r"\bregardless\s+of\s+(?:games|minutes|playing\s+time)\b",
    r"\bany\s+number\s+of\s+(?:games|minutes)\b",
    r"\bwithout\s+a\s+(?:minimum|cutoff)\b",
)

NO_FLOOR = "none"


def detect_user_floor(question: str):
    """Read an explicit minimum out of the question.

    Returns a Floor when one is stated, the sentinel NO_FLOOR when the user asked for
    no minimum at all, or None when they said nothing about it.
    """
    q = (question or "").lower()

    for pat in _NO_FLOOR_PATTERNS:
        if re.search(pat, q):
            return NO_FLOOR

    for pat in _MIN_PATTERNS:
        m = re.search(pat, q)
        if m:
            value, unit = m.group(1), m.group(2)
            column, label = _UNIT_COLUMNS[unit]
            try:
                return Floor(column, float(value), label, source="user")
            except ValueError:
                continue
    return None


def floors_for_plan(plan, question: str) -> list[Floor]:
    """Every floor to apply to this plan, in the order they should be stated.

    A user-stated minimum always wins, including "minimum 1 game" — that is a real
    request to see everyone, and it is honoured rather than quietly raised. A rate
    floor is additive: asking for "the best 3P shooter with a minimum of 50 games"
    means 50 games AND enough attempts for the percentage to mean anything, because
    the games number does not constrain the denominator at all.
    """
    from Interpreter.router_plan import table_has_column

    table = getattr(plan, "table", None)
    if not table:
        return []

    user = detect_user_floor(question)
    if user is NO_FLOOR:
        logger.info("Floor: user asked for no minimum")
        return []

    # A career leaderboard aggregates whole careers, so a per-SEASON floor deletes
    # seasons out of the middle of a total. "Most career playoff points" answered
    # *LeBron James, 1,445 in 45 games* — every playoff run shorter than 20 games had
    # been dropped before the sum. The real figure is 8,521 across 302 games.
    if bool(getattr(plan, "is_career_leaderboard", lambda: False)()):
        logger.info("Floor: skipped — career aggregation would drop qualifying seasons")
        return []

    is_leaderboard = bool(getattr(plan, "is_leaderboard", lambda: False)())
    has_entities = bool(getattr(plan, "entities", None))

    out: list[Floor] = []

    if isinstance(user, Floor):
        volume = user
        # Honour the unit they named; if the table has no such column, keep their
        # number but measure it in the unit this table actually has.
        if not table_has_column(table, volume.column):
            fallback = _default_volume_floor(plan, table)
            if fallback is None:
                logger.info(
                    "Floor: user unit %s not on %s and no default — skipped",
                    volume.column, table,
                )
                volume = None  # type: ignore[assignment]
            else:
                volume = Floor(fallback.column, volume.value, fallback.label, source="user")
        if volume is not None:
            logger.info("Floor: user override %s >= %s", volume.column, volume.value)
            out.append(volume)
    elif is_leaderboard and not has_entities:
        # No user instruction: the default is for ranking questions only. A named-entity
        # question must never filter out its own subject.
        default = _default_volume_floor(plan, table)
        if default is not None and table_has_column(table, default.column):
            out.append(default)

    # The denominator floor is about whether the RANKING STATISTIC is meaningful, so it
    # applies to any leaderboard on a percentage column — including one where the user
    # named their own games minimum.
    if is_leaderboard and not has_entities:
        per_mode = (getattr(plan, "per_modes", None) or ["PerGame"])[0]
        rate = rate_floor_for(getattr(plan, "order_by", None), per_mode)
        if rate is not None and table_has_column(table, rate.column):
            if not any(f.column == rate.column for f in out):
                out.append(rate)

        rating = rating_floor_for(getattr(plan, "order_by", None), per_mode)
        if rating is not None and table_has_column(table, rating.column):
            if not any(f.column == rating.column for f in out):
                out.append(rating)

    return out


def _default_volume_floor(plan, table: str) -> Floor | None:
    """The table's default volume floor, adjusted for postseason schedules."""
    default = FLOOR_DEFAULTS.get(table)
    if default is None:
        return None
    if default.column == "GP" and _postseason(plan):
        return Floor("GP", PLAYOFF_GAMES_FLOOR, "playoff games")
    return default


def floor_for_plan(plan, question: str) -> Floor | None:
    """Back-compat single-floor accessor: the first floor `floors_for_plan` returns."""
    floors = floors_for_plan(plan, question)
    return floors[0] if floors else None


def soften_if_empty(plan, conn, floor: Floor) -> Floor | None:
    """Drop the floor if it would return nothing.

    A defensible threshold on a thin slice — an early season, a short playoff run —
    can wipe the result set, and an empty answer is worse than a noisy one. Only ever
    relaxes a DEFAULT: a user's explicit minimum is theirs to own, and silently
    ignoring it would be the worse failure.
    """
    if floor.source == "user":
        return floor
    try:
        from Interpreter.sql_builder import build_select_sql

        per_mode = (plan.per_modes or ["PerGame"])[0]
        sql = build_select_sql(plan, per_mode, conn)
        inner = sql.split(" LIMIT ")[0]
        inner = re.sub(r"\s+ORDER BY\s+.*$", "", inner, flags=re.IGNORECASE)
        inner = inner.replace("SELECT * FROM", "SELECT COUNT(*) FROM", 1)
        row = conn.execute(inner).fetchone()
        if row and int(row[0]) == 0:
            logger.info(
                "Floor %s >= %s would return 0 rows — dropped", floor.column, floor.value
            )
            return None
    except Exception as exc:  # noqa: BLE001 — probing must never break the query
        logger.debug("Floor emptiness probe failed: %s", exc)
    return floor
