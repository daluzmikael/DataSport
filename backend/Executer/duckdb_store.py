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
    # Shot-level detail (6.3M rows). Registered so it stages and uploads; the
    # router cannot reach it until it gains a table_catalog.yaml entry.
    "player_shot_chart": "player_shot_chart",
    "player_tracking": "player_tracking",
    "team_tracking": "team_tracking",
    "lineups": "lineups",
    "player_on_off": "player_on_off",
    "player_estimated_metrics": "player_estimated_metrics",
    "team_estimated_metrics": "team_estimated_metrics",
}

_conn: duckdb.DuckDBPyConnection | None = None
_duck_lock = threading.Lock()


def default_staging_dir() -> Path:
    backend_root = Path(__file__).resolve().parent.parent
    raw = os.getenv("STAGING_DATA_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (backend_root / "data" / "staging").resolve()


_REMOTE_SCHEMES = ("s3://", "r2://", "gs://", "gcs://", "http://", "https://")


def staging_uri() -> str:
    """Base location of the staging parquet files: a local directory or a remote prefix.

    STAGING_DATA_URI wins when set (e.g. r2://datasport-vault/staging). Otherwise the
    local directory from STAGING_DATA_DIR / backend/data/staging is used.
    """
    raw = os.getenv("STAGING_DATA_URI", "").strip()
    if raw:
        return raw.rstrip("/")
    return str(default_staging_dir())


def is_remote_staging() -> bool:
    return staging_uri().startswith(_REMOTE_SCHEMES)


def _parquet_path(staging_dir: Path, stem: str) -> Path:
    return staging_dir / f"{stem}.parquet"


def _escape_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _parquet_uri(stem: str) -> str:
    """Remote URI for one staging table."""
    return f"{staging_uri()}/{stem}.parquet"


def _configure_remote_access(conn: duckdb.DuckDBPyConnection) -> None:
    """Install httpfs and register object-storage credentials from the environment.

    Public HTTPS parquet needs no credentials. Private buckets use a DuckDB secret:
    R2 (r2:// + R2_ACCOUNT_ID) or any S3-compatible endpoint (s3:// + S3_ENDPOINT).
    """
    conn.execute("INSTALL httpfs")
    conn.execute("LOAD httpfs")

    key_id = os.getenv("S3_ACCESS_KEY_ID", "").strip()
    secret = os.getenv("S3_SECRET_ACCESS_KEY", "").strip()
    if not (key_id and secret):
        logger.info("Remote staging without credentials (public HTTPS access assumed)")
        return

    account_id = os.getenv("R2_ACCOUNT_ID", "").strip()
    if account_id:
        conn.execute(
            "CREATE OR REPLACE SECRET datasport_staging "
            "(TYPE R2, KEY_ID ?, SECRET ?, ACCOUNT_ID ?)",
            [key_id, secret, account_id],
        )
        logger.info("Remote staging secret registered (R2 account %s)", account_id)
        return

    endpoint = os.getenv("S3_ENDPOINT", "").strip()
    region = os.getenv("S3_REGION", "auto").strip() or "auto"
    url_style = os.getenv("S3_URL_STYLE", "path").strip() or "path"
    params = ["TYPE S3", "KEY_ID ?", "SECRET ?", "REGION ?", "URL_STYLE ?"]
    args = [key_id, secret, region, url_style]
    if endpoint:
        params.append("ENDPOINT ?")
        args.append(endpoint.replace("https://", "").replace("http://", ""))
    conn.execute(
        f"CREATE OR REPLACE SECRET datasport_staging ({', '.join(params)})", args
    )
    logger.info("Remote staging secret registered (S3 endpoint %s)", endpoint or "aws")


def _source_for_view(stem: str) -> str | None:
    """read_parquet() argument for one table, or None when the file is absent locally.

    Remote sources are not probed here — a missing object surfaces when the view is
    created, which costs one request instead of an extra existence check per table.
    """
    if is_remote_staging():
        return _parquet_uri(stem)
    path = _parquet_path(default_staging_dir(), stem)
    if not path.exists() or path.stat().st_size == 0:
        return None
    return _escape_path(path)


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection with views registered over staging parquet files."""
    global _conn
    if _conn is not None:
        return _conn

    remote = is_remote_staging()
    location = staging_uri()
    if not remote and not default_staging_dir().is_dir():
        raise FileNotFoundError(
            f"Staging directory not found: {location}. "
            "Run: python -m ingestion.stage_all --phase 1, "
            "or point STAGING_DATA_URI at object storage."
        )

    _conn = duckdb.connect(database=":memory:")
    if remote:
        _configure_remote_access(_conn)

    registered: list[str] = []
    missing: list[str] = []

    for stem, view_name in STAGING_VIEWS.items():
        source = _source_for_view(stem)
        if source is None:
            missing.append(stem)
            continue
        try:
            _conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS "
                f"SELECT * FROM read_parquet('{source}')"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Staging view skipped (%s): %s", stem, exc)
            missing.append(stem)
            continue
        registered.append(view_name)

    if not registered:
        # Drop the half-built connection so a later call retries. Otherwise a
        # transient network failure against remote staging would be cached as a
        # view-less connection for the life of the process.
        try:
            _conn.close()
        except Exception:  # noqa: BLE001
            pass
        _conn = None
        raise FileNotFoundError(
            f"No staging parquet files found at {location}. "
            f"Expected at least one of: {', '.join(STAGING_VIEWS)}"
        )

    if missing:
        logger.warning("Staging views skipped (file missing): %s", ", ".join(missing))

    logger.info(
        "DuckDB staging ready | source=%s | remote=%s | views=%s",
        location,
        remote,
        ", ".join(registered),
    )
    return _conn


def refresh_views() -> duckdb.DuckDBPyConnection:
    """Drop cached connection so the next get_connection() re-reads parquet from disk."""
    global _conn, _schema_cache
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
    _conn = None
    _schema_cache = {"value": None, "fetched_at": 0.0}
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
        f"Staging source: {staging_uri()}",
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
    except Exception as exc:
        logger.error("DuckDB query failed: %s", exc)
        raise

    if df is None:
        df = pd.DataFrame()

    logger.info("Query OK | rows=%d cols=%d", len(df), len(df.columns))
    if not df.empty:
        logger.debug("Columns: %s", ", ".join(df.columns.astype(str).tolist()[:12]))
    return df
