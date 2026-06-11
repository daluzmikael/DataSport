"""game_context <- boxscoresummaryv3 (one file per game_id)"""
from __future__ import annotations

import logging
from pathlib import Path

from nba_api.stats.endpoints import boxscoresummaryv3

from ingestion.config import GAME_PULL_ORDER, PULL_STATE_FILE, RAW_TABLE_DIRS
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.game_ids import GamePullOrder, load_game_ids
from ingestion.utils.nba_client import call_with_retry, save_json

logger = logging.getLogger(__name__)


def pull_game_context(
    game_ids: list[str] | None = None,
    limit: int | None = None,
    order: GamePullOrder | None = None,
) -> None:
    out_dir = RAW_TABLE_DIRS["game_context"]
    game_ids = game_ids or load_game_ids(order=order or GAME_PULL_ORDER)
    if limit:
        game_ids = game_ids[:limit]

    for i, game_id in enumerate(game_ids, start=1):
        gid = str(game_id).zfill(10)
        key = f"game_context|{gid}"
        out_path = out_dir / f"{gid}.json"
        if is_done(PULL_STATE_FILE, key) and out_path.exists():
            continue
        try:
            ep = call_with_retry(
                lambda g=gid: boxscoresummaryv3.BoxScoreSummaryV3(game_id=g),
                key,
            )
            payload = {"game_id": gid, "datasets": {}}
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
            if i % 250 == 0:
                logger.info("game_context progress %s/%s", i, len(game_ids))
        except Exception as exc:  # noqa: BLE001
            mark_failed(PULL_STATE_FILE, key, str(exc))
            logger.exception("failed game_context %s", gid)
