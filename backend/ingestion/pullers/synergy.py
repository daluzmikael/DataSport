"""player_synergy / team_synergy <- SynergyPlayTypes.

Play-type breakdowns for ISO / pick-and-roll / spot-up / transition / post-up
questions — the shape of question the vault currently cannot answer at all.

Two things make this cheap compared with the other pullers:

* It is LEAGUE-WIDE per call. One request returns every player for a given play type,
  so the cost is play_types x seasons x entity x offense/defense, not per player.
* Synergy tracking only starts at 2015-16. Older seasons return an empty body, which
  looks identical to a transport failure and would otherwise burn four retries each,
  so the range is clamped rather than discovered.
"""
from __future__ import annotations

import logging

from nba_api.stats.endpoints import synergyplaytypes

from ingestion.config import (
    LEAGUE_ID,
    PULL_STATE_FILE,
    RAW_TABLE_DIRS,
    SEASON_TYPES,
    SYNERGY_PLAY_TYPES,
    SYNERGY_START_SEASON,
)
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import (
    call_with_retry,
    is_resultset_unavailable,
    save_parquet,
)
from ingestion.utils.seasons import iter_seasons, season_type_slug

logger = logging.getLogger(__name__)

# Offensive and defensive splits are separate reads on this endpoint.
_TYPE_GROUPINGS = ("offensive", "defensive")

# Totals is the only per_mode worth storing here: the endpoint's PerGame variant is
# derivable from it, and doubling the call count for that is not worth the rate budget.
_PER_MODE = "Totals"


def _pull(entity: str, seasons: list[str] | None = None) -> None:
    """entity is 'player' or 'team'."""
    abbrev = "P" if entity == "player" else "T"
    table = f"{entity}_synergy"
    out_dir = RAW_TABLE_DIRS[table]

    all_seasons = seasons or iter_seasons()
    usable = [s for s in all_seasons if s >= SYNERGY_START_SEASON]
    skipped = len(all_seasons) - len(usable)
    if skipped:
        logger.info(
            "%s: skipping %s season(s) before %s — Synergy has no data that far back",
            table, skipped, SYNERGY_START_SEASON,
        )

    total = len(usable) * len(SEASON_TYPES) * len(SYNERGY_PLAY_TYPES) * len(_TYPE_GROUPINGS)
    logger.info("%s: %s calls planned", table, total)
    done = 0

    for season in usable:
        for season_type in SEASON_TYPES:
            for play_type in SYNERGY_PLAY_TYPES:
                for grouping in _TYPE_GROUPINGS:
                    done += 1
                    key = f"{table}|{season}|{season_type}|{play_type}|{grouping}"
                    out_path = (
                        out_dir
                        / season
                        / f"{season_type_slug(season_type)}_{play_type.lower()}_{grouping}.parquet"
                    )
                    if is_done(PULL_STATE_FILE, key) and out_path.exists():
                        continue
                    try:
                        ep = call_with_retry(
                            lambda s=season, st=season_type, pt=play_type, g=grouping: (
                                synergyplaytypes.SynergyPlayTypes(
                                    league_id=LEAGUE_ID,
                                    season=s,
                                    season_type_all_star=st,
                                    per_mode_simple=_PER_MODE,
                                    player_or_team_abbreviation=abbrev,
                                    play_type_nullable=pt,
                                    type_grouping_nullable=g,
                                )
                            ),
                            key,
                        )
                        frames = ep.get_data_frames()
                        if not frames or frames[0].empty:
                            mark_done(PULL_STATE_FILE, key)
                            continue
                        df = frames[0]
                        df["season"] = season
                        df["season_type"] = season_type
                        df["play_type"] = play_type
                        df["type_grouping"] = grouping
                        df["per_mode"] = _PER_MODE
                        save_parquet(df, out_path)
                        mark_done(PULL_STATE_FILE, key)
                    except Exception as exc:  # noqa: BLE001
                        if is_resultset_unavailable(exc):
                            mark_done(PULL_STATE_FILE, key)
                            continue
                        mark_failed(PULL_STATE_FILE, key, str(exc))
                        logger.warning("%s failed: %s", key, exc)
                    if done % 50 == 0:
                        logger.info("%s progress %s/%s", table, done, total)


def pull_player_synergy(seasons: list[str] | None = None) -> None:
    _pull("player", seasons)


def pull_team_synergy(seasons: list[str] | None = None) -> None:
    _pull("team", seasons)
