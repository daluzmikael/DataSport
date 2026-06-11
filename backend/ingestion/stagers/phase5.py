"""Stage phase-5 table: court shot zones (shotchartdetail per player)."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import concat_parquet_files_batched, season_type_from_slug

logger = logging.getLogger(__name__)


def _enrich_court_shot(df: pd.DataFrame, path: Path) -> None:
    # layout: court_shots/{season}/{regular_season|playoffs}/{player_id}.parquet
    df.insert(0, "player_id", path.stem)
    df.insert(0, "season_type", season_type_from_slug(path.parent.name))
    df.insert(0, "season", path.parent.parent.name)


def stage_court_shots() -> Path:
    root = RAW_TABLE_DIRS["court_shots"]
    out_path = STAGING_ROOT / "court_shots.parquet"
    parquet_files = sorted(root.rglob("*.parquet"))
    if not parquet_files:
        logger.warning("no court_shots parquet files to stage")
        return out_path

    row_count = concat_parquet_files_batched(
        parquet_files,
        out_path,
        enrich=_enrich_court_shot,
        batch_size=1000,
        log_label="court_shots",
    )
    logger.info("wrote %s (%s rows)", out_path, row_count)
    return out_path


def run_phase5() -> None:
    stage_court_shots()
