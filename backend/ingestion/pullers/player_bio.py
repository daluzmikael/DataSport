"""player_bio / team_roster / player_awards / franchise_history <- nba_api.

Player identity and accolades: height, weight, position, draft, country, experience,
season rosters with jersey numbers, awards, and franchise records. The home-prototype
profile pages mock all of this today.

Grain note: unlike everything else in the vault, `player_bio` and `player_awards` are
PLAYER-grain, not season-grain — one call per player, not per player-season. The
checkpoint key reflects that, so a resumed run skips by player id and a season range
argument does not apply to them.
"""
from __future__ import annotations

import logging

import pandas as pd
from nba_api.stats.endpoints import (
    commonplayerinfo,
    commonteamroster,
    franchisehistory,
    playerawards,
)

from ingestion.config import LEAGUE_ID, PULL_STATE_FILE, RAW_TABLE_DIRS
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import (
    call_with_retry,
    is_resultset_unavailable,
    save_parquet,
)
from ingestion.utils.seasons import iter_seasons, season_type_slug

logger = logging.getLogger(__name__)


def _vault_player_ids() -> list[int]:
    """Every player id the staged season table knows about.

    Read from the vault rather than from a league-wide roster call so the pull covers
    exactly the players the app can actually ask about, and stays stable across runs.
    """
    from Executer.data_backend import get_connection

    rows = get_connection().execute(
        "SELECT DISTINCT PLAYER_ID FROM player_season_stats WHERE PLAYER_ID IS NOT NULL"
    ).fetchall()
    return sorted(int(r[0]) for r in rows)


def _vault_team_seasons() -> list[tuple[int, str]]:
    from Executer.data_backend import get_connection

    rows = get_connection().execute(
        "SELECT DISTINCT TEAM_ID, season FROM team_season_stats "
        "WHERE TEAM_ID IS NOT NULL ORDER BY season, TEAM_ID"
    ).fetchall()
    return [(int(r[0]), str(r[1])) for r in rows]


def _pull_player_endpoint(
    player_ids: list[int] | None,
    *,
    table: str,
    key_prefix: str,
    build,
    label: str,
) -> None:
    """Shared loop for the two player-grain endpoints."""
    ids = player_ids if player_ids is not None else _vault_player_ids()
    out_dir = RAW_TABLE_DIRS[table]
    logger.info("%s: %s players", label, len(ids))

    for i, pid in enumerate(ids, start=1):
        key = f"{key_prefix}|{pid}"
        out_path = out_dir / f"{pid}.parquet"
        if is_done(PULL_STATE_FILE, key) and out_path.exists():
            continue
        try:
            ep = call_with_retry(lambda p=pid: build(p), key)
            frames = ep.get_data_frames()
            if not frames or frames[0].empty:
                # A player with no awards is a real, valid answer — record it as done
                # so the next run does not keep paying for the same empty response.
                save_parquet(pd.DataFrame(), out_path)
                mark_done(PULL_STATE_FILE, key)
                continue
            save_parquet(frames[0], out_path)
            mark_done(PULL_STATE_FILE, key)
        except Exception as exc:  # noqa: BLE001
            if is_resultset_unavailable(exc):
                save_parquet(pd.DataFrame(), out_path)
                mark_done(PULL_STATE_FILE, key)
                logger.info("%s: no data for %s", label, pid)
                continue
            mark_failed(PULL_STATE_FILE, key, str(exc))
            logger.warning("%s failed for %s: %s", label, pid, exc)
        if i % 100 == 0:
            logger.info("%s progress %s/%s", label, i, len(ids))


def pull_player_bio(player_ids: list[int] | None = None) -> None:
    """CommonPlayerInfo — height, weight, position, draft, country, experience."""
    _pull_player_endpoint(
        player_ids,
        table="player_bio",
        key_prefix="player_bio",
        build=lambda p: commonplayerinfo.CommonPlayerInfo(player_id=p),
        label="player_bio",
    )


def pull_player_awards(player_ids: list[int] | None = None) -> None:
    """PlayerAwards — accolades. Many players legitimately have none."""
    _pull_player_endpoint(
        player_ids,
        table="player_awards",
        key_prefix="player_awards",
        build=lambda p: playerawards.PlayerAwards(player_id=p),
        label="player_awards",
    )


def pull_team_roster(seasons: list[str] | None = None) -> None:
    """CommonTeamRoster — season roster and jersey numbers, per team-season."""
    out_dir = RAW_TABLE_DIRS["team_roster"]
    wanted = set(seasons) if seasons else None
    pairs = [(t, s) for t, s in _vault_team_seasons() if wanted is None or s in wanted]
    logger.info("team_roster: %s team-seasons", len(pairs))

    for i, (team_id, season) in enumerate(pairs, start=1):
        key = f"team_roster|{season}|{team_id}"
        out_path = out_dir / season / f"team_{team_id}.parquet"
        if is_done(PULL_STATE_FILE, key) and out_path.exists():
            continue
        try:
            ep = call_with_retry(
                lambda t=team_id, s=season: commonteamroster.CommonTeamRoster(
                    team_id=t, season=s, league_id_nullable=LEAGUE_ID
                ),
                key,
            )
            df = ep.get_data_frames()[0]
            df["season"] = season
            save_parquet(df, out_path)
            mark_done(PULL_STATE_FILE, key)
        except Exception as exc:  # noqa: BLE001
            if is_resultset_unavailable(exc):
                mark_done(PULL_STATE_FILE, key)
                continue
            mark_failed(PULL_STATE_FILE, key, str(exc))
            logger.warning("team_roster failed for %s %s: %s", season, team_id, exc)
        if i % 100 == 0:
            logger.info("team_roster progress %s/%s", i, len(pairs))


def pull_franchise_history() -> None:
    """FranchiseHistory — one league-wide call covering every franchise's record."""
    key = "franchise_history|all"
    out_dir = RAW_TABLE_DIRS["franchise_history"]
    out_path = out_dir / "franchise_history.parquet"
    defunct_path = out_dir / "defunct_teams.parquet"
    if is_done(PULL_STATE_FILE, key) and out_path.exists():
        logger.info("skip %s", key)
        return
    try:
        ep = call_with_retry(
            lambda: franchisehistory.FranchiseHistory(league_id=LEAGUE_ID), key
        )
        frames = ep.get_data_frames()
        save_parquet(frames[0], out_path)
        if len(frames) > 1 and not frames[1].empty:
            save_parquet(frames[1], defunct_path)
        mark_done(PULL_STATE_FILE, key)
        logger.info("saved %s (%s rows)", out_path, len(frames[0]))
    except Exception as exc:  # noqa: BLE001
        mark_failed(PULL_STATE_FILE, key, str(exc))
        logger.exception("failed %s", key)
