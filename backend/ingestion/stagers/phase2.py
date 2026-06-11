"""Stage phase-2 tables: player and team game logs."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import season_type_from_slug

logger = logging.getLogger(__name__)


def _stage_game_logs(root: Path, out_name: str) -> Path:
    out_path = STAGING_ROOT / out_name
    frames: list[pd.DataFrame] = []

    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for parquet_file in sorted(season_dir.glob("*.parquet")):
            df = pd.read_parquet(parquet_file)
            df["season"] = season_dir.name
            slug = parquet_file.stem
            df["season_type"] = season_type_from_slug(slug)
            frames.append(df)

    if not frames:
        logger.warning("no game logs to stage in %s", root)
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols)", out_path, len(combined), len(combined.columns))
    return out_path


def stage_player_game_logs() -> Path:
    return _stage_game_logs(RAW_TABLE_DIRS["player_game_logs"], "player_game_logs.parquet")


def stage_team_game_logs() -> Path:
    return _stage_game_logs(RAW_TABLE_DIRS["team_game_logs"], "team_game_logs.parquet")


def run_phase2() -> None:
    stage_player_game_logs()
    stage_team_game_logs()
