"""Pull pre-1996-97 data, which the main dash endpoints cannot reach.

The vault starts at 1996-97 because `LeagueDashPlayerStats` — the endpoint every phase-1
puller uses — returns nothing earlier. That floor is what makes every "all-time" answer
quietly wrong: asked for the career assists leader, the vault says Chris Paul (12,552)
because John Stockton's 15,806 are mostly outside the window, and asked for the scoring
leader it puts Kobe second because Kareem and Karl Malone are absent entirely.

Three endpoints do reach back, verified live:

    LeagueLeaders            1951-52 onward, ~30 box-score columns per season
    PlayerCareerStats        full career totals for any player, any era
    AllTimeLeadersGrids      all-time top-N per stat, already ranked

`LeagueLeaders` is the workhorse: it is one request per season per stat category and
returns every qualified player, so 45 pre-1996 seasons is 45 requests. It carries no
advanced metrics — those simply did not exist — but it has the full counting line plus
percentages, which is what an all-time question actually needs.

    python -m ingestion.pullers.legacy --seasons 1951-52:1995-96
    python -m ingestion.pullers.legacy --careers          # career totals for everyone
    python -m ingestion.pullers.legacy --all-time

Output goes to data/raw/legacy/ and is staged separately, so nothing here touches the
existing 1996-97+ tables.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from ingestion.config import RAW_ROOT  # noqa: E402

logger = logging.getLogger(__name__)

LEGACY_ROOT = Path(RAW_ROOT) / "legacy"

# NBA.com has no LeagueLeaders data before this; 1946-47 through 1950-51 return empty.
EARLIEST_SEASON = "1951-52"
# Where the existing vault takes over.
VAULT_START = "1996-97"

# Be polite: stats.nba.com throttles aggressively and a 45-season sweep is a long run.
REQUEST_DELAY_SECONDS = float(1.0)
MAX_RETRIES = 3


def season_range(first: str, last: str) -> list[str]:
    out: list[str] = []
    start, end = int(first[:4]), int(last[:4])
    for y in range(start, end + 1):
        out.append(f"{y}-{str(y + 1)[-2:]}")
    return out


def _with_retry(fn, label: str):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — stats.nba.com is flaky under load
            if attempt == MAX_RETRIES:
                logger.error("%s failed after %d attempts: %s", label, MAX_RETRIES, exc)
                return None
            wait = REQUEST_DELAY_SECONDS * (2 ** attempt)
            logger.warning("%s attempt %d failed (%s) — retrying in %.1fs",
                           label, attempt, exc, wait)
            time.sleep(wait)
    return None


def pull_season_leaders(season: str, season_type: str = "Regular Season") -> pd.DataFrame | None:
    """Every qualified player's box-score line for one season."""
    from nba_api.stats.endpoints import leagueleaders

    def call():
        return leagueleaders.LeagueLeaders(
            season=season,
            season_type_all_star=season_type,
            stat_category_abbreviation="PTS",  # ranks by PTS; all columns come back
            per_mode48="Totals",
        ).get_data_frames()[0]

    df = _with_retry(call, f"LeagueLeaders {season} {season_type}")
    if df is None or df.empty:
        return None
    df["season"] = season
    df["season_type"] = season_type
    return df


def pull_seasons(first: str, last: str, season_types=("Regular Season", "Playoffs")) -> Path:
    out_dir = LEGACY_ROOT / "season_leaders"
    out_dir.mkdir(parents=True, exist_ok=True)

    for season in season_range(first, last):
        for season_type in season_types:
            slug = season_type.lower().replace(" ", "_")
            path = out_dir / f"{season}_{slug}.parquet"
            if path.exists():
                logger.info("skip %s (already pulled)", path.name)
                continue
            df = pull_season_leaders(season, season_type)
            time.sleep(REQUEST_DELAY_SECONDS)
            if df is None:
                logger.warning("no data: %s %s", season, season_type)
                continue
            df.to_parquet(path, index=False)
            logger.info("wrote %s (%d rows)", path.name, len(df))
    return out_dir


def pull_career_totals(player_ids: list[int] | None = None) -> Path:
    """Career regular-season totals — the number an all-time question actually wants."""
    from nba_api.stats.endpoints import commonallplayers, playercareerstats

    out_dir = LEGACY_ROOT / "career_totals"
    out_dir.mkdir(parents=True, exist_ok=True)

    if player_ids is None:
        roster = _with_retry(
            lambda: commonallplayers.CommonAllPlayers(is_only_current_season=0).get_data_frames()[0],
            "CommonAllPlayers",
        )
        if roster is None:
            return out_dir
        # Anyone whose career ended before the vault begins is the point of this pull.
        roster["TO_YEAR"] = pd.to_numeric(roster["TO_YEAR"], errors="coerce")
        player_ids = roster.loc[roster["TO_YEAR"].notna(), "PERSON_ID"].astype(int).tolist()
        logger.info("%d players to pull", len(player_ids))

    frames: list[pd.DataFrame] = []
    for i, pid in enumerate(player_ids, 1):
        path = out_dir / f"{pid}.parquet"
        if path.exists():
            continue
        df = _with_retry(
            lambda: playercareerstats.PlayerCareerStats(player_id=pid).get_data_frames()[1],
            f"PlayerCareerStats {pid}",
        )
        time.sleep(REQUEST_DELAY_SECONDS)
        if df is None or df.empty:
            continue
        df["PLAYER_ID"] = pid
        df.to_parquet(path, index=False)
        frames.append(df)
        if i % 50 == 0:
            logger.info("... %d/%d players", i, len(player_ids))
    return out_dir


def pull_all_time_leaders(top_n: int = 500) -> Path:
    """Pre-ranked all-time leaderboards, one frame per stat."""
    from nba_api.stats.endpoints import alltimeleadersgrids

    out_dir = LEGACY_ROOT / "all_time"
    out_dir.mkdir(parents=True, exist_ok=True)

    res = _with_retry(
        lambda: alltimeleadersgrids.AllTimeLeadersGrids(topx=top_n),
        "AllTimeLeadersGrids",
    )
    if res is None:
        return out_dir

    # Name each grid after its stat column. nba_api 1.11 has no `get_data_sets()`, and
    # `data_sets` holds dataset OBJECTS rather than names — using them as filenames
    # produces `<...endpoint.dataset object at 0x...>.parquet` and an OSError. The stat
    # column is the grid's identity anyway, so derive it and skip the indirection.
    frames = res.get_data_frames()
    labels: list[str] = []
    for df in frames:
        stat = next(
            (c for c in df.columns
             if c not in ("PLAYER_ID", "PLAYER_NAME", "IS_ACTIVE_FLAG")
             and not c.endswith("_RANK")),
            "grid",
        )
        labels.append(str(stat).lower())

    for label, df in zip(labels, frames):
        if df is None or df.empty:
            continue
        df.to_parquet(out_dir / f"{label}.parquet", index=False)
        logger.info("wrote all_time/%s.parquet (%d rows)", label, len(df))
    return out_dir


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seasons", help="range like 1951-52:1995-96")
    ap.add_argument("--careers", action="store_true", help="career totals for every player")
    ap.add_argument("--all-time", action="store_true", help="all-time leader grids")
    ap.add_argument("--top-n", type=int, default=500)
    args = ap.parse_args()

    if not (args.seasons or args.careers or args.all_time):
        ap.print_help()
        return 1

    if args.seasons:
        first, _, last = args.seasons.partition(":")
        first = first or EARLIEST_SEASON
        last = last or "1995-96"
        if first < EARLIEST_SEASON:
            logger.warning("NBA.com has no season data before %s — starting there", EARLIEST_SEASON)
            first = EARLIEST_SEASON
        print(f"Pulling season leaders {first} -> {last}")
        print(f"  ~{len(season_range(first, last)) * 2} requests at {REQUEST_DELAY_SECONDS}s apart")
        pull_seasons(first, last)

    if args.careers:
        print("Pulling career totals (long run — resumable, skips what exists)")
        pull_career_totals()

    if args.all_time:
        print(f"Pulling all-time leader grids (top {args.top_n})")
        pull_all_time_leaders(args.top_n)

    print(f"\nDone. Raw output under {LEGACY_ROOT}")
    print("Nothing staged yet — the 1996-97+ tables are untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
