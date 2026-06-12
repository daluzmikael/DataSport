"""Ingestion paths, season ranges, and API defaults."""
from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = BACKEND_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"
STAGING_ROOT = DATA_ROOT / "staging"
LOGS_ROOT = DATA_ROOT / "logs"
MANIFESTS_ROOT = DATA_ROOT / "manifests"
THIRD_PARTY_METRICS_ROOT = RAW_ROOT / "third_party_metrics"

RAW_TABLE_DIRS = {
    "game_context": RAW_ROOT / "game_context",
    "player_game_logs": RAW_ROOT / "player_game_logs",
    "team_game_logs": RAW_ROOT / "team_game_logs",
    "player_game_advanced": RAW_ROOT / "player_game_advanced",
    "team_game_advanced": RAW_ROOT / "team_game_advanced",
    "court_shots": RAW_ROOT / "court_shots",
    "team_standings": RAW_ROOT / "team_standings",
    "player_season_stats": RAW_ROOT / "player_season_stats",
    "team_season_stats": RAW_ROOT / "team_season_stats",
    "player_shot_zones": RAW_ROOT / "player_shot_zones",
    "team_shot_zones": RAW_ROOT / "team_shot_zones",
    "player_tracking": RAW_ROOT / "player_tracking",
    "team_tracking": RAW_ROOT / "team_tracking",
    "lineups": RAW_ROOT / "lineups",
    "player_on_off": RAW_ROOT / "player_on_off",
    "player_estimated_metrics": RAW_ROOT / "player_estimated_metrics",
    "team_estimated_metrics": RAW_ROOT / "team_estimated_metrics",
    "third_party_metrics": THIRD_PARTY_METRICS_ROOT,
}

START_SEASON = "1996-97"
END_SEASON = "2025-26"

SEASON_TYPES = ("Regular Season", "Playoffs")

# Legacy alias — Base PerGame/Totals only (extended pulls use PER_MODES_DASH_EXTENDED).
PER_MODES_DASH = ("PerGame", "Totals")
PER_MODES_DASH_EXTENDED = (
    "PerGame",
    "Totals",
    "Per100Possessions",
    "Per36",
    "Per40",
)

MEASURE_TYPES_PLAYER_DASH = ("Base", "Advanced", "Usage", "Misc", "Scoring", "Defense")
MEASURE_TYPES_TEAM_DASH = ("Base", "Advanced", "Misc", "Scoring", "Defense")
MEASURE_TYPES_PLAYER_CLUTCH = ("Base", "Advanced", "Misc", "Scoring", "Usage")
MEASURE_TYPES_TEAM_CLUTCH = ("Base", "Advanced", "Misc", "Scoring")

PT_MEASURE_TYPES = (
    "SpeedDistance",
    "Rebounding",
    "Possessions",
    "CatchShoot",
    "PullUpShot",
    "Defense",
    "Drives",
    "Passing",
    "ElbowTouch",
    "PostTouch",
    "PaintTouch",
    "Efficiency",
)

LINEUP_GROUP_QUANTITIES = (5,)
LINEUP_MEASURE_TYPES = ("Base", "Advanced", "Misc", "Four Factors", "Scoring", "Opponent")

CLUTCH_DEFAULTS = {
    "clutch_time": "Last 5 Minutes",
    "ahead_behind": "Ahead or Behind",
    "point_diff": 5,
}

LEAGUE_ID = "00"
RATE_SLEEP_SEC = 0.6
MAX_RETRIES = 4
RETRY_BACKOFF_SEC = 2.0
# stats.nba.com can be slow under bulk pulls; endpoints default to 30s
API_TIMEOUT_SEC = 60
# ShotChartDetail responses can be large; use a longer read timeout in phase 5.
COURT_SHOTS_TIMEOUT_SEC = 90
COURT_SHOTS_RATE_SLEEP_SEC = 1.0

PULL_STATE_FILE = MANIFESTS_ROOT / "pull_state.json"
GAME_IDS_FILE = MANIFESTS_ROOT / "game_ids.txt"
# Phase 3 per-game pulls: "recent" (newest first) or "oldest" (manifest file order).
GAME_PULL_ORDER = "recent"
FAILED_GAMES_FILE = MANIFESTS_ROOT / "failed_game_ids.json"


def ensure_data_dirs() -> None:
    """Create raw/staging/log/manifest folders and per-table raw dirs."""
    for path in (
        RAW_ROOT,
        STAGING_ROOT,
        LOGS_ROOT,
        MANIFESTS_ROOT,
        *RAW_TABLE_DIRS.values(),
    ):
        path.mkdir(parents=True, exist_ok=True)
