"""player_season_stats / team_season_stats <- leaguedash*, clutch, hustle; career <- playercareerstats"""
from __future__ import annotations

import logging

import pandas as pd
from nba_api.stats.endpoints import (
    leaguedashplayerclutch,
    leaguedashplayerstats,
    leaguedashteamclutch,
    leaguedashteamstats,
    leaguehustlestatsplayer,
    leaguehustlestatsteam,
    playercareerstats,
)

from ingestion.config import (
    API_TIMEOUT_SEC,
    CLUTCH_DEFAULTS,
    PER_MODES_DASH,
    PULL_STATE_FILE,
    RAW_TABLE_DIRS,
    SEASON_TYPES,
)
from ingestion.utils.checkpoint import failed_keys, is_done, load_checkpoint, mark_done, mark_failed
from ingestion.utils.nba_client import (
    call_with_retry,
    is_resultset_unavailable,
    load_parquet_if_exists,
    save_json,
    save_parquet,
)
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
    "measure_type_detailed_defense": "Base",
}


def _pull_player_dash(seasons: list[str]) -> None:
    out_dir = RAW_TABLE_DIRS["player_season_stats"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            for per_mode in PER_MODES_DASH:
                key = f"player_dash|{season}|{season_type}|{per_mode}"
                out_path = out_dir / season / f"dash_{season_type_slug(season_type)}_{per_mode.lower()}.parquet"
                if is_done(PULL_STATE_FILE, key) and out_path.exists():
                    continue
                try:
                    ep = call_with_retry(
                        lambda s=season, st=season_type, pm=per_mode: leaguedashplayerstats.LeagueDashPlayerStats(
                            season=s,
                            season_type_all_star=st,
                            per_mode_detailed=pm,
                            **_DASH_DEFAULTS,
                        ),
                        key,
                    )
                    save_parquet(ep.get_data_frames()[0], out_path)
                    mark_done(PULL_STATE_FILE, key)
                    logger.info("saved %s", out_path)
                except Exception as exc:  # noqa: BLE001
                    mark_failed(PULL_STATE_FILE, key, str(exc))
                    logger.exception("failed %s", key)


def _pull_player_clutch(seasons: list[str]) -> None:
    out_dir = RAW_TABLE_DIRS["player_season_stats"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            for per_mode in PER_MODES_DASH:
                key = f"player_clutch|{season}|{season_type}|{per_mode}"
                out_path = out_dir / season / f"clutch_{season_type_slug(season_type)}_{per_mode.lower()}.parquet"
                if is_done(PULL_STATE_FILE, key) and out_path.exists():
                    continue
                try:
                    ep = call_with_retry(
                        lambda s=season, st=season_type, pm=per_mode: leaguedashplayerclutch.LeagueDashPlayerClutch(
                            season=s,
                            season_type_all_star=st,
                            per_mode_detailed=pm,
                            clutch_time=CLUTCH_DEFAULTS["clutch_time"],
                            ahead_behind=CLUTCH_DEFAULTS["ahead_behind"],
                            point_diff=CLUTCH_DEFAULTS["point_diff"],
                            **_DASH_DEFAULTS,
                        ),
                        key,
                    )
                    save_parquet(ep.get_data_frames()[0], out_path)
                    mark_done(PULL_STATE_FILE, key)
                    logger.info("saved %s", out_path)
                except Exception as exc:  # noqa: BLE001
                    mark_failed(PULL_STATE_FILE, key, str(exc))
                    logger.exception("failed %s", key)


def _pull_player_hustle(seasons: list[str]) -> None:
    out_dir = RAW_TABLE_DIRS["player_season_stats"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            for per_mode in ("PerGame", "Totals"):
                key = f"player_hustle|{season}|{season_type}|{per_mode}"
                out_path = out_dir / season / f"hustle_{season_type_slug(season_type)}_{per_mode.lower()}.parquet"
                if is_done(PULL_STATE_FILE, key) and out_path.exists():
                    continue
                try:
                    ep = call_with_retry(
                        lambda s=season, st=season_type, pm=per_mode: leaguehustlestatsplayer.LeagueHustleStatsPlayer(
                            season=s,
                            season_type_all_star=st,
                            per_mode_time=pm,
                        ),
                        key,
                    )
                    save_parquet(ep.get_data_frames()[0], out_path)
                    mark_done(PULL_STATE_FILE, key)
                    logger.info("saved %s", out_path)
                except Exception as exc:  # noqa: BLE001
                    mark_failed(PULL_STATE_FILE, key, str(exc))
                    logger.exception("failed %s", key)


def _pull_team_dash_clutch_hustle(seasons: list[str]) -> None:
    out_dir = RAW_TABLE_DIRS["team_season_stats"]
    for season in seasons:
        for season_type in SEASON_TYPES:
            for per_mode in PER_MODES_DASH:
                key = f"team_dash|{season}|{season_type}|{per_mode}"
                out_path = out_dir / season / f"dash_{season_type_slug(season_type)}_{per_mode.lower()}.parquet"
                if not (is_done(PULL_STATE_FILE, key) and out_path.exists()):
                    try:
                        ep = call_with_retry(
                            lambda s=season, st=season_type, pm=per_mode: leaguedashteamstats.LeagueDashTeamStats(
                                season=s,
                                season_type_all_star=st,
                                per_mode_detailed=pm,
                                **_DASH_DEFAULTS,
                            ),
                            key,
                        )
                        save_parquet(ep.get_data_frames()[0], out_path)
                        mark_done(PULL_STATE_FILE, key)
                        logger.info("saved %s", out_path)
                    except Exception as exc:  # noqa: BLE001
                        mark_failed(PULL_STATE_FILE, key, str(exc))
                        logger.exception("failed %s", key)

                key = f"team_clutch|{season}|{season_type}|{per_mode}"
                out_path = out_dir / season / f"clutch_{season_type_slug(season_type)}_{per_mode.lower()}.parquet"
                if not (is_done(PULL_STATE_FILE, key) and out_path.exists()):
                    try:
                        ep = call_with_retry(
                            lambda s=season, st=season_type, pm=per_mode: leaguedashteamclutch.LeagueDashTeamClutch(
                                season=s,
                                season_type_all_star=st,
                                per_mode_detailed=pm,
                                clutch_time=CLUTCH_DEFAULTS["clutch_time"],
                                ahead_behind=CLUTCH_DEFAULTS["ahead_behind"],
                                point_diff=CLUTCH_DEFAULTS["point_diff"],
                                **_DASH_DEFAULTS,
                            ),
                            key,
                        )
                        save_parquet(ep.get_data_frames()[0], out_path)
                        mark_done(PULL_STATE_FILE, key)
                        logger.info("saved %s", out_path)
                    except Exception as exc:  # noqa: BLE001
                        mark_failed(PULL_STATE_FILE, key, str(exc))
                        logger.exception("failed %s", key)

            for per_mode in ("PerGame", "Totals"):
                key = f"team_hustle|{season}|{season_type}|{per_mode}"
                out_path = out_dir / season / f"hustle_{season_type_slug(season_type)}_{per_mode.lower()}.parquet"
                if is_done(PULL_STATE_FILE, key) and out_path.exists():
                    continue
                try:
                    ep = call_with_retry(
                        lambda s=season, st=season_type, pm=per_mode: leaguehustlestatsteam.LeagueHustleStatsTeam(
                            season=s,
                            season_type_all_star=st,
                            per_mode_time=pm,
                        ),
                        key,
                    )
                    save_parquet(ep.get_data_frames()[0], out_path)
                    mark_done(PULL_STATE_FILE, key)
                    logger.info("saved %s", out_path)
                except Exception as exc:  # noqa: BLE001
                    mark_failed(PULL_STATE_FILE, key, str(exc))
                    logger.exception("failed %s", key)


def pull_player_season_stats(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    _pull_player_dash(seasons)
    _pull_player_clutch(seasons)
    _pull_player_hustle(seasons)


def pull_team_season_stats(seasons: list[str] | None = None) -> None:
    seasons = seasons or iter_seasons()
    _pull_team_dash_clutch_hustle(seasons)


def _collect_player_ids(seasons: list[str]) -> list[str]:
    out_dir = RAW_TABLE_DIRS["player_season_stats"]
    ids: set[str] = set()
    for season in seasons:
        path = out_dir / season / "dash_regular_season_pergame.parquet"
        df = load_parquet_if_exists(path)
        if df is None or df.empty:
            continue
        col = "PLAYER_ID" if "PLAYER_ID" in df.columns else "player_id"
        if col in df.columns:
            ids.update(df[col].astype(str).unique())
    return sorted(ids)


def _career_player_ids_to_pull(
    seasons: list[str],
    player_ids: list[str] | None = None,
    retry_failed_only: bool = False,
) -> list[str]:
    out_dir = RAW_TABLE_DIRS["player_season_stats"] / "career"
    state = load_checkpoint(PULL_STATE_FILE)
    completed = set(state.get("completed", []))

    if player_ids is not None:
        candidates = player_ids
    elif retry_failed_only:
        candidates = [
            key.split("|", 1)[1]
            for key in failed_keys(PULL_STATE_FILE, "player_career|")
        ]
    else:
        candidates = _collect_player_ids(seasons)

    work: list[str] = []
    for player_id in candidates:
        key = f"player_career|{player_id}"
        out_path = out_dir / f"{player_id}.json"
        if key in completed and out_path.exists():
            continue
        work.append(player_id)
    return work


def pull_player_career_stats(
    seasons: list[str] | None = None,
    player_ids: list[str] | None = None,
    retry_failed_only: bool = False,
) -> None:
    """playercareerstats per player_id -> raw/player_season_stats/career/{id}.json"""
    seasons = seasons or iter_seasons()
    out_dir = RAW_TABLE_DIRS["player_season_stats"] / "career"
    out_dir.mkdir(parents=True, exist_ok=True)

    if player_ids is None and not retry_failed_only:
        all_ids = _collect_player_ids(seasons)
        if not all_ids:
            logger.warning("No player IDs found for career pull; run player dash first.")
            return

    ids = _career_player_ids_to_pull(seasons, player_ids, retry_failed_only)
    if not ids:
        logger.info("career pull: nothing to fetch (all complete)")
        return

    failed_count = len(failed_keys(PULL_STATE_FILE, "player_career|"))
    logger.info(
        "career pull: fetching %s players (%s previously failed in checkpoint)",
        len(ids),
        failed_count,
    )

    for i, player_id in enumerate(ids, start=1):
        key = f"player_career|{player_id}"
        out_path = out_dir / f"{player_id}.json"
        try:
            ep = call_with_retry(
                lambda pid=player_id: playercareerstats.PlayerCareerStats(
                    player_id=pid,
                    per_mode36="Totals",
                    timeout=API_TIMEOUT_SEC,
                ),
                key,
            )
            payload = {"player_id": player_id, "datasets": {}}
            try:
                named = ep.get_data_frames(return_names=True)
                if isinstance(named, dict):
                    for name, df in named.items():
                        payload["datasets"][name] = df.to_dict(orient="records")
                else:
                    for idx, df in enumerate(named):
                        payload["datasets"][str(idx)] = df.to_dict(orient="records")
            except TypeError:
                for idx, df in enumerate(ep.get_data_frames()):
                    payload["datasets"][str(idx)] = df.to_dict(orient="records")
            save_json(payload, out_path)
            mark_done(PULL_STATE_FILE, key)
            if i % 25 == 0 or i == len(ids):
                logger.info("career progress: %s/%s (player %s)", i, len(ids), player_id)
        except Exception as exc:  # noqa: BLE001
            if is_resultset_unavailable(exc):
                save_json(
                    {
                        "player_id": player_id,
                        "datasets": {},
                        "unavailable": True,
                        "reason": "no resultSet from playercareerstats",
                    },
                    out_path,
                )
                mark_done(PULL_STATE_FILE, key)
                logger.warning("career unavailable for %s (no API data); saved stub", player_id)
                continue
            mark_failed(PULL_STATE_FILE, key, str(exc))
            logger.exception("failed career %s", player_id)
