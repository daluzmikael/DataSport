"""Deterministic SQL generation from a RouterPlan — no LLM, one table, no joins."""
from __future__ import annotations

import logging
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
# season per entity, so this is generous but still bounded.
ENTITY_ROW_CAP = int(os.getenv("ROUTER_ENTITY_ROW_CAP", "200"))

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

    declared = catalog_entry(table).get("name_column")
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
    """Match names accent-insensitively.

    The vault stores names exactly as NBA.com publishes them ("Nikola Jokić",
    "Luka Dončić"), while users type plain ASCII. Folding both sides means either
    spelling finds the player.
    """
    if not plan.entities:
        return None
    col = entity_name_column(plan, conn)
    if not col:
        logger.warning("No name column on %s — entity filter skipped", plan.table)
        return None
    clauses = [
        f"strip_accents({col}) ILIKE '%{_escape_literal(_ascii_fold(e))}%'"
        for e in plan.entities
    ]
    return "(" + " OR ".join(clauses) + ")"


def _season_filter(plan: RouterPlan, conn: Any | None = None) -> str | None:
    """Season labels sort lexicographically ('1999-00' < '2000-01'), so BETWEEN works."""
    table = plan.table
    if not table or not table_has_column(table, "season", conn):
        return None

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

    return clauses


def build_select_sql(plan: RouterPlan, per_mode: str, conn: Any | None = None) -> str:
    """Build the single SELECT for this plan and per_mode. Always SELECT *.

    Column pruning happens later, when serialising for the analyst — the API `data`
    field and the frontend still expect full rows.
    """
    conn = conn or get_connection()
    table = plan.table
    if not table:
        raise ValueError("Plan has no table")

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
