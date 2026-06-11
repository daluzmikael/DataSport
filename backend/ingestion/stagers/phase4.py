"""Stage phase-4 table: player career stats (from playercareerstats JSON)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT

logger = logging.getLogger(__name__)


def stage_player_career() -> Path:
    root = RAW_TABLE_DIRS["player_season_stats"] / "career"
    out_path = STAGING_ROOT / "player_career.parquet"
    json_files = sorted(root.glob("*.json"))
    if not json_files:
        logger.warning("no player career JSON to stage")
        return out_path

    frames: list[pd.DataFrame] = []
    unavailable_count = 0

    for json_path in json_files:
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("skip invalid career JSON %s", json_path)
            continue

        player_id = str(payload.get("player_id") or json_path.stem)
        unavailable = bool(payload.get("unavailable"))
        datasets = payload.get("datasets") or {}

        if unavailable and not datasets:
            unavailable_count += 1
            continue

        for dataset_key, records in datasets.items():
            if not records:
                continue
            df = pd.DataFrame(records)
            # Career datasets use different schemas; coerce to string to avoid 'NR' vs int clashes.
            for col in df.columns:
                df[col] = df[col].astype(str)
            df.insert(0, "unavailable", unavailable)
            df.insert(0, "dataset", str(dataset_key))
            df.insert(0, "player_id", player_id)
            frames.append(df)

    if not frames:
        logger.warning(
            "no career datasets to stage (%s unavailable stubs skipped)",
            unavailable_count,
        )
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info(
        "wrote %s (%s rows, %s players, %s unavailable stubs skipped)",
        out_path,
        len(combined),
        combined["player_id"].nunique(),
        unavailable_count,
    )
    return out_path


def run_phase4() -> None:
    stage_player_career()
