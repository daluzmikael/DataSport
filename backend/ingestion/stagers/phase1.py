"""Stage phase-1 tables: season stats, standings, shot zones."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import (
    normalize_team_identity,
    _clutch_path_for_dash,
    _hustle_path_for_dash,
    flatten_shot_zone_columns,
    prefix_columns,
    reorder_slice_context_columns,
)
from ingestion.utils.slice_names import legacy_slice_filename, slice_filename

logger = logging.getLogger(__name__)

_JOIN_PLAYER = ["PLAYER_ID", "TEAM_ID"]
_JOIN_TEAM = ["TEAM_ID"]

# The staged season tables are deliberately WIDE: one row per entity per season per
# season_type per per_mode, with every measure type folded in as extra COLUMNS.
#
# The raw tree also holds Advanced/Usage/Misc/Scoring/Defense as separate files. The
# tempting move — concat them all and add a `measure_type` column — is what the
# wide-schema redesign removed, because it multiplied 2023-24 from 1,572 to 22,864 rows
# and reintroduced the binder errors that motivated the redesign. So they are joined
# sideways onto the Base spine instead.
_SEASON_TYPES = ("Regular Season", "Playoffs")

# All five per-modes now stage as ROWS (decided 2026-08-19). PerGame and Totals were
# the original two; Per36/Per40/Per100Possessions were pulled at the same time and sat
# unused in raw.
#
# COVERAGE IS NOT UNIFORM, and the router has to know it: only the season dash and
# clutch families were pulled at the alternate modes. Hustle, tracking, shot zones,
# lineups and on/off exist at PerGame/Totals only. So "per-36 points" is answerable and
# "per-36 drives" is not — see the per_mode note in table_catalog.yaml.
_PER_MODES = ("PerGame", "Totals", "Per36", "Per40", "Per100Possessions")

# Hustle was only ever pulled at these modes; asking for it at Per36 finds no file.
_HUSTLE_PER_MODES = ("PerGame", "Totals")

# Clutch measure types folded in as COLUMNS alongside Base clutch (decided 2026-08-19).
# Same column-wise treatment the dash slices get, so clutch TS%/USG% land as
# clutch_TS_PCT / clutch_USG_PCT rather than as extra rows.
_CLUTCH_EXTRA_MEASURES = ("Advanced", "Usage", "Misc", "Scoring")

# Joined onto the spine in this order. First writer of a column wins, so precedence is
# just list order: Advanced owns USG_PCT, and Usage's copy is dropped as a duplicate.
_EXTRA_MEASURES = ("Advanced", "Usage", "Misc", "Scoring", "Defense")

# NBA's internal scratch columns — same values as their unprefixed twins, no analytical use.
_SKIP_PREFIXES = ("sp_work_",)

# Redundant with Base PerGame, and misleading on a Totals row.
_SKIP_COLUMNS = {"FGM_PG", "FGA_PG", "FGM_PG_RANK", "FGA_PG_RANK"}


def _base_dash_path(season_dir: Path, season_type: str, per_mode: str) -> Path | None:
    """The Base file to hang the clutch/hustle lookups off, canonical preferred."""
    canonical = season_dir / slice_filename("dash", season_type, "Base", per_mode)
    if canonical.exists():
        return canonical
    legacy = season_dir / legacy_slice_filename("dash", season_type, per_mode)
    return legacy if legacy.exists() else None


def _load_base_spine(
    season_dir: Path, season_type: str, per_mode: str, join_keys: list[str]
) -> pd.DataFrame | None:
    """Base rows for one slice, unioning the canonical and legacy files.

    Both spellings sit in the raw tree. They are usually identical — but not always:
    team 2016-17 Playoffs Totals has 15 rows canonically and 16 in the legacy file,
    the missing one being the Utah Jazz. Preferring canonical outright silently drops
    that team from the staged table.

    So canonical wins on values, and any entity present only in the legacy file is
    appended. Reading both without this de-duplication would instead double every
    Base row, which is the trap in globbing `dash_*.parquet`.
    """
    canonical_path = season_dir / slice_filename("dash", season_type, "Base", per_mode)
    legacy_path = season_dir / legacy_slice_filename("dash", season_type, per_mode)

    frames: list[pd.DataFrame] = []
    canonical = pd.read_parquet(canonical_path) if canonical_path.exists() else None
    legacy = pd.read_parquet(legacy_path) if legacy_path.exists() else None

    if canonical is not None and not canonical.empty:
        frames.append(canonical)
    if legacy is not None and not legacy.empty:
        if not frames:
            frames.append(legacy)
        else:
            keys = [k for k in join_keys if k in canonical.columns and k in legacy.columns]
            if keys:
                have = set(map(tuple, canonical[keys].itertuples(index=False, name=None)))
                extra_mask = ~legacy[keys].apply(lambda r: tuple(r) in have, axis=1)
                extra = legacy[extra_mask]
                if not extra.empty:
                    logger.info(
                        "%s %s %s: %d row(s) only in the legacy Base file — kept (%s)",
                        season_dir.name, season_type, per_mode, len(extra),
                        ", ".join(str(v) for v in extra[keys[0]].tolist()[:5]),
                    )
                    frames.append(extra)

    if not frames:
        return None
    spine = pd.concat(frames, ignore_index=True)
    keys = [k for k in join_keys if k in spine.columns]
    return spine.drop_duplicates(subset=keys) if keys else spine


def _new_columns_only(
    extra: pd.DataFrame, spine_columns: set[str], join_keys: list[str]
) -> pd.DataFrame | None:
    """Narrow an extra slice to its join keys plus columns the spine does not have."""
    keys = [k for k in join_keys if k in extra.columns]
    if not keys:
        return None

    keep: list[str] = []
    for col in extra.columns:
        if col in keys or col in spine_columns or col in _SKIP_COLUMNS:
            continue
        low = col.lower()
        # Substring, not startswith: clutch slices arrive already prefixed and
        # lowercased by `prefix_columns`, so the scratch columns show up as
        # `clutch_sp_work_off_rating` rather than `sp_work_OFF_RATING`.
        if any(sk.strip("_") in low for sk in _SKIP_PREFIXES):
            continue
        if low.replace("clutch_", "") in {c.lower() for c in _SKIP_COLUMNS}:
            continue
        keep.append(col)

    if not keep:
        return None
    narrowed = extra[keys + keep]
    # One row per entity: a duplicated key would fan the spine out.
    return narrowed.drop_duplicates(subset=keys)


def _merge_season_folder(
    season_dir: Path,
    season_label: str,
    join_keys: list[str],
    id_cols: list[str],
) -> list[pd.DataFrame]:
    """Build wide rows for one season: Base spine + clutch + hustle + measure columns.

    Returns one frame per (season_type, per_mode) — four at most, never one per
    measure type.
    """
    rows: list[pd.DataFrame] = []

    for season_type in _SEASON_TYPES:
        for per_mode in _PER_MODES:
            dash_path = _base_dash_path(season_dir, season_type, per_mode)
            if dash_path is None:
                continue

            spine = _load_base_spine(season_dir, season_type, per_mode, join_keys)
            if spine is None or spine.empty:
                continue

            spine["season"] = season_label
            spine["season_type"] = season_type
            spine["per_mode"] = per_mode
            # Deliberately NO measure_type column: the grain is one row per per_mode.

            # Clutch (Base box score only, as before) and hustle, both prefixed.
            clutch_path = _clutch_path_for_dash(dash_path, season_type, "Base", per_mode)
            if clutch_path.exists():
                clutch = pd.read_parquet(clutch_path)
                if not clutch.empty:
                    clutch = prefix_columns(clutch, "clutch_", join_keys + list(id_cols))
                    on = [c for c in join_keys if c in spine.columns and c in clutch.columns]
                    if on:
                        spine = spine.merge(
                            clutch.drop_duplicates(subset=on), on=on, how="left",
                            suffixes=("", "_clutch_dup"),
                        )

            # Clutch advanced/usage/misc/scoring as prefixed COLUMNS.
            for measure in _CLUTCH_EXTRA_MEASURES:
                cpath = season_dir / slice_filename("clutch", season_type, measure, per_mode)
                if not cpath.exists():
                    continue
                extra = pd.read_parquet(cpath)
                if extra.empty:
                    continue
                extra = prefix_columns(extra, "clutch_", join_keys + list(id_cols))
                narrowed = _new_columns_only(extra, set(spine.columns), join_keys)
                if narrowed is None:
                    continue
                on = [c for c in join_keys if c in spine.columns and c in narrowed.columns]
                if not on:
                    continue
                spine = spine.merge(
                    narrowed, on=on, how="left", suffixes=("", f"_clutch_{measure.lower()}_dup")
                )

            hustle_path = _hustle_path_for_dash(dash_path, season_type, per_mode)
            if per_mode in _HUSTLE_PER_MODES and hustle_path.exists():
                hustle = pd.read_parquet(hustle_path)
                if not hustle.empty:
                    hustle = prefix_columns(hustle, "hustle_", join_keys + list(id_cols))
                    on = [c for c in join_keys if c in spine.columns and c in hustle.columns]
                    if on:
                        spine = spine.merge(
                            hustle.drop_duplicates(subset=on), on=on, how="left",
                            suffixes=("", "_hustle_dup"),
                        )

            # The point of this restage: TS_PCT, EFG_PCT, USG_PCT, PIE and the rest,
            # joined on as columns rather than stacked as rows.
            for measure in _EXTRA_MEASURES:
                path = season_dir / slice_filename("dash", season_type, measure, per_mode)
                if not path.exists():
                    continue  # e.g. team has no Usage slice
                extra = pd.read_parquet(path)
                if extra.empty:
                    # Player Defense is genuinely empty for some seasons (2000-01,
                    # 2023-24). Skipping keeps the rows; pd.concat backfills the
                    # columns as NA from the seasons that do have them.
                    logger.debug("%s %s %s %s is empty — skipped",
                                 season_label, season_type, measure, per_mode)
                    continue

                narrowed = _new_columns_only(extra, set(spine.columns), join_keys)
                if narrowed is None:
                    continue
                on = [c for c in join_keys if c in spine.columns and c in narrowed.columns]
                if not on:
                    continue
                before = len(spine)
                spine = spine.merge(narrowed, on=on, how="left", suffixes=("", f"_{measure.lower()}_dup"))
                if len(spine) != before:
                    logger.warning(
                        "%s %s %s %s changed row count %d -> %d",
                        season_label, season_type, measure, per_mode, before, len(spine),
                    )

            rows.append(spine)

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
    combined = normalize_team_identity(combined)
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
    combined = normalize_team_identity(combined)
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
    combined = normalize_team_identity(combined)

    # LeagueStandings splits the name across TeamCity + TeamName, so the only
    # filterable name on this table was the bare nickname. Everyone types the full
    # name, so "the Washington Bullets' record in 1996-97" matched nothing while the
    # row sat right there as Washington + Bullets. Compose the joined form; the era's
    # own city is preserved by normalize_team_identity, so 1996-97 still reads
    # "Washington Bullets" and 2020-21 reads "Washington Wizards".
    if {"TeamCity", "TeamName"}.issubset(combined.columns):
        combined["TEAM_FULL_NAME"] = (
            combined["TeamCity"].fillna("").astype(str).str.strip()
            + " "
            + combined["TeamName"].fillna("").astype(str).str.strip()
        ).str.strip()

    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols)", out_path, len(combined), len(combined.columns))
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
    combined = normalize_team_identity(combined)
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
