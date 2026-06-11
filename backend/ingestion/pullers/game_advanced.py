"""player_game_advanced / team_game_advanced <- boxscore advanced + misc + hustle v3/v2"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import boxscoreadvancedv3, boxscorehustlev2, boxscoremiscv3

from ingestion.config import API_TIMEOUT_SEC, GAME_PULL_ORDER, PULL_STATE_FILE, RAW_TABLE_DIRS
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.game_ids import GamePullOrder, load_game_ids
from ingestion.utils.nba_client import call_with_retry, save_parquet

logger = logging.getLogger(__name__)

_BOX_RANGE = dict(start_period=1, end_period=10, start_range=0, end_range=0, range_type=0)


def _prefix_hustle_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    hustle_cols = [
        "contestedShots",
        "contestedShots2pt",
        "contestedShots3pt",
        "deflections",
        "chargesDrawn",
        "screenAssists",
        "screenAssistPoints",
        "looseBallsRecoveredOffensive",
        "looseBallsRecoveredDefensive",
        "looseBallsRecoveredTotal",
        "offensiveBoxOuts",
        "defensiveBoxOuts",
        "boxOutPlayerTeamRebounds",
        "boxOutPlayerRebounds",
        "boxOuts",
    ]
    rename = {c: f"hustle_{c}" for c in hustle_cols if c in out.columns}
    return out.rename(columns=rename)


def _merge_frames(frames: list[pd.DataFrame], on: list[str]) -> pd.DataFrame:
    merged = frames[0]
    for df in frames[1:]:
        cols = [c for c in df.columns if c not in merged.columns or c in on]
        merged = merged.merge(df[cols], on=on, how="outer")
    return merged


def _fetch_optional(endpoint_fn, label: str, game_id: str):
    """Endpoints that are absent or empty for many older games must not block adv."""
    gid = str(game_id).zfill(10)
    try:
        return call_with_retry(
            lambda: endpoint_fn(gid),
            f"{label}|{gid}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s skipped for %s: %s", label, gid, exc)
        return None


def _pull_for_entity(game_id: str, entity: str) -> None:
    gid = str(game_id).zfill(10)
    key = f"{entity}_game_advanced|{gid}"
    out_dir = RAW_TABLE_DIRS[f"{entity}_game_advanced"]
    out_path = out_dir / f"{gid}.parquet"
    if is_done(PULL_STATE_FILE, key) and out_path.exists():
        return

    try:
        adv = call_with_retry(
            lambda: boxscoreadvancedv3.BoxScoreAdvancedV3(
                game_id=gid, timeout=API_TIMEOUT_SEC, **_BOX_RANGE
            ),
            f"adv|{gid}",
        )
        misc = _fetch_optional(
            lambda g: boxscoremiscv3.BoxScoreMiscV3(
                game_id=g, timeout=API_TIMEOUT_SEC, **_BOX_RANGE
            ),
            "misc",
            gid,
        )
        hustle = _fetch_optional(
            lambda g: boxscorehustlev2.BoxScoreHustleV2(game_id=g, timeout=API_TIMEOUT_SEC),
            "hustle",
            gid,
        )
        adv_dfs = adv.get_data_frames()

        idx = 0 if entity == "player" else 1
        join_keys = ["gameId", "teamId"]
        if entity == "player":
            join_keys.append("personId")

        parts = [adv_dfs[idx]]
        if misc is not None:
            misc_dfs = misc.get_data_frames()
            parts.append(misc_dfs[idx])
        if hustle is not None:
            hustle_dfs = hustle.get_data_frames()
            parts.append(_prefix_hustle_columns(hustle_dfs[idx]))
        if len(parts) == 1:
            merged = parts[0]
        else:
            merged = _merge_frames(parts, on=[k for k in join_keys if k in parts[0].columns])
        save_parquet(merged, out_path)
        mark_done(PULL_STATE_FILE, key)
    except Exception as exc:  # noqa: BLE001
        mark_failed(PULL_STATE_FILE, key, str(exc))
        logger.exception("failed %s %s", entity, gid)


def pull_game_advanced(
    game_ids: list[str] | None = None,
    limit: int | None = None,
    order: GamePullOrder | None = None,
) -> None:
    game_ids = game_ids or load_game_ids(order=order or GAME_PULL_ORDER)
    if limit:
        game_ids = game_ids[:limit]
    for i, game_id in enumerate(game_ids, start=1):
        _pull_for_entity(game_id, "player")
        _pull_for_entity(game_id, "team")
        if i % 100 == 0:
            logger.info("game_advanced progress %s/%s", i, len(game_ids))
