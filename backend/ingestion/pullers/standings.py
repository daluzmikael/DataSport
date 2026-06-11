"""team_standings <- leaguestandingsv3"""
from __future__ import annotations

import logging

from nba_api.stats.endpoints import leaguestandingsv3

from ingestion.config import LEAGUE_ID, PULL_STATE_FILE, RAW_TABLE_DIRS
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import call_with_retry, save_parquet
from ingestion.utils.seasons import iter_seasons, season_type_slug

logger = logging.getLogger(__name__)


def pull_team_standings(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_dir = RAW_TABLE_DIRS["team_standings"]

    for season in seasons:
        for season_type in ("Regular Season",):
            key = f"standings|{season}|{season_type}"
            out_path = out_dir / season / f"{season_type_slug(season_type)}.parquet"
            if is_done(PULL_STATE_FILE, key) and out_path.exists():
                logger.info("skip %s", key)
                continue
            try:
                ep = call_with_retry(
                    lambda: leaguestandingsv3.LeagueStandingsV3(
                        league_id=LEAGUE_ID,
                        season=season,
                        season_type=season_type,
                    ),
                    key,
                )
                df = ep.get_data_frames()[0]
                save_parquet(df, out_path)
                mark_done(PULL_STATE_FILE, key)
                logger.info("saved %s (%s rows)", out_path, len(df))
            except Exception as exc:  # noqa: BLE001
                mark_failed(PULL_STATE_FILE, key, str(exc))
                logger.exception("failed %s", key)
