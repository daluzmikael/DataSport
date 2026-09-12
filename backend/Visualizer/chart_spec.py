"""The one contract between chart selection and every renderer.

Pydantic rather than a dataclass so FastAPI serialises it without help and a malformed
spec fails at construction instead of in the browser.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ChartKind = Literal[
    "leaderboard",
    "trend",
    "compare_trend",
    "radar",
    "compare_radar",
    "scatter",
    "shot_chart",
    "table",
]

# How a value should be read, not how it is stored. The vault keeps percentages as
# fractions (FG_PCT 0.523), so the renderer needs to be told it is looking at one.
Unit = Literal["pct", "per_game", "count", "rating"]


class FieldSpec(BaseModel):
    column: str
    """Real vault column, e.g. FG3_PCT."""

    label: str
    """Broadcast name, e.g. 3P%."""

    unit: Unit | None = None
    precision: int = 1


class ChartSpec(BaseModel):
    kind: ChartKind
    title: str
    subtitle: str | None = None
    """Season span, season type and per_mode. A Totals leaderboard and a PerGame one
    are different pictures and are otherwise indistinguishable in a screenshot."""

    x: FieldSpec | None = None
    y: list[FieldSpec] = Field(default_factory=list)
    series: str | None = None
    """Column whose values split the rows into series, when the kind has more than one.
    For a single-subject chart (radar, shot_chart) this carries the bare entity name."""

    mode: str | None = None
    """shot_chart only: makes | volume | accuracy | hotspots | coldspots. A presentation
    default; the renderer lets the reader switch, so nothing is inferred from phrasing."""

    points: list[dict[str, Any]] = Field(default_factory=list)
    """shot_chart only: the individual attempts, when the scope is small enough to draw
    them one by one. Hex bins need volume to mean anything — over a single game no cell
    reaches the accuracy floor and every cell reads 0% or 100% — so a small sample is
    shown as makes and misses instead. Empty for a binned (large-scope) chart."""

    rows: list[dict[str, Any]] = Field(default_factory=list)
    """Already shaped for the renderer — see the row contract per kind in shaping.py."""

    citation: str = ""
    """plan.citation() — provenance travels WITH the picture."""

    notes: list[str] = Field(default_factory=list)
    """Applied floors, name corrections, row caps. A leaderboard filtered to "at least
    20 games" answers a narrower question than the one asked; a reader who only looks
    at the chart must not be misled by it, so the footer has to say so."""
