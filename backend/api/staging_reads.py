"""Read-only REST endpoints over DuckDB staging parquet (home-prototype)."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from Analyzer.player_composite import player_impact_label
from Executer.data_backend import get_connection, use_duckdb_staging
from Executer.duckdb_store import default_staging_dir, list_registered_tables, refresh_views
from Executer.executor import execute_query, validate_and_normalize_sql

router = APIRouter(prefix="/api/staging", tags=["staging"])

_SEASON_RE = re.compile(r"^\d{4}-\d{2}$")
_NUM_ID_RE = re.compile(r"^\d+$")
_SEASON_TYPES = {"Regular Season", "Playoffs"}
_PER_MODES = {
    "PerGame",
    "Totals",
    "Per100Possessions",
    "Per36",
    "Per40",
    "Per100Plays",
}
_MEASURE_TYPES = {"Base", "Advanced", "Usage", "Misc", "Scoring", "Defense"}


def _require_staging() -> None:
    if not use_duckdb_staging():
        raise HTTPException(
            status_code=503,
            detail="Staging API requires DATA_BACKEND=duckdb (or unset with no POSTGRES_HOST)",
        )


def _season(value: str) -> str:
    if not _SEASON_RE.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid season: {value}")
    return value


def _num_id(value: str, label: str) -> str:
    if not _NUM_ID_RE.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid {label}: {value}")
    return value


def _season_type(value: str) -> str:
    if value not in _SEASON_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid season_type: {value}")
    return value


def _per_mode(value: str) -> str:
    if value not in _PER_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid per_mode: {value}")
    return value


def _measure_type(value: str) -> str:
    if value not in _MEASURE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid measure_type: {value}")
    return value


_measure_type_column_available: bool | None = None


def _measure_type_sql(alias: str = "", measure_type: str = "Base") -> str:
    """Filter by measure_type when staged; no-op until column exists in parquet.

    As of the 2026-08-19 restage this is permanently a no-op for the season tables:
    the advanced dash slices were folded in as COLUMNS rather than stacked as rows, so
    there is no `measure_type` column and every row is effectively Base + Advanced at
    once. Season TS_PCT / EFG_PCT / USG_PCT / PIE are readable as plain columns and
    need no measure filter. The probe is kept so the function stays correct if a table
    that does carry `measure_type` (lineups) is ever read through here.
    """
    global _measure_type_column_available
    if _measure_type_column_available is None:
        try:
            execute_query(get_connection(), "SELECT measure_type FROM player_season_stats LIMIT 0")
            _measure_type_column_available = True
        except Exception:
            _measure_type_column_available = False
    if not _measure_type_column_available:
        return "1=1"
    col = f"{alias}measure_type" if alias else "measure_type"
    mt = _measure_type(measure_type)
    if mt == "Base":
        return f"({col} = 'Base' OR {col} IS NULL)"
    return f"{col} = '{mt}'"


def _sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure JSON-safe values (no NaN/inf)."""
    out = df.replace({np.nan: None})
    for col in out.select_dtypes(include=[np.number]).columns:
        out[col] = out[col].replace([np.inf, -np.inf], None)
    return out


def _q(sql: str) -> list[dict[str, Any]]:
    _require_staging()
    conn = get_connection()
    normalized = validate_and_normalize_sql(sql)
    df = execute_query(conn, normalized)
    return _sanitize_df(df).to_dict(orient="records")


def _like_escape(value: str) -> str:
    return value.replace("'", "''")


def _ascii_fold(value: str) -> str:
    """Drop diacritics so a typed 'Doncic' can match the stored 'Dončić'."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _player_id_sql(pid: str, alias: str = "", col: str = "PLAYER_ID") -> str:
    """Match player id whether stored as int, float, or string in parquet."""
    col_name = f"{alias}{col}" if alias else col
    return f"FLOOR(TRY_CAST({col_name} AS DOUBLE)) = {int(pid)}"


def _season_label_sql(alias: str = "") -> str:
    prefix = f"{alias}" if alias else ""
    return f"COALESCE(NULLIF(TRIM({prefix}season), ''), NULLIF(TRIM({prefix}SEASON_YEAR), ''))"


def _normalize_game_id(game_id: str) -> str:
    gid = re.sub(r"\D", "", game_id).zfill(10)
    if len(gid) != 10:
        raise HTTPException(status_code=400, detail=f"Invalid game_id: {game_id}")
    return gid


def _player_adv_join_on(gl_alias: str = "gl.", adv_alias: str = "adv.") -> str:
    return (
        f"lpad(CAST({gl_alias}GAME_ID AS VARCHAR), 10, '0') "
        f"= lpad(CAST({adv_alias}game_id AS VARCHAR), 10, '0') "
        f"AND FLOOR(TRY_CAST({adv_alias}personId AS DOUBLE)) "
        f"= FLOOR(TRY_CAST({gl_alias}PLAYER_ID AS DOUBLE))"
    )


def _team_adv_join_on(gl_alias: str = "gl.", adv_alias: str = "adv.") -> str:
    return (
        f"lpad(CAST({gl_alias}GAME_ID AS VARCHAR), 10, '0') "
        f"= lpad(CAST({adv_alias}game_id AS VARCHAR), 10, '0') "
        f"AND CAST({gl_alias}TEAM_ID AS VARCHAR) "
        f"= CAST({adv_alias}teamId AS VARCHAR)"
    )


def _split_home_away_teams(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    away: dict[str, Any] | None = None
    home: dict[str, Any] | None = None
    for row in rows:
        matchup = str(row.get("MATCHUP") or row.get("matchup") or "")
        if "@" in matchup:
            away = row
        elif "vs" in matchup.lower():
            home = row
    if away is None or home is None:
        if len(rows) >= 2:
            return rows[0], rows[1]
        if len(rows) == 1:
            return rows[0], None
        return None, None
    return away, home


def _player_game_log_seasons(pid: str, season_type: str | None = "Regular Season") -> list[str]:
    season_expr = _season_label_sql()
    season_type_clause = (
        f"AND season_type = '{season_type}'" if season_type else ""
    )
    rows = _q(
        f"""
        SELECT DISTINCT {season_expr} AS season
        FROM player_game_logs
        WHERE {_player_id_sql(pid)}
          AND {season_expr} IS NOT NULL
          {season_type_clause}
        ORDER BY season DESC
        """
    )
    return [str(r["season"]) for r in rows if r.get("season")]


@router.get("/health")
def staging_health() -> dict[str, Any]:
    _require_staging()
    tables = list_registered_tables(get_connection())
    return {
        "success": True,
        "staging_dir": str(default_staging_dir()),
        "tables": tables,
    }


@router.post("/refresh")
def staging_refresh() -> dict[str, Any]:
    _require_staging()
    refresh_views()
    return {"success": True, "tables": list_registered_tables(get_connection())}


@router.get("/tables")
def staging_tables() -> dict[str, Any]:
    return {"success": True, "data": list_registered_tables(get_connection())}


@router.get("/seasons")
def list_seasons() -> dict[str, Any]:
    rows = _q(
        """
        SELECT DISTINCT season
        FROM player_season_stats
        WHERE season IS NOT NULL
        ORDER BY season DESC
        """
    )
    return {"success": True, "data": [r["season"] for r in rows]}


@router.get("/players/search")
def search_players(
    q: str = Query(..., min_length=2),
    season: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    # The vault stores names as NBA.com publishes them — "Dončić", "Jokić", "Šarić".
    # A plain ILIKE '%Doncic%' matches none of them, so the search box returned nothing
    # for the players people search for most, while the analyst (which folds accents in
    # `sql_builder._entity_filter`) found them fine. Fold both sides here too.
    term = _like_escape(_ascii_fold(q.strip()))
    if season and season.strip().lower() not in ("", "all"):
        season = _season(season)
        rows = _q(
            f"""
            SELECT DISTINCT PLAYER_ID, PLAYER_NAME, TEAM_ABBREVIATION, TEAM_ID
            FROM player_season_stats
            WHERE season = '{season}'
              AND season_type = 'Regular Season'
              AND per_mode = 'PerGame'
              AND {_measure_type_sql(measure_type="Base")}
              AND strip_accents(PLAYER_NAME) ILIKE '%{term}%'
            ORDER BY PLAYER_NAME
            LIMIT {int(limit)}
            """
        )
    else:
        rows = _q(
            f"""
            WITH matched AS (
                SELECT *
                FROM player_season_stats
                WHERE season_type = 'Regular Season'
                  AND per_mode = 'PerGame'
                  AND {_measure_type_sql(measure_type="Base")}
                  AND strip_accents(PLAYER_NAME) ILIKE '%{term}%'
            ),
            agg AS (
                SELECT
                    CAST(PLAYER_ID AS VARCHAR) AS PLAYER_ID,
                    MAX(PLAYER_NAME) AS PLAYER_NAME,
                    ARG_MAX(TEAM_ABBREVIATION, season) AS TEAM_ABBREVIATION,
                    ARG_MAX(TEAM_ID, season) AS TEAM_ID,
                    MIN(season) AS first_season,
                    MAX(season) AS last_season,
                    COUNT(DISTINCT season) AS season_count
                FROM matched
                GROUP BY CAST(PLAYER_ID AS VARCHAR)
            )
            SELECT
                PLAYER_ID,
                PLAYER_NAME,
                TEAM_ABBREVIATION,
                TEAM_ID,
                first_season,
                last_season,
                season_count
            FROM agg
            ORDER BY PLAYER_NAME
            LIMIT {int(limit)}
            """
        )
    return {"success": True, "data": rows}


@router.get("/players/{player_id}/season-stats")
def player_season_stats(
    player_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
    measure_type: str = "Base",
) -> dict[str, Any]:
    pid = _num_id(player_id, "player_id")
    season = _season(season)
    season_type = _season_type(season_type)
    per_mode = _per_mode(per_mode)
    measure_type = _measure_type(measure_type)
    rows = _q(
        f"""
        SELECT *
        FROM player_season_stats
        WHERE {_player_id_sql(pid)}
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = '{per_mode}'
          AND {_measure_type_sql(measure_type=measure_type)}
        LIMIT 1
        """
    )
    return {"success": True, "data": rows[0] if rows else None}


@router.get("/players/{player_id}/impact-profile")
def player_impact_profile(
    player_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """NBA-native composite label from Advanced + estimated metrics (not DARKO/EPM)."""
    pid = _num_id(player_id, "player_id")
    season = _season(season)
    season_type = _season_type(season_type)
    try:
        adv_rows = _q(
            f"""
            SELECT PIE, NET_RATING, USG_PCT, OFF_RATING, DEF_RATING, GP, PLAYER_NAME, TEAM_ABBREVIATION
            FROM player_season_stats
            WHERE {_player_id_sql(pid)}
              AND season = '{season}'
              AND season_type = '{season_type}'
              AND per_mode = 'PerGame'
              AND measure_type = 'Advanced'
            LIMIT 1
            """
        )
    except Exception:
        adv_rows = []
    try:
        est_rows = _q(
            f"""
            SELECT E_NET_RATING, E_OFF_RATING, E_DEF_RATING, E_USG_PCT, GP, PLAYER_NAME
            FROM player_estimated_metrics
            WHERE {_player_id_sql(pid)}
              AND season = '{season}'
              AND season_type = '{season_type}'
            LIMIT 1
            """
        )
    except Exception:
        est_rows = []
    adv = adv_rows[0] if adv_rows else {}
    est = est_rows[0] if est_rows else {}
    profile = player_impact_label(
        net_rating=est.get("E_NET_RATING") or adv.get("NET_RATING"),
        usg_pct=est.get("E_USG_PCT") or adv.get("USG_PCT"),
        pie=adv.get("PIE"),
        gp=adv.get("GP") or est.get("GP"),
    )
    profile["player_id"] = pid
    profile["season"] = season
    profile["season_type"] = season_type
    profile["player_name"] = adv.get("PLAYER_NAME") or est.get("PLAYER_NAME")
    profile["team_abbr"] = adv.get("TEAM_ABBREVIATION")
    profile["e_net_rating"] = est.get("E_NET_RATING")
    return {"success": True, "data": profile}


@router.get("/players/{player_id}/game-log-seasons")
def player_game_log_seasons(
    player_id: str,
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """Distinct seasons with game logs for this player (newest first)."""
    pid = _num_id(player_id, "player_id")
    season_type = _season_type(season_type)
    seasons = _player_game_log_seasons(pid, season_type)
    return {
        "success": True,
        "data": seasons,
        "meta": {"season_type": season_type, "count": len(seasons)},
    }


_GAME_LOG_LIST_COLS = """
    gl.PLAYER_ID, gl.PLAYER_NAME, gl.GAME_ID, gl.GAME_DATE, gl.MATCHUP, gl.WL,
    gl.MIN, gl.PTS, gl.FGM, gl.FGA, gl.FG_PCT, gl.FG3M, gl.FG3A, gl.FG3_PCT,
    gl.FTM, gl.FTA, gl.FT_PCT, gl.OREB, gl.DREB, gl.REB, gl.AST,
    gl.STL, gl.BLK, gl.TOV, gl.PF, gl.PLUS_MINUS,
    gl.TEAM_ABBREVIATION, gl.season, gl.season_type, gl.SEASON_YEAR
"""

_ADV_GAME_LOG_COLS = """
    adv.offensiveRating,
    adv.defensiveRating,
    adv.netRating,
    adv.trueShootingPercentage,
    adv.effectiveFieldGoalPercentage,
    adv.usagePercentage,
    adv.PIE,
    adv.pacePer40,
    adv.estimatedPace,
    adv.assistPercentage,
    adv.assistToTurnover,
    adv.assistRatio,
    adv.offensiveReboundPercentage,
    adv.defensiveReboundPercentage,
    adv.reboundPercentage,
    adv.turnoverRatio,
    adv.hustle_contestedShots,
    adv.hustle_contestedShots2pt,
    adv.hustle_contestedShots3pt,
    adv.hustle_deflections,
    adv.hustle_chargesDrawn,
    adv.hustle_screenAssists,
    adv.hustle_screenAssistPoints,
    adv.hustle_looseBallsRecoveredOffensive,
    adv.hustle_looseBallsRecoveredDefensive,
    adv.hustle_looseBallsRecoveredTotal,
    adv.hustle_offensiveBoxOuts,
    adv.hustle_defensiveBoxOuts,
    adv.hustle_boxOutPlayerTeamRebounds,
    adv.hustle_boxOutPlayerRebounds,
    adv.hustle_boxOuts
"""


@router.get("/players/{player_id}/game-logs")
def player_game_logs(
    player_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    limit: int = Query(500, ge=1, le=500),
    include_advanced: bool = Query(True),
) -> dict[str, Any]:
    pid = _num_id(player_id, "player_id")
    season = _season(season)
    season_type = _season_type(season_type)
    season_expr = _season_label_sql("gl.")
    where = (
        f"{_player_id_sql(pid, 'gl.')} "
        f"AND {season_expr} = '{season}' "
        f"AND gl.season_type = '{season_type}'"
    )
    join_sql = f"""
        SELECT
            {_GAME_LOG_LIST_COLS},
            {_ADV_GAME_LOG_COLS}
        FROM player_game_logs gl
        LEFT JOIN player_game_advanced adv
          ON {_player_adv_join_on()}
        WHERE {where}
        ORDER BY gl.GAME_DATE DESC
        LIMIT {int(limit)}
        """
    basic_sql = f"""
        SELECT {_GAME_LOG_LIST_COLS}
        FROM player_game_logs gl
        WHERE {where}
        ORDER BY gl.GAME_DATE DESC
        LIMIT {int(limit)}
        """
    if include_advanced:
        try:
            rows = _q(join_sql)
        except Exception:
            rows = _q(basic_sql)
    else:
        rows = _q(basic_sql)
    return {
        "success": True,
        "data": rows,
        "meta": {
            "season": season,
            "season_type": season_type,
            "count": len(rows),
            "include_advanced": include_advanced,
        },
    }


@router.get("/players/{player_id}/game-log/{game_id}")
def player_game_log_single(player_id: str, game_id: str) -> dict[str, Any]:
    """Single player game log row (+ advanced when staged)."""
    pid = _num_id(player_id, "player_id")
    gid = _normalize_game_id(game_id)
    where = (
        f"{_player_id_sql(pid, 'gl.')} "
        f"AND lpad(CAST(gl.GAME_ID AS VARCHAR), 10, '0') = '{gid}'"
    )
    join_sql = f"""
        SELECT
            gl.*,
            adv.offensiveRating,
            adv.defensiveRating,
            adv.netRating,
            adv.trueShootingPercentage,
            adv.effectiveFieldGoalPercentage,
            adv.usagePercentage,
            adv.PIE,
            adv.pacePer40,
            adv.estimatedPace,
            adv.assistPercentage,
            adv.assistToTurnover,
            adv.assistRatio,
            adv.offensiveReboundPercentage,
            adv.defensiveReboundPercentage,
            adv.reboundPercentage,
            adv.turnoverRatio,
            adv.hustle_contestedShots,
            adv.hustle_contestedShots2pt,
            adv.hustle_contestedShots3pt,
            adv.hustle_deflections,
            adv.hustle_chargesDrawn,
            adv.hustle_screenAssists,
            adv.hustle_screenAssistPoints,
            adv.hustle_looseBallsRecoveredOffensive,
            adv.hustle_looseBallsRecoveredDefensive,
            adv.hustle_looseBallsRecoveredTotal,
            adv.hustle_offensiveBoxOuts,
            adv.hustle_defensiveBoxOuts,
            adv.hustle_boxOutPlayerTeamRebounds,
            adv.hustle_boxOutPlayerRebounds,
            adv.hustle_boxOuts
        FROM player_game_logs gl
        LEFT JOIN player_game_advanced adv
          ON {_player_adv_join_on()}
        WHERE {where}
        LIMIT 1
        """
    basic_sql = f"""
        SELECT *
        FROM player_game_logs gl
        WHERE {where}
        LIMIT 1
        """
    try:
        rows = _q(join_sql)
    except Exception:
        rows = _q(basic_sql)
    return {"success": True, "data": rows[0] if rows else None, "meta": {"game_id": gid}}


_ADV_PLAYER_COLS = """
            adv.offensiveRating,
            adv.defensiveRating,
            adv.netRating,
            adv.trueShootingPercentage,
            adv.effectiveFieldGoalPercentage,
            adv.usagePercentage,
            adv.PIE,
            adv.pacePer40,
            adv.estimatedPace,
            adv.assistPercentage,
            adv.assistToTurnover,
            adv.assistRatio,
            adv.offensiveReboundPercentage,
            adv.defensiveReboundPercentage,
            adv.reboundPercentage,
            adv.turnoverRatio,
            adv.hustle_contestedShots,
            adv.hustle_contestedShots2pt,
            adv.hustle_contestedShots3pt,
            adv.hustle_deflections,
            adv.hustle_chargesDrawn,
            adv.hustle_screenAssists,
            adv.hustle_screenAssistPoints,
            adv.hustle_looseBallsRecoveredOffensive,
            adv.hustle_looseBallsRecoveredDefensive,
            adv.hustle_looseBallsRecoveredTotal,
            adv.hustle_offensiveBoxOuts,
            adv.hustle_defensiveBoxOuts,
            adv.hustle_boxOutPlayerTeamRebounds,
            adv.hustle_boxOutPlayerRebounds,
            adv.hustle_boxOuts
"""


@router.get("/games/{game_id}/summary")
def game_summary(game_id: str) -> dict[str, Any]:
    """Final score, quarter lines, and metadata from phase-2/3 staging."""
    gid = _normalize_game_id(game_id)
    teams = _q(
        f"""
        SELECT *
        FROM team_game_logs
        WHERE lpad(CAST(GAME_ID AS VARCHAR), 10, '0') = '{gid}'
        """
    )
    if not teams:
        return {"success": True, "data": None, "meta": {"game_id": gid}}

    away_row, home_row = _split_home_away_teams(teams)
    if not away_row or not home_row:
        return {"success": True, "data": None, "meta": {"game_id": gid}}

    line_rows = _q(
        f"""
        SELECT teamTricode, period1Score, period2Score, period3Score, period4Score
        FROM game_context
        WHERE game_id = '{gid}' AND dataset = '4'
        """
    )
    lines_by_abbr = {
        str(r.get("teamTricode") or "").upper(): r for r in line_rows
    }

    def _line_for(abbr: str) -> dict[str, Any]:
        row = lines_by_abbr.get(abbr.upper(), {})
        out: dict[str, Any] = {}
        for i, key in enumerate(
            ("period1Score", "period2Score", "period3Score", "period4Score"),
            start=1,
        ):
            val = row.get(key)
            if val is not None and str(val) not in ("", "nan"):
                out[f"q{i}"] = val
        return out

    away_abbr = str(away_row.get("TEAM_ABBREVIATION") or "")
    home_abbr = str(home_row.get("TEAM_ABBREVIATION") or "")
    game_date = away_row.get("GAME_DATE") or home_row.get("GAME_DATE")

    return {
        "success": True,
        "data": {
            "game_id": gid,
            "game_date": game_date,
            "status": "Final",
            "away": {
                "abbr": away_abbr,
                "score": away_row.get("PTS"),
                "wl": away_row.get("WL"),
                "line": _line_for(away_abbr),
            },
            "home": {
                "abbr": home_abbr,
                "score": home_row.get("PTS"),
                "wl": home_row.get("WL"),
                "line": _line_for(home_abbr),
            },
        },
        "meta": {"game_id": gid},
    }


@router.get("/games/{game_id}/box-score")
def game_box_score(game_id: str) -> dict[str, Any]:
    """Full game box score: player logs + phase-3 advanced, team totals."""
    gid = _normalize_game_id(game_id)
    player_sql = f"""
        SELECT
            gl.*,
            {_ADV_PLAYER_COLS}
        FROM player_game_logs gl
        LEFT JOIN player_game_advanced adv
          ON {_player_adv_join_on()}
        WHERE lpad(CAST(gl.GAME_ID AS VARCHAR), 10, '0') = '{gid}'
        ORDER BY gl.TEAM_ABBREVIATION, CAST(gl.PTS AS DOUBLE) DESC NULLS LAST
        """
    basic_sql = f"""
        SELECT *
        FROM player_game_logs gl
        WHERE lpad(CAST(gl.GAME_ID AS VARCHAR), 10, '0') = '{gid}'
        ORDER BY gl.TEAM_ABBREVIATION, CAST(gl.PTS AS DOUBLE) DESC NULLS LAST
        """
    try:
        players = _q(player_sql)
    except Exception:
        players = _q(basic_sql)

    team_log_sql = f"""
        SELECT *
        FROM team_game_logs
        WHERE lpad(CAST(GAME_ID AS VARCHAR), 10, '0') = '{gid}'
        """
    team_logs = _q(team_log_sql)

    team_adv_sql = f"""
        SELECT *
        FROM team_game_advanced
        WHERE lpad(CAST(game_id AS VARCHAR), 10, '0') = '{gid}'
        """
    try:
        team_adv = _q(team_adv_sql)
    except Exception:
        team_adv = []

    adv_by_abbr = {
        str(r.get("teamTricode") or "").upper(): r for r in team_adv
    }
    team_totals: dict[str, Any] = {}
    for row in team_logs:
        abbr = str(row.get("TEAM_ABBREVIATION") or "").upper()
        merged = {**row, **(adv_by_abbr.get(abbr) or {})}
        team_totals[abbr] = merged

    return {
        "success": True,
        "data": {
            "players": players,
            "team_totals": team_totals,
        },
        "meta": {"game_id": gid, "player_count": len(players)},
    }


@router.get("/players/{player_id}/season-trends")
def player_season_trends(
    player_id: str,
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """Per-season per-game stat lines for career trend charts (oldest → newest)."""
    pid = _num_id(player_id, "player_id")
    season_type = _season_type(season_type)
    rows = _q(
        f"""
        SELECT season, PTS, AST, REB, STL, BLK, GP, TEAM_ABBREVIATION
        FROM player_season_stats
        WHERE {_player_id_sql(pid)}
          AND season_type = '{season_type}'
          AND per_mode = 'PerGame'
          AND {_measure_type_sql(measure_type="Base")}
        ORDER BY season ASC
        """
    )
    return {"success": True, "data": rows, "meta": {"count": len(rows)}}


@router.get("/players/{player_id}/career")
def player_career(player_id: str) -> dict[str, Any]:
    pid = _num_id(player_id, "player_id")
    rows = _q(
        f"""
        SELECT *
        FROM player_career
        WHERE FLOOR(TRY_CAST(player_id AS DOUBLE)) = {int(pid)}
        ORDER BY dataset
        """
    )
    return {"success": True, "data": rows}


@router.get("/players/{player_id}/shot-zones")
def player_shot_zones(
    player_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
) -> dict[str, Any]:
    pid = _num_id(player_id, "player_id")
    season = _season(season)
    season_type = _season_type(season_type)
    per_mode = _per_mode(per_mode)
    rows = _q(
        f"""
        SELECT *
        FROM player_shot_zones
        WHERE {_player_id_sql(pid, col="player_id")}
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = '{per_mode}'
        LIMIT 1
        """
    )
    return {"success": True, "data": rows[0] if rows else None}


@router.get("/players/{player_id}/court-shots")
def player_court_shots(
    player_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    pid = _num_id(player_id, "player_id")
    season = _season(season)
    season_type = _season_type(season_type)
    rows = _q(
        f"""
        SELECT *
        FROM court_shots
        WHERE {_player_id_sql(pid, col="player_id")}
          AND season = '{season}'
          AND season_type = '{season_type}'
        """
    )
    return {"success": True, "data": rows}


@router.get("/teams/by-abbr/{abbr}/id")
def team_id_by_abbr(abbr: str) -> dict[str, Any]:
    code = abbr.strip().upper().replace("'", "")
    if len(code) != 3:
        raise HTTPException(status_code=400, detail="Team abbr must be 3 letters")
    rows = _q(
        f"""
        SELECT TEAM_ID, TEAM_ABBREVIATION, TEAM_NAME
        FROM team_season_stats
        WHERE TEAM_ABBREVIATION = '{code}'
          AND {_measure_type_sql(measure_type="Base")}
        ORDER BY season DESC
        LIMIT 1
        """
    )
    return {"success": True, "data": rows[0] if rows else None}


@router.get("/teams/{team_id}/season-stats")
def team_season_stats(
    team_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
    measure_type: str = "Base",
) -> dict[str, Any]:
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    per_mode = _per_mode(per_mode)
    measure_type = _measure_type(measure_type)
    rows = _q(
        f"""
        SELECT *
        FROM team_season_stats
        WHERE TEAM_ID = {tid}
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = '{per_mode}'
          AND {_measure_type_sql(measure_type=measure_type)}
        LIMIT 1
        """
    )
    return {"success": True, "data": rows[0] if rows else None}


def _team_season_list(tid: str, season_type: str) -> list[str]:
    rows = _q(
        f"""
        SELECT DISTINCT season
        FROM (
            SELECT season
            FROM team_game_logs
            WHERE CAST(TEAM_ID AS VARCHAR) = '{tid}'
              AND season_type = '{season_type}'
            UNION
            SELECT season
            FROM team_standings
            WHERE TeamID = {tid}
              AND season_type = '{season_type}'
            UNION
            SELECT season
            FROM team_season_stats
            WHERE TEAM_ID = {tid}
              AND season_type = '{season_type}'
        ) AS seasons_union
        WHERE season IS NOT NULL
          AND TRIM(season) != ''
        ORDER BY season DESC
        """
    )
    return [str(r["season"]) for r in rows if r.get("season")]


@router.get("/teams/{team_id}/game-log-seasons")
def team_game_log_seasons(
    team_id: str,
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """Distinct seasons for this team (newest first)."""
    tid = _num_id(team_id, "team_id")
    season_type = _season_type(season_type)
    seasons = _team_season_list(tid, season_type)
    return {
        "success": True,
        "data": seasons,
        "meta": {"season_type": season_type, "count": len(seasons)},
    }


@router.get("/teams/{team_id}/seasons")
def team_seasons(
    team_id: str,
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """All distinct seasons for this team (logs + standings + season stats)."""
    tid = _num_id(team_id, "team_id")
    season_type = _season_type(season_type)
    seasons = _team_season_list(tid, season_type)
    return {
        "success": True,
        "data": seasons,
        "meta": {"season_type": season_type, "count": len(seasons)},
    }


@router.get("/teams/{team_id}/season-history")
def team_season_history(
    team_id: str,
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
) -> dict[str, Any]:
    """Franchise season-by-season averages (1996–present when staged)."""
    tid = _num_id(team_id, "team_id")
    season_type = _season_type(season_type)
    per_mode = _per_mode(per_mode)
    rows = _q(
        f"""
        SELECT season, W, L, PTS, REB, AST, FG_PCT, FG3_PCT
        FROM team_season_stats
        WHERE TEAM_ID = {tid}
          AND season_type = '{season_type}'
          AND per_mode = '{per_mode}'
          AND {_measure_type_sql(measure_type="Base")}
        ORDER BY season DESC
        """
    )
    return {"success": True, "data": rows, "meta": {"count": len(rows)}}


@router.get("/teams/{team_id}/roster")
def team_roster(
    team_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """Players on the team for a season (from player_season_stats)."""
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    rows = _q(
        f"""
        SELECT PLAYER_ID, PLAYER_NAME, GP, MIN, PTS, REB, AST
        FROM player_season_stats
        WHERE TEAM_ID = {tid}
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = 'PerGame'
          AND {_measure_type_sql(measure_type="Base")}
        ORDER BY MIN DESC NULLS LAST, PTS DESC NULLS LAST
        """
    )
    return {
        "success": True,
        "data": rows,
        "meta": {"season": season, "season_type": season_type, "count": len(rows)},
    }


@router.get("/teams/{team_id}/shot-zones")
def team_shot_zones(
    team_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
) -> dict[str, Any]:
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    per_mode = _per_mode(per_mode)
    rows = _q(
        f"""
        SELECT *
        FROM team_shot_zones
        WHERE CAST(team_id AS VARCHAR) = '{tid}'
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = '{per_mode}'
        LIMIT 1
        """
    )
    return {"success": True, "data": rows[0] if rows else None}


@router.get("/teams/{team_id}/game-logs")
def team_game_logs(
    team_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    limit: int = Query(82, ge=1, le=500),
    include_advanced: bool = Query(False),
) -> dict[str, Any]:
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    where = (
        f"CAST(gl.TEAM_ID AS VARCHAR) = '{tid}' "
        f"AND gl.season = '{season}' "
        f"AND gl.season_type = '{season_type}'"
    )
    basic_sql = f"""
        SELECT gl.*
        FROM team_game_logs gl
        WHERE {where}
        ORDER BY gl.GAME_DATE DESC
        LIMIT {int(limit)}
        """
    join_sql = f"""
        SELECT
            gl.*,
            adv.offensiveRating,
            adv.defensiveRating,
            adv.netRating,
            adv.trueShootingPercentage,
            adv.effectiveFieldGoalPercentage,
            adv.usagePercentage,
            adv.PIE,
            adv.pacePer40,
            adv.estimatedPace,
            adv.assistPercentage,
            adv.assistToTurnover,
            adv.assistRatio,
            adv.offensiveReboundPercentage,
            adv.defensiveReboundPercentage,
            adv.reboundPercentage,
            adv.turnoverRatio
        FROM team_game_logs gl
        LEFT JOIN team_game_advanced adv
          ON {_team_adv_join_on()}
        WHERE {where}
        ORDER BY gl.GAME_DATE DESC
        LIMIT {int(limit)}
        """
    if include_advanced:
        try:
            rows = _q(join_sql)
        except Exception:
            rows = _q(basic_sql)
    else:
        rows = _q(basic_sql)
    return {
        "success": True,
        "data": rows,
        "meta": {
            "season": season,
            "season_type": season_type,
            "count": len(rows),
            "include_advanced": include_advanced,
        },
    }


@router.get("/teams/{team_id}/all-time-record")
def team_all_time_record(
    team_id: str,
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """Sum wins/losses across all staged seasons in team_standings."""
    tid = _num_id(team_id, "team_id")
    season_type = _season_type(season_type)
    rows = _q(
        f"""
        SELECT
            COALESCE(SUM(WINS), 0) AS total_wins,
            COALESCE(SUM(LOSSES), 0) AS total_losses,
            COUNT(*) AS seasons_count
        FROM team_standings
        WHERE TeamID = {tid}
          AND season_type = '{season_type}'
        """
    )
    row = rows[0] if rows else {"total_wins": 0, "total_losses": 0, "seasons_count": 0}
    return {"success": True, "data": row}


@router.get("/teams/{team_id}/best-player")
def team_best_player(
    team_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    min_gp: int = Query(10, ge=1, le=82),
) -> dict[str, Any]:
    """Top player on the team by Hollinger game score (PerGame season line)."""
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    gs_expr = (
        "PTS + 0.4 * FGM - 0.7 * FGA - 0.4 * (FTA - FTM) "
        "+ 0.7 * OREB + 0.3 * DREB + STL + 0.7 * AST + 0.7 * BLK "
        "- 0.4 * PF - TOV"
    )
    rows = _q(
        f"""
        SELECT
            PLAYER_ID,
            PLAYER_NAME,
            GP,
            ({gs_expr}) AS game_score
        FROM player_season_stats
        WHERE TEAM_ID = {tid}
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = 'PerGame'
          AND {_measure_type_sql(measure_type="Base")}
          AND GP >= {int(min_gp)}
        ORDER BY game_score DESC NULLS LAST
        LIMIT 1
        """
    )
    return {
        "success": True,
        "data": rows[0] if rows else None,
        "meta": {"season": season, "season_type": season_type, "min_gp": min_gp},
    }


@router.get("/teams/{team_id}/standings")
def team_standings(
    team_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    rows = _q(
        f"""
        SELECT
            Record,
            PlayoffRank,
            Conference,
            WINS,
            LOSSES,
            season,
            season_type
        FROM team_standings
        WHERE TeamID = {tid}
          AND season = '{season}'
          AND season_type = '{season_type}'
        LIMIT 1
        """
    )
    return {"success": True, "data": rows[0] if rows else None}


_LEADER_STAT_EXPR: dict[str, str] = {
    "PTS": "PTS",
    "REB": "REB",
    "AST": "AST",
    "STL": "STL",
    "BLK": "BLK",
    "FG3M": "FG3M",
    "TOV": "TOV",
    "MIN": "MIN",
    "FG_PCT": "FG_PCT",
    "FG3_PCT": "FG3_PCT",
    "TS_PCT": (
        "CASE WHEN (FGA + 0.44 * FTA) > 0 "
        "THEN PTS / (2.0 * (FGA + 0.44 * FTA)) ELSE NULL END"
    ),
}

_LEADER_STAT_PATTERN = "^(" + "|".join(_LEADER_STAT_EXPR.keys()) + ")$"


@router.get("/teams/{team_id}/leaders")
def team_season_leaders(
    team_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    stat: str = Query("PTS", pattern=_LEADER_STAT_PATTERN),
    min_gp: int = Query(10, ge=1, le=82),
) -> dict[str, Any]:
    """Top players on a team for a per-game stat (player_season_stats)."""
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    stat_key = stat.upper()
    expr = _LEADER_STAT_EXPR[stat_key]
    value_sql = expr if expr.isidentifier() else f"({expr})"
    rows = _q(
        f"""
        SELECT
            PLAYER_ID,
            PLAYER_NAME,
            TEAM_ABBREVIATION,
            {value_sql} AS value
        FROM player_season_stats
        WHERE TEAM_ID = {tid}
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = 'PerGame'
          AND {_measure_type_sql(measure_type="Base")}
          AND GP >= {int(min_gp)}
        ORDER BY value DESC NULLS LAST
        LIMIT 5
        """
    )
    return {
        "success": True,
        "data": rows,
        "meta": {"stat": stat_key, "min_gp": min_gp},
    }


@router.get("/league/leaders")
def league_season_leaders(
    season: str = "2022-23",
    season_type: str = "Regular Season",
    stat: str = Query("PTS", pattern=_LEADER_STAT_PATTERN),
    min_gp: int = Query(20, ge=1, le=82),
    limit: int = Query(10, ge=1, le=25),
    highlight_player_id: str | None = None,
) -> dict[str, Any]:
    """League-wide per-game leaders for a season (player_season_stats)."""
    season = _season(season)
    season_type = _season_type(season_type)
    stat_key = stat.upper()
    expr = _LEADER_STAT_EXPR[stat_key]
    value_sql = expr if expr.isidentifier() else f"({expr})"
    base_where = f"""
        season = '{season}'
        AND season_type = '{season_type}'
        AND per_mode = 'PerGame'
        AND {_measure_type_sql(measure_type="Base")}
        AND GP >= {int(min_gp)}
    """
    rows = _q(
        f"""
        SELECT
            PLAYER_ID,
            PLAYER_NAME,
            TEAM_ABBREVIATION,
            {value_sql} AS value
        FROM player_season_stats
        WHERE {base_where}
        ORDER BY value DESC NULLS LAST
        LIMIT {int(limit)}
        """
    )
    if highlight_player_id:
        hid = int(_num_id(highlight_player_id, "highlight_player_id"))
        seen = {
            int(float(r["PLAYER_ID"]))
            for r in rows
            if r.get("PLAYER_ID") is not None
        }
        if hid not in seen:
            extra = _q(
                f"""
                SELECT
                    PLAYER_ID,
                    PLAYER_NAME,
                    TEAM_ABBREVIATION,
                    {value_sql} AS value
                FROM player_season_stats
                WHERE {_player_id_sql(hid)}
                  AND {base_where}
                LIMIT 1
                """
            )
            if extra:
                rows = sorted(
                    [*rows, *extra],
                    key=lambda r: float(r.get("value") or 0),
                    reverse=True,
                )[: int(limit)]
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return {
        "success": True,
        "data": rows,
        "meta": {
            "season": season,
            "season_type": season_type,
            "stat": stat_key,
            "min_gp": min_gp,
            "limit": limit,
        },
    }


def _leader_value_sql(stat_key: str) -> str:
    expr = _LEADER_STAT_EXPR[stat_key.upper()]
    return expr if expr.isidentifier() else f"({expr})"


@router.get("/league/scatter")
def league_scatter(
    season: str = "2023-24",
    season_type: str = "Regular Season",
    x_stat: str = Query("MIN", pattern=_LEADER_STAT_PATTERN),
    y_stat: str = Query("PTS", pattern=_LEADER_STAT_PATTERN),
    min_gp: int = Query(20, ge=1, le=82),
    limit: int = Query(500, ge=1, le=750),
) -> dict[str, Any]:
    """League scatter rows for dashboard-style Scatter charts (player_name, x_value, y_value)."""
    season = _season(season)
    season_type = _season_type(season_type)
    x_key = x_stat.upper()
    y_key = y_stat.upper()
    x_sql = _leader_value_sql(x_key)
    y_sql = _leader_value_sql(y_key)
    rows = _q(
        f"""
        SELECT
            PLAYER_NAME AS player_name,
            {x_sql} AS x_value,
            {y_sql} AS y_value,
            PLAYER_ID
        FROM player_season_stats
        WHERE season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = 'PerGame'
          AND {_measure_type_sql(measure_type="Base")}
          AND GP >= {int(min_gp)}
          AND {x_sql} IS NOT NULL
          AND {y_sql} IS NOT NULL
        ORDER BY {y_sql} DESC NULLS LAST
        LIMIT {int(limit)}
        """
    )
    return {
        "success": True,
        "data": rows,
        "meta": {
            "season": season,
            "season_type": season_type,
            "x_stat": x_key,
            "y_stat": y_key,
            "min_gp": min_gp,
            "limit": limit,
        },
    }


# ==========================================================================
# Phase 7-9 tables — bio, awards, franchise history, coordinate shot charts.
#
# These are the reads that let the prototype drop its mock modules: accolades,
# franchise facts, jersey numbers and real shot coordinates all existed only as
# hand-written fixtures because there was no endpoint to fetch them.
# ==========================================================================

_HEIGHT_RE = re.compile(r"^(\d+)-(\d+)$")


def _height_inches(value: Any) -> int | None:
    """'6-4' -> 76. HEIGHT is stored as a feet-dash-inches string, so it does not
    sort or compare numerically without this."""
    m = _HEIGHT_RE.match(str(value or "").strip())
    if not m:
        return None
    return int(m.group(1)) * 12 + int(m.group(2))


@router.get("/players/{player_id}/bio")
def player_bio(player_id: str) -> dict[str, Any]:
    """Physical / draft / origin profile for one player (player_bio)."""
    pid = _num_id(player_id, "player_id")
    rows = _q(
        f"""
        SELECT *
        FROM player_bio
        WHERE {_player_id_sql(pid, col="PERSON_ID")}
        LIMIT 1
        """
    )
    if not rows:
        return {"success": True, "data": None}
    row = rows[0]
    row["HEIGHT_INCHES"] = _height_inches(row.get("HEIGHT"))
    return {"success": True, "data": row}


# Weekly and monthly honours outnumber every career award combined (1,396 Player
# of the Week rows against 37 MVPs), so a profile that lists them un-grouped reads
# as noise. They are still returned — just flagged so the UI can fold them away.
_PERIODIC_AWARDS = (
    "NBA Player of the Week",
    "NBA Player of the Month",
    "NBA Rookie of the Month",
    "NBA Defensive Player of the Month",
)


@router.get("/players/{player_id}/awards")
def player_awards(
    player_id: str,
    season: str | None = None,
    include_periodic: bool = Query(True),
) -> dict[str, Any]:
    """Accolades for one player, plus a per-award-type count summary."""
    pid = _num_id(player_id, "player_id")
    where = [_player_id_sql(pid, col="PERSON_ID")]
    if season:
        where.append(f"TRIM(SEASON) = '{_like_escape(_season(season))}'")
    if not include_periodic:
        joined = ", ".join(f"'{_like_escape(a)}'" for a in _PERIODIC_AWARDS)
        where.append(f"DESCRIPTION NOT IN ({joined})")

    rows = _q(
        f"""
        SELECT PERSON_ID, PLAYER_NAME, TEAM, DESCRIPTION, SEASON,
               ALL_NBA_TEAM_NUMBER, CONFERENCE, MONTH, WEEK
        FROM player_awards
        WHERE {' AND '.join(where)}
        ORDER BY SEASON DESC, DESCRIPTION
        """
    )

    summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        desc = str(row.get("DESCRIPTION") or "").strip()
        if not desc:
            continue
        entry = summary.setdefault(
            desc,
            {"description": desc, "count": 0, "seasons": [], "periodic": desc in _PERIODIC_AWARDS},
        )
        entry["count"] += 1
        label = str(row.get("SEASON") or "").strip()
        if label and label not in entry["seasons"]:
            entry["seasons"].append(label)

    ordered = sorted(
        summary.values(),
        key=lambda e: (e["periodic"], -e["count"], e["description"]),
    )
    return {
        "success": True,
        "data": rows,
        "summary": ordered,
        "meta": {"count": len(rows), "season": season, "include_periodic": include_periodic},
    }


@router.get("/teams/{team_id}/franchise")
def team_franchise(team_id: str) -> dict[str, Any]:
    """Franchise history rows for a team id.

    nba.com returns one row per franchise ERA (Charlotte 1610612766 has a Hornets
    row, a Bobcats row and a second Hornets row), so the caller gets both the era
    detail and the franchise-wide roll-up rather than one arbitrary row.
    """
    tid = _num_id(team_id, "team_id")
    rows = _q(
        f"""
        SELECT *
        FROM franchise_history
        WHERE CAST(TEAM_ID AS VARCHAR) = '{tid}'
        ORDER BY TRY_CAST(START_YEAR AS INTEGER)
        """
    )
    if not rows:
        return {"success": True, "data": None, "eras": []}

    def _years(row: dict[str, Any]) -> float:
        try:
            return float(row.get("YEARS") or 0)
        except (TypeError, ValueError):
            return 0.0

    # The widest span is the franchise-wide row; narrower rows are the individual
    # name eras nested inside it.
    overall = max(rows, key=_years)
    eras = [r for r in rows if r is not overall]
    return {"success": True, "data": overall, "eras": eras, "meta": {"count": len(rows)}}


@router.get("/players/{player_id}/shot-chart")
def player_shot_chart(
    player_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    game_id: str | None = None,
    limit: int = Query(3000, ge=1, le=8000),
) -> dict[str, Any]:
    """Per-shot LOC_X / LOC_Y for one player-season (player_shot_chart).

    Distinct from `/court-shots`, which reads the zone-grid `court_shots` table and
    has no coordinates at all.
    """
    pid = _num_id(player_id, "player_id")
    season = _season(season)
    season_type = _season_type(season_type)
    where = [
        _player_id_sql(pid, col="PLAYER_ID"),
        f"season = '{season}'",
        f"season_type = '{season_type}'",
    ]
    if game_id:
        where.append(f"GAME_ID = '{_like_escape(_normalize_game_id(game_id))}'")

    rows = _q(
        f"""
        SELECT GAME_ID, GAME_DATE, PERIOD, MINUTES_REMAINING, SECONDS_REMAINING,
               ACTION_TYPE, SHOT_TYPE, SHOT_ZONE_BASIC, SHOT_ZONE_AREA,
               SHOT_ZONE_RANGE, SHOT_DISTANCE, LOC_X, LOC_Y, SHOT_MADE_FLAG
        FROM player_shot_chart
        WHERE {' AND '.join(where)}
        ORDER BY GAME_DATE, GAME_EVENT_ID
        LIMIT {int(limit)}
        """
    )
    made = sum(1 for r in rows if r.get("SHOT_MADE_FLAG") == 1)
    return {
        "success": True,
        "data": rows,
        "meta": {
            "season": season,
            "season_type": season_type,
            "game_id": game_id,
            "attempts": len(rows),
            "made": made,
            "fg_pct": round(made / len(rows), 4) if rows else None,
            "truncated": len(rows) >= limit,
        },
    }


@router.get("/players/{player_id}/shot-chart-seasons")
def player_shot_chart_seasons(
    player_id: str,
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """Seasons for which this player has coordinate shot data."""
    pid = _num_id(player_id, "player_id")
    season_type = _season_type(season_type)
    rows = _q(
        f"""
        SELECT season, COUNT(*) AS attempts
        FROM player_shot_chart
        WHERE {_player_id_sql(pid, col="PLAYER_ID")}
          AND season_type = '{season_type}'
        GROUP BY season
        ORDER BY season DESC
        """
    )
    return {"success": True, "data": rows}


@router.get("/teams/{team_id}/roster-detail")
def team_roster_detail(
    team_id: str,
    season: str = "2024-25",
) -> dict[str, Any]:
    """Roster with jersey number, position and physicals (team_roster), joined to
    the season box-score line so one call fills the whole roster table."""
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    rows = _q(
        f"""
        SELECT
            r.PLAYER_ID,
            r.PLAYER          AS PLAYER_NAME,
            r.NUM,
            r.POSITION,
            r.HEIGHT,
            r.WEIGHT,
            r.AGE,
            r.EXP,
            r.SCHOOL,
            r.HOW_ACQUIRED,
            s.GP, s.MIN, s.PTS, s.REB, s.AST
        FROM team_roster r
        LEFT JOIN player_season_stats s
               ON FLOOR(TRY_CAST(s.PLAYER_ID AS DOUBLE)) = FLOOR(TRY_CAST(r.PLAYER_ID AS DOUBLE))
              AND s.season = r.season
              AND s.season_type = 'Regular Season'
              AND s.per_mode = 'PerGame'
        WHERE CAST(r.TeamID AS VARCHAR) = '{tid}'
          AND r.season = '{season}'
        ORDER BY s.MIN DESC NULLS LAST, r.PLAYER
        """
    )
    for row in rows:
        row["HEIGHT_INCHES"] = _height_inches(row.get("HEIGHT"))
    return {
        "success": True,
        "data": rows,
        "meta": {"season": season, "count": len(rows)},
    }


# ==========================================================================
# Team directory and a real games board.
#
# The prototype's team list, live feed and "past days" rail were hand-written
# fixtures. There is no live endpoint yet, but the vault holds every completed
# game through the 2025-26 finals, so the board can be driven by real results
# instead of invented scores.
# ==========================================================================


@router.get("/teams")
def teams_directory(season: str | None = None) -> dict[str, Any]:
    """Every team that played in `season` (default: the latest staged season).

    Reads team_season_stats rather than franchise_history so the names are the
    ones that franchise actually used that year — asking for 1996-97 returns the
    Seattle SuperSonics and the Washington Bullets, not their modern successors.
    """
    if season:
        season = _season(season)
    else:
        rows = _q("SELECT MAX(season) AS s FROM team_game_logs")
        season = str(rows[0]["s"]) if rows and rows[0].get("s") else "2025-26"

    # Read team_game_logs, not team_season_stats: the season table has TEAM_ID and
    # TEAM_NAME but no tricode column at all, and the tricode is what the UI keys on.
    rows = _q(
        f"""
        SELECT DISTINCT
            CAST(TEAM_ID AS VARCHAR) AS team_id,
            TEAM_NAME               AS team_full_name,
            TEAM_ABBREVIATION       AS abbr
        FROM team_game_logs
        WHERE season = '{season}'
          AND season_type = 'Regular Season'
        ORDER BY TEAM_NAME
        """
    )
    # TEAM_NAME is the full "Boston Celtics"; split so the UI can show either half
    # without re-deriving it. The nickname is the last token except for the two
    # two-word nicknames in the league.
    two_word = ("Trail Blazers",)
    for row in rows:
        full = str(row.get("team_full_name") or "").strip()
        nickname = full.rsplit(" ", 1)[-1] if full else ""
        for phrase in two_word:
            if full.endswith(phrase):
                nickname = phrase
        row["nickname"] = nickname
        row["city"] = full[: len(full) - len(nickname)].strip() if nickname else full
    return {"success": True, "data": rows, "meta": {"season": season, "count": len(rows)}}


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _game_date(value: str) -> str:
    if not _DATE_RE.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid date: {value}")
    return value


@router.get("/games/dates")
def game_dates(
    season: str | None = None,
    season_type: str = "Regular Season",
    limit: int = Query(14, ge=1, le=120),
) -> dict[str, Any]:
    """Most recent dates that have games, newest first — the board's day rail."""
    season_type = _season_type(season_type)
    where = [f"season_type = '{season_type}'"]
    if season:
        where.append(f"season = '{_season(season)}'")
    rows = _q(
        f"""
        SELECT
            CAST(CAST(GAME_DATE AS DATE) AS VARCHAR) AS game_date,
            COUNT(DISTINCT GAME_ID)                  AS games
        FROM team_game_logs
        WHERE {' AND '.join(where)}
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT {int(limit)}
        """
    )
    return {"success": True, "data": rows, "meta": {"season": season, "season_type": season_type}}


@router.get("/games/by-date")
def games_by_date(
    date: str,
    season_type: str = "Regular Season",
) -> dict[str, Any]:
    """Every game played on one date, with final score, records and quarter lines."""
    day = _game_date(date)
    season_type = _season_type(season_type)
    rows = _q(
        f"""
        SELECT
            lpad(CAST(GAME_ID AS VARCHAR), 10, '0') AS game_id,
            CAST(CAST(GAME_DATE AS DATE) AS VARCHAR) AS game_date,
            TEAM_ID, TEAM_ABBREVIATION, TEAM_NAME, MATCHUP, WL, PTS,
            FGM, FGA, FG3M, FG3A, FTM, FTA, REB, AST, TOV, PF, season
        FROM team_game_logs
        WHERE CAST(GAME_DATE AS DATE) = DATE '{day}'
          AND season_type = '{season_type}'
        ORDER BY GAME_ID, MATCHUP
        """
    )
    if not rows:
        return {"success": True, "data": [], "meta": {"date": day, "count": 0}}

    game_ids = sorted({str(r["game_id"]) for r in rows})
    id_list = ", ".join(f"'{_like_escape(g)}'" for g in game_ids)
    line_rows = _q(
        f"""
        SELECT game_id, teamTricode,
               period1Score, period2Score, period3Score, period4Score
        FROM game_context
        WHERE game_id IN ({id_list}) AND dataset = '4'
        """
    )
    lines: dict[tuple[str, str], dict[str, Any]] = {
        (str(r.get("game_id")), str(r.get("teamTricode") or "").upper()): r
        for r in line_rows
    }

    def _line(gid: str, abbr: str) -> dict[str, Any]:
        row = lines.get((gid, abbr.upper()), {})
        out: dict[str, Any] = {}
        for i, key in enumerate(
            ("period1Score", "period2Score", "period3Score", "period4Score"), start=1
        ):
            val = row.get(key)
            if val is not None and str(val) not in ("", "nan"):
                out[f"q{i}"] = val
        return out

    by_game: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_game.setdefault(str(row["game_id"]), []).append(row)

    games: list[dict[str, Any]] = []
    for gid in game_ids:
        pair = by_game.get(gid) or []
        if len(pair) != 2:
            continue
        away_row, home_row = _split_home_away_teams(pair)
        if not away_row or not home_row:
            continue

        def _side(row: dict[str, Any]) -> dict[str, Any]:
            abbr = str(row.get("TEAM_ABBREVIATION") or "")
            return {
                "team_id": str(row.get("TEAM_ID") or ""),
                "abbr": abbr,
                "name": str(row.get("TEAM_NAME") or abbr),
                "score": row.get("PTS"),
                "wl": row.get("WL"),
                "line": _line(gid, abbr),
                "stats": {
                    "fg": f"{row.get('FGM')}/{row.get('FGA')}",
                    "fg3": f"{row.get('FG3M')}/{row.get('FG3A')}",
                    "ft": f"{row.get('FTM')}/{row.get('FTA')}",
                    "reb": row.get("REB"),
                    "ast": row.get("AST"),
                    "tov": row.get("TOV"),
                    "pf": row.get("PF"),
                },
            }

        games.append(
            {
                "game_id": gid,
                "game_date": away_row.get("game_date"),
                "season": away_row.get("season"),
                "status": "Final",
                "away": _side(away_row),
                "home": _side(home_row),
            }
        )

    return {
        "success": True,
        "data": games,
        "meta": {"date": day, "season_type": season_type, "count": len(games)},
    }


@router.get("/games/{game_id}/leaders")
def game_leaders(game_id: str, top: int = Query(3, ge=1, le=5)) -> dict[str, Any]:
    """Top scorers / assists / rebounds for a finished game — the card summaries."""
    gid = _normalize_game_id(game_id)
    rows = _q(
        f"""
        SELECT PLAYER_ID, PLAYER_NAME, TEAM_ABBREVIATION, PTS, AST, REB
        FROM player_game_logs
        WHERE lpad(CAST(GAME_ID AS VARCHAR), 10, '0') = '{gid}'
        """
    )

    def _top(key: str) -> list[dict[str, Any]]:
        ranked = sorted(
            (r for r in rows if r.get(key) is not None),
            key=lambda r: float(r.get(key) or 0),
            reverse=True,
        )
        return [
            {
                "player_id": str(r.get("PLAYER_ID") or ""),
                "name": r.get("PLAYER_NAME"),
                "team": r.get("TEAM_ABBREVIATION"),
                "value": r.get(key),
            }
            for r in ranked[:top]
        ]

    return {
        "success": True,
        "data": {"points": _top("PTS"), "assists": _top("AST"), "rebounds": _top("REB")},
        "meta": {"game_id": gid, "player_count": len(rows)},
    }


@router.get("/games/{game_id}/shot-chart")
def game_shot_chart(game_id: str) -> dict[str, Any]:
    """Every shot in one game, both teams, with coordinates.

    One read instead of one per player: the game view needs the whole court, and
    `player_shot_chart` is keyed on GAME_ID so this is a single scan.
    """
    gid = _normalize_game_id(game_id)
    rows = _q(
        f"""
        SELECT PLAYER_ID, PLAYER_NAME, TEAM_ID, TEAM_NAME, PERIOD,
               ACTION_TYPE, SHOT_TYPE, SHOT_ZONE_BASIC, SHOT_DISTANCE,
               LOC_X, LOC_Y, SHOT_MADE_FLAG, HTM, VTM
        FROM player_shot_chart
        WHERE GAME_ID = '{_like_escape(gid)}'
        ORDER BY PERIOD, GAME_EVENT_ID
        """
    )
    by_player: dict[str, dict[str, Any]] = {}
    for row in rows:
        pid = str(row.get("PLAYER_ID") or "")
        entry = by_player.setdefault(
            pid,
            {
                "player_id": pid,
                "name": row.get("PLAYER_NAME"),
                "team_id": str(row.get("TEAM_ID") or ""),
                "team_name": row.get("TEAM_NAME"),
                "attempts": 0,
                "made": 0,
            },
        )
        entry["attempts"] += 1
        if row.get("SHOT_MADE_FLAG") == 1:
            entry["made"] += 1

    return {
        "success": True,
        "data": rows,
        "players": sorted(
            by_player.values(), key=lambda e: -int(e["attempts"])
        ),
        "meta": {"game_id": gid, "attempts": len(rows)},
    }
