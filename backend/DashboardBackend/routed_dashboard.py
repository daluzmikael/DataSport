"""Interim /api/dashboards on top of the router pipeline.

The Team45 interpreter (dashboardInterpreter.py) asks the model for Postgres SQL against
tables that no longer exist, so every request failed. Until DASHBOARD_PLAN.md's ChartSpec
lands, this picks a chart deterministically from the RouterPlan + DataFrame (one router
call, no analyst call) and returns it in the shape ai_analyst's Recharts components read:
{success, chartType, data, config}.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any

import pandas as pd

from Executer.data_backend import get_connection
from Interpreter.pipeline import run_routed_query
from Interpreter.router_plan import RouterPlan
from Interpreter.smalltalk import CAPABILITIES, classify_smalltalk, smalltalk_reply
from Interpreter.sql_builder import entity_name_column

logger = logging.getLogger(__name__)

_LABELS = {
    "PTS": "Points", "AST": "Assists", "REB": "Rebounds", "STL": "Steals", "BLK": "Blocks",
    "TOV": "Turnovers", "FG_PCT": "FG%", "FG3_PCT": "3P%", "FT_PCT": "FT%", "FG3M": "3PM",
    "FG3A": "3PA", "MIN": "Minutes", "GP": "Games", "OREB": "Off. Rebounds",
    "DREB": "Def. Rebounds", "PLUS_MINUS": "+/-", "WINS": "Wins", "LOSSES": "Losses",
    "WinPCT": "Win %", "W_PCT": "Win %", "TS_PCT": "TS%", "EFG_PCT": "eFG%",
    "USG_PCT": "USG%", "NET_RATING": "Net Rating", "OFF_RATING": "Off. Rating",
    "DEF_RATING": "Def. Rating", "PIE": "PIE",
}
_NON_STAT = {"GP", "MIN", "W", "L", "AGE", "PLAYER_ID", "TEAM_ID", "SEASON_ID", "GAME_ID"}
_RADAR = ("PTS", "AST", "REB", "STL", "BLK")
_RADAR_WORDS = re.compile(r"\b(profile|radar|skill|all[- ]around|overall game)\b", re.I)


class DashboardError(Exception):
    """Message safe to show the user in the dashboard's error alert."""


def _label(col: str) -> str:
    return _LABELS.get(col, _LABELS.get(col.upper(), col.replace("_", " ").title()))


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else round(f, 3)


def _pick_stat(plan: RouterPlan, df: pd.DataFrame) -> str | None:
    cols = {c.lower(): c for c in df.columns}
    candidates = ([plan.order_by] if plan.order_by else []) + list(plan.stat_focus) + ["PTS"]
    fallback = None
    for name in candidates:
        col = cols.get(str(name).lower())
        if not col or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        if col.upper() not in _NON_STAT:
            return col
        fallback = fallback or col
    return fallback


def _names(plan: RouterPlan, df: pd.DataFrame) -> pd.Series:
    if "TeamCity" in df.columns and "TeamName" in df.columns:
        return df["TeamCity"].astype(str) + " " + df["TeamName"].astype(str)
    col = entity_name_column(plan, get_connection())
    if col and col in df.columns:
        return df[col].astype(str)
    for c in ("PLAYER_NAME", "player_name", "TEAM_NAME", "GROUP_NAME"):
        if c in df.columns:
            return df[c].astype(str)
    return pd.Series(["Unknown"] * len(df), index=df.index)


def _pick_frame(bundles: dict[str, pd.DataFrame]) -> pd.DataFrame:
    for label, df in bundles.items():
        if label.endswith("PerGame") and not df.empty:
            return df
    return next(iter(bundles.values()))


def build_dashboard(question: str) -> dict[str, Any]:
    intent = classify_smalltalk(question)
    if intent:
        raise DashboardError(smalltalk_reply(intent))

    routed_question = question
    if _RADAR_WORDS.search(question):
        # Steer "skill profile" asks to the box-score table so the radar has its axes.
        routed_question += (
            " (chart hint: read player_season_stats PerGame with stat_focus "
            "PTS, AST, REB, STL, BLK)"
        )
    bundles, plan = run_routed_query(routed_question)
    if plan.is_off_topic():
        raise DashboardError(smalltalk_reply("off_topic"))
    if not plan.supported:
        raise DashboardError(
            "That chart needs data from more than one table at once, which isn't supported "
            "yet. Try one stat area at a time, e.g. \"Jokic points per game by season\"."
        )
    if not bundles:
        raise DashboardError(
            "No data found for that. Check the player/team spelling or add a season, "
            "e.g. \"Top 10 scorers 2024-25\"."
        )

    df = _pick_frame(bundles).copy()
    stat = _pick_stat(plan, df)
    if not stat:
        raise DashboardError("I found rows but no numeric stat to chart. Try naming a stat.")

    df["_name"] = _names(plan, df)
    x_key = "season" if "season" in df.columns else None
    for c in ("GAME_DATE", "game_date"):
        if c in df.columns and plan.table and "game" in plan.table:
            x_key = c
    # Traded players have one row per team: keep the row with the most games.
    if "GP" in df.columns and x_key:
        df = df.sort_values("GP", ascending=False).drop_duplicates(["_name", x_key])

    timeframe = plan.season_label() if plan.season_from or plan.season_to else None
    config: dict[str, Any] = {
        "statKey": "stat_value",
        "statDisplayName": _label(stat),
        "xAxisKey": "game_date" if x_key and x_key.lower() == "game_date" else "season",
        "timeFrame": timeframe,
        "playerNames": [],
        "citation": plan.citation(),
    }
    names = list(dict.fromkeys(df["_name"].tolist()))

    # Leaderboard
    if plan.is_leaderboard() or len(names) > 4:
        ascending = plan.sort_dir == "asc"
        df = df.dropna(subset=[stat]).sort_values(stat, ascending=ascending)
        df = df.drop_duplicates("_name").head(plan.limit or 10)
        rows = [
            {
                "player_name": r["_name"],
                "team_abbreviation": r.get("TEAM_ABBREVIATION"),
                "stat_value": _num(r[stat]),
            }
            for _, r in df.iterrows()
        ]
        return {"success": True, "chartType": "Leaderboard", "data": rows, "config": config}

    # Skill radar
    upper = {c.upper(): c for c in df.columns}
    if _RADAR_WORDS.search(question) and all(k in upper for k in _RADAR):
        from DashboardBackend.dashboardInterpreter import process_categorical_data

        latest = df.sort_values(x_key) if x_key else df
        latest = latest.drop_duplicates("_name", keep="last")
        raw = [
            {"player_name": r["_name"], **{k: _num(r[upper[k]]) or 0 for k in _RADAR}}
            for _, r in latest.iterrows()
        ]
        config["playerNames"] = [r["player_name"] for r in raw]
        chart = "CompareCategoricalBreakdown" if len(raw) > 1 else "CategoricalBreakdown"
        return {
            "success": True,
            "chartType": chart,
            "data": process_categorical_data(raw, len(raw)),
            "config": config,
        }

    if not x_key:
        raise DashboardError("That data has no season or date to chart against.")
    df = df.sort_values(x_key)
    last_n = re.search(r"\blast (\d{1,2}) games?\b", question, re.I)
    if last_n:
        df = df.tail(int(last_n.group(1)))

    if len(names) == 1:
        rows = [
            {config["xAxisKey"]: str(r[x_key])[:10], "stat_value": _num(r[stat])}
            for _, r in df.iterrows()
        ]
        config["playerNames"] = names
        return {"success": True, "chartType": "SinglePlayerStat", "data": rows, "config": config}

    # 2-4 entities: grouped bars per season / date
    from DashboardBackend.dashboardInterpreter import process_comparison_data

    raw = [
        {"full_name": r["_name"], "season": str(r[x_key])[:10], "stat_value": _num(r[stat])}
        for _, r in df.iterrows()
    ]
    config["playerNames"] = names
    config["xAxisKey"] = "season"
    return {
        "success": True,
        "chartType": "CompareStats",
        "data": process_comparison_data(raw),
        "config": config,
    }


def dashboard_for_question(question: str) -> dict[str, Any]:
    """Never raises: returns {success: False, error: <friendly text>} on any failure."""
    try:
        return build_dashboard(question)
    except DashboardError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Dashboard failed for %r", question)
        return {
            "success": False,
            "error": "Couldn't build a chart for that. " + CAPABILITIES.split("\n", 1)[0],
        }


__all__ = ["dashboard_for_question", "build_dashboard"]
