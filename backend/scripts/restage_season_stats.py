"""Restage ONLY player_season_stats and team_season_stats.

Rebuilds the two wide season tables so they carry the season-level advanced dash
slices (TS_PCT, EFG_PCT, USG_PCT, PIE, ratings, pace) that were pulled into raw on
2026-06-11 but never staged, and applies canonical team identity on write.

Deliberately narrow:
  * no re-pull — every raw file is already on disk
  * phases 2-6 are not touched
  * the other phase-1 tables (standings, shot zones) are not touched
  * grain is unchanged: one row per entity per season per season_type per per_mode
  * no measure_type column, no Per36/Per40/Per100Possessions rows

    python -m scripts.restage_season_stats --dry-run
    python -m scripts.restage_season_stats

Timestamped backups are written beside the originals before anything is overwritten.
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from ingestion.config import STAGING_ROOT  # noqa: E402
from ingestion.stagers.phase1 import (  # noqa: E402
    stage_player_season_stats,
    stage_team_season_stats,
)

TARGETS = ("player_season_stats", "team_season_stats")


def summarize(path: Path, label: str) -> None:
    if not path.exists():
        print(f"  {label}: (missing)")
        return
    df = pd.read_parquet(path)
    print(f"  {label}: {len(df):,} rows x {df.shape[1]} cols")
    if "per_mode" in df.columns:
        print(f"      per_mode: {sorted(df['per_mode'].dropna().unique())}")
    print(f"      measure_type column: {'measure_type' in df.columns}")
    adv = [c for c in ("TS_PCT", "EFG_PCT", "USG_PCT", "PIE") if c in df.columns]
    print(f"      advanced cols: {adv or 'none'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report current state, write nothing")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    root = Path(STAGING_ROOT)
    paths = {name: root / f"{name}.parquet" for name in TARGETS}

    print("BEFORE")
    for name, p in paths.items():
        summarize(p, name)

    if args.dry_run:
        print("\ndry run — nothing written.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    print("\nbacking up")
    for name, p in paths.items():
        if p.exists():
            backup = p.with_suffix(f".parquet.bak-{stamp}")
            shutil.copy2(p, backup)
            print(f"  {p.name} -> {backup.name}")

    print("\nrestaging")
    stage_player_season_stats()
    stage_team_season_stats()

    print("\nAFTER")
    for name, p in paths.items():
        summarize(p, name)

    print("\nRestart the backend (or POST /api/staging/refresh) to reload the views.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
