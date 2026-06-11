"""Load and order game_id manifest for per-game pullers."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from ingestion.config import GAME_IDS_FILE

GamePullOrder = Literal["recent", "oldest"]


def load_game_ids(
    path: Path = GAME_IDS_FILE,
    order: GamePullOrder = "recent",
) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run phase 2 first (python -m ingestion.pull_all --phase 2)."
        )
    ids = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    # Manifest is sorted ascending; NBA game ids sort roughly oldest season -> newest.
    if order == "recent":
        ids.reverse()
    return ids
