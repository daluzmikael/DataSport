"""
Natural language → SQL → DuckDB (staged Parquet) for phase-1 unified tables.

Flow: question → GPT SQL → validate → execute → DataFrame
"""
from __future__ import annotations

import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

from Executer.data_backend import get_connection, get_db_schema, use_duckdb_staging
from Executer.executor import execute_query, limit_rows, validate_and_normalize_sql

load_dotenv()
logger = logging.getLogger(__name__)

_api_key = os.getenv("OPENAI_API_KEY")
from llm.client import openai_base_url

_client = OpenAI(api_key=_api_key, base_url=openai_base_url()) if _api_key else None

_STAGING_SQL_MODEL = os.getenv("STAGING_SQL_MODEL", "gpt-5.4-mini")


def _build_staging_prompt(schema_description: str, user_input: str) -> str:
    return f"""You are a senior SQL engineer for an NBA analytics DuckDB database.
Convert the user request into ONE valid DuckSQL SELECT query.

DATABASE
- Engine: DuckDB over Parquet views (not PostgreSQL).
- Use only table names listed in DATABASE SCHEMA below.
- Tables (when staged): player_season_stats, team_season_stats, team_standings,
  player_shot_zones, team_shot_zones, player_game_logs, team_game_logs,
  game_context, player_game_advanced, team_game_advanced, player_career, court_shots,
  player_tracking, team_tracking, lineups, player_on_off,
  player_estimated_metrics, team_estimated_metrics.
- Use only table names listed in DATABASE SCHEMA below.

SLICE COLUMNS (filter in WHERE; exact string match)
- season: e.g. '2024-25' (hyphenated). Career rows use season = 'CAREER' when present.
- season_type: 'Regular Season' or 'Playoffs'
- per_mode: PerGame, Totals, Per100Possessions, Per36, Per40, …
- measure_type: Base, Advanced, Usage, Misc, Scoring, Defense (season dash tables)
- pt_measure_type: Drives, Passing, … (tracking tables)

TABLE PICKING
- Player season box score / leaderboards / player comparisons → player_season_stats
  (default measure_type = 'Base', per_mode = 'PerGame')
- Advanced metrics (TS%, USG%, NET_RATING, PIE) → player_season_stats
  WHERE measure_type = 'Advanced' AND per_mode = 'PerGame'
- NBA estimated impact (E_NET_RATING, …) → player_estimated_metrics
- Player tracking (drives, passing, …) → player_tracking WHERE pt_measure_type = '…'
- 5-man lineups → lineups WHERE group_quantity = 5
- On/off court → player_on_off
- Team season stats → team_season_stats
- Standings, seeds, W-L, point differential → team_standings (no per_mode)
- Player shot zones / shooting areas → player_shot_zones
- Team shot zones → team_shot_zones

COLUMN CASING (critical)
- player_season_stats, team_season_stats: UPPERCASE (PLAYER_ID, PLAYER_NAME, TEAM_ID, PTS, GP, …)
- team_standings: CamelCase (TeamID, TeamName, TeamCity, WinPCT, DiffPointsPG, …)
- player_shot_zones, team_shot_zones: lowercase (player_id, player_name, team_id, …)

PLAYER / TEAM NAMES
- Use ILIKE with wildcards: PLAYER_NAME ILIKE '%Curry%' or player_name ILIKE '%curry%'
- Never exact-match names with =

SEASON MAPPING
- "2024-25" / "this season" (2024-25 data) → season = '2024-25'
- Bare start year "2020" → season = '2020-21'
- Playoffs: season_type = 'Playoffs'; regular: season_type = 'Regular Season'
- Per-game stats: per_mode = 'PerGame'; season totals: per_mode = 'Totals'
- Per-100-poss: per_mode = 'Per100Possessions'
- Always set measure_type for season dash queries (default 'Base' for box score)
- Clutch columns are prefixed clutch_ (already on player_season_stats / team_season_stats)
- Hustle columns are prefixed hustle_

QUERY POLICY (analyzer does math/ranking after fetch)
- Return RAW rows: SELECT explicit columns only (no SELECT *).
- Do NOT use SUM, AVG, COUNT, GROUP BY, HAVING, window functions unless the user explicitly
  asks for aggregation across many rows in one query.
- ORDER BY and LIMIT are allowed when the user asks for top-N or recent ordering.
- Do not invent columns; use DATABASE SCHEMA only.

OUTPUT
Return ONLY the SQL. No markdown, no backticks, no explanation.

DATABASE SCHEMA:
{schema_description}

USER REQUEST:
{user_input}

SQL:"""


def _strip_sql_fences(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = cleaned.replace("```sql", "").replace("```", "").strip()
    return cleaned


def repair_staging_sql(
    original_sql: str,
    error_message: str,
    schema_description: str,
    user_input: str,
) -> str:
    if _client is None:
        raise RuntimeError("OPENAI_API_KEY is not set")

    prompt = f"""Fix this DuckDB SELECT query.

Schema:
{schema_description}

User request:
{user_input}

Failed SQL:
{original_sql}

Error:
{error_message}

Rules: DuckDB syntax; only use tables/columns from schema; keep slice filters
(season, season_type, per_mode) when relevant.

Return ONLY the corrected SQL."""

    response = _client.chat.completions.create(
        model=_STAGING_SQL_MODEL,
        messages=[
            {"role": "system", "content": "Return only valid DuckDB SELECT SQL."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_completion_tokens=1500,
    )
    return _strip_sql_fences(response.choices[0].message.content or "")


def natural_language_to_sql_staging(user_input: str):
    if not use_duckdb_staging():
        raise RuntimeError("staging_query called but DATA_BACKEND is not duckdb")

    if not _client:
        logger.error("OPENAI_API_KEY missing — cannot generate SQL")
        return None

    raw = (user_input or "").strip()
    if raw.lower().startswith(
        ("select ", "with ", "insert ", "update ", "delete ", "create ", "drop ", "alter ")
    ):
        raise ValueError("Raw SQL passthrough is disabled for natural language requests")

    conn = get_connection()
    schema_description = get_db_schema(conn)
    prompt = _build_staging_prompt(schema_description, raw)

    try:
        response = _client.chat.completions.create(
            model=_STAGING_SQL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You write DuckDB SELECT queries for NBA staged tables. SQL only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_completion_tokens=1500,
        )
        sql_query = _strip_sql_fences(response.choices[0].message.content or "")
        logger.info("Generated staging SQL:\n%s", sql_query)
    except Exception as exc:
        logger.error("OpenAI error: %s", exc)
        return None

    sql_query = limit_rows(sql_query)
    try:
        sql_query = validate_and_normalize_sql(sql_query)
    except ValueError as exc:
        logger.error("SQL validation failed: %s", exc)
        return None

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            logger.info("Executing staging SQL (attempt %d)", attempt + 1)
            return execute_query(conn, sql_query)
        except Exception as exc:
            err = str(exc)
            logger.error("Execution error: %s", err)
            if attempt >= max_attempts - 1:
                return None
            if not any(k in err.lower() for k in ("does not exist", "column", "binder", "catalog")):
                return None
            try:
                sql_query = repair_staging_sql(sql_query, err, schema_description, raw)
                sql_query = limit_rows(sql_query)
                sql_query = validate_and_normalize_sql(sql_query)
            except Exception as repair_exc:
                logger.error("Repair failed: %s", repair_exc)
                return None

    return None


def debug_staging_routing(user_input: str, model_sql: str | None = None) -> dict:
    conn = get_connection()
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchdf()
    return {
        "backend": "duckdb",
        "staging_dir": str(os.getenv("STAGING_DATA_DIR", "")) or "data/staging (default)",
        "registered_tables": tables["table_name"].tolist() if not tables.empty else [],
        "input_model_sql": model_sql,
        "user_input": user_input,
    }
