"""Stage phase-1 tables: season stats, standings, shot zones."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import (
    _clutch_path_for_dash,
    _hustle_path_for_dash,
    flatten_shot_zone_columns,
    prefix_columns,
    reorder_slice_context_columns,
)
from ingestion.utils.slice_names import parse_raw_slice_filename

logger = logging.getLogger(__name__)

_JOIN_PLAYER = ["PLAYER_ID", "TEAM_ID"]
_JOIN_TEAM = ["TEAM_ID"]


def _merge_season_folder(
    season_dir: Path,
    season_label: str,
    join_keys: list[str],
    id_cols: list[str],
) -> list[pd.DataFrame]:
    """Merge dash + clutch + hustle slices for one season directory."""
    dash_files = sorted(season_dir.glob("dash_*.parquet"))
    if not dash_files:
        return []

    rows: list[pd.DataFrame] = []
    for dash_path in dash_files:
        parsed = parse_raw_slice_filename(dash_path)
        if not parsed:
            logger.warning("skip unrecognized file %s", dash_path)
            continue
        _, season_type, measure_type, per_mode = parsed

        base = pd.read_parquet(dash_path)
        base["season"] = season_label
        base["season_type"] = season_type
        base["measure_type"] = measure_type
        base["per_mode"] = per_mode

        clutch_path = _clutch_path_for_dash(dash_path, season_type, measure_type, per_mode)
        if clutch_path.exists():
            clutch = pd.read_parquet(clutch_path)
            clutch = prefix_columns(clutch, "clutch_", join_keys + list(id_cols))
            base = base.merge(
                clutch,
                on=[c for c in join_keys if c in base.columns and c in clutch.columns],
                how="left",
                suffixes=("", "_clutch_dup"),
            )

        if measure_type == "Base":
            hustle_path = _hustle_path_for_dash(dash_path, season_type, per_mode)
            if hustle_path.exists():
                hustle = pd.read_parquet(hustle_path)
                hustle = prefix_columns(hustle, "hustle_", join_keys + list(id_cols))
                base = base.merge(
                    hustle,
                    on=[c for c in join_keys if c in base.columns and c in hustle.columns],
                    how="left",
                    suffixes=("", "_hustle_dup"),
                )

        rows.append(base)
    return rows


def stage_player_season_stats() -> Path:
    root = RAW_TABLE_DIRS["player_season_stats"]
    out_path = STAGING_ROOT / "player_season_stats.parquet"
    all_rows: list[pd.DataFrame] = []

    for season_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "career"):
        all_rows.extend(
            _merge_season_folder(
                season_dir,
                season_dir.name,
                _JOIN_PLAYER,
                ["PLAYER_NAME", "NICKNAME", "TEAM_ABBREVIATION", "AGE"],
            )
        )

    if not all_rows:
        logger.warning("no player season stats to stage")
        return out_path

    combined = pd.concat(all_rows, ignore_index=True)
    combined = reorder_slice_context_columns(combined, id_col="PLAYER_ID")
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols)", out_path, len(combined), len(combined.columns))
    return out_path


def stage_team_season_stats() -> Path:
    root = RAW_TABLE_DIRS["team_season_stats"]
    out_path = STAGING_ROOT / "team_season_stats.parquet"
    all_rows: list[pd.DataFrame] = []

    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        all_rows.extend(
            _merge_season_folder(
                season_dir,
                season_dir.name,
                _JOIN_TEAM,
                ["TEAM_NAME"],
            )
        )

    if not all_rows:
        logger.warning("no team season stats to stage")
        return out_path

    combined = pd.concat(all_rows, ignore_index=True)
    combined = reorder_slice_context_columns(combined, id_col="TEAM_ID")
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols)", out_path, len(combined), len(combined.columns))
    return out_path


def stage_team_standings() -> Path:
    root = RAW_TABLE_DIRS["team_standings"]
    out_path = STAGING_ROOT / "team_standings.parquet"
    frames: list[pd.DataFrame] = []

    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for parquet_file in sorted(season_dir.glob("*.parquet")):
            df = pd.read_parquet(parquet_file)
            df["season"] = season_dir.name
            if "regular_season" in parquet_file.stem:
                df["season_type"] = "Regular Season"
            elif "playoffs" in parquet_file.stem:
                df["season_type"] = "Playoffs"
            frames.append(df)

    if not frames:
        logger.warning("no standings to stage")
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    combined = reorder_slice_context_columns(
        combined,
        id_col="TeamID",
        context_cols=("season", "season_type"),
    )
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows)", out_path, len(combined))
    return out_path


def _stage_shot_zones(root: Path, out_name: str, id_col: str) -> Path:
    out_path = STAGING_ROOT / out_name
    frames: list[pd.DataFrame] = []

    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for parquet_file in sorted(season_dir.glob("*.parquet")):
            df = flatten_shot_zone_columns(pd.read_parquet(parquet_file))
            df["season"] = season_dir.name
            stem = parquet_file.stem
            if "regular_season" in stem:
                df["season_type"] = "Regular Season"
                df["per_mode"] = "PerGame" if stem.endswith("pergame") else "Totals"
            elif "playoffs" in stem:
                df["season_type"] = "Playoffs"
                df["per_mode"] = "PerGame" if stem.endswith("pergame") else "Totals"
            frames.append(df)

    if not frames:
        logger.warning("no shot zones to stage in %s", root)
        return out_path

    combined = pd.concat(frames, ignore_index=True)
    combined = reorder_slice_context_columns(
        combined,
        id_col=id_col,
        context_cols=("season", "season_type", "per_mode"),
    )
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows)", out_path, len(combined))
    return out_path


def stage_player_shot_zones() -> Path:
    return _stage_shot_zones(
        RAW_TABLE_DIRS["player_shot_zones"],
        "player_shot_zones.parquet",
        "PLAYER_ID",
    )


def stage_team_shot_zones() -> Path:
    return _stage_shot_zones(
        RAW_TABLE_DIRS["team_shot_zones"],
        "team_shot_zones.parquet",
        "TEAM_ID",
    )


def run_phase1() -> None:
    """Build all phase-1 staging tables."""
    stage_player_season_stats()
    stage_team_season_stats()
    stage_team_standings()
    stage_player_shot_zones()
    stage_team_shot_zones()
