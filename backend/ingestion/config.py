"""Ingestion paths, season ranges, and API defaults."""
from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = BACKEND_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"
STAGING_ROOT = DATA_ROOT / "staging"
LOGS_ROOT = DATA_ROOT / "logs"
MANIFESTS_ROOT = DATA_ROOT / "manifests"

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
}

START_SEASON = "1996-97"
END_SEASON = "2025-26"

SEASON_TYPES = ("Regular Season", "Playoffs")
PER_MODES_DASH = ("PerGame", "Totals")

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
