"""Stage the pre-1996-97 pulls into queryable tables.

Two tables, deliberately separate from the modern ones:

**`legacy_season_stats`** — one row per player per season per season_type, 1951-52
through 1995-96, from `LeagueLeaders`. Column names are aligned to
`player_season_stats` (`PLAYER_NAME`, `season`, `season_type`, `per_mode`, `GP`, `PTS`
…) so a question does not have to be phrased differently depending on the era.

**`all_time_leaders`** — NBA.com's own career leaderboards, already ranked, covering
every era. This is what actually fixes the all-time questions: asked for the career
assists leader the vault said Chris Paul (12,552) because Stockton's 15,806 are mostly
outside the window, and it put Kobe second for points because Kareem and Malone are
absent. One read of this table answers those correctly.

**Why not append into `player_season_stats`.** That table is 289 columns of modern
box-score plus advanced metrics; `LeagueLeaders` returns about 30 and none of the
advanced ones, because they did not exist. Appending would add ~5,000 rows that are
NULL across 250 columns, and every existing aggregate, floor and rate leaderboard would
silently start including rows with no denominator. A separate table keeps the modern
tables exactly as they are, and the router picks between them by season.

Per-mode note: `LeagueLeaders` is pulled with `per_mode48='Totals'`, so `per_mode` is
set to `Totals` on every row. There is no per-game variant for these seasons — deriving
one by dividing by GP would be inventing precision the source does not have.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_ROOT, STAGING_ROOT

logger = logging.getLogger(__name__)

LEGACY_RAW = Path(RAW_ROOT) / "legacy"

# LeagueLeaders -> player_season_stats spelling, so both eras answer to the same names.
_RENAME = {
    "PLAYER": "PLAYER_NAME",
    "TEAM": "TEAM_ABBREVIATION",
}

# Dropped: RANK is a per-request artifact of the stat we happened to sort by, and EFF /
# AST_TOV / STL_TOV are NBA.com's own composites that no other staged table carries.
_DROP = ("RANK", "EFF", "AST_TOV", "STL_TOV")


def stage_legacy_season_stats() -> Path | None:
    src = LEGACY_RAW / "season_leaders"
    out_path = Path(STAGING_ROOT) / "legacy_season_stats.parquet"
    if not src.exists():
        logger.warning("no legacy season pulls at %s", src)
        return None

    frames: list[pd.DataFrame] = []
    for path in sorted(src.glob("*.parquet")):
        try:
            df = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("skip %s: %s", path.name, exc)
            continue
        if df.empty:
            continue
        frames.append(df)

    if not frames:
        logger.warning("no legacy season rows to stage")
        return None

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.rename(columns=_RENAME)
    combined = combined.drop(columns=[c for c in _DROP if c in combined.columns])

    # These seasons are totals only; say so in the data rather than leaving it implied.
    combined["per_mode"] = "Totals"

    # The three-point line did not exist before 1979-80, so those columns are None
    # rather than 0 in the source. Leave them null: a null means "not a thing yet",
    # and writing 0 would make it look like players tried and missed.
    for col in ("FG3M", "FG3A", "FG3_PCT"):
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    lead = [c for c in ("PLAYER_ID", "PLAYER_NAME", "season", "season_type", "per_mode",
                        "TEAM_ID", "TEAM_ABBREVIATION") if c in combined.columns]
    rest = [c for c in combined.columns if c not in lead]
    combined = combined[lead + rest]

    Path(STAGING_ROOT).mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols, %s -> %s)", out_path, len(combined),
                len(combined.columns), combined["season"].min(), combined["season"].max())
    return out_path


def stage_all_time_leaders() -> Path | None:
    """Flatten NBA.com's per-stat leader grids into one long table."""
    src = LEGACY_RAW / "all_time"
    out_path = Path(STAGING_ROOT) / "all_time_leaders.parquet"
    if not src.exists():
        logger.warning("no all-time pulls at %s", src)
        return None

    rows: list[pd.DataFrame] = []
    for path in sorted(src.glob("*.parquet")):
        try:
            df = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("skip %s: %s", path.name, exc)
            continue
        if df.empty or "PLAYER_ID" not in df.columns:
            continue

        # Each grid is (PLAYER_ID, PLAYER_NAME, <STAT>, <STAT>_RANK, IS_ACTIVE_FLAG).
        # Normalising to one row per player per stat means a single table answers
        # "most career X" for any X, instead of one column per grid.
        stat_cols = [
            c for c in df.columns
            if c not in ("PLAYER_ID", "PLAYER_NAME", "IS_ACTIVE_FLAG")
            and not c.endswith("_RANK")
        ]
        for stat in stat_cols:
            rank_col = f"{stat}_RANK"
            block = pd.DataFrame({
                "PLAYER_ID": df["PLAYER_ID"],
                "PLAYER_NAME": df.get("PLAYER_NAME"),
                "STAT": stat,
                "VALUE": pd.to_numeric(df[stat], errors="coerce"),
                "STAT_RANK": pd.to_numeric(df[rank_col], errors="coerce")
                if rank_col in df.columns else pd.NA,
                "IS_ACTIVE": df.get("IS_ACTIVE_FLAG"),
                "SOURCE_GRID": path.stem,
            })
            rows.append(block)

    if not rows:
        logger.warning("no all-time rows to stage")
        return None

    combined = pd.concat(rows, ignore_index=True).dropna(subset=["VALUE"])
    Path(STAGING_ROOT).mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, stats: %s)", out_path, len(combined),
                ", ".join(sorted(combined["STAT"].unique())[:12]))
    return out_path


def stage_all() -> list[Path]:
    out = []
    for fn in (stage_legacy_season_stats, stage_all_time_leaders):
        path = fn()
        if path:
            out.append(path)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for p in stage_all():
        print("staged:", p)
