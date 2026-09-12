"""Apply canonical team identity to the ALREADY-STAGED parquet files.

Why this exists rather than just re-running `stage_all`:

The stagers now call `normalize_team_identity`, so every future re-stage is clean.
But re-staging `player_season_stats` / `team_season_stats` today would also pull in
the raw `Advanced/Usage/Scoring/Misc` measure-type slices that the current staged
files predate, which changes those tables' grain and row count ~14x. That is a
separate decision, deliberately deferred.

So this script applies exactly the team-name fix to the existing files, in place,
leaving every other column and the row count untouched.

    python -m scripts.normalize_staged_team_names --dry-run
    python -m scripts.normalize_staged_team_names

A timestamped backup of every modified file is written next to it before any change.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from ingestion.config import STAGING_ROOT  # noqa: E402
from ingestion.stagers._helpers import normalize_team_identity  # noqa: E402

TEAM_COLUMNS = {
    "TEAM_NAME", "team_name", "TEAM_CITY", "TeamCity", "team_city", "teamCity",
    "TeamName", "teamName", "TEAM_ABBREVIATION", "team_abbreviation", "teamTricode",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report changes, write nothing")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = Path(STAGING_ROOT)
    files = sorted(root.glob("*.parquet"))
    if not files:
        print(f"no staged parquet files under {root}")
        return 1

    total_changed = 0
    for path in files:
        try:
            df = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            print(f"{path.name:28} SKIP (read error: {exc})")
            continue

        cols = [c for c in df.columns if c in TEAM_COLUMNS]
        if not cols:
            print(f"{path.name:28} -- no team identity columns")
            continue

        before = df[cols].copy()
        after = normalize_team_identity(df.copy())

        diffs: dict[str, int] = {}
        samples: list[str] = []
        for c in cols:
            # NA-safe comparison. A plain `!=` propagates pd.NA, which then counts as
            # truthy in .sum(), so null-heavy columns reported tens of thousands of
            # phantom "nan -> nan" changes on tables the normalizer never touched.
            b, a = before[c], after[c]
            both_null = b.isna() & a.isna()
            changed_mask = (b.astype("string") != a.astype("string")).fillna(True) & ~both_null
            n = int(changed_mask.sum())
            if n:
                diffs[c] = n
                ex = changed_mask.idxmax()
                samples.append(f"{c}: {before.at[ex, c]!r} -> {after.at[ex, c]!r}")

        if not diffs:
            print(f"{path.name:28} OK (already canonical)")
            continue

        total_changed += 1
        detail = ", ".join(f"{c}×{n:,}" for c, n in diffs.items())
        print(f"{path.name:28} CHANGE {detail}")
        for s in samples[:3]:
            print(f"{'':30}   {s}")

        if not args.dry_run:
            backup = path.with_suffix(f".parquet.bak-{stamp}")
            shutil.copy2(path, backup)
            after.to_parquet(path, index=False)
            print(f"{'':30}   written (backup: {backup.name})")

    print()
    print(f"{total_changed} file(s) {'would be' if args.dry_run else ''} changed")
    if args.dry_run:
        print("dry run — nothing written. Re-run without --dry-run to apply.")
    else:
        print("Restart the backend (or POST /api/staging/refresh) to reload the views.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
