"""Season list helpers."""
from __future__ import annotations

from ingestion.config import END_SEASON, START_SEASON


def season_label_to_start_year(label: str) -> int:
    """'2023-24' -> 2023."""
    return int(label.split("-")[0])


def start_year_to_label(start_year: int) -> str:
    """2023 -> '2023-24'."""
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def iter_seasons(start: str = START_SEASON, end: str = END_SEASON) -> list[str]:
    """Inclusive list of NBA season strings from start through end."""
    y0 = season_label_to_start_year(start)
    y1 = season_label_to_start_year(end)
    return [start_year_to_label(y) for y in range(y0, y1 + 1)]


def season_type_slug(season_type: str) -> str:
    return season_type.lower().replace(" ", "_")
