"""Deterministic SQL generation from a RouterPlan — no LLM, one table, no joins."""
from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
from typing import Any

import pandas as pd

from Executer.data_backend import get_connection
from Executer.duckdb_store import execute_query
from Executer.executor import validate_and_normalize_sql
from Interpreter.router_plan import (
    RouterPlan,
    bundle_label,
    catalog_entry,
    resolve_column,
    table_has_column,
)

logger = logging.getLogger(__name__)

# Safety cap for named-entity pulls. Season ranges legitimately return one row per
# season per entity, and a full career of game logs is ~1,600 rows, so the cap has
# to clear that comfortably — at the old 200 a "whole career" question silently
# answered from the player's first two and a half seasons.
#
# The cap is now a backstop against a runaway scan (whole-league game logs are
# 26k rows/season), not a working limit. Whenever it does bite, the true match
# count is measured first and carried on df.attrs["true_row_count"] so nothing
# downstream can mistake a truncated frame for a complete one.
ENTITY_ROW_CAP = int(os.getenv("ROUTER_ENTITY_ROW_CAP", "5000"))

# Minimum rows for a leaderboard, so the analyst always has runners-up to
# explain the winner against.
LEADERBOARD_MIN_ROWS = int(os.getenv("ROUTER_LEADERBOARD_MIN_ROWS", "5"))

_PLAYER_NAME_CANDIDATES = ("PLAYER_NAME", "player_name", "PlayerName")
_TEAM_NAME_CANDIDATES = ("TEAM_NAME", "team_name", "TeamName", "teamName", "GROUP_NAME")


def _escape_literal(value: str) -> str:
    return value.replace("'", "''").strip()


def entity_name_column(plan: RouterPlan, conn: Any | None = None) -> str | None:
    """Resolve the column used to match entity names, catalog first then live schema."""
    table = plan.table
    if not table:
        return None

    spec = catalog_entry(table)

    # A table can carry BOTH a person name and a team name — team_roster has PLAYER
    # and TEAM_NAME. A single declared `name_column` cannot express that, so a team
    # question was matched against the player column and found nobody. When the plan
    # is about a team and the catalog names a team column, that wins.
    if plan.entity_type == "team" and spec.get("team_name_column"):
        resolved = resolve_column(table, spec["team_name_column"], conn)
        if resolved:
            return resolved

    declared = spec.get("name_column")
    if declared:
        resolved = resolve_column(table, declared, conn)
        if resolved:
            return resolved

    candidates = (
        _TEAM_NAME_CANDIDATES if plan.entity_type == "team" else _PLAYER_NAME_CANDIDATES
    )
    for candidate in candidates:
        resolved = resolve_column(table, candidate, conn)
        if resolved:
            return resolved
    return None


def _ascii_fold(value: str) -> str:
    """Drop diacritics from a search term so 'Jokic' can match 'Jokić'."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _entity_filter(plan: RouterPlan, conn: Any | None = None) -> str | None:
    """Match names accent-insensitively, exactly when the name is already canonical.

    The vault stores names as NBA.com publishes them ("Nikola Jokić", "Luka Dončić")
    while users type plain ASCII, so both sides are accent-folded.

    Matching is EXACT rather than substring. Unanchored `ILIKE '%name%'` used to make
    "LA" match nine teams and "Jordan" match twenty-one players, and the analyst would
    answer confidently from whichever row came first. Entities reaching here have been
    through `entity_resolver`, so they are full canonical names; anything that could
    not be resolved falls back to substring so a partial name still finds something
    rather than silently returning nothing.
    """
    if not plan.entities:
        return None
    col = entity_name_column(plan, conn)
    if not col:
        logger.warning("No name column on %s — entity filter skipped", plan.table)
        return None

    clauses: list[str] = []
    for e in plan.entities:
        folded = _escape_literal(_ascii_fold(e))
        if getattr(plan, "entities_are_canonical", False):
            clauses.append(f"strip_accents({col}) ILIKE '{folded}'")
        else:
            clauses.append(f"strip_accents({col}) ILIKE '%{folded}%'")
    return "(" + " OR ".join(clauses) + ")"


# Tables where the season is a plain data column rather than the canonical
# lowercase `season` slice, AND the labels are not uniformly 'YYYY-YY'.
# `player_awards.SEASON` mixes NBA labels ('2015-16') with bare Olympic years
# ('2016'), so the lexicographic BETWEEN used everywhere else silently mixes the
# two: a range of 2019-20..2021-22 swallows the bare '2020' and '2021' Olympic
# rows, while a single-season filter for 2015-16 misses the 2016 gold medal that
# belongs to exactly that season. Both formats are folded to the END year, which
# is the one year they agree on.
_PLAIN_SEASON_COLUMNS = {"player_awards": "SEASON"}


def _end_year_sql(col: str) -> str:
    """End-year of a season label, for tables that mix 'YYYY-YY' and 'YYYY'.

    A season label always spans consecutive years, so the end year is simply the
    start year plus one — no century arithmetic needed for '1999-00'.
    """
    trimmed = f"TRIM({col})"
    return (
        "CASE "
        f"WHEN regexp_matches({trimmed}, '^\\d{{4}}-\\d{{2}}$') "
        f"THEN TRY_CAST(SUBSTR({trimmed}, 1, 4) AS INTEGER) + 1 "
        f"WHEN regexp_matches({trimmed}, '^\\d{{4}}$') "
        f"THEN TRY_CAST({trimmed} AS INTEGER) "
        "ELSE NULL END"
    )


def _season_end_year(label: str | None) -> int | None:
    if not label:
        return None
    label = label.strip()
    if re.fullmatch(r"\d{4}-\d{2}", label):
        return int(label[:4]) + 1
    if re.fullmatch(r"\d{4}", label):
        return int(label)
    return None


def _plain_season_filter(table: str, plan: RouterPlan, conn: Any | None) -> str | None:
    """Season filter for tables in `_PLAIN_SEASON_COLUMNS`."""
    col = resolve_column(table, _PLAIN_SEASON_COLUMNS[table], conn)
    if not col:
        return None

    start = _season_end_year(plan.season_from)
    end = _season_end_year(plan.season_to)
    if start is None and end is None:
        return None
    expr = _end_year_sql(col)
    if start is not None and end is not None:
        lo, hi = min(start, end), max(start, end)
        if lo == hi:
            return f"{expr} = {lo}"
        return f"{expr} >= {lo} AND {expr} <= {hi}"
    year = start if start is not None else end
    return f"{expr} = {year}"


def _season_filter(plan: RouterPlan, conn: Any | None = None) -> str | None:
    """Season labels sort lexicographically ('1999-00' < '2000-01'), so BETWEEN works."""
    table = plan.table
    if not table or not table_has_column(table, "season", conn):
        return None

    if table in _PLAIN_SEASON_COLUMNS:
        return _plain_season_filter(table, plan, conn)

    start, end = plan.season_from, plan.season_to
    if start and end:
        if start == end:
            return f"season = '{_escape_literal(start)}'"
        return f"season >= '{_escape_literal(start)}' AND season <= '{_escape_literal(end)}'"
    if start:
        return f"season = '{_escape_literal(start)}'"
    if end:
        return f"season = '{_escape_literal(end)}'"
    return None


def _slice_filters(plan: RouterPlan, per_mode: str, conn: Any | None = None) -> list[str]:
    table = plan.table
    clauses: list[str] = []

    season_clause = _season_filter(plan, conn)
    if season_clause:
        clauses.append(season_clause)

    if table_has_column(table, "season_type", conn):
        clauses.append(f"season_type = '{_escape_literal(plan.season_type)}'")

    if table_has_column(table, "per_mode", conn):
        clauses.append(f"per_mode = '{_escape_literal(per_mode)}'")

    if plan.pt_measure_type and table_has_column(table, "pt_measure_type", conn):
        clauses.append(f"pt_measure_type = '{_escape_literal(plan.pt_measure_type)}'")

    if plan.measure_type and table_has_column(table, "measure_type", conn):
        clauses.append(f"measure_type = '{_escape_literal(plan.measure_type)}'")

    if plan.group_quantity is not None and table_has_column(table, "group_quantity", conn):
        clauses.append(f"group_quantity = {int(plan.group_quantity)}")

    clauses.extend(_row_filter_clauses(plan, conn))

    return clauses


def _row_filter_clauses(plan: RouterPlan, conn: Any | None = None) -> list[str]:
    """Turn validated structured conditions into SQL. Never model-written SQL.

    Columns are already resolved against the live schema by `validate_plan`, and the
    operator comes from a closed set, so the only free-form part is the literal — which
    is escaped or coerced to a number here.
    """
    out: list[str] = []
    for f in getattr(plan, "row_filters", None) or []:
        col = f.get("column")
        op = str(f.get("op", "eq")).lower()
        val = f.get("value")
        if not col or val is None:
            continue

        if op in ("contains", "not_contains"):
            negate = "NOT " if op == "not_contains" else ""
            out.append(f"{negate}strip_accents({col}) ILIKE '%{_escape_literal(_ascii_fold(str(val)))}%'")
            continue

        sym = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}.get(op)
        if not sym:
            continue
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            out.append(f"{col} {sym} {val}")
        else:
            out.append(f"{col} {sym} '{_escape_literal(str(val))}'")
    return out


# Counting stats that are meaningful to add up across seasons. Percentages and ratings
# are deliberately absent: summing FG_PCT over 20 seasons produces a number with no
# meaning at all, and the ones that CAN be rebuilt (FG_PCT from FGM/FGA) are rebuilt
# downstream in Analyzer.aggregates rather than guessed at here.
_CAREER_SUM_COLUMNS = (
    "GP", "W", "L", "MIN", "PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
    "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "PLUS_MINUS",
    "DD2", "TD3", "POSS",
)


def build_career_select_sql(plan: RouterPlan, per_mode: str, conn: Any | None = None) -> str:
    """One row per PLAYER, summed across every season, for all-time leaderboards.

    The ordinary leaderboard SELECT ranks player-SEASON rows, so "who has scored the
    most points ever" returns the best single season. This aggregates first and ranks
    after, which is the only shape that answers the question.
    """
    conn = conn or get_connection()
    table = plan.table
    name_col = entity_name_column(plan, conn)
    if not name_col:
        raise ValueError(f"{table} has no name column to group a career leaderboard by")

    where_parts = _slice_filters(plan, per_mode, conn)

    order_col = plan.order_by if plan.order_by else None
    sums: list[str] = []
    seen: set[str] = set()
    for candidate in ((order_col,) if order_col else ()) + _CAREER_SUM_COLUMNS:
        if not candidate:
            continue
        resolved = resolve_column(table, candidate, conn)
        if not resolved or resolved.upper() in seen:
            continue
        seen.add(resolved.upper())
        sums.append(f"SUM(TRY_CAST({resolved} AS DOUBLE)) AS {resolved}")

    # A table of one row per award has nothing to sum — the ranking value is the row
    # count itself ("who has the most All-Star selections").
    if not sums:
        sums = ["COUNT(*) AS award_count"]
        rank_expr = "award_count"
    else:
        rank_expr = (
            resolve_column(table, order_col, conn) if order_col else None
        ) or "COUNT(*)"

    select = [name_col, "COUNT(*) AS seasons_counted", *sums]
    sql = f"SELECT {', '.join(select)} FROM {table}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    sql += f" GROUP BY {name_col}"

    direction = "ASC" if plan.sort_dir == "asc" else "DESC"
    sql += f" ORDER BY {rank_expr} {direction} NULLS LAST"
    sql += f" LIMIT {max(int(plan.limit or 0), LEADERBOARD_MIN_ROWS)}"
    return sql


# --------------------------------------------------------------------------
# Shot charts
# --------------------------------------------------------------------------
# These MIRROR the renderer's constants in
# frontend/home-prototype/src/components/ShotChartCourt.tsx. The grid indexing has to
# agree exactly or the hexes land off the court, so change them together.
#
#   PADDING 20 · COURT_LEFT -250 · COURT_TOP 422 · COURT_BOTTOM -52 · HEX_RADIUS 8
#   toSvg(x, y) = (x + 270, 442 - y)
#   hexW = 16 · hexH = sqrt(3) * 8
SHOT_HEX_RADIUS = 8.0
SHOT_HEX_W = SHOT_HEX_RADIUS * 2          # 16
SHOT_HEX_H = math.sqrt(3) * SHOT_HEX_RADIUS  # 13.856406460551018
SHOT_COL_STEP = SHOT_HEX_W * 0.75         # 12
SHOT_X_OFFSET = 270.0                     # -COURT_LEFT + PADDING
SHOT_Y_OFFSET = 442.0                     # COURT_TOP + PADDING
SHOT_Y_MIN, SHOT_Y_MAX = -52.0, 420.0

# Generous backstop. The grid itself caps the result at roughly 1,200 cells times the
# handful of zones a cell can straddle, so this should never bite.
SHOT_CELL_CAP = int(os.getenv("ROUTER_SHOT_CELL_CAP", "20000"))

# At or below this many attempts the chart is drawn shot by shot instead of binned.
SHOT_POINT_CAP = int(os.getenv("ROUTER_SHOT_POINT_CAP", "800"))


def _opponent_tricode(value: str, season: str | None) -> str:
    """Resolve whatever the router wrote for a team into the tricode HTM/VTM hold.

    The catalog spells out that these columns are tricodes, and the router still
    produced `VTM ILIKE '%Spurs%'` — which matches nothing, silently. Nicknames, full
    names and tricodes all resolve through the same alias table the rest of the
    pipeline uses, and it is era-aware, so "the Sonics" becomes SEA rather than OKC.
    """
    from ingestion.team_identity import ALIAS_TO_ID, _norm, identity_for_id

    try:
        team_id = ALIAS_TO_ID.get(_norm(value))
        if team_id is None:
            return value
        identity = identity_for_id(team_id, season)
        return getattr(identity, "tricode", None) or value
    except Exception:  # noqa: BLE001 — an unresolvable name is not worth failing over
        return value


def _shot_where_sql(plan: RouterPlan, conn: Any | None = None) -> str:
    """WHERE clause shared by the binned and shot-by-shot forms.

    Row filters are handled here rather than through `_slice_filters` because an
    opponent filter has to become an OR: this table has no MATCHUP column, only HTM and
    VTM tricodes, and row_filters are otherwise ANDed together. Asking for "Tatum
    against the Spurs" used to come back with `SHOT_ZONE_BASIC ILIKE '%Spurs%'` — a
    clause that validates, means nothing, and matched zero rows.
    """
    per_mode = plan.per_modes[0] if plan.per_modes else "PerGame"
    bare = plan.model_copy(update={"row_filters": []})
    where_parts = _slice_filters(bare, per_mode, conn)

    # An exact GAME_DATE already identifies the game, and it is more precise than the
    # season slice the router guessed around it — so the slice must not be allowed to
    # contradict it. "Tatum against the Spurs on April 30 2021" came back empty because
    # the router read late April as the postseason and added season_type='Playoffs',
    # while that compressed season ran into May and the game was regular season.
    has_game_date = any(
        str(f.get("column", "")).upper() == "GAME_DATE"
        for f in (plan.row_filters or [])
    )
    if has_game_date:
        where_parts = [c for c in where_parts if not c.lstrip("(").startswith("season")]

    entity_clause = _entity_filter(plan, conn)
    if entity_clause:
        where_parts.append(entity_clause)

    for f in plan.row_filters or []:
        column = str(f.get("column", "")).upper()
        if column in ("HTM", "VTM", "TEAM_NAME"):
            raw = str(f.get("value", "")).strip()
            if not raw:
                continue
            value = _escape_literal(_opponent_tricode(raw, plan.season_from or plan.season_to))
            # Either side of the fixture matches; the player's own team is already
            # pinned by the entity filter.
            where_parts.append(f"(HTM ILIKE '%{value}%' OR VTM ILIKE '%{value}%')")
            continue
        one = plan.model_copy(update={"row_filters": [f]})
        where_parts.extend(_row_filter_clauses(one, conn))

    where_parts.append(f"LOC_Y BETWEEN {SHOT_Y_MIN} AND {SHOT_Y_MAX}")
    where_parts.append("LOC_X IS NOT NULL AND LOC_Y IS NOT NULL")
    return " WHERE " + " AND ".join(where_parts) if where_parts else ""


def _shot_row_count(where_sql: str, conn: Any | None = None) -> int:
    conn = conn or get_connection()
    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM player_shot_chart{where_sql}"
        ).fetchone()
        return int(row[0]) if row else 0
    except Exception:  # noqa: BLE001 — fall back to the binned form, which is always safe
        logger.warning("Shot-chart count probe failed; using the binned form")
        return SHOT_POINT_CAP + 1


def build_shot_chart_sql(plan: RouterPlan, conn: Any | None = None) -> str:
    """Aggregate shot attempts into hex cells IN DuckDB.

    The point of binning here rather than in pandas or the browser is that the hex grid
    has a fixed ceiling — a half court over radius 8 is about 1,200 cells — while the
    source does not. LeBron's career is 37,669 attempts and the whole 2023-24 league is
    232,540, and both collapse to roughly the same ~1,200 rows. So scope stops being a
    payload question, and ENTITY_ROW_CAP can never silently truncate a chart into
    looking complete when it is not.

    SHOT_ZONE_BASIC rides along in the GROUP BY so one read serves both consumers: the
    chart sums over zone to get cells, and the analyst sums over cells to get zones.
    """
    conn = conn or get_connection()
    where_sql = _shot_where_sql(plan, conn)

    # A small sample is returned SHOT BY SHOT rather than binned. Hex bins need volume
    # to mean anything — for a single game no cell reaches the accuracy floor, and the
    # hotspot view falls back to one-attempt cells that all read 0% or 100%. Individual
    # makes and misses are the honest picture at that size, and 800 rows is nothing.
    if _shot_row_count(where_sql, conn) <= SHOT_POINT_CAP:
        return (
            "SELECT LOC_X, LOC_Y, SHOT_MADE_FLAG, SHOT_ZONE_BASIC AS zone"
            f" FROM player_shot_chart{where_sql} LIMIT {SHOT_POINT_CAP}"
        )

    half_h = SHOT_HEX_H / 2

    return (
        "WITH binned AS ("
        f" SELECT CAST(ROUND((LOC_X + {SHOT_X_OFFSET}) / {SHOT_COL_STEP}) AS INTEGER) AS hex_col,"
        f" ({SHOT_Y_OFFSET} - LOC_Y) AS py,"
        " SHOT_MADE_FLAG AS made,"
        " SHOT_ZONE_BASIC AS zone"
        f" FROM player_shot_chart{where_sql}"
        " )"
        " SELECT hex_col,"
        f" CAST(ROUND((py - CASE WHEN hex_col % 2 = 0 THEN 0.0 ELSE {half_h} END)"
        f" / {SHOT_HEX_H}) AS INTEGER) AS hex_row,"
        " zone,"
        " CAST(SUM(made) AS INTEGER) AS made,"
        " CAST(COUNT(*) AS INTEGER) AS total"
        " FROM binned"
        " GROUP BY hex_col, hex_row, zone"
        f" LIMIT {SHOT_CELL_CAP}"
    )


def build_select_sql(plan: RouterPlan, per_mode: str, conn: Any | None = None) -> str:
    """Build the single SELECT for this plan and per_mode. Always SELECT *.

    Column pruning happens later, when serialising for the analyst — the API `data`
    field and the frontend still expect full rows.
    """
    conn = conn or get_connection()
    table = plan.table
    if not table:
        raise ValueError("Plan has no table")

    if plan.is_career_leaderboard():
        return build_career_select_sql(plan, per_mode, conn)

    # Shot charts are aggregated in the query, not read row by row.
    if table == "player_shot_chart":
        return build_shot_chart_sql(plan, conn)

    where_parts = _slice_filters(plan, per_mode, conn)

    entity_clause = _entity_filter(plan, conn)
    if entity_clause:
        where_parts.append(entity_clause)


    sql = f"SELECT * FROM {table}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)

    if plan.order_by and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", plan.order_by):
        direction = "ASC" if plan.sort_dir == "asc" else "DESC"
        sql += f" ORDER BY {plan.order_by} {direction} NULLS LAST"
    elif table_has_column(table, "season", conn) and plan.is_multi_season():
        sql += " ORDER BY season ASC"

    if plan.is_leaderboard() and plan.limit and plan.limit > 0:
        # Pull a few extra rows beyond what was asked for. "Which team had the best
        # record" routes to limit=1, and a single row gives the analyst nothing to
        # explain the result against — the answer needs a comparison set to say why.
        sql += f" LIMIT {max(int(plan.limit), LEADERBOARD_MIN_ROWS)}"
    else:
        sql += f" LIMIT {ENTITY_ROW_CAP}"

    return sql


def count_matching_rows(plan: RouterPlan, per_mode: str, conn: Any | None = None) -> int | None:
    """How many rows the plan's filters actually match, ignoring the LIMIT.

    Needed so a capped result can never be reported as a complete one.
    """
    conn = conn or get_connection()
    try:
        sql = build_select_sql(plan, per_mode, conn)
        inner = sql.split(" LIMIT ")[0]
        inner = re.sub(r"\s+ORDER BY\s+.*$", "", inner, flags=re.IGNORECASE)
        inner = inner.replace("SELECT * FROM", "SELECT COUNT(*) FROM", 1)
        row = conn.execute(inner).fetchone()
        return int(row[0]) if row else None
    except Exception as exc:  # noqa: BLE001 — counting is best-effort
        logger.debug("Row count probe failed for %s: %s", plan.table, exc)
        return None


def execute_plan(
    plan: RouterPlan, conn: Any | None = None
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Run one SELECT per per_mode. Returns (bundles, error strings)."""
    conn = conn or get_connection()
    bundles: dict[str, pd.DataFrame] = {}
    errors: list[str] = []

    per_modes = plan.per_modes or ["PerGame"]
    if not table_has_column(plan.table, "per_mode", conn):
        per_modes = per_modes[:1]  # table has no per_mode slice; one read is enough

    for per_mode in per_modes:
        label = bundle_label(plan, per_mode)
        try:
            sql = build_select_sql(plan, per_mode, conn)
            sql = validate_and_normalize_sql(sql)
            logger.info("[ROUTER SQL] %s\n%s", label, sql)
            df = execute_query(conn, sql)
            if df is None or df.empty:
                logger.warning("[ROUTER SQL] %s returned 0 rows", label)
                continue

            # Only pay for the COUNT probe when the result looks capped.
            true_count = len(df)
            if len(df) >= ENTITY_ROW_CAP:
                probed = count_matching_rows(plan, per_mode, conn)
                if probed is not None and probed > len(df):
                    true_count = probed
                    logger.warning(
                        "[ROUTER SQL] %s capped: %d of %d matching rows returned",
                        label, len(df), probed,
                    )
            df.attrs["true_row_count"] = true_count
            bundles[label] = df
        except Exception as exc:  # noqa: BLE001 — surfaced to the repair path
            message = f"{label}: {exc}"
            logger.error("[ROUTER SQL FAILED] %s", message)
            errors.append(message)

    return bundles, errors


def primary_bundle_for_frontend(bundles: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Pick the largest non-empty bundle for the backward-compatible `data` field."""
    if not bundles:
        return pd.DataFrame()
    return max(bundles.values(), key=lambda df: len(df))


def bundles_to_records(bundles: dict[str, pd.DataFrame]) -> dict[str, list[dict]]:
    import numpy as np

    out: dict[str, list[dict]] = {}
    for label, df in bundles.items():
        clean = df.replace({np.nan: None})
        out[label] = clean.to_dict(orient="records")
    return out
