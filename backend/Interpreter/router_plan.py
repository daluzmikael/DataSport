"""Pydantic model, catalog rendering and validation for the analyst router plan.

Schema v2 (wide-table vault):
  * exactly ONE table per plan — no joins, no unions
  * season range via season_from / season_to instead of one season at a time
  * explicit `supported` flag so Call 1 can reject multi-table questions
"""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from Executer.duckdb_store import list_registered_tables
from ingestion.config import (
    LINEUP_GROUP_QUANTITIES,
    LINEUP_MEASURE_TYPES,
    PER_MODES_DASH_EXTENDED,
    PT_MEASURE_TYPES,
    SEASON_TYPES,
)

logger = logging.getLogger(__name__)

MAX_PER_MODES = int(os.getenv("ROUTER_MAX_PER_MODES", "2"))
MAX_STAT_FOCUS = int(os.getenv("ROUTER_MAX_STAT_FOCUS", "12"))

_CATALOG_PATH = Path(__file__).resolve().parent / "table_catalog.yaml"
_catalog_cache: dict[str, Any] | None = None

_SEASON_RE = re.compile(r"^\d{4}-\d{2}$")


def load_table_catalog() -> dict[str, Any]:
    global _catalog_cache
    if _catalog_cache is None:
        with open(_CATALOG_PATH, encoding="utf-8") as f:
            _catalog_cache = yaml.safe_load(f)
    return _catalog_cache


def catalog_entry(table: str) -> dict[str, Any]:
    return load_table_catalog().get("tables", {}).get(table, {}) or {}


def catalog_defaults() -> dict[str, Any]:
    return load_table_catalog().get("defaults", {}) or {}


# --------------------------------------------------------------------------
# Column helpers (case-insensitive resolution against the live DuckDB views)
# --------------------------------------------------------------------------
@lru_cache(maxsize=64)
def _columns_cached(table: str, conn_id: int) -> tuple[str, ...]:
    del conn_id  # cache key only; the connection is a process-wide singleton
    from Executer.data_backend import get_connection

    rows = get_connection().execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'main' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()
    return tuple(str(r[0]) for r in rows)


def columns_for_table(table: str, conn: Any | None = None) -> tuple[str, ...]:
    """All column names for a staged view, cached per table."""
    if conn is not None:
        try:
            rows = conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'main' AND table_name = ?
                ORDER BY ordinal_position
                """,
                [table],
            ).fetchall()
            return tuple(str(r[0]) for r in rows)
        except Exception:  # noqa: BLE001 — mocked conns in tests
            return ()
    return _columns_cached(table, 0)


def resolve_column(table: str, name: str, conn: Any | None = None) -> str | None:
    """Return the real column name for `name`, matching case-insensitively."""
    if not name:
        return None
    cols = columns_for_table(table, conn)
    if not cols:
        return None
    target = name.strip().lower()
    for col in cols:
        if col.lower() == target:
            return col
    return None


def table_has_column(table: str, column: str, conn: Any | None = None) -> bool:
    return resolve_column(table, column, conn) is not None


# --------------------------------------------------------------------------
# Prompt rendering
# --------------------------------------------------------------------------
def table_catalog_prompt_text(conn: Any | None = None) -> str:
    """Compact catalog for the router prompt, limited to registered tables."""
    catalog = load_table_catalog()
    try:
        registered = set(list_registered_tables(conn))
    except Exception:  # noqa: BLE001 — allow prompt building without a live DB
        registered = set(catalog.get("tables", {}))

    lines: list[str] = ["AVAILABLE TABLES (pick exactly ONE):"]

    for table, spec in catalog.get("tables", {}).items():
        if table not in registered:
            continue
        lines.append("")
        lines.append(f"TABLE {table}")
        lines.append(f"  entity: {spec.get('entity', '?')} | grain: {spec.get('grain', '?')}")
        name_col = spec.get("name_column")
        lines.append(f"  name column: {name_col if name_col else 'NONE — cannot filter by name'}")
        slices = spec.get("slices") or []
        lines.append(f"  slice columns: {', '.join(slices) if slices else 'none'}")
        covers = " ".join(str(spec.get("covers", "")).split())
        if covers:
            lines.append(f"  covers: {covers}")
        key_cols = spec.get("key_columns") or []
        if key_cols:
            lines.append(f"  key columns: {', '.join(key_cols)}")
        for family in spec.get("column_families") or []:
            lines.append(f"  family: {family}")
        pt_guide = spec.get("pt_measure_type_guide") or {}
        for pt_type, cols in pt_guide.items():
            lines.append(f"  pt_measure_type {pt_type}: {cols}")
        measure_types = spec.get("measure_types") or []
        if measure_types:
            lines.append(f"  measure_type values: {', '.join(measure_types)}")
        limits = " ".join(str(spec.get("limits", "")).split())
        if limits:
            lines.append(f"  LIMITS: {limits}")

    lines.append("")
    lines.append("ENUMS")
    lines.append(f"  season_type: {', '.join(SEASON_TYPES)}")
    lines.append(f"  per_mode: {', '.join(PER_MODES_DASH_EXTENDED)}")
    lines.append(f"  pt_measure_type (tracking tables only): {', '.join(PT_MEASURE_TYPES)}")
    lines.append(f"  measure_type (lineups only): {', '.join(LINEUP_MEASURE_TYPES)}")

    lines.append("")
    lines.append("REJECT (set supported=false) when the question needs two tables at once:")
    for shape in load_table_catalog().get("unsupported_shapes", []):
        lines.append(f"  - {shape}")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Plan model
# --------------------------------------------------------------------------
class RouterPlan(BaseModel):
    supported: bool = True
    unsupported_reason: str | None = None

    entity_type: Literal["player", "team", "league"] = "player"
    entities: list[str] = Field(default_factory=list)

    season_from: str | None = None
    season_to: str | None = None
    season_type: str = "Regular Season"

    table: str | None = None
    per_modes: list[str] = Field(default_factory=lambda: ["PerGame"])
    measure_type: str | None = None
    pt_measure_type: str | None = None
    group_quantity: int | None = None

    topic: str | None = None
    stat_focus: list[str] = Field(default_factory=list)
    order_by: str | None = None
    sort_dir: Literal["desc", "asc"] = "desc"
    limit: int | None = None

    @field_validator("per_modes")
    @classmethod
    def _non_empty_per_modes(cls, v: list[str]) -> list[str]:
        return (v or ["PerGame"])[:MAX_PER_MODES]

    @field_validator("entities")
    @classmethod
    def _clean_entities(cls, v: list[str]) -> list[str]:
        return [e.strip() for e in (v or []) if e and e.strip()]

    # -- derived -----------------------------------------------------------
    def is_leaderboard(self) -> bool:
        return not self.entities and bool(self.order_by or self.limit)

    def is_multi_season(self) -> bool:
        return bool(self.season_from and self.season_to and self.season_from != self.season_to)

    def season_label(self) -> str:
        if self.season_from and self.season_to:
            if self.season_from == self.season_to:
                return self.season_from
            return f"{self.season_from} → {self.season_to}"
        return self.season_from or self.season_to or "all seasons"

    def citation(self) -> str:
        """One-line provenance string for the analyst and the debug log."""
        bits = [f"table={self.table}", f"seasons={self.season_label()}", f"season_type={self.season_type}"]
        if self.per_modes:
            bits.append(f"per_mode={'/'.join(self.per_modes)}")
        if self.pt_measure_type:
            bits.append(f"pt_measure_type={self.pt_measure_type}")
        if self.measure_type:
            bits.append(f"measure_type={self.measure_type}")
        return " | ".join(bits)


class PlanValidationError(ValueError):
    pass


def plan_from_dict(data: dict[str, Any]) -> RouterPlan:
    return RouterPlan.model_validate(data)


def bundle_label(plan: RouterPlan, per_mode: str) -> str:
    parts = [plan.table or "unknown"]
    if plan.pt_measure_type:
        parts.append(plan.pt_measure_type)
    if plan.measure_type:
        parts.append(plan.measure_type)
    parts.append(per_mode)
    return "__".join(parts)


def validate_plan(plan: RouterPlan, conn: Any | None = None) -> None:
    """Raise PlanValidationError if the plan cannot be executed as written.

    Invalid `stat_focus` entries are dropped with a warning rather than failing —
    they only steer analyst column selection. `order_by` must be real, because a
    bad ORDER BY is a hard SQL error.
    """
    if not plan.supported:
        if not (plan.unsupported_reason or "").strip():
            raise PlanValidationError("supported=false requires unsupported_reason")
        return

    errors: list[str] = []

    if not plan.table:
        raise PlanValidationError("table is required when supported=true")

    registered = set(list_registered_tables(conn))
    if plan.table not in registered:
        known = ", ".join(sorted(registered))
        raise PlanValidationError(
            f"unknown table '{plan.table}' (registered tables: {known})"
        )

    spec = catalog_entry(plan.table)
    slices = set(spec.get("slices") or [])

    if plan.season_type not in SEASON_TYPES:
        errors.append(f"invalid season_type '{plan.season_type}'")

    for field_name in ("season_from", "season_to"):
        value = getattr(plan, field_name)
        if value and not _SEASON_RE.match(value):
            errors.append(f"{field_name} must look like '2023-24', got '{value}'")

    if plan.season_from and plan.season_to and plan.season_from > plan.season_to:
        errors.append(
            f"season_from '{plan.season_from}' is after season_to '{plan.season_to}'"
        )

    if "per_mode" in slices:
        for pm in plan.per_modes:
            if pm not in PER_MODES_DASH_EXTENDED:
                errors.append(f"invalid per_mode '{pm}'")

    if plan.pt_measure_type:
        if "pt_measure_type" not in slices:
            errors.append(f"pt_measure_type is not valid on {plan.table}")
        elif plan.pt_measure_type not in PT_MEASURE_TYPES:
            errors.append(f"invalid pt_measure_type '{plan.pt_measure_type}'")
    elif "pt_measure_type" in slices:
        errors.append(
            f"{plan.table} requires pt_measure_type — pick the slice matching the question"
        )

    if plan.measure_type:
        if "measure_type" not in slices:
            errors.append(f"measure_type is not valid on {plan.table}")
        elif plan.measure_type not in LINEUP_MEASURE_TYPES:
            errors.append(f"invalid measure_type '{plan.measure_type}'")

    if plan.group_quantity is not None:
        if "group_quantity" not in slices:
            errors.append(f"group_quantity is not valid on {plan.table}")
        elif plan.group_quantity not in LINEUP_GROUP_QUANTITIES:
            errors.append(f"invalid group_quantity {plan.group_quantity}")

    if plan.entities and not spec.get("name_column"):
        errors.append(
            f"{plan.table} has no name column, so it cannot be filtered by entity name"
        )

    if not plan.entities and not plan.is_leaderboard() and plan.entity_type != "league":
        errors.append("entities required unless this is a leaderboard (set order_by/limit)")

    if plan.order_by:
        resolved = resolve_column(plan.table, plan.order_by, conn)
        if resolved is None:
            errors.append(f"order_by column '{plan.order_by}' does not exist on {plan.table}")
        else:
            plan.order_by = resolved

    if plan.stat_focus:
        kept: list[str] = []
        dropped: list[str] = []
        for col in plan.stat_focus[:MAX_STAT_FOCUS]:
            resolved = resolve_column(plan.table, col, conn)
            if resolved:
                kept.append(resolved)
            else:
                dropped.append(col)
        if dropped:
            logger.warning(
                "Router stat_focus columns not on %s, dropped: %s",
                plan.table,
                ", ".join(dropped),
            )
        plan.stat_focus = kept

    if errors:
        raise PlanValidationError("; ".join(errors))
