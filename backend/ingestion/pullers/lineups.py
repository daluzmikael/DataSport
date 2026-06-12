"""lineups <- leaguedashlineups (5-man units)"""
from __future__ import annotations

import logging

from nba_api.stats.endpoints import leaguedashlineups

from ingestion.config import (
    LINEUP_GROUP_QUANTITIES,
    LINEUP_MEASURE_TYPES,
    PER_MODES_DASH,
    PULL_STATE_FILE,
    RAW_TABLE_DIRS,
    SEASON_TYPES,
)
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import call_with_retry, save_parquet
from ingestion.utils.seasons import iter_seasons, season_type_slug
from ingestion.utils.slice_names import measure_slug, per_mode_slug

logger = logging.getLogger(__name__)

_LINEUP_DEFAULTS = {
    "last_n_games": 0,
    "month": 0,
    "opponent_team_id": 0,
    "pace_adjust": "N",
    "period": 0,
    "plus_minus": "N",
    "rank": "N",
}


def pull_lineups(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_root = RAW_TABLE_DIRS["lineups"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            for group_qty in LINEUP_GROUP_QUANTITIES:
                for measure_type in LINEUP_MEASURE_TYPES:
                    for per_mode in PER_MODES_DASH:
                        key = (
                            f"lineups|{season}|{season_type}|{group_qty}|"
                            f"{measure_type}|{per_mode}"
                        )
                        st = season_type_slug(season_type)
                        ms = measure_slug(measure_type)
                        pm = per_mode_slug(per_mode)
                        out_path = out_root / season / f"g{group_qty}_{st}_{ms}_{pm}.parquet"
                        if is_done(PULL_STATE_FILE, key) and out_path.exists():
                            continue
                        try:
                            ep = call_with_retry(
                                lambda s=season, st=season_type, g=group_qty, mt=measure_type, mode=per_mode: leaguedashlineups.LeagueDashLineups(
                                    season=s,
                                    season_type_all_star=st,
                                    group_quantity=str(g),
                                    measure_type_detailed_defense=mt,
                                    per_mode_detailed=mode,
                                    **_LINEUP_DEFAULTS,
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
