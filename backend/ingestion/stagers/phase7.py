"""Stage phase-7 tables: player bio, team rosters, awards, franchise history.

These are the profile-page tables. Two of them are PLAYER-grain rather than
season-grain, which is unusual for this vault and worth stating in the catalog: a
question like "how tall is Wembanyama" has no season in it.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion.config import RAW_TABLE_DIRS, STAGING_ROOT
from ingestion.stagers._helpers import normalize_team_identity

logger = logging.getLogger(__name__)


def _concat_flat(root: Path, label: str) -> pd.DataFrame:
    """Concatenate every parquet directly under `root` (one file per player)."""
    frames = []
    for path in sorted(root.glob("*.parquet")):
        try:
            df = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s: unreadable %s (%s)", label, path.name, exc)
            continue
        if not df.empty:
            frames.append(df)
    if not frames:
        logger.warning("no %s data to stage", label)
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _write(df: pd.DataFrame, name: str) -> Path:
    out_path = STAGING_ROOT / f"{name}.parquet"
    if df.empty:
        return out_path
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    df = normalize_team_identity(df)
    df.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows, %s cols)", out_path, len(df), len(df.columns))
    return out_path


def _numeric_bio_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add sortable twins for the columns CommonPlayerInfo publishes as text.

    Every one of these is a string in the raw feed, and each one produces a wrong
    answer when a query treats it as a number:

    * `HEIGHT` is "6-9". Sorted as text, "6-10" lands BELOW "6-9", so a tallest-player
      leaderboard quietly drops every player between 6'10" and 6'11".
    * `DRAFT_NUMBER` is "1", "54" — or "Undrafted". Cast loosely, "Undrafted" becomes
      0, and "who was drafted first overall in 2003" came back saying nobody was,
      because a wall of undrafted players sorted ahead of LeBron.
    * `WEIGHT` is a numeric string, harmless but inconsistent with the rest.

    The numeric twins are NULL where the text value has no number in it, which is the
    honest representation of "undrafted" and keeps those rows out of any ranking.
    """
    if df.empty:
        return df

    if "HEIGHT" in df.columns:
        parts = df["HEIGHT"].astype(str).str.strip().str.extract(r"^(\d+)-(\d+)$")
        df["HEIGHT_INCHES"] = (
            pd.to_numeric(parts[0], errors="coerce") * 12
            + pd.to_numeric(parts[1], errors="coerce")
        )

    if "WEIGHT" in df.columns:
        df["WEIGHT_LBS"] = pd.to_numeric(
            df["WEIGHT"].astype(str).str.strip(), errors="coerce"
        )

    for source, target in (
        ("DRAFT_YEAR", "DRAFT_YEAR_NUM"),
        ("DRAFT_ROUND", "DRAFT_ROUND_NUM"),
        ("DRAFT_NUMBER", "DRAFT_NUMBER_NUM"),
    ):
        if source in df.columns:
            df[target] = pd.to_numeric(
                df[source].astype(str).str.strip(), errors="coerce"
            )

    return df


def stage_player_bio() -> Path:
    df = _numeric_bio_columns(_concat_flat(Path(RAW_TABLE_DIRS["player_bio"]), "player_bio"))
    return _write(df, "player_bio")


def stage_player_awards() -> Path:
    df = _concat_flat(Path(RAW_TABLE_DIRS["player_awards"]), "player_awards")
    if not df.empty and {"FIRST_NAME", "LAST_NAME"}.issubset(df.columns):
        # The endpoint splits the name, which leaves the table unfilterable by person
        # and makes the router reject it outright ("no name column"). Compose the
        # published form so it matches every other player table.
        df.insert(
            1,
            "PLAYER_NAME",
            (df["FIRST_NAME"].fillna("").astype(str).str.strip()
             + " "
             + df["LAST_NAME"].fillna("").astype(str).str.strip()).str.strip(),
        )
    return _write(df, "player_awards")


def stage_team_roster() -> Path:
    root = Path(RAW_TABLE_DIRS["team_roster"])
    frames = []
    for season_dir in sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []:
        for path in sorted(season_dir.glob("*.parquet")):
            df = pd.read_parquet(path)
            if df.empty:
                continue
            # CommonTeamRoster returns SEASON as a bare start year ("1996"), which
            # does not match the hyphenated labels every other table uses and made a
            # season filter return nothing. Normalise to the vault's format and drop
            # the duplicate the earlier concat introduced.
            df["season"] = season_dir.name
            if "SEASON" in df.columns:
                df = df.drop(columns=["SEASON"])
            df = df.drop(columns=[c for c in df.columns if c == "season_1"], errors="ignore")
            # CommonTeamRoster returns only TeamID — no team name at all — so the table
            # cannot be filtered by the name a user actually types. Compose the era's
            # own name from the id, so "the 2016-17 Warriors" resolves.
            if "TeamID" in df.columns:
                from ingestion.team_identity import identity_for_id

                idents = [identity_for_id(t, season_dir.name) for t in df["TeamID"]]
                df["TEAM_NAME"] = [i.full_name if i else None for i in idents]
                df["TEAM_ABBREVIATION"] = [i.tricode if i else None for i in idents]
            frames.append(df)
    if not frames:
        logger.warning("no team_roster data to stage")
        return STAGING_ROOT / "team_roster.parquet"
    return _write(pd.concat(frames, ignore_index=True), "team_roster")


def stage_franchise_history() -> Path:
    root = Path(RAW_TABLE_DIRS["franchise_history"])
    path = root / "franchise_history.parquet"
    if not path.exists():
        logger.warning("no franchise_history data to stage")
        return STAGING_ROOT / "franchise_history.parquet"
    # Rows are franchise-era records (START_YEAR/END_YEAR), not seasons, so team
    # identity normalization is deliberately skipped — a Sonics era row must keep
    # saying Seattle, and there is no `season` column to place it with anyway.
    df = pd.read_parquet(path)
    if {"TEAM_CITY", "TEAM_NAME"}.issubset(df.columns):
        # TEAM_NAME holds the nickname only ("Celtics") with the city in TEAM_CITY —
        # the same split that made "Los Angeles Lakers" match nothing on
        # team_standings. Add the joined form; the era's own city is preserved, so a
        # Seattle row still reads "Seattle SuperSonics".
        df.insert(
            df.columns.get_loc("TEAM_NAME") + 1,
            "TEAM_FULL_NAME",
            (df["TEAM_CITY"].fillna("").astype(str).str.strip()
             + " "
             + df["TEAM_NAME"].fillna("").astype(str).str.strip()).str.strip(),
        )
    out_path = STAGING_ROOT / "franchise_history.parquet"
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    logger.info("wrote %s (%s rows)", out_path, len(df))
    return out_path


def stage_phase7() -> None:
    stage_player_bio()
    stage_team_roster()
    stage_player_awards()
    stage_franchise_history()
