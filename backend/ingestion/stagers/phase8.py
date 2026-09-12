"""Stage phase-8 tables: Synergy play types.

Grain: one row per player (or team) per season per season_type per play_type per
type_grouping. `play_type` and `type_grouping` are slice columns — a question about
isolation offense is one filtered read, not a join.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import normalize_team_identity, reorder_slice_context_columns

logger = logging.getLogger(__name__)


def _stage(entity: str) -> Path:
    table = f"{entity}_synergy"
    root = Path(RAW_TABLE_DIRS[table])
    out_path = STAGING_ROOT / f"{table}.parquet"

    frames = []
    if root.exists():
        for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for path in sorted(season_dir.glob("*.parquet")):
                df = pd.read_parquet(path)
                if df.empty:
                    continue
                # The puller stamps season / season_type / play_type / type_grouping,
                # so nothing has to be re-derived from the filename here.
                if "season" not in df.columns:
                    df["season"] = season_dir.name
                frames.append(df)

    if not frames:
        logger.warning("no %s data to stage", table)
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    id_col = "PLAYER_ID" if entity == "player" else "TEAM_ID"
    combined = reorder_slice_context_columns(
        combined,
        id_col=id_col,
        context_cols=("season", "season_type", "play_type", "type_grouping", "per_mode"),
    )
    combined = normalize_team_identity(combined)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols)", out_path, len(combined), len(combined.columns))
    return out_path


def stage_player_synergy() -> Path:
    return _stage("player")


def stage_team_synergy() -> Path:
    return _stage("team")


def stage_phase8() -> None:
    stage_player_synergy()
    stage_team_synergy()
