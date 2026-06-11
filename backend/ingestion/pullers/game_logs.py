"""player_game_logs / team_game_logs <- playergamelogs / teamgamelogs"""
from __future__ import annotations

import logging

import pandas as pd
from nba_api.stats.endpoints import playergamelogs, teamgamelogs

from ingestion.config import GAME_IDS_FILE, PULL_STATE_FILE, RAW_TABLE_DIRS, SEASON_TYPES
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import call_with_retry, save_parquet
from ingestion.utils.seasons import iter_seasons, season_type_slug

logger = logging.getLogger(__name__)


def pull_player_game_logs(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_dir = RAW_TABLE_DIRS["player_game_logs"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            key = f"player_game_logs|{season}|{season_type}"
            out_path = out_dir / season / f"{season_type_slug(season_type)}.parquet"
            if is_done(PULL_STATE_FILE, key) and out_path.exists():
                continue
            try:
                ep = call_with_retry(
                    lambda s=season, st=season_type: playergamelogs.PlayerGameLogs(
                        season_nullable=s,
                        season_type_nullable=st,
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


def pull_team_game_logs(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    out_dir = RAW_TABLE_DIRS["team_game_logs"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            key = f"team_game_logs|{season}|{season_type}"
            out_path = out_dir / season / f"{season_type_slug(season_type)}.parquet"
            if is_done(PULL_STATE_FILE, key) and out_path.exists():
                continue
            try:
                ep = call_with_retry(
                    lambda s=season, st=season_type: teamgamelogs.TeamGameLogs(
                        season_nullable=s,
                        season_type_nullable=st,
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


def build_game_id_manifest(seasons: list[str] | None = None) -> list[str]:
    seasons = seasons or iter_seasons()
    game_ids: set[str] = set()
    for sub in (RAW_TABLE_DIRS["player_game_logs"], RAW_TABLE_DIRS["team_game_logs"]):
        for season in seasons:
            for season_type in SEASON_TYPES:
                path = sub / season / f"{season_type_slug(season_type)}.parquet"
                if not path.exists():
                    logger.warning("missing %s for game_id manifest", path)
                    continue
                df = pd.read_parquet(path)
                col = "GAME_ID" if "GAME_ID" in df.columns else "game_id"
                if col in df.columns:
                    game_ids.update(df[col].astype(str).str.zfill(10).unique())

    ordered = sorted(game_ids)
    GAME_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GAME_IDS_FILE.write_text("\n".join(ordered) + ("\n" if ordered else ""), encoding="utf-8")
    logger.info("wrote %s game ids to %s", len(ordered), GAME_IDS_FILE)
    return ordered
