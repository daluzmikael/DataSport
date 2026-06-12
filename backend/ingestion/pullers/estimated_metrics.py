"""player_estimated_metrics / team_estimated_metrics <- playerestimatedmetrics / teamestimatedmetrics"""
from __future__ import annotations

import logging

from nba_api.stats.endpoints import playerestimatedmetrics, teamestimatedmetrics

from ingestion.config import LEAGUE_ID, PULL_STATE_FILE, RAW_TABLE_DIRS, SEASON_TYPES
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import call_with_retry, save_parquet
from ingestion.utils.seasons import iter_seasons, season_type_slug

logger = logging.getLogger(__name__)


def pull_player_estimated_metrics(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_root = RAW_TABLE_DIRS["player_estimated_metrics"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            key = f"player_estimated|{season}|{season_type}"
            st = season_type_slug(season_type)
            out_path = out_root / season / f"{st}.parquet"
            if is_done(PULL_STATE_FILE, key) and out_path.exists():
                continue
            try:
                ep = call_with_retry(
                    lambda s=season, st=season_type: playerestimatedmetrics.PlayerEstimatedMetrics(
                        league_id=LEAGUE_ID,
                        season=s,
                        season_type=st,
                    ),
                    key,
                )
                out_path.parent.mkdir(parents=True, exist_ok=True)
                save_parquet(ep.get_data_frames()[0], out_path)
                mark_done(PULL_STATE_FILE, key)
                logger.info("saved %s", out_path)
            except Exception as exc:  # noqa: BLE001
                mark_failed(PULL_STATE_FILE, key, str(exc))
                logger.exception("failed %s", key)


def pull_team_estimated_metrics(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_root = RAW_TABLE_DIRS["team_estimated_metrics"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            key = f"team_estimated|{season}|{season_type}"
            st = season_type_slug(season_type)
            out_path = out_root / season / f"{st}.parquet"
            if is_done(PULL_STATE_FILE, key) and out_path.exists():
                continue
            try:
                ep = call_with_retry(
                    lambda s=season, st=season_type: teamestimatedmetrics.TeamEstimatedMetrics(
                        league_id=LEAGUE_ID,
                        season=s,
                        season_type=st,
                    ),
                    key,
                )
                out_path.parent.mkdir(parents=True, exist_ok=True)
                save_parquet(ep.get_data_frames()[0], out_path)
                mark_done(PULL_STATE_FILE, key)
                logger.info("saved %s", out_path)
            except Exception as exc:  # noqa: BLE001
                mark_failed(PULL_STATE_FILE, key, str(exc))
                logger.exception("failed %s", key)
