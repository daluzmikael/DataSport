"""Standardize player-name and date formats across the staged parquet files.

Two inconsistencies, both of which make correct queries return nothing:

**Names (#5).** `player_on_off` stores "Tatum, Jayson" while every other player table
stores "Jayson Tatum". The whole table — 62k rows, the only on/off data in the vault —
is unreachable by name.

Names are resolved by `PLAYER_ID` against `player_season_stats` rather than by flipping
the string, because the string form has traps: 'Butler III, Jimmy' must become
'Jimmy Butler III' (not 'III Jimmy Butler'), and 'Yao Ming', 'Zhou Qi' and 'Nene' carry
no comma at all and must be left alone. The id join gets those right for free; the
string flip is only a fallback for ids absent from the season table.

**Dates (#6).** Five different formats across eight columns:

    '1997-06-13T00:00:00'   player_game_logs, team_game_logs, player_career.DATE_EST, player_bio
    '20260322'              player_shot_chart
    '2000-10-31T20:30:00Z'  game_context
    'Mar 19 1997'           player_career.GAME_DATE
    'JUN 25, 1966'          team_roster

All become 'YYYY-MM-DD'. Kept as VARCHAR deliberately — that sorts and compares correctly
as a string, so `GAME_DATE >= '2024-01-01'` just works, with no type migration and no
change to how anything reads them.

Time-of-day is dropped. Only `game_context.gameDate` carries one, and it is null on
703,554 of 741,532 rows; the raw pull keeps it if tipoff time is ever needed.

    python -m scripts.standardize_staged_formats --dry-run
    python -m scripts.standardize_staged_formats

Every modified file is backed up alongside itself first.
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

# table -> date columns to normalize
DATE_COLUMNS: dict[str, tuple[str, ...]] = {
    "player_game_logs": ("GAME_DATE",),
    "team_game_logs": ("GAME_DATE",),
    "player_shot_chart": ("GAME_DATE",),
    "game_context": ("gameDate",),
    "player_career": ("GAME_DATE", "DATE_EST"),
    "player_bio": ("BIRTHDATE",),
    "team_roster": ("BIRTH_DATE",),
}

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_COMPACT = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_MON_D_Y = re.compile(r"^([A-Za-z]{3,})\.?\s+(\d{1,2}),?\s+(\d{4})$")


def to_iso_date(value) -> object:
    """Any of the five observed formats -> 'YYYY-MM-DD'. Unknown input passes through."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return value
    s = str(value).strip()
    if not s:
        return value

    m = _ISO.match(s)          # '1997-06-13T00:00:00', '2000-10-31T20:30:00Z', already-clean
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = _COMPACT.match(s)      # '20260322'
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = _MON_D_Y.match(s)      # 'Mar 19 1997', 'JUN 25, 1966'
    if m:
        mon = _MONTHS.get(m.group(1)[:3].lower())
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}"

    return value               # leave anything unrecognised untouched


def flip_comma_name(value) -> object:
    """'Butler III, Jimmy' -> 'Jimmy Butler III'. No comma means no change."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return value
    s = str(value).strip()
    if ", " not in s:
        return value           # 'Yao Ming', 'Nene' — already correct
    last, first = s.split(", ", 1)
    return f"{first} {last}".strip()


def canonical_name_map(root: Path) -> dict:
    """PLAYER_ID -> published name, taken from player_season_stats."""
    path = root / "player_season_stats.parquet"
    if not path.exists():
        return {}
    df = pd.read_parquet(path, columns=["PLAYER_ID", "PLAYER_NAME"])
    df = df.dropna(subset=["PLAYER_ID", "PLAYER_NAME"]).drop_duplicates("PLAYER_ID")
    return dict(zip(df["PLAYER_ID"], df["PLAYER_NAME"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report changes, write nothing")
    args = ap.parse_args()

    root = Path(STAGING_ROOT)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    id_to_name = canonical_name_map(root)
    print(f"canonical name map: {len(id_to_name):,} players\n")

    targets = sorted(set(DATE_COLUMNS) | {"player_on_off"})
    changed_files = 0

    for table in targets:
        path = root / f"{table}.parquet"
        if not path.exists():
            print(f"{table:22} SKIP (not staged)")
            continue

        df = pd.read_parquet(path)
        notes: list[str] = []

        # ---- names -------------------------------------------------------
        if table == "player_on_off" and "PLAYER_NAME" in df.columns:
            before = df["PLAYER_NAME"].copy()
            if "PLAYER_ID" in df.columns:
                mapped = df["PLAYER_ID"].map(id_to_name)
                df["PLAYER_NAME"] = mapped.where(
                    mapped.notna(), df["PLAYER_NAME"].map(flip_comma_name)
                )
                by_id = int(mapped.notna().sum())
                notes.append(f"names: {by_id:,} by PLAYER_ID, "
                             f"{len(df) - by_id:,} by string flip")
            else:
                df["PLAYER_NAME"] = df["PLAYER_NAME"].map(flip_comma_name)
                notes.append("names: string flip only (no PLAYER_ID column)")
            n = int((before.astype("string") != df["PLAYER_NAME"].astype("string")).fillna(False).sum())
            notes.append(f"{n:,} name values changed")
            if n:
                ex = before[before != df["PLAYER_NAME"]].index[:1]
                for i in ex:
                    notes.append(f"e.g. {before.loc[i]!r} -> {df.loc[i, 'PLAYER_NAME']!r}")

        # ---- dates -------------------------------------------------------
        for col in DATE_COLUMNS.get(table, ()):
            if col not in df.columns:
                continue
            before = df[col].copy()
            df[col] = df[col].map(to_iso_date)
            n = int((before.astype("string") != df[col].astype("string")).fillna(False).sum())
            if n:
                first = before[before.notna()].index[:1]
                sample = ""
                for i in first:
                    sample = f"  ({before.loc[i]!r} -> {df.loc[i, col]!r})"
                notes.append(f"{col}: {n:,} values reformatted{sample}")
            else:
                notes.append(f"{col}: already standard")

        if not notes:
            print(f"{table:22} -- nothing to do")
            continue

        print(f"{table:22} {'; '.join(notes)}")
        if not args.dry_run:
            backup = path.with_suffix(f".parquet.bak-{stamp}")
            shutil.copy2(path, backup)
            df.to_parquet(path, index=False)
            print(f"{'':22} written (backup: {backup.name})")
        changed_files += 1

    print()
    print(f"{changed_files} file(s) {'would be ' if args.dry_run else ''}updated")
    if args.dry_run:
        print("dry run — nothing written.")
    else:
        print("Restart the backend so DuckDB reloads the views.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
