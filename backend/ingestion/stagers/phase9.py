"""Stage phase-9: player_shot_chart (LOC_X / LOC_Y per-shot coordinates).

Separate table from `court_shots`, which is a zone grid and is left untouched.

This is the largest staged table in the vault by row count — roughly one row per
shot attempt per player per season — so it is concatenated in season batches rather
than loading every file at once.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import normalize_team_identity

logger = logging.getLogger(__name__)

# Columns worth keeping. The endpoint also returns GRID_TYPE and a few redundant
# flags; SHOT_ATTEMPTED_FLAG is always 1 for a context_measure of FGA.
_KEEP = [
    "GAME_ID", "GAME_EVENT_ID", "GAME_DATE", "PLAYER_ID", "PLAYER_NAME",
    "TEAM_ID", "TEAM_NAME", "PERIOD", "MINUTES_REMAINING", "SECONDS_REMAINING",
    "EVENT_TYPE", "ACTION_TYPE", "SHOT_TYPE",
    "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "SHOT_ZONE_RANGE", "SHOT_DISTANCE",
    "LOC_X", "LOC_Y", "SHOT_MADE_FLAG", "HTM", "VTM",
    "season", "season_type",
]


def stage_player_shot_chart() -> Path:
    root = Path(RAW_TABLE_DIRS["player_shot_chart"])
    out_path = STAGING_ROOT / "player_shot_chart.parquet"
    if not root.exists():
        logger.warning("no player_shot_chart data to stage")
        return out_path

    season_frames: list[pd.DataFrame] = []
    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(season_dir.rglob("*.parquet"))
        if not files:
            continue
        parts = []
        for path in files:
            try:
                df = pd.read_parquet(path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("unreadable %s (%s)", path, exc)
                continue
            if df.empty:
                continue
            if "season" not in df.columns:
                df["season"] = season_dir.name
            if "season_type" not in df.columns:
                # <season>/<regular_season|playoffs>/<player>.parquet
                slug = path.parent.name
                df["season_type"] = (
                    "Regular Season" if slug == "regular_season" else "Playoffs"
                )
            parts.append(df[[c for c in _KEEP if c in df.columns]])
        if parts:
            season_frames.append(pd.concat(parts, ignore_index=True))
            logger.info("shot_chart %s: %s rows", season_dir.name, len(season_frames[-1]))

    if not season_frames:
        logger.warning("no player_shot_chart data to stage")
        return out_path

    combined = pd.concat(season_frames, ignore_index=True)
    combined = normalize_team_identity(combined)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols)", out_path, len(combined), len(combined.columns))
    return out_path


def stage_phase9() -> None:
    stage_player_shot_chart()
