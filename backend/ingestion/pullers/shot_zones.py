"""player_shot_zones / team_shot_zones <- leaguedash*shotlocations"""
from __future__ import annotations

import logging

from nba_api.stats.endpoints import leaguedashplayershotlocations, leaguedashteamshotlocations

from ingestion.config import PER_MODES_DASH, PULL_STATE_FILE, RAW_TABLE_DIRS, SEASON_TYPES
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import call_with_retry, save_parquet
from ingestion.utils.seasons import iter_seasons, season_type_slug

logger = logging.getLogger(__name__)

_DASH_DEFAULTS = {
    "last_n_games": 0,
    "month": 0,
    "opponent_team_id": 0,
    "pace_adjust": "N",
    "period": 0,
    "plus_minus": "N",
    "rank": "N",
    "distance_range": "By Zone",
    "measure_type_simple": "Base",
}


def pull_player_shot_zones(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_dir = RAW_TABLE_DIRS["player_shot_zones"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            for per_mode in PER_MODES_DASH:
                key = f"player_shot_zones|{season}|{season_type}|{per_mode}"
                slug = f"{season_type_slug(season_type)}_{per_mode.lower()}"
                out_path = out_dir / season / f"{slug}.parquet"
                if is_done(PULL_STATE_FILE, key) and out_path.exists():
                    continue
                try:
                    ep = call_with_retry(
                        lambda s=season, st=season_type, pm=per_mode: leaguedashplayershotlocations.LeagueDashPlayerShotLocations(
                            season=s,
                            season_type_all_star=st,
                            per_mode_detailed=pm,
                            **_DASH_DEFAULTS,
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


def pull_team_shot_zones(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_dir = RAW_TABLE_DIRS["team_shot_zones"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            for per_mode in PER_MODES_DASH:
                key = f"team_shot_zones|{season}|{season_type}|{per_mode}"
                slug = f"{season_type_slug(season_type)}_{per_mode.lower()}"
                out_path = out_dir / season / f"{slug}.parquet"
                if is_done(PULL_STATE_FILE, key) and out_path.exists():
                    continue
                try:
                    ep = call_with_retry(
                        lambda s=season, st=season_type, pm=per_mode: leaguedashteamshotlocations.LeagueDashTeamShotLocations(
                            season=s,
                            season_type_all_star=st,
                            per_mode_detailed=pm,
                            **_DASH_DEFAULTS,
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
