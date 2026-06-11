"""Rate-limited nba_api calls with retries and parquet/json writes."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from ingestion.config import MAX_RETRIES, RATE_SLEEP_SEC, RETRY_BACKOFF_SEC

logger = logging.getLogger(__name__)


def is_resultset_unavailable(exc: BaseException) -> bool:
    """NBA stats API returned a body with no resultSet (no data for this id)."""
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, KeyError) and str(cur.args[0]) == "resultSet":
            return True
        if "resultset" in str(cur).lower():
            return True
        cur = cur.__cause__
    return False


def sleep_after_call(rate_sleep: float | None = None) -> None:
    time.sleep(rate_sleep if rate_sleep is not None else RATE_SLEEP_SEC)


def call_with_retry(
    fn: Callable[[], Any],
    label: str,
    *,
    rate_sleep: float | None = None,
) -> Any:
    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = fn()
            sleep_after_call(rate_sleep)
            return result
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            wait = RETRY_BACKOFF_SEC * attempt
            logger.warning("%s attempt %s/%s failed: %s; sleep %.1fs", label, attempt, MAX_RETRIES, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"{label} failed after {MAX_RETRIES} retries") from last_err


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def load_parquet_if_exists(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_parquet(path)
    return None
