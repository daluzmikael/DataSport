"""Read-only REST endpoints over DuckDB staging parquet (home-prototype)."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from Executer.data_backend import get_connection, use_duckdb_staging
from Executer.duckdb_store import default_staging_dir, list_registered_tables, refresh_views
from Executer.executor import execute_query, validate_and_normalize_sql

router = APIRouter(prefix="/api/staging", tags=["staging"])

_SEASON_RE = re.compile(r"^\d{4}-\d{2}$")
_NUM_ID_RE = re.compile(r"^\d+$")
_SEASON_TYPES = {"Regular Season", "Playoffs"}
_PER_MODES = {"PerGame", "Totals"}


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
    season: str = "2024-25",
    limit: int = Query(25, ge=1, le=100),
) -> dict[str, Any]:
    season = _season(season)
    term = _like_escape(q.strip())
    rows = _q(
        f"""
        SELECT DISTINCT PLAYER_ID, PLAYER_NAME, TEAM_ABBREVIATION, TEAM_ID
        FROM player_season_stats
        WHERE season = '{season}'
          AND season_type = 'Regular Season'
          AND per_mode = 'PerGame'
          AND PLAYER_NAME ILIKE '%{term}%'
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
) -> dict[str, Any]:
    pid = _num_id(player_id, "player_id")
    season = _season(season)
    season_type = _season_type(season_type)
    per_mode = _per_mode(per_mode)
    rows = _q(
        f"""
        SELECT *
        FROM player_season_stats
        WHERE {_player_id_sql(pid)}
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = '{per_mode}'
        LIMIT 1
        """
    )
    return {"success": True, "data": rows[0] if rows else None}


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
        SELECT DISTINCT TEAM_ID, TEAM_ABBREVIATION, TEAM_NAME
        FROM team_season_stats
        WHERE TEAM_ABBREVIATION = '{code}'
          AND season = '2024-25'
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
) -> dict[str, Any]:
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    per_mode = _per_mode(per_mode)
    rows = _q(
        f"""
        SELECT *
        FROM team_season_stats
        WHERE TEAM_ID = {tid}
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
) -> dict[str, Any]:
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    rows = _q(
        f"""
        SELECT *
        FROM team_game_logs
        WHERE CAST(TEAM_ID AS VARCHAR) = '{tid}'
          AND season = '{season}'
          AND season_type = '{season_type}'
        ORDER BY GAME_DATE DESC
        LIMIT {int(limit)}
        """
    )
    return {"success": True, "data": rows}


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
        SELECT *
        FROM team_standings
        WHERE TeamID = {tid}
          AND season = '{season}'
          AND season_type = '{season_type}'
        LIMIT 1
        """
    )
    return {"success": True, "data": rows[0] if rows else None}


@router.get("/teams/{team_id}/leaders")
def team_season_leaders(
    team_id: str,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    stat: str = Query("PTS", pattern="^(PTS|REB|AST)$"),
) -> dict[str, Any]:
    tid = _num_id(team_id, "team_id")
    season = _season(season)
    season_type = _season_type(season_type)
    col = stat
    rows = _q(
        f"""
        SELECT PLAYER_ID, PLAYER_NAME, TEAM_ABBREVIATION, {col} AS value
        FROM player_season_stats
        WHERE TEAM_ID = {tid}
          AND season = '{season}'
          AND season_type = '{season_type}'
          AND per_mode = 'PerGame'
        ORDER BY {col} DESC NULLS LAST
        LIMIT 5
        """
    )
    return {"success": True, "data": rows, "meta": {"stat": stat}}
