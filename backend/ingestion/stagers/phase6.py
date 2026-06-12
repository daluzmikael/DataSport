"""Stage phase-6 tables: tracking, lineups, on/off, estimated metrics."""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import reorder_slice_context_columns
from ingestion.config import PT_MEASURE_TYPES
from ingestion.utils.slice_names import (
    MEASURE_SLUG_TO_API,
    PER_MODE_SLUG_TO_API,
    season_type_from_slug,
)

_PT_SLUG_TO_API = {m.lower().replace(" ", ""): m for m in PT_MEASURE_TYPES}

logger = logging.getLogger(__name__)

_TRACKING_RE = re.compile(
    r"^(player|team)_(regular_season|playoffs)_([a-z]+)_(pergame|totals)\.parquet$",
    re.IGNORECASE,
)
_LINEUP_RE = re.compile(
    r"^g(\d+)_(regular_season|playoffs)_([a-z_]+)_(pergame|totals)\.parquet$",
    re.IGNORECASE,
)
_ON_OFF_RE = re.compile(
    r"^team_(\d+)_(regular_season|playoffs)_(pergame|totals)\.parquet$",
    re.IGNORECASE,
)


def _stage_tracking(root: Path, out_name: str, entity: str) -> Path:
    out_path = STAGING_ROOT / out_name
    frames: list[pd.DataFrame] = []
    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(season_dir.glob("*.parquet")):
            m = _TRACKING_RE.match(path.name)
            if not m:
                continue
            ent, st_slug, pt_slug, pm_slug = m.groups()
            if ent != entity:
                continue
            df = pd.read_parquet(path)
            df["season"] = season_dir.name
            df["season_type"] = season_type_from_slug(st_slug)
            df["pt_measure_type"] = _PT_SLUG_TO_API.get(pt_slug, pt_slug)
            df["per_mode"] = PER_MODE_SLUG_TO_API.get(pm_slug, pm_slug)
            frames.append(df)

    if not frames:
        logger.warning("no %s tracking to stage", entity)
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    id_col = "PLAYER_ID" if entity == "player" else "TEAM_ID"
    combined = reorder_slice_context_columns(
        combined,
        id_col=id_col,
        context_cols=("season", "season_type", "pt_measure_type", "per_mode"),
    )
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows)", out_path, len(combined))
    return out_path


def stage_player_tracking() -> Path:
    return _stage_tracking(RAW_TABLE_DIRS["player_tracking"], "player_tracking.parquet", "player")


def stage_team_tracking() -> Path:
    return _stage_tracking(RAW_TABLE_DIRS["team_tracking"], "team_tracking.parquet", "team")


def stage_lineups() -> Path:
    out_path = STAGING_ROOT / "lineups.parquet"
    root = RAW_TABLE_DIRS["lineups"]
    frames: list[pd.DataFrame] = []
    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(season_dir.glob("*.parquet")):
            m = _LINEUP_RE.match(path.name)
            if not m:
                continue
            group_qty, st_slug, measure_slug, pm_slug = m.groups()
            measure_type = MEASURE_SLUG_TO_API.get(measure_slug, measure_slug)
            df = pd.read_parquet(path)
            df["season"] = season_dir.name
            df["season_type"] = season_type_from_slug(st_slug)
            df["group_quantity"] = int(group_qty)
            df["measure_type"] = measure_type
            df["per_mode"] = PER_MODE_SLUG_TO_API.get(pm_slug, pm_slug)
            frames.append(df)

    if not frames:
        logger.warning("no lineups to stage")
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    combined = reorder_slice_context_columns(
        combined,
        id_col="GROUP_ID",
        context_cols=("season", "season_type", "group_quantity", "measure_type", "per_mode"),
    )
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows)", out_path, len(combined))
    return out_path


def stage_player_on_off() -> Path:
    out_path = STAGING_ROOT / "player_on_off.parquet"
    root = RAW_TABLE_DIRS["player_on_off"]
    frames: list[pd.DataFrame] = []
    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(season_dir.glob("*.parquet")):
            m = _ON_OFF_RE.match(path.name)
            if not m:
                continue
            team_id, st_slug, pm_slug = m.groups()
            df = pd.read_parquet(path)
            df["season"] = season_dir.name
            df["season_type"] = season_type_from_slug(st_slug)
            df["per_mode"] = PER_MODE_SLUG_TO_API.get(pm_slug, pm_slug)
            if "TEAM_ID" not in df.columns:
                df["TEAM_ID"] = team_id
            frames.append(df)

    if not frames:
        logger.warning("no on/off data to stage")
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    combined = reorder_slice_context_columns(
        combined,
        id_col="PLAYER_ID",
        context_cols=("season", "season_type", "per_mode", "TEAM_ID"),
    )
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows)", out_path, len(combined))
    return out_path


def _stage_estimated(root: Path, out_name: str) -> Path:
    out_path = STAGING_ROOT / out_name
    frames: list[pd.DataFrame] = []
    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(season_dir.glob("*.parquet")):
            df = pd.read_parquet(path)
            df["season"] = season_dir.name
            if "regular_season" in path.stem:
                df["season_type"] = "Regular Season"
            elif "playoffs" in path.stem:
                df["season_type"] = "Playoffs"
            frames.append(df)

    if not frames:
        logger.warning("no estimated metrics to stage in %s", root)
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    id_col = "PLAYER_ID" if "player" in out_name else "TEAM_ID"
    combined = reorder_slice_context_columns(
        combined,
        id_col=id_col,
        context_cols=("season", "season_type"),
    )
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows)", out_path, len(combined))
    return out_path


def stage_player_estimated_metrics() -> Path:
    return _stage_estimated(
        RAW_TABLE_DIRS["player_estimated_metrics"],
        "player_estimated_metrics.parquet",
    )


def stage_team_estimated_metrics() -> Path:
    return _stage_estimated(
        RAW_TABLE_DIRS["team_estimated_metrics"],
        "team_estimated_metrics.parquet",
    )


def run_phase6() -> None:
    stage_player_tracking()
    stage_team_tracking()
    stage_lineups()
    stage_player_on_off()
    stage_player_estimated_metrics()
    stage_team_estimated_metrics()
