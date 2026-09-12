"""DuckDB connection over staged Parquet files (unified ingestion tables)."""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

_schema_cache: dict[str, Any] = {"value": None, "fetched_at": 0.0}
_SCHEMA_TTL_SECONDS = 600

# Parquet stem -> SQL view name (snake_case, stable for GPT)
STAGING_VIEWS: dict[str, str] = {
    "player_season_stats": "player_season_stats",
    "team_season_stats": "team_season_stats",
    "team_standings": "team_standings",
    "player_shot_zones": "player_shot_zones",
    "team_shot_zones": "team_shot_zones",
    "player_game_logs": "player_game_logs",
    "team_game_logs": "team_game_logs",
    "game_context": "game_context",
    "player_game_advanced": "player_game_advanced",
    "team_game_advanced": "team_game_advanced",
    "player_career": "player_career",
    "court_shots": "court_shots",
    "player_tracking": "player_tracking",
    "team_tracking": "team_tracking",
    "lineups": "lineups",
    "player_on_off": "player_on_off",
    "player_estimated_metrics": "player_estimated_metrics",
    "team_estimated_metrics": "team_estimated_metrics",
    # Phase 7-8. A staged parquet that is not listed here is invisible to the router,
    # which is the same failure mode that hid player_on_off for months.
    "player_synergy": "player_synergy",
    "team_synergy": "team_synergy",
    "player_bio": "player_bio",
    "team_roster": "team_roster",
    "player_awards": "player_awards",
    "franchise_history": "franchise_history",
    # Phase 9 — per-shot LOC_X/LOC_Y. Distinct from court_shots (zone grid).
    "player_shot_chart": "player_shot_chart",
    # Legacy. The modern dash endpoints stop at 1996-97, which silently truncated every
    # all-time answer — the career assists leader came back as Chris Paul because
    # Stockton's 15,806 are mostly outside the window. These two cover what came before.
    "legacy_season_stats": "legacy_season_stats",
    "all_time_leaders": "all_time_leaders",
}

# The single real connection. Never handed out directly — see get_connection().
_conn: duckdb.DuckDBPyConnection | None = None
_duck_lock = threading.Lock()

# One cursor per thread, retired whenever the root is rebuilt.
_local = threading.local()
_generation = 0


def default_staging_dir() -> Path:
    backend_root = Path(__file__).resolve().parent.parent
    raw = os.getenv("STAGING_DATA_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (backend_root / "data" / "staging").resolve()


def _parquet_path(staging_dir: Path, stem: str) -> Path:
    return staging_dir / f"{stem}.parquet"


def _escape_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _build_root() -> duckdb.DuckDBPyConnection:
    """Open the one real connection and register every staging view on it."""
    global _conn

    staging_dir = default_staging_dir()
    if not staging_dir.is_dir():
        raise FileNotFoundError(
            f"Staging directory not found: {staging_dir}. "
            "Run: python -m ingestion.stage_all --phase 1"
        )

    _conn = duckdb.connect(database=":memory:")
    registered: list[str] = []
    missing: list[str] = []

    for stem, view_name in STAGING_VIEWS.items():
        path = _parquet_path(staging_dir, stem)
        if not path.exists() or path.stat().st_size == 0:
            missing.append(stem)
            continue
        sql_path = _escape_path(path)
        try:
            _conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS "
                f"SELECT * FROM read_parquet('{sql_path}')"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Staging view skipped (%s): %s", stem, exc)
            missing.append(stem)
            continue
        registered.append(view_name)

    if not registered:
        raise FileNotFoundError(
            f"No staging parquet files found in {staging_dir}. "
            f"Expected at least one of: {', '.join(STAGING_VIEWS)}"
        )

    if missing:
        logger.warning("Staging views skipped (file missing): %s", ", ".join(missing))

    logger.info(
        "DuckDB staging ready | dir=%s | views=%s",
        staging_dir,
        ", ".join(registered),
    )
    return _conn


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return this thread's DuckDB handle onto the staging views.

    A DuckDB connection holds ONE result set. Handing the same connection to every
    request means a `.execute()` on one thread can land between another thread's
    `.execute()` and its `.fetchdf()`, and the second thread silently receives the
    first one's rows — or none at all.

    That is not theoretical. `execute_query` takes `_duck_lock`, but roughly twenty
    other call sites (`list_registered_tables`, `_columns_for_table`, the router's
    schema probes, the empty-result diagnosis) execute on the connection directly with
    no lock. Under two concurrent requests, a player search for LeBron logged
    `Query OK | rows=0 cols=0` and returned an empty list, while the identical SQL run
    in isolation returned his row. Nothing errored; the answer was just wrong.

    `.cursor()` is DuckDB's supported answer: it returns an independent connection onto
    the same in-memory database, with its own result set and full visibility of the
    views. One per thread, cached — the FastAPI threadpool reuses threads, so this is a
    handful of cursors, not one per request.
    """
    root = _conn if _conn is not None else _build_root()

    cached = getattr(_local, "conn", None)
    if cached is not None and getattr(_local, "generation", -1) == _generation:
        return cached

    conn = root.cursor()
    _local.conn = conn
    _local.generation = _generation
    return conn


def refresh_views() -> duckdb.DuckDBPyConnection:
    """Drop cached connections so the next get_connection() re-reads parquet from disk."""
    global _conn, _schema_cache, _generation
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
    _conn = None
    _schema_cache = {"value": None, "fetched_at": 0.0}
    # Bumping the generation retires every thread-local cursor without having to reach
    # into other threads to close them.
    _generation += 1
    _build_root()
    return get_connection()


def list_registered_tables(conn: duckdb.DuckDBPyConnection | None = None) -> list[str]:
    conn = conn or get_connection()
    rows = conn.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_type = 'VIEW'
        ORDER BY table_name
        """
    ).fetchall()
    return [r[0] for r in rows]


def _columns_for_table(conn: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    df = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'main' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchdf()
    if df.empty:
        return []
    return [str(c) for c in df["column_name"].tolist()]


def get_db_schema(conn: duckdb.DuckDBPyConnection | None = None) -> str:
    now = time.time()
    if _schema_cache["value"] and (now - _schema_cache["fetched_at"]) < _SCHEMA_TTL_SECONDS:
        return _schema_cache["value"]

    conn = conn or get_connection()
    tables = list_registered_tables(conn)
    parts: list[str] = [
        "=== DuckDB staging database (Parquet-backed views) ===",
        f"Staging directory: {default_staging_dir()}",
        "",
        "Slice columns on every table (when present):",
        "  season       — e.g. '2024-25' (career rows use 'CAREER' when available)",
        "  season_type  — 'Regular Season' or 'Playoffs'",
        "  per_mode     — PerGame, Totals, Per100Possessions, Per36, Per40, …",
        "  measure_type — Base, Advanced, Usage, Misc, Scoring, Defense (season dash tables)",
        "  pt_measure_type — Drives, Passing, … (player_tracking / team_tracking)",
        "",
        "Always filter season / season_type / per_mode / measure_type in WHERE when present.",
        "",
    ]

    table_blurbs = {
        "player_season_stats": (
            "Player season dashboard: box score + clutch_* + hustle_* columns. "
            "Use for player season stats, leaderboards, comparisons. "
            "IDs: PLAYER_ID, PLAYER_NAME (UPPERCASE). "
            "Clutch/hustle prefixed columns already merged."
        ),
        "team_season_stats": (
            "Team season dashboard (dash + clutch + hustle). "
            "IDs: TEAM_ID, TEAM_NAME (UPPERCASE)."
        ),
        "team_standings": (
            "League standings per team/season. "
            "IDs: TeamID, TeamCity, TeamName (CamelCase). No per_mode column."
        ),
        "player_shot_zones": (
            "Player shooting by zone. "
            "IDs: player_id, player_name (lowercase)."
        ),
        "team_shot_zones": (
            "Team shooting by zone. "
            "IDs: team_id, team_name (lowercase)."
        ),
        "player_game_logs": (
            "Player game-by-game logs. "
            "Slice: season, season_type. IDs: PLAYER_ID, GAME_ID (UPPERCASE)."
        ),
        "team_game_logs": (
            "Team game-by-game logs. "
            "Slice: season, season_type. IDs: TEAM_ID, GAME_ID (UPPERCASE)."
        ),
        "game_context": (
            "Per-game context from boxscoresummaryv3. "
            "Columns: game_id, dataset (string key), plus endpoint fields."
        ),
        "player_game_advanced": (
            "Per-game player advanced + misc + hustle. "
            "Column game_id (10-digit string). IDs: personId, teamId (camelCase)."
        ),
        "team_game_advanced": (
            "Per-game team advanced + misc + hustle. "
            "Column game_id. IDs: teamId (camelCase)."
        ),
        "player_career": (
            "Player career datasets from playercareerstats. "
            "Columns: player_id, dataset, unavailable (bool), plus API fields."
        ),
        "court_shots": (
            "Player shot chart zone grid per season. "
            "Slice: season, season_type. IDs: player_id (string)."
        ),
        "player_tracking": (
            "Season player tracking (leaguedashptstats). "
            "Slice: season, season_type, pt_measure_type, per_mode."
        ),
        "team_tracking": (
            "Season team tracking (leaguedashptstats). "
            "Slice: season, season_type, pt_measure_type, per_mode."
        ),
        "lineups": (
            "5-man lineup units (leaguedashlineups). "
            "Slice: season, season_type, group_quantity, measure_type, per_mode."
        ),
        "player_on_off": (
            "Player on/off court summary per team. "
            "Slice: season, season_type, per_mode. IDs: PLAYER_ID, TEAM_ID."
        ),
        "player_estimated_metrics": (
            "NBA estimated impact (E_NET_RATING, E_OFF_RATING, E_USG_PCT, …). "
            "Slice: season, season_type."
        ),
        "team_estimated_metrics": (
            "Team NBA estimated impact metrics. Slice: season, season_type."
        ),
    }

    for table in tables:
        cols = _columns_for_table(conn, table)
        col_text = ", ".join(cols)
        if len(cols) > 40:
            col_text = ", ".join(cols[:40]) + f", ... (+{len(cols) - 40} more)"
        blurb = table_blurbs.get(table, "")
        parts.append(f"TABLE {table} ({len(cols)} columns)\n{blurb}\nColumns: {col_text}\n")

    expected = set(STAGING_VIEWS)
    missing_views = sorted(expected - set(tables))
    if missing_views:
        parts.append(
            "STAGED FILES NOT YET ON DISK (run ingestion.stage_all for the matching phase): "
            + ", ".join(missing_views)
            + ".\n"
        )

    schema_description = "\n".join(parts)
    _schema_cache["value"] = schema_description
    _schema_cache["fetched_at"] = now
    logger.debug("DuckDB schema: %d chars, %d tables", len(schema_description), len(tables))
    return schema_description


def execute_query(
    conn: duckdb.DuckDBPyConnection,
    sql_query: str,
    *,
    timeout_ms: int | None = None,
) -> pd.DataFrame:
    del timeout_ms  # reserved for future PRAGMA
    logger.info("Executing DuckDB SQL: %s", (sql_query or "")[:600])
    try:
        with _duck_lock:
            df = conn.execute(sql_query).fetchdf()
    except duckdb.ConnectionException as exc:
        # The cached handle is process-wide, so anything that closes it takes every
        # later request down with it — and `_conn` stays non-None, so the dead object
        # is handed out forever. One request to the retired `/api/dashboards` did
        # exactly this and every read after it returned "Connection already closed"
        # until the backend was restarted. Rebuild and retry once.
        #
        # Recovery lives HERE rather than in `get_connection()` on purpose: a liveness
        # probe there would run outside `_duck_lock`, and a DuckDB connection holds one
        # result set at a time. A probe firing mid-query replaced another worker's rows
        # with its own — a player search returned `[{"1": 1}]`, the probe's answer.
        logger.warning("DuckDB connection was closed (%s) — rebuilding and retrying", exc)
        conn = refresh_views()
        with _duck_lock:
            df = conn.execute(sql_query).fetchdf()
    except Exception as exc:
        logger.error("DuckDB query failed: %s", exc)
        raise

    if df is None:
        df = pd.DataFrame()

    logger.info("Query OK | rows=%d cols=%d", len(df), len(df.columns))
    if not df.empty:
        logger.debug("Columns: %s", ", ".join(df.columns.astype(str).tolist()[:12]))
    return df
