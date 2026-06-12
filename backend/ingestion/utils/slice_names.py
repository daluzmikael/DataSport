"""Filename slugs and parsing for season dash/clutch/hustle slices."""
from __future__ import annotations

import re
from pathlib import Path

MEASURE_SLUG_TO_API: dict[str, str] = {
    "base": "Base",
    "advanced": "Advanced",
    "usage": "Usage",
    "misc": "Misc",
    "scoring": "Scoring",
    "defense": "Defense",
    "four_factors": "Four Factors",
    "opponent": "Opponent",
}

PER_MODE_SLUG_TO_API: dict[str, str] = {
    "pergame": "PerGame",
    "totals": "Totals",
    "per100possessions": "Per100Possessions",
    "per36": "Per36",
    "per40": "Per40",
    "per100plays": "Per100Plays",
}

_API_TO_MEASURE_SLUG = {v: k for k, v in MEASURE_SLUG_TO_API.items()}
_API_TO_PER_MODE_SLUG = {v: k for k, v in PER_MODE_SLUG_TO_API.items()}

_LEGACY_RAW_FILE_RE = re.compile(
    r"^(dash|clutch|hustle)_(regular_season|playoffs)_(pergame|totals)\.parquet$",
    re.IGNORECASE,
)
_EXTENDED_RAW_FILE_RE = re.compile(
    r"^(dash|clutch|hustle)_(regular_season|playoffs)_"
    r"(base|advanced|usage|misc|scoring|defense)_"
    r"(pergame|totals|per100possessions|per36|per40|per100plays)\.parquet$",
    re.IGNORECASE,
)


def measure_slug(measure_type: str) -> str:
    return _API_TO_MEASURE_SLUG.get(measure_type, measure_type.lower().replace(" ", ""))


def per_mode_slug(per_mode: str) -> str:
    return _API_TO_PER_MODE_SLUG.get(per_mode, per_mode.lower().replace(" ", ""))


def season_type_from_slug(slug: str) -> str:
    return "Regular Season" if slug == "regular_season" else "Playoffs"


def slice_filename(kind: str, season_type: str, measure_type: str, per_mode: str) -> str:
    st_slug = "regular_season" if season_type == "Regular Season" else "playoffs"
    return f"{kind}_{st_slug}_{measure_slug(measure_type)}_{per_mode_slug(per_mode)}.parquet"


def legacy_slice_filename(kind: str, season_type: str, per_mode: str) -> str:
    """Pre-gap-analysis filenames (Base measure only, PerGame/Totals only)."""
    st_slug = "regular_season" if season_type == "Regular Season" else "playoffs"
    return f"{kind}_{st_slug}_{per_mode_slug(per_mode)}.parquet"


def parse_raw_slice_filename(path: Path) -> tuple[str, str, str, str] | None:
    """Return (kind, season_type, measure_type, per_mode) from a raw slice file."""
    name = path.name
    m = _EXTENDED_RAW_FILE_RE.match(name)
    if m:
        kind, season_slug, measure_slug_val, per_slug = m.groups()
        return (
            kind.lower(),
            season_type_from_slug(season_slug),
            MEASURE_SLUG_TO_API[measure_slug_val.lower()],
            PER_MODE_SLUG_TO_API[per_slug.lower()],
        )
    m = _LEGACY_RAW_FILE_RE.match(name)
    if m:
        kind, season_slug, per_slug = m.groups()
        return (
            kind.lower(),
            season_type_from_slug(season_slug),
            "Base",
            PER_MODE_SLUG_TO_API[per_slug.lower()],
        )
    return None


def dash_out_paths(
    out_dir: Path,
    season: str,
    season_type: str,
    measure_type: str,
    per_mode: str,
) -> tuple[Path, Path | None]:
    """Return (canonical_path, legacy_path_if_applicable)."""
    season_dir = out_dir / season
    canonical = season_dir / slice_filename("dash", season_type, measure_type, per_mode)
    legacy: Path | None = None
    if measure_type == "Base" and per_mode in ("PerGame", "Totals"):
        legacy = season_dir / legacy_slice_filename("dash", season_type, per_mode)
    return canonical, legacy


def clutch_out_paths(
    out_dir: Path,
    season: str,
    season_type: str,
    measure_type: str,
    per_mode: str,
) -> tuple[Path, Path | None]:
    season_dir = out_dir / season
    canonical = season_dir / slice_filename("clutch", season_type, measure_type, per_mode)
    legacy: Path | None = None
    if measure_type == "Base" and per_mode in ("PerGame", "Totals"):
        legacy = season_dir / legacy_slice_filename("clutch", season_type, per_mode)
    return canonical, legacy
