"""Make `player_awards.SEASON` queryable without falsifying what it means.

The column mixes two formats — `'1964-65'` for season awards and `'2008'` for Olympics
and Hall of Fame inductions — and a lexicographic range filter silently mixes them: a
range over 2019-20..2021-22 also swallows the bare `'2020'` and `'2021'` rows.

The obvious fix is to rewrite the bare years into season labels. That would be **wrong**.
Those 334 rows are not season awards:

    110  Olympic Gold Medal        52  Olympic Bronze Medal
    107  Olympic Appearance        34  Olympic Silver Medal
     31  Hall of Fame Inductee

The 2008 Beijing Olympics happened in August 2008 — between the 2007-08 and 2008-09
seasons, belonging to neither. Stamping either label on Chris Paul's gold medal would
invent a fact. Hall of Fame induction is the same: a career honour with a ceremony date,
not a season.

So `SEASON` keeps saying exactly what the source said, and two derived columns carry the
comparable form:

    SEASON_END_YEAR  INTEGER   1964-65 -> 1965,  2008 -> 2008
    IS_SEASON_AWARD  BOOLEAN   True for NBA season awards, False for calendar events

`SEASON_END_YEAR` is the one year both formats agree on, so ranges and equality work
across the whole table. `IS_SEASON_AWARD` lets a query keep the two kinds apart when the
distinction matters — "MVPs in the 2010s" should not return Olympic medals.

    python -m scripts.normalize_awards_season --dry-run
    python -m scripts.normalize_awards_season
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from ingestion.config import STAGING_ROOT  # noqa: E402

_SEASON_LABEL = re.compile(r"^(\d{4})-(\d{2})$")
_BARE_YEAR = re.compile(r"^(\d{4})$")


def season_end_year(value) -> int | None:
    """The year both formats agree on: '1964-65' -> 1965, '2008' -> 2008."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    m = _SEASON_LABEL.match(s)
    if m:
        # A season always spans consecutive years, so end = start + 1. No century
        # arithmetic needed, which is what makes '1999-00' safe.
        return int(m.group(1)) + 1
    m = _BARE_YEAR.match(s)
    if m:
        return int(m.group(1))
    return None


def is_season_award(value) -> bool | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return bool(_SEASON_LABEL.match(str(value).strip()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = Path(STAGING_ROOT) / "player_awards.parquet"
    if not path.exists():
        print(f"not staged: {path}")
        return 1

    df = pd.read_parquet(path)
    if "SEASON" not in df.columns:
        print("player_awards has no SEASON column")
        return 1

    end_year = df["SEASON"].map(season_end_year)
    season_award = df["SEASON"].map(is_season_award)

    n_season = int(season_award.fillna(False).sum())
    n_event = int((~season_award.fillna(True)).sum())
    n_unparsed = int(end_year.isna().sum())

    print(f"rows                : {len(df):,}")
    print(f"season-label rows   : {n_season:,}  (e.g. '2023-24' -> SEASON_END_YEAR 2024)")
    print(f"calendar-event rows : {n_event:,}  (Olympics, Hall of Fame — left as-is)")
    print(f"unparsed SEASON     : {n_unparsed:,}")
    print()
    sample = df.loc[season_award == False, ["PLAYER_NAME", "DESCRIPTION", "SEASON"]].head(3)
    if not sample.empty:
        print("calendar events keep their year:")
        print(sample.to_string(index=False))
        print()

    if args.dry_run:
        print("dry run — nothing written.")
        return 0

    df["SEASON_END_YEAR"] = end_year.astype("Int64")
    df["IS_SEASON_AWARD"] = season_award.astype("boolean")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(f".parquet.bak-{stamp}")
    shutil.copy2(path, backup)
    df.to_parquet(path, index=False)
    print(f"written (backup: {backup.name})")
    print("Added SEASON_END_YEAR (Int64) and IS_SEASON_AWARD (boolean). SEASON unchanged.")
    print("Restart the backend so DuckDB reloads the view.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
