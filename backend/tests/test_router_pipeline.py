"""Unit tests for router plan → SQL builder (schema v2, no API keys required)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from Interpreter.router_plan import (  # noqa: E402
    PlanValidationError,
    RouterPlan,
    plan_from_dict,
    validate_plan,
)
from Interpreter.sql_builder import build_select_sql  # noqa: E402


def _cols(*names: str):
    """Patch target for column lookups: pretend these columns exist."""
    lowered = {n.lower() for n in names}

    def _resolve(table, name, conn=None):
        if not name:
            return None
        for real in names:
            if real.lower() == name.strip().lower():
                return real
        return None

    def _has(table, column, conn=None):
        return column.strip().lower() in lowered

    return _resolve, _has


SEASON_COLS = (
    "season", "season_type", "per_mode", "PLAYER_NAME", "TEAM_NAME",
    "PTS", "PTS_RANK", "FG3_PCT", "FG3M", "GP", "MIN",
)


# --------------------------------------------------------------------------
# validate_plan
# --------------------------------------------------------------------------
def test_validate_plan_rejects_unknown_table():
    plan = RouterPlan(entities=["<ENTITY_A>"], season_from="2023-24", season_to="2023-24",
                      table="not_a_real_table")
    with patch("Interpreter.router_plan.list_registered_tables",
               return_value=["player_season_stats"]):
        with pytest.raises(PlanValidationError, match="unknown table"):
            validate_plan(plan, MagicMock())


def test_validate_plan_rejects_pt_measure_type_on_non_tracking_table():
    plan = RouterPlan(entities=["<ENTITY_A>"], table="player_season_stats",
                      pt_measure_type="Defense")
    with patch("Interpreter.router_plan.list_registered_tables",
               return_value=["player_season_stats"]):
        with pytest.raises(PlanValidationError, match="pt_measure_type is not valid"):
            validate_plan(plan, MagicMock())


def test_validate_plan_requires_pt_measure_type_on_tracking_table():
    plan = RouterPlan(entities=["<ENTITY_A>"], table="player_tracking")
    with patch("Interpreter.router_plan.list_registered_tables",
               return_value=["player_tracking"]):
        with pytest.raises(PlanValidationError, match="requires pt_measure_type"):
            validate_plan(plan, MagicMock())


def test_validate_plan_rejects_backwards_season_range():
    plan = RouterPlan(entities=["<ENTITY_A>"], table="player_season_stats",
                      season_from="2024-25", season_to="2015-16")
    resolve, _ = _cols(*SEASON_COLS)
    with patch("Interpreter.router_plan.list_registered_tables",
               return_value=["player_season_stats"]), \
         patch("Interpreter.router_plan.resolve_column", side_effect=resolve):
        with pytest.raises(PlanValidationError, match="is after season_to"):
            validate_plan(plan, MagicMock())


def test_validate_plan_rejects_malformed_season_label():
    plan = RouterPlan(entities=["<ENTITY_A>"], table="player_season_stats",
                      season_from="2023", season_to="2023")
    with patch("Interpreter.router_plan.list_registered_tables",
               return_value=["player_season_stats"]):
        with pytest.raises(PlanValidationError, match="must look like"):
            validate_plan(plan, MagicMock())


def test_validate_plan_drops_unknown_stat_focus_but_fails_bad_order_by():
    resolve, _ = _cols(*SEASON_COLS)
    with patch("Interpreter.router_plan.list_registered_tables",
               return_value=["player_season_stats"]), \
         patch("Interpreter.router_plan.resolve_column", side_effect=resolve):
        ok = RouterPlan(entities=["<ENTITY_A>"], table="player_season_stats",
                        stat_focus=["PTS", "NOT_A_COLUMN"])
        validate_plan(ok, MagicMock())
        assert ok.stat_focus == ["PTS"]

        bad = RouterPlan(table="player_season_stats", order_by="NOT_A_COLUMN", limit=10)
        with pytest.raises(PlanValidationError, match="order_by column"):
            validate_plan(bad, MagicMock())


def test_validate_plan_normalizes_order_by_casing():
    resolve, _ = _cols(*SEASON_COLS)
    plan = RouterPlan(table="player_season_stats", order_by="pts", limit=5)
    with patch("Interpreter.router_plan.list_registered_tables",
               return_value=["player_season_stats"]), \
         patch("Interpreter.router_plan.resolve_column", side_effect=resolve):
        validate_plan(plan, MagicMock())
    assert plan.order_by == "PTS"


def test_unsupported_plan_requires_reason():
    with pytest.raises(PlanValidationError, match="unsupported_reason"):
        validate_plan(RouterPlan(supported=False), MagicMock())

    validate_plan(
        RouterPlan(supported=False, unsupported_reason="needs two tables"), MagicMock()
    )


# --------------------------------------------------------------------------
# build_select_sql
# --------------------------------------------------------------------------
def test_sql_single_season_entity_pull():
    plan = plan_from_dict({
        "entity_type": "player",
        "entities": ["<ENTITY_A>", "<ENTITY_B>"],
        "season_from": "2023-24",
        "season_to": "2023-24",
        "season_type": "Regular Season",
        "table": "player_season_stats",
        "per_modes": ["PerGame"],
        "stat_focus": ["PTS"],
    })
    resolve, has = _cols(*SEASON_COLS)
    with patch("Interpreter.sql_builder.resolve_column", side_effect=resolve), \
         patch("Interpreter.sql_builder.table_has_column", side_effect=has):
        sql = build_select_sql(plan, "PerGame", MagicMock())

    assert "SELECT * FROM player_season_stats" in sql
    assert "season = '2023-24'" in sql
    assert "season_type = 'Regular Season'" in sql
    assert "per_mode = 'PerGame'" in sql
    assert "strip_accents(PLAYER_NAME) ILIKE '%<ENTITY_A>%'" in sql
    assert "strip_accents(PLAYER_NAME) ILIKE '%<ENTITY_B>%'" in sql
    assert "JOIN" not in sql.upper()
    assert "UNION" not in sql.upper()


def test_sql_season_range_uses_between_not_multiple_queries():
    plan = plan_from_dict({
        "entities": ["<ENTITY_A>"],
        "season_from": "2015-16",
        "season_to": "2024-25",
        "table": "player_season_stats",
        "per_modes": ["PerGame"],
    })
    resolve, has = _cols(*SEASON_COLS)
    with patch("Interpreter.sql_builder.resolve_column", side_effect=resolve), \
         patch("Interpreter.sql_builder.table_has_column", side_effect=has):
        sql = build_select_sql(plan, "PerGame", MagicMock())

    assert "season >= '2015-16'" in sql
    assert "season <= '2024-25'" in sql
    assert "ORDER BY season ASC" in sql
    assert "UNION" not in sql.upper()


def test_sql_leaderboard_uses_order_by_and_limit():
    plan = plan_from_dict({
        "entities": [],
        "season_from": "2020-21",
        "season_to": "2020-21",
        "table": "player_season_stats",
        "per_modes": ["PerGame"],
        "order_by": "FG3M",
        "limit": 20,
    })
    resolve, has = _cols(*SEASON_COLS, "FG3M")
    with patch("Interpreter.sql_builder.resolve_column", side_effect=resolve), \
         patch("Interpreter.sql_builder.table_has_column", side_effect=has):
        sql = build_select_sql(plan, "PerGame", MagicMock())

    assert "ORDER BY FG3M DESC" in sql
    assert "LIMIT 20" in sql
    assert "ILIKE" not in sql


def test_sql_ascending_leaderboard():
    plan = plan_from_dict({
        "entities": [],
        "table": "player_season_stats",
        "order_by": "PTS",
        "sort_dir": "asc",
        "limit": 5,
    })
    resolve, has = _cols(*SEASON_COLS)
    with patch("Interpreter.sql_builder.resolve_column", side_effect=resolve), \
         patch("Interpreter.sql_builder.table_has_column", side_effect=has):
        sql = build_select_sql(plan, "PerGame", MagicMock())

    assert "ORDER BY PTS ASC" in sql


def test_sql_skips_entity_filter_when_table_has_no_name_column():
    plan = plan_from_dict({
        "entities": ["<ENTITY_A>"],
        "season_from": "2023-24",
        "season_to": "2023-24",
        "table": "court_shots",
        "per_modes": ["PerGame"],
    })
    resolve, has = _cols("season", "season_type", "player_id")
    with patch("Interpreter.sql_builder.resolve_column", side_effect=resolve), \
         patch("Interpreter.sql_builder.table_has_column", side_effect=has):
        sql = build_select_sql(plan, "PerGame", MagicMock())

    assert "ILIKE" not in sql
    assert "per_mode" not in sql
    assert "season = '2023-24'" in sql


def test_sql_tracking_slice_is_applied():
    plan = plan_from_dict({
        "entities": ["<ENTITY_A>"],
        "season_from": "2023-24",
        "season_to": "2023-24",
        "table": "player_tracking",
        "pt_measure_type": "Defense",
        "per_modes": ["PerGame"],
    })
    resolve, has = _cols("season", "season_type", "per_mode", "pt_measure_type", "PLAYER_NAME")
    with patch("Interpreter.sql_builder.resolve_column", side_effect=resolve), \
         patch("Interpreter.sql_builder.table_has_column", side_effect=has):
        sql = build_select_sql(plan, "PerGame", MagicMock())

    assert "pt_measure_type = 'Defense'" in sql
    assert "strip_accents(PLAYER_NAME) ILIKE '%<ENTITY_A>%'" in sql


# --------------------------------------------------------------------------
# plan helpers
# --------------------------------------------------------------------------
def test_season_label_and_multi_season_flags():
    single = RouterPlan(table="player_season_stats", season_from="2023-24", season_to="2023-24")
    assert single.season_label() == "2023-24"
    assert not single.is_multi_season()

    span = RouterPlan(table="player_season_stats", season_from="2015-16", season_to="2024-25")
    assert span.is_multi_season()
    assert "2015-16" in span.season_label() and "2024-25" in span.season_label()

    allseasons = RouterPlan(table="player_season_stats")
    assert allseasons.season_label() == "all seasons"


def test_citation_contains_source_slice():
    plan = RouterPlan(table="player_season_stats", season_from="2023-24", season_to="2023-24",
                      per_modes=["PerGame"])
    citation = plan.citation()
    assert "player_season_stats" in citation
    assert "2023-24" in citation
    assert "Regular Season" in citation
