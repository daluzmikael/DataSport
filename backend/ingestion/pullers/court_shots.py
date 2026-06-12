"""court_shots <- shotchartdetail (per player per season; very large)"""
from __future__ import annotations

import logging
from typing import NamedTuple

from nba_api.stats.endpoints import shotchartdetail

from ingestion.config import (
    COURT_SHOTS_RATE_SLEEP_SEC,
    COURT_SHOTS_TIMEOUT_SEC,
    LEAGUE_ID,
    PULL_STATE_FILE,
    RAW_TABLE_DIRS,
    SEASON_TYPES,
)
from ingestion.utils.checkpoint import failed_keys, load_checkpoint, mark_done, mark_failed
from ingestion.utils.nba_client import call_with_retry, load_parquet_if_exists, save_parquet
from ingestion.utils.seasons import iter_seasons, season_type_slug

logger = logging.getLogger(__name__)

_SHOT_DEFAULTS = {
    "last_n_games": 0,
    "month": 0,
    "opponent_team_id": 0,
    "period": 0,
    "context_measure_simple": "FGA",
}


class _CourtShotJob(NamedTuple):
    season: str
    season_type: str
    player_id: str

    @property
    def key(self) -> str:
        return f"court_shots|{self.season}|{self.season_type}|{self.player_id}"

    def out_path(self, root):
        return (
            root
            / self.season
            / season_type_slug(self.season_type)
            / f"{self.player_id}.parquet"
        )


def _player_ids_for_season(season: str) -> list[str]:
    season_dir = RAW_TABLE_DIRS["player_season_stats"] / season
    if not season_dir.is_dir():
        return []
    ids: set[str] = set()
    for path in sorted(season_dir.glob("dash_*.parquet")):
        df = load_parquet_if_exists(path)
        if df is None or df.empty:
            continue
        col = "PLAYER_ID" if "PLAYER_ID" in df.columns else "player_id"
        if col in df.columns:
            ids.update(df[col].astype(str).unique())
    return sorted(ids)


def _court_shot_jobs(
    seasons: list[str],
    player_ids: list[str] | None,
    max_players: int | None,
    retry_failed_only: bool,
) -> list[_CourtShotJob]:
    if retry_failed_only:
        jobs: list[_CourtShotJob] = []
        for key in failed_keys(PULL_STATE_FILE, "court_shots|"):
            parts = key.split("|")
            if len(parts) != 4:
                continue
            _, season, season_type, player_id = parts
            jobs.append(_CourtShotJob(season, season_type, player_id))
        return jobs

    state = load_checkpoint(PULL_STATE_FILE)
    completed = set(state.get("completed", []))
    jobs = []
    for season in seasons:
        ids = player_ids or _player_ids_for_season(season)
        if max_players:
            ids = ids[:max_players]
        if not ids:
            logger.warning("no player ids for court_shots season %s", season)
            continue
        for season_type in SEASON_TYPES:
            for player_id in ids:
                job = _CourtShotJob(season, season_type, player_id)
                if job.key in completed:
                    continue
                jobs.append(job)
    return jobs


def pull_court_shots(
    seasons: list[str] | None = None,
    player_ids: list[str] | None = None,
    max_players: int | None = None,
    retry_failed_only: bool = False,
) -> None:
    seasons = seasons or iter_seasons()
    out_dir = RAW_TABLE_DIRS["court_shots"]
    jobs = _court_shot_jobs(seasons, player_ids, max_players, retry_failed_only)
    if not jobs:
        logger.info("court_shots: nothing to fetch")
        return

    failed_count = len(failed_keys(PULL_STATE_FILE, "court_shots|"))
    logger.info(
        "court_shots: fetching %s jobs (%s previously failed, timeout=%ss)",
        len(jobs),
        failed_count,
        COURT_SHOTS_TIMEOUT_SEC,
    )

    for i, job in enumerate(jobs, start=1):
        out_path = job.out_path(out_dir)
        try:
            ep = call_with_retry(
                lambda j=job: shotchartdetail.ShotChartDetail(
                    team_id=0,
                    player_id=int(j.player_id),
                    season_nullable=j.season,
                    season_type_all_star=j.season_type,
                    league_id=LEAGUE_ID,
                    timeout=COURT_SHOTS_TIMEOUT_SEC,
                    **_SHOT_DEFAULTS,
                ),
                job.key,
                rate_sleep=COURT_SHOTS_RATE_SLEEP_SEC,
            )
            frames = ep.get_data_frames()
            df = frames[1] if len(frames) > 1 else frames[0]
            if df.empty:
                mark_done(PULL_STATE_FILE, job.key)
                continue
            save_parquet(df, out_path)
            mark_done(PULL_STATE_FILE, job.key)
            if i % 500 == 0 or i == len(jobs):
                logger.info("court_shots progress: %s/%s (%s)", i, len(jobs), job.key)
        except Exception as exc:  # noqa: BLE001
            mark_failed(PULL_STATE_FILE, job.key, str(exc))
            logger.exception("failed %s", job.key)
