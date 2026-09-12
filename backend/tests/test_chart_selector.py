"""Unit tests for chart selection (pure — no DuckDB, no API keys, no network).

Every branch of the selector is reachable without a database, which is the point of
moving chart choice off the model: Team45's equivalent could only be tested by making
a GPT call and hoping.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from Interpreter.router_plan import RouterPlan  # noqa: E402
from Visualizer.selector import chart_hint_line, select_charts  # noqa: E402


def _plan(**kwargs) -> RouterPlan:
    base = dict(
        supported=True,
        entity_type="player",
        table="player_season_stats",
        season_from="2023-24",
        season_to="2023-24",
        per_modes=["PerGame"],
    )
    base.update(kwargs)
    return RouterPlan(**base)


def _bundle(df: pd.DataFrame, per_mode: str = "PerGame") -> dict[str, pd.DataFrame]:
    return {f"player_season_stats__{per_mode}": df}


def _kind(plan: RouterPlan, bundles) -> str | None:
    charts = select_charts(plan, bundles)
    return charts[0].kind if charts else None


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
def test_no_plan_no_chart():
    assert select_charts(None, _bundle(pd.DataFrame([{"PTS": 1}]))) == []


def test_unsupported_plan_no_chart():
    plan = _plan(supported=False, unsupported_reason="NOT_BASKETBALL: nope")
    assert select_charts(plan, _bundle(pd.DataFrame([{"PTS": 1}]))) == []


def test_no_bundles_no_chart():
    assert select_charts(_plan(), {}) == []


def test_empty_frame_no_chart():
    assert select_charts(_plan(), _bundle(pd.DataFrame())) == []


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------
def _leaderboard_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"PLAYER_NAME": "Joel Embiid", "TEAM_ABBREVIATION": "PHI", "PTS": 34.7, "GP": 39},
            {"PLAYER_NAME": "Luka Doncic", "TEAM_ABBREVIATION": "DAL", "PTS": 33.9, "GP": 70},
            {"PLAYER_NAME": "Giannis Antetokounmpo", "TEAM_ABBREVIATION": "MIL", "PTS": 30.4, "GP": 73},
        ]
    )


def test_leaderboard_selected():
    plan = _plan(entities=[], order_by="PTS", limit=10, stat_focus=["PTS"])
    charts = select_charts(plan, _bundle(_leaderboard_frame()))
    assert len(charts) == 1
    spec = charts[0]
    assert spec.kind == "leaderboard"
    assert spec.rows[0] == {
        "rank": 1,
        "name": "Joel Embiid",
        "teamAbbr": "PHI",
        "value": 34.7,
    }
    assert spec.y[0].column == "PTS"
    assert spec.y[0].label == "Points per game"


def test_leaderboard_subtitle_names_per_mode():
    plan = _plan(entities=[], order_by="PTS", limit=10, stat_focus=["PTS"], per_modes=["Totals"])
    charts = select_charts(plan, _bundle(_leaderboard_frame(), per_mode="Totals"))
    assert "Totals" in charts[0].subtitle
    assert charts[0].y[0].label == "Total points"


def test_leaderboard_row_cap():
    rows = [
        {"PLAYER_NAME": f"Player {i}", "TEAM_ABBREVIATION": "XXX", "PTS": 30 - i * 0.1, "GP": 70}
        for i in range(40)
    ]
    plan = _plan(entities=[], order_by="PTS", limit=40, stat_focus=["PTS"])
    charts = select_charts(plan, _bundle(pd.DataFrame(rows)))
    assert len(charts[0].rows) == 15
    assert any("Showing 15 of 40" in n for n in charts[0].notes)


def test_career_leaderboard_titled_all_time():
    plan = _plan(
        entities=[], order_by="PTS", limit=10, stat_focus=["PTS"],
        career_scope=True, per_modes=["Totals"],
    )
    charts = select_charts(plan, _bundle(_leaderboard_frame(), per_mode="Totals"))
    assert charts[0].kind == "leaderboard"
    assert charts[0].title.startswith("All-time")


def test_applied_floor_reaches_the_footer():
    plan = _plan(
        entities=[], order_by="FG3_PCT", limit=10, stat_focus=["FG3_PCT"],
        applied_floors=[{"phrase": "at least 20 games played", "column": "GP", "value": 20}],
    )
    frame = pd.DataFrame(
        [{"PLAYER_NAME": "Someone", "TEAM_ABBREVIATION": "BOS", "FG3_PCT": 0.44, "GP": 70}]
    )
    charts = select_charts(plan, _bundle(frame))
    assert any("at least 20 games played" in n for n in charts[0].notes)


# ---------------------------------------------------------------------------
# Scatter — checked before leaderboard, since both are rankings
# ---------------------------------------------------------------------------
def test_scatter_ignores_the_context_columns_the_router_always_adds():
    """The router returns [USG_PCT, TS_PCT, GP, MIN] for a two-stat question.

    Counting GP and MIN would make the scatter rule unreachable in practice — this is
    the case that proved it, against the live router.
    """
    frame = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Nikola Jokic", "TEAM_ABBREVIATION": "DEN",
                "USG_PCT": 0.29, "TS_PCT": 0.701, "GP": 79, "MIN": 34.6,
            },
            {
                "PLAYER_NAME": "Joel Embiid", "TEAM_ABBREVIATION": "PHI",
                "USG_PCT": 0.37, "TS_PCT": 0.646, "GP": 39, "MIN": 33.6,
            },
        ]
    )
    plan = _plan(
        entities=[], order_by="TS_PCT", limit=25,
        stat_focus=["USG_PCT", "TS_PCT", "GP", "MIN"],
    )
    assert _kind(plan, _bundle(frame)) == "scatter"


def test_three_subject_stats_is_a_leaderboard_not_a_scatter():
    """"Top 25 scorers by TS% and usage" is a ranking with supporting columns."""
    frame = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Joel Embiid", "TEAM_ABBREVIATION": "PHI",
                "PTS": 34.7, "TS_PCT": 0.646, "USG_PCT": 0.37, "GP": 39, "MIN": 33.6,
            }
        ]
    )
    plan = _plan(
        entities=[], order_by="PTS", limit=25,
        stat_focus=["PTS", "TS_PCT", "USG_PCT", "GP", "MIN"],
    )
    assert _kind(plan, _bundle(frame)) == "leaderboard"


def test_scatter_wins_when_two_stats_are_focused():
    frame = pd.DataFrame(
        [
            {"PLAYER_NAME": "Nikola Jokic", "TEAM_ABBREVIATION": "DEN", "PTS": 26.4, "TS_PCT": 0.701},
            {"PLAYER_NAME": "Joel Embiid", "TEAM_ABBREVIATION": "PHI", "PTS": 34.7, "TS_PCT": 0.646},
        ]
    )
    plan = _plan(entities=[], order_by="PTS", limit=20, stat_focus=["PTS", "TS_PCT"])
    charts = select_charts(plan, _bundle(frame))
    assert charts[0].kind == "scatter"
    assert charts[0].rows[0] == {
        "name": "Nikola Jokic",
        "teamAbbr": "DEN",
        "x": 26.4,
        "y": 0.701,
    }
    assert charts[0].x.column == "PTS"
    assert charts[0].y[0].column == "TS_PCT"
    assert charts[0].y[0].unit == "pct"


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------
def _trend_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"PLAYER_NAME": "Stephen Curry", "SEASON": "2021-22", "FG3_PCT": 0.380, "GP": 64},
            {"PLAYER_NAME": "Stephen Curry", "SEASON": "2022-23", "FG3_PCT": 0.427, "GP": 56},
            {"PLAYER_NAME": "Stephen Curry", "SEASON": "2023-24", "FG3_PCT": 0.408, "GP": 74},
        ]
    )


def test_trend_selected_for_one_entity_over_seasons():
    plan = _plan(
        entities=["Stephen Curry"], season_from="2021-22", season_to="2023-24",
        stat_focus=["FG3_PCT"],
    )
    charts = select_charts(plan, _bundle(_trend_frame()))
    assert charts[0].kind == "trend"
    assert charts[0].rows == [
        {"season": "2021-22", "value": 0.38},
        {"season": "2022-23", "value": 0.427},
        {"season": "2023-24", "value": 0.408},
    ]


def test_trend_prefers_the_fullest_row_for_a_traded_player():
    frame = pd.DataFrame(
        [
            {"PLAYER_NAME": "A Player", "SEASON": "2022-23", "PTS": 9.0, "GP": 12},
            {"PLAYER_NAME": "A Player", "SEASON": "2022-23", "PTS": 21.0, "GP": 55},
            {"PLAYER_NAME": "A Player", "SEASON": "2023-24", "PTS": 20.0, "GP": 70},
        ]
    )
    plan = _plan(
        entities=["A Player"], season_from="2022-23", season_to="2023-24", stat_focus=["PTS"]
    )
    charts = select_charts(plan, _bundle(frame))
    assert charts[0].rows == [
        {"season": "2022-23", "value": 21.0},
        {"season": "2023-24", "value": 20.0},
    ]


def test_single_season_is_not_a_trend():
    plan = _plan(entities=["Stephen Curry"], stat_focus=["FG3_PCT"])
    frame = pd.DataFrame(
        [{"PLAYER_NAME": "Stephen Curry", "SEASON": "2023-24", "FG3_PCT": 0.408, "GP": 74}]
    )
    assert _kind(plan, _bundle(frame)) == "table"


# ---------------------------------------------------------------------------
# compare_trend
# ---------------------------------------------------------------------------
def test_compare_trend_pivots_one_key_per_entity():
    frame = pd.DataFrame(
        [
            {"PLAYER_NAME": "LeBron James", "SEASON": "2022-23", "PTS": 28.9, "GP": 55},
            {"PLAYER_NAME": "LeBron James", "SEASON": "2023-24", "PTS": 25.7, "GP": 71},
            {"PLAYER_NAME": "Stephen Curry", "SEASON": "2022-23", "PTS": 29.4, "GP": 56},
            {"PLAYER_NAME": "Stephen Curry", "SEASON": "2023-24", "PTS": 26.4, "GP": 74},
        ]
    )
    plan = _plan(
        entities=["LeBron James", "Stephen Curry"],
        season_from="2022-23", season_to="2023-24", stat_focus=["PTS"],
    )
    charts = select_charts(plan, _bundle(frame))
    assert charts[0].kind == "compare_trend"
    assert charts[0].series == "PLAYER_NAME"
    assert charts[0].rows == [
        {"season": "2022-23", "LeBron James": 28.9, "Stephen Curry": 29.4},
        {"season": "2023-24", "LeBron James": 25.7, "Stephen Curry": 26.4},
    ]


# ---------------------------------------------------------------------------
# Radar
# ---------------------------------------------------------------------------
def test_radar_normalizes_against_player_ceilings():
    frame = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Nikola Jokic", "SEASON": "2023-24",
                "PTS": 26.4, "AST": 9.0, "REB": 12.4, "STL": 1.4, "BLK": 0.9, "GP": 79,
            }
        ]
    )
    plan = _plan(entities=["Nikola Jokic"], stat_focus=["PTS", "AST", "REB", "STL", "BLK"])
    charts = select_charts(plan, _bundle(frame))
    spec = charts[0]
    assert spec.kind == "radar"
    assert len(spec.rows) == 5
    # 26.4 of a 35.0 ceiling.
    assert spec.rows[0] == {"category": "Points", "normalized": 75.4, "raw": 26.4}
    # Both keys present makes this a drop-in for the TS SkillRadarCategory type.
    assert set(spec.rows[0]) == {"category", "normalized", "raw"}


def test_pivoted_kinds_do_not_claim_a_truncation_that_never_happened():
    """12 player-season rows pivot into 6 season rows — that is not "6 of 12"."""
    rows = [
        {"PLAYER_NAME": name, "SEASON": season, "PTS": 25.0, "GP": 70}
        for name in ("LeBron James", "Stephen Curry")
        for season in ("2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24")
    ]
    plan = _plan(
        entities=["LeBron James", "Stephen Curry"],
        season_from="2018-19", season_to="2023-24", stat_focus=["PTS"],
    )
    charts = select_charts(plan, _bundle(pd.DataFrame(rows)))
    assert charts[0].kind == "compare_trend"
    assert len(charts[0].rows) == 6
    assert not any("Showing" in n for n in charts[0].notes)


def test_compare_radar_names_the_players_it_left_out():
    rows = [
        {
            "PLAYER_NAME": name, "SEASON": "2022-23",
            "PTS": 25.0, "AST": 5.0, "REB": 8.0, "STL": 1.0, "BLK": 1.0, "GP": 70,
        }
        for name in ("Nikola Jokic", "Joel Embiid", "Third Guy")
    ]
    plan = _plan(
        entities=["Nikola Jokic", "Joel Embiid", "Third Guy"],
        stat_focus=["PTS", "AST", "REB", "STL", "BLK"],
    )
    charts = select_charts(plan, _bundle(pd.DataFrame(rows)))
    assert any("Third Guy not shown" in n for n in charts[0].notes)


def test_compare_radar_caps_at_two_series():
    rows = [
        {
            "PLAYER_NAME": name, "SEASON": "2022-23",
            "PTS": pts, "AST": 5.0, "REB": 8.0, "STL": 1.0, "BLK": 1.0, "GP": 70,
        }
        for name, pts in [("Nikola Jokic", 24.5), ("Joel Embiid", 33.1), ("Third Guy", 20.0)]
    ]
    plan = _plan(
        entities=["Nikola Jokic", "Joel Embiid", "Third Guy"],
        season_from="2022-23", season_to="2022-23",
        stat_focus=["PTS", "AST", "REB", "STL", "BLK"],
    )
    charts = select_charts(plan, _bundle(pd.DataFrame(rows)))
    spec = charts[0]
    assert spec.kind == "compare_radar"
    assert "Third Guy" not in spec.rows[0]
    assert set(spec.rows[0]) == {"category", "Nikola Jokic", "Joel Embiid"}


def test_two_stats_is_not_enough_for_a_radar():
    frame = pd.DataFrame(
        [{"PLAYER_NAME": "Someone", "SEASON": "2023-24", "PTS": 20.0, "AST": 5.0, "GP": 70}]
    )
    plan = _plan(entities=["Someone"], stat_focus=["PTS", "AST"])
    assert _kind(plan, _bundle(frame)) == "table"


# ---------------------------------------------------------------------------
# Table fallback
# ---------------------------------------------------------------------------
def test_table_is_the_fallback_not_a_blank():
    frame = pd.DataFrame(
        [{"PLAYER_NAME": "LeBron James", "DRAFT_YEAR_NUM": 2003, "DRAFT_NUMBER_NUM": 1}]
    )
    plan = _plan(
        entities=[],
        row_filters=[{"column": "DRAFT_YEAR_NUM", "op": "eq", "value": 2003}],
        stat_focus=["DRAFT_NUMBER_NUM"],
    )
    charts = select_charts(plan, _bundle(frame))
    assert charts[0].kind == "table"
    assert charts[0].rows[0]["PLAYER_NAME"] == "LeBron James"


def test_rank_columns_are_never_charted():
    frame = pd.DataFrame(
        [{"PLAYER_NAME": "Someone", "TEAM_ABBREVIATION": "BOS", "PTS_RANK": 1, "GP": 70}]
    )
    plan = _plan(entities=[], order_by="PTS_RANK", limit=5)
    charts = select_charts(plan, _bundle(frame))
    assert charts == [] or charts[0].kind == "table"


# ---------------------------------------------------------------------------
# Provenance + analyst hint
# ---------------------------------------------------------------------------
def test_citation_travels_with_the_chart():
    plan = _plan(entities=[], order_by="PTS", limit=10, stat_focus=["PTS"])
    charts = select_charts(plan, _bundle(_leaderboard_frame()))
    assert "player_season_stats" in charts[0].citation


# ---------------------------------------------------------------------------
# Regressions from the 40-question hardening pass
# ---------------------------------------------------------------------------
def _kobe_frame() -> pd.DataFrame:
    """Kobe Bryant 2005-06, as the vault really returns it.

    The frame is SELECT *, so REB/AST/STL/BLK are present even though the router never
    put them in stat_focus — which is exactly why the radar used to chart shooting
    splits and call the result a skill profile.
    """
    return pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Kobe Bryant", "SEASON": "2005-06", "GP": 80, "MIN": 41.0,
                "PTS": 35.4, "REB": 5.3, "AST": 4.5, "STL": 1.8, "BLK": 0.4,
                "FGM": 12.2, "FGA": 27.2, "FG_PCT": 0.450,
                "FG3M": 2.3, "FG3A": 6.5, "FG3_PCT": 0.347,
                "FTM": 8.7, "FTA": 10.2, "FT_PCT": 0.850,
            }
        ]
    )


def _tracking_frame() -> pd.DataFrame:
    """A table with no core counting stats — the fallback path."""
    return pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Kobe Bryant", "SEASON": "2005-06", "GP": 80, "MIN": 41.0,
                "FGM": 12.2, "FGA": 27.2, "FG_PCT": 0.450,
                "FG3M": 2.3, "FG3A": 6.5, "FG3_PCT": 0.347,
                "FTM": 8.7, "FTA": 10.2, "FT_PCT": 0.850,
            }
        ]
    )


def _cats(spec) -> list[str]:
    return [r["category"] for r in spec.rows]


def test_radar_defaults_to_points_rebounds_assists_steals_blocks():
    """A generic profile question charts how someone PLAYS, not how they shot.

    The router pads stat_focus with GP, MIN and every shooting split; none of that is
    what a radar is for.
    """
    plan = _plan(entities=["Kobe Bryant"], stat_focus=KOBE_FOCUS)
    spec = select_charts(plan, _bundle(_kobe_frame()))[0]
    assert spec.kind == "radar"
    assert _cats(spec) == ["Points", "Rebounds", "Assists", "Steals", "Blocks"]


def test_radar_honours_an_explicitly_narrow_shooting_request():
    """Asking for the percentages specifically still gets them."""
    plan = _plan(entities=["Kobe Bryant"], stat_focus=["FG_PCT", "FG3_PCT", "FT_PCT"])
    spec = select_charts(plan, _bundle(_kobe_frame()))[0]
    assert spec.kind == "radar"
    assert _cats(spec) == ["FG%", "3P%", "FT%"]


def test_radar_carries_the_bare_entity_name_for_the_caption():
    plan = _plan(entities=["Kobe Bryant"], stat_focus=KOBE_FOCUS)
    spec = select_charts(plan, _bundle(_kobe_frame()))[0]
    assert spec.series == "Kobe Bryant"
    assert spec.title == "Kobe Bryant: skill profile"


KOBE_FOCUS = [
    "GP", "MIN", "PTS", "FGM", "FGA", "FG_PCT",
    "FG3M", "FG3A", "FG3_PCT", "FTM", "FTA", "FT_PCT",
]


def test_f1_no_axis_is_pegged_by_a_frame_max_fallback():
    """A solo frame has one row, so normalising against it always produced 100.0."""
    plan = _plan(entities=["Kobe Bryant"], stat_focus=KOBE_FOCUS)
    spec = select_charts(plan, _bundle(_tracking_frame()))[0]
    assert spec.kind == "radar"
    pegged = [r["category"] for r in spec.rows if r["normalized"] == 100.0]
    # Only genuine ceiling exceedances survive: 35.4 pts > 35.0, 41.0 min > 38.0.
    assert set(pegged) <= {"Points", "Minutes"}


def test_f2_radar_axes_are_capped():
    plan = _plan(entities=["Kobe Bryant"], stat_focus=KOBE_FOCUS)
    spec = select_charts(plan, _bundle(_tracking_frame()))[0]
    assert len(spec.rows) <= 6


def test_f3_games_and_minutes_are_not_skill_axes():
    plan = _plan(entities=["Kobe Bryant"], stat_focus=KOBE_FOCUS)
    spec = select_charts(plan, _bundle(_kobe_frame()))[0]
    assert "Games played" not in [r["category"] for r in spec.rows]


def test_f4_made_and_attempted_do_not_both_appear():
    plan = _plan(entities=["Kobe Bryant"], stat_focus=KOBE_FOCUS)
    spec = select_charts(plan, _bundle(_tracking_frame()))[0]
    cats = {r["category"] for r in spec.rows}
    for made, attempted in (
        ("Field goals made", "Field goals attempted"),
        ("3-pointers made", "3-pointers attempted"),
        ("Free throws made", "Free throws attempted"),
    ):
        assert not ({made, attempted} <= cats)


def test_f5_all_time_leaders_grid_charts_the_value_column():
    frame = pd.DataFrame(
        [
            {"PLAYER_NAME": "LeBron James", "STAT": "PTS", "VALUE": 43440.0, "STAT_RANK": 1.0},
            {"PLAYER_NAME": "Kareem Abdul-Jabbar", "STAT": "PTS", "VALUE": 38387.0, "STAT_RANK": 2.0},
        ]
    )
    plan = _plan(entities=[], order_by="STAT_RANK", limit=5, stat_focus=["VALUE"])
    spec = select_charts(plan, _bundle(frame))[0]
    assert spec.kind == "leaderboard"
    assert spec.rows[0]["name"] == "LeBron James"
    assert spec.rows[0]["value"] == 43440.0
    assert spec.title == "All-time points leaders"
    # F9: a career total is not a per-game figure.
    assert "PerGame" not in (spec.subtitle or "")


def test_f6_a_plain_leaderboard_is_not_turned_into_a_scatter_by_its_floor_column():
    """[PTS, GP] with order_by=PTS is a scoring leaderboard; GP is only the floor.

    Promoting GP here produced a "Games played vs Points" scatter for the single most
    common question the app gets.
    """
    plan = _plan(entities=[], order_by="PTS", limit=5, stat_focus=["PTS", "GP"])
    assert _kind(plan, _bundle(_leaderboard_frame())) == "leaderboard"


def test_f6_a_question_really_about_minutes_keeps_minutes():
    frame = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Mikal Bridges", "TEAM_ABBREVIATION": "BKN",
                "MIN": 37.6, "PLUS_MINUS": -1.2, "GP": 83,
            }
        ]
    )
    plan = _plan(entities=[], order_by="MIN", limit=30, stat_focus=["MIN", "PLUS_MINUS", "GP"])
    spec = select_charts(plan, _bundle(frame))[0]
    assert spec.kind == "scatter"


def test_f7_series_follow_the_order_the_question_named():
    frame = pd.DataFrame(
        [
            {
                "PLAYER_NAME": name, "SEASON": "2018-19",
                "PTS": pts, "REB": 5.0, "AST": 6.0, "STL": 1.0, "BLK": 0.5, "GP": 70,
            }
            for name, pts in [("Damian Lillard", 25.8), ("Stephen Curry", 27.3)]
        ]
    )
    plan = _plan(
        entities=["Stephen Curry", "Damian Lillard"],
        season_from="2018-19", season_to="2018-19",
        stat_focus=["PTS", "REB", "AST", "STL", "BLK"],
    )
    spec = select_charts(plan, _bundle(frame))[0]
    assert spec.title == "Stephen Curry vs Damian Lillard"


def test_f8_rate_goes_on_the_y_axis():
    frame = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Stephen Curry", "TEAM_ABBREVIATION": "GSW",
                "FG3_PCT": 0.408, "FG3A": 11.8, "GP": 74,
            }
        ]
    )
    plan = _plan(entities=[], order_by="FG3_PCT", limit=20, stat_focus=["FG3_PCT", "FG3A", "GP"])
    spec = select_charts(plan, _bundle(frame))[0]
    assert spec.kind == "scatter"
    assert spec.x.column == "FG3A"
    assert spec.y[0].column == "FG3_PCT"


def test_f10_inverted_stats_say_lower_is_better():
    frame = pd.DataFrame(
        [
            {"PLAYER_NAME": "Kawhi Leonard", "SEASON": s, "DEF_RATING": v, "GP": 70}
            for s, v in [("2014-15", 98.3), ("2015-16", 95.9), ("2016-17", 105.1)]
        ]
    )
    plan = _plan(
        entities=["Kawhi Leonard"], season_from="2014-15", season_to="2016-17",
        stat_focus=["DEF_RATING"],
    )
    spec = select_charts(plan, _bundle(frame))[0]
    assert spec.kind == "trend"
    assert any("lower is better" in n.lower() for n in spec.notes)


# ---------------------------------------------------------------------------
# Shot charts
# ---------------------------------------------------------------------------
def _binned_shot_frame() -> pd.DataFrame:
    """What build_shot_chart_sql returns: hex cells, split by zone."""
    return pd.DataFrame(
        [
            {"hex_col": 22, "hex_row": 30, "zone": "Restricted Area", "made": 6, "total": 9},
            {"hex_col": 23, "hex_row": 30, "zone": "Restricted Area", "made": 4, "total": 7},
            {"hex_col": 40, "hex_row": 12, "zone": "Above the Break 3", "made": 3, "total": 8},
            # Same cell, two zones — a hex on a boundary. Must collapse to ONE cell.
            {"hex_col": 40, "hex_row": 12, "zone": "Mid-Range", "made": 1, "total": 2},
        ]
    )


def _shot_plan(**kw) -> RouterPlan:
    return _plan(table="player_shot_chart", entities=["Stephen Curry"], **kw)


def test_shot_chart_selected_and_cells_collapse_across_zones():
    spec = select_charts(_shot_plan(), _bundle(_binned_shot_frame()))[0]
    assert spec.kind == "shot_chart"
    assert spec.mode == "volume"
    assert len(spec.rows) == 3  # four source rows, one shared between two zones
    shared = [r for r in spec.rows if r["total"] == 10][0]
    assert shared["made"] == 4


def test_shot_chart_cell_centres_match_the_renderer_geometry():
    """cx = col * 12 ; cy = row * hexH + (col even ? 0 : hexH/2) — ShotChartCourt's own."""
    import math

    hex_h = math.sqrt(3) * 8.0
    spec = select_charts(_shot_plan(), _bundle(_binned_shot_frame()))[0]
    by_x = {round(r["x"], 2): r for r in spec.rows}
    assert round(22 * 12.0, 2) in by_x  # even column, no row offset
    assert by_x[round(22 * 12.0, 2)]["y"] == round(30 * hex_h, 2)
    odd = by_x[round(23 * 12.0, 2)]
    assert odd["y"] == round(30 * hex_h + hex_h / 2, 2)


def test_shot_chart_footer_reports_attempts_and_accuracy():
    spec = select_charts(_shot_plan(), _bundle(_binned_shot_frame()))[0]
    # 9 + 7 + 8 + 2 attempts, 6 + 4 + 3 + 1 made
    assert any("26 attempts plotted" in n for n in spec.notes)
    assert any("53.8%" in n for n in spec.notes)


def test_shot_chart_omits_per_mode_from_subtitle_and_citation():
    """player_shot_chart has no per_mode column, so claiming one is false provenance."""
    spec = select_charts(_shot_plan(), _bundle(_binned_shot_frame()))[0]
    assert "PerGame" not in (spec.subtitle or "")
    assert "per_mode" not in spec.citation
    assert "player_shot_chart" in spec.citation


def test_shot_chart_carries_the_bare_name_for_the_caption():
    spec = select_charts(_shot_plan(), _bundle(_binned_shot_frame()))[0]
    assert spec.series == "Stephen Curry"


def test_league_wide_shot_chart_is_allowed():
    """No entity is fine — the grid caps the payload, so scope is not a payload problem."""
    spec = select_charts(_plan(table="player_shot_chart", entities=[]), _bundle(_binned_shot_frame()))[0]
    assert spec.kind == "shot_chart"
    assert spec.title.startswith("The league")


def test_zone_summary_is_what_the_analyst_gets():
    from Visualizer.shaping import shot_zone_summary

    zones = shot_zone_summary(_binned_shot_frame())
    assert zones[0]["zone"] == "Restricted Area"
    assert zones[0]["fga"] == 16
    assert zones[0]["fg_pct"] == 0.625


def test_shot_chart_shows_individual_attempts_for_a_small_sample():
    """A single game is drawn shot by shot: hex bins need volume to mean anything."""
    frame = pd.DataFrame(
        [
            {"LOC_X": -109, "LOC_Y": 41, "SHOT_MADE_FLAG": 1, "zone": "In The Paint (Non-RA)"},
            {"LOC_X": 12, "LOC_Y": 8, "SHOT_MADE_FLAG": 0, "zone": "Restricted Area"},
            {"LOC_X": 220, "LOC_Y": 240, "SHOT_MADE_FLAG": 1, "zone": "Above the Break 3"},
        ]
    )
    spec = select_charts(_shot_plan(), _bundle(frame))[0]
    assert spec.kind == "shot_chart"
    assert spec.mode == "makes"
    assert len(spec.points) == 3
    assert spec.points[0] == {"loc_x": -109, "loc_y": 41, "shot_made_flag": 1}
    # The hex cells are still built, so the heat views remain available.
    assert spec.rows
    assert any("2 made, 1 missed" in n for n in spec.notes)


def test_binned_frame_has_no_points_and_opens_on_volume():
    spec = select_charts(_shot_plan(), _bundle(_binned_shot_frame()))[0]
    assert spec.points == []
    assert spec.mode == "volume"


def test_opponent_names_resolve_to_the_tricode_htm_vtm_hold():
    """`VTM ILIKE '%Spurs%'` matched nothing — these columns hold tricodes."""
    from Interpreter.sql_builder import build_shot_chart_sql

    for value in ("Spurs", "San Antonio Spurs", "SAS"):
        plan = _plan(
            table="player_shot_chart", entities=["Jayson Tatum"], entities_are_canonical=True,
            season_from="2020-21", season_to="2020-21",
            row_filters=[{"column": "VTM", "op": "contains", "value": value}],
        )
        sql = build_shot_chart_sql(plan)
        assert "(HTM ILIKE '%SAS%' OR VTM ILIKE '%SAS%')" in sql, value
        assert "Spurs" not in sql


def test_an_exact_game_date_overrides_the_guessed_season_slice():
    """April 30 2021 was regular season; the router read late April as the playoffs."""
    from Interpreter.sql_builder import build_shot_chart_sql

    plan = _plan(
        table="player_shot_chart", entities=["Jayson Tatum"], entities_are_canonical=True,
        season_from="2020-21", season_to="2020-21", season_type="Playoffs",
        row_filters=[{"column": "GAME_DATE", "op": "eq", "value": "2021-04-30"}],
    )
    sql = build_shot_chart_sql(plan)
    assert "GAME_DATE = '2021-04-30'" in sql
    assert "season_type" not in sql
    assert "season =" not in sql


def test_a_game_scoped_chart_is_labelled_by_date_not_the_guessed_season():
    """It was captioned "2020-21 · Playoffs" for a regular-season night."""
    frame = pd.DataFrame(
        [{"LOC_X": 12, "LOC_Y": 8, "SHOT_MADE_FLAG": 1, "zone": "Restricted Area"}]
    )
    plan = _plan(
        table="player_shot_chart", entities=["Jayson Tatum"],
        season_from="2020-21", season_to="2020-21", season_type="Playoffs",
        row_filters=[{"column": "GAME_DATE", "op": "eq", "value": "2021-04-30"}],
    )
    spec = select_charts(plan, _bundle(frame))[0]
    assert spec.subtitle == "2021-04-30"
    assert "Playoffs" not in spec.citation
    assert "game_date=2021-04-30" in spec.citation


def test_chart_hint_line():
    plan = _plan(entities=[], order_by="PTS", limit=10, stat_focus=["PTS"])
    charts = select_charts(plan, _bundle(_leaderboard_frame()))
    assert chart_hint_line(charts) == "leaderboard chart of Points per game by rank"
    assert chart_hint_line([]) is None
