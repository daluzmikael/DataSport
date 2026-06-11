"""Stage phase-3 tables: game context + per-game advanced stats."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import concat_parquet_files_batched

logger = logging.getLogger(__name__)


def _enrich_game_id(df: pd.DataFrame, path: Path) -> None:
    df.insert(0, "game_id", path.stem.zfill(10))


def _stage_game_advanced(root: Path, out_name: str) -> Path:
    out_path = STAGING_ROOT / out_name
    parquet_files = sorted(root.glob("*.parquet"))
    if not parquet_files:
        logger.warning("no game advanced files in %s", root)
        return out_path

    row_count = concat_parquet_files_batched(
        parquet_files,
        out_path,
        enrich=_enrich_game_id,
        batch_size=500,
        log_label=out_name,
    )
    logger.info("wrote %s (%s rows)", out_path, row_count)
    return out_path


def stage_player_game_advanced() -> Path:
    return _stage_game_advanced(
        RAW_TABLE_DIRS["player_game_advanced"],
        "player_game_advanced.parquet",
    )


def stage_team_game_advanced() -> Path:
    return _stage_game_advanced(
        RAW_TABLE_DIRS["team_game_advanced"],
        "team_game_advanced.parquet",
    )


def stage_game_context() -> Path:
    root = RAW_TABLE_DIRS["game_context"]
    out_path = STAGING_ROOT / "game_context.parquet"
    json_files = sorted(root.glob("*.json"))
    if not json_files:
        logger.warning("no game context JSON to stage")
        return out_path

    frames: list[pd.DataFrame] = []
    batch: list[pd.DataFrame] = []
    batch_size = 2000

    for i, json_path in enumerate(json_files, start=1):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("skip invalid JSON %s", json_path)
            continue

        game_id = str(payload.get("game_id") or json_path.stem).zfill(10)
        datasets = payload.get("datasets") or {}
        for dataset_key, records in datasets.items():
            if not records:
                continue
            df = pd.DataFrame(records)
            for col in df.columns:
                df[col] = df[col].astype(str)
            df.insert(0, "dataset", str(dataset_key))
            df.insert(0, "game_id", game_id)
            batch.append(df)

        if len(batch) >= batch_size:
            frames.append(pd.concat(batch, ignore_index=True))
            batch = []
            logger.info("game_context staging progress: %s/%s files", i, len(json_files))

    if batch:
        frames.append(pd.concat(batch, ignore_index=True))

    if not frames:
        logger.warning("no game context records to stage")
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols)", out_path, len(combined), len(combined.columns))
    return out_path


def run_phase3() -> None:
    stage_game_context()
    stage_player_game_advanced()
    stage_team_game_advanced()
