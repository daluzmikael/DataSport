"""player_on_off <- teamplayeronoffsummary (per team, all players on roster)"""
from __future__ import annotations

import logging

import pandas as pd
from nba_api.stats.endpoints import teamplayeronoffsummary
from nba_api.stats.static import teams as nba_teams

from ingestion.config import PER_MODES_DASH, PULL_STATE_FILE, RAW_TABLE_DIRS, SEASON_TYPES
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import call_with_retry, save_parquet
from ingestion.utils.seasons import iter_seasons, season_type_slug
from ingestion.utils.slice_names import per_mode_slug

logger = logging.getLogger(__name__)

_ON_OFF_DEFAULTS = {
    "last_n_games": 0,
    "month": 0,
    "opponent_team_id": 0,
    "pace_adjust": "N",
    "period": 0,
    "measure_type_detailed_defense": "Base",
    "plus_minus": "N",
    "rank": "N",
}


def _nba_team_ids() -> list[str]:
    return sorted({str(t["id"]) for t in nba_teams.get_teams()})


def pull_player_on_off(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_root = RAW_TABLE_DIRS["player_on_off"]
    team_ids = _nba_team_ids()
    for season in seasons:
        for season_type in SEASON_TYPES:
            for team_id in team_ids:
                for per_mode in PER_MODES_DASH:
                    key = f"player_on_off|{season}|{season_type}|{team_id}|{per_mode}"
                    st = season_type_slug(season_type)
                    pm = per_mode_slug(per_mode)
                    out_path = out_root / season / f"team_{team_id}_{st}_{pm}.parquet"
                    if is_done(PULL_STATE_FILE, key) and out_path.exists():
                        continue
                    try:
                        ep = call_with_retry(
                            lambda s=season, st=season_type, tid=team_id, mode=per_mode: teamplayeronoffsummary.TeamPlayerOnOffSummary(
                                team_id=tid,
                                season=s,
                                season_type_all_star=st,
                                per_mode_detailed=mode,
                                **_ON_OFF_DEFAULTS,
                            ),
                            key,
                        )
                        datasets = ep.get_data_frames(return_names=True)
                        if not isinstance(datasets, dict):
                            frames = ep.get_data_frames()
                            datasets = {
                                "PlayersOnCourtTeamPlayerOnOffSummary": frames[2]
                                if len(frames) > 2
                                else frames[0],
                                "PlayersOffCourtTeamPlayerOnOffSummary": frames[1]
                                if len(frames) > 1
                                else None,
                            }
                        parts: list[pd.DataFrame] = []
                        for name in (
                            "PlayersOnCourtTeamPlayerOnOffSummary",
                            "PlayersOffCourtTeamPlayerOnOffSummary",
                        ):
                            part = datasets.get(name)
                            if part is not None and not part.empty:
                                parts.append(part)
                        if not parts:
                            mark_done(PULL_STATE_FILE, key)
                            continue
                        df = pd.concat(parts, ignore_index=True)
                        if "VS_PLAYER_ID" in df.columns and "PLAYER_ID" not in df.columns:
                            df = df.rename(columns={"VS_PLAYER_ID": "PLAYER_ID"})
                        if "VS_PLAYER_NAME" in df.columns and "PLAYER_NAME" not in df.columns:
                            df = df.rename(columns={"VS_PLAYER_NAME": "PLAYER_NAME"})
                        df["TEAM_ID"] = team_id
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        save_parquet(df, out_path)
                        mark_done(PULL_STATE_FILE, key)
                        logger.info("saved %s", out_path)
                    except Exception as exc:  # noqa: BLE001
                        mark_failed(PULL_STATE_FILE, key, str(exc))
                        logger.exception("failed %s", key)
