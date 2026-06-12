"""player_tracking / team_tracking <- leaguedashptstats"""
from __future__ import annotations

import logging

from nba_api.stats.endpoints import leaguedashptstats

from ingestion.config import (
    PER_MODES_DASH,
    PT_MEASURE_TYPES,
    PULL_STATE_FILE,
    RAW_TABLE_DIRS,
    SEASON_TYPES,
)
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import call_with_retry, save_parquet
from ingestion.utils.seasons import iter_seasons, season_type_slug
from ingestion.utils.slice_names import measure_slug, per_mode_slug

logger = logging.getLogger(__name__)

_PT_DEFAULTS = {
    "last_n_games": 0,
    "month": 0,
    "opponent_team_id": 0,
}


def _tracking_filename(season_type: str, pt_measure: str, per_mode: str, entity: str) -> str:
    st = season_type_slug(season_type)
    pt_slug = measure_slug(pt_measure)
    pm_slug = per_mode_slug(per_mode)
    return f"{entity}_{st}_{pt_slug}_{pm_slug}.parquet"


def _pull_entity(entity: str, seasons: list[str]) -> None:
    out_root = RAW_TABLE_DIRS[f"{entity}_tracking"]
    player_or_team = "Player" if entity == "player" else "Team"
    for season in seasons:
        for season_type in SEASON_TYPES:
            for pt_measure in PT_MEASURE_TYPES:
                for per_mode in PER_MODES_DASH:
                    key = f"{entity}_tracking|{season}|{season_type}|{pt_measure}|{per_mode}"
                    out_path = (
                        out_root
                        / season
                        / _tracking_filename(season_type, pt_measure, per_mode, entity)
                    )
                    if is_done(PULL_STATE_FILE, key) and out_path.exists():
                        continue
                    try:
                        ep = call_with_retry(
                            lambda s=season, st=season_type, pm=pt_measure, mode=per_mode: leaguedashptstats.LeagueDashPtStats(
                                season=s,
                                season_type_all_star=st,
                                per_mode_simple=mode,
                                player_or_team=player_or_team,
                                pt_measure_type=pm,
                                **_PT_DEFAULTS,
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


def pull_player_tracking(seasons: list[str] | None = None) -> None:
    _pull_entity("player", seasons or iter_seasons())


def pull_team_tracking(seasons: list[str] | None = None) -> None:
    _pull_entity("team", seasons or iter_seasons())
