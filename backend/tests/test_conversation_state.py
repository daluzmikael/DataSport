"""Unit tests for Interpreter/conversation_state.py (pure functions, no network/DB)."""
import pandas as pd

from Interpreter import conversation_state as cs
from Interpreter.router_plan import RouterPlan


def _plan(**kw):
    base = dict(
        entity_type="player",
        season_from="2023-24",
        season_to="2023-24",
        season_type="Regular Season",
        table="player_season_stats",
        topic="scoring",
        stat_focus=["PTS"],
    )
    base.update(kw)
    return RouterPlan(**base)


def _rows(*names, col="PLAYER_NAME"):
    return {"player_season_stats__PerGame": pd.DataFrame({col: list(names), "PTS": range(len(names))})}


def test_first_turn_builds_state_from_plan_and_canonical_names():
    plan = _plan(entities=["Nikola Jokic"])
    s = cs.update_state(None, question="Jokic ppg 2023-24", plan=plan, bundles=_rows("Nikola Jokić"))
    assert s["turn"] == 1
    assert s["entities"] == ["Nikola Jokić"]  # vault spelling wins when counts match
    assert (s["season_from"], s["season_to"], s["season_type"]) == ("2023-24", "2023-24", "Regular Season")
    assert s["leaderboard"] is False and s["top_results"] == []
    assert "Nikola Jokić" in s["summary"] and "2023-24" in s["summary"]


def test_router_names_kept_when_fuzzy_match_returns_extra_rows():
    plan = _plan(entities=["Thompson"])
    s = cs.update_state(None, question="q", plan=plan, bundles=_rows("Klay Thompson", "Tristan Thompson"))
    assert s["entities"] == ["Thompson"]


def test_focus_switch_moves_old_entities_to_recent():
    s1 = cs.update_state(None, question="q1", plan=_plan(entities=["Stephen Curry"]))
    s2 = cs.update_state(s1, question="Klay Thompson?", plan=_plan(entities=["Klay Thompson"]))
    assert s2["entities"] == ["Klay Thompson"]
    assert s2["recent_entities"][0] == "Stephen Curry"
    s3 = cs.update_state(s2, question="both", plan=_plan(entities=["Stephen Curry", "Klay Thompson"]))
    assert "Stephen Curry" not in s3["recent_entities"]  # current focus is never duplicated in recent


def test_leaderboard_records_top_results_and_no_entities():
    plan = _plan(entities=[], order_by="AST", limit=1, season_from="2015-16", season_to="2015-16", topic="assists")
    s = cs.update_state(None, question="assist leader 2015-16", plan=plan, bundles=_rows("Rajon Rondo", "Russell Westbrook"))
    assert s["leaderboard"] is True
    assert s["entities"] == []
    assert s["top_results"][:2] == ["Rajon Rondo", "Russell Westbrook"]
    assert s["stat_focus"][0] == "AST"
    assert "Rajon Rondo" in s["summary"]
    # The leader becomes reachable as a recent entity once focus moves on.
    s2 = cs.update_state(s, question="and Westbrook?", plan=_plan(entities=["Russell Westbrook"]))
    assert s2["recent_entities"][0] == "Rajon Rondo"
    assert s2["top_results"] == []


def test_name_column_hint_and_alt_columns():
    bundles = {"team_season_stats__PerGame": pd.DataFrame({"TEAM_NAME": ["Boston Celtics"]})}
    assert cs.top_names_from_bundles(bundles) == ["Boston Celtics"]
    bundles = {"x": pd.DataFrame({"teamName": ["Denver Nuggets"]})}
    assert cs.top_names_from_bundles(bundles, name_column="teamName") == ["Denver Nuggets"]
    assert cs.top_names_from_bundles({"x": pd.DataFrame()}) == []


def test_turn_without_plan_keeps_focus():
    s1 = cs.update_state(None, question="q1", plan=_plan(entities=["Joel Embiid"]))
    s2 = cs.update_state(s1, question="hustle stats in 2010?", plan=None, answer="Not available.")
    assert s2["entities"] == ["Joel Embiid"]
    assert s2["season_from"] == "2023-24"
    assert s2["turn"] == 2
    assert s2["last_question"] == "hustle stats in 2010?"


def test_unsupported_plan_with_entities_updates_entities_but_keeps_season():
    s1 = cs.update_state(None, question="q1", plan=_plan(entities=["Boston Celtics"], entity_type="team"))
    bad = RouterPlan(supported=False, unsupported_reason="two tables", entity_type="team", entities=["Boston Celtics", "Denver Nuggets"])
    s2 = cs.update_state(s1, question="compare them to Denver", plan=bad)
    assert s2["entities"] == ["Boston Celtics", "Denver Nuggets"]
    assert s2["season_from"] == "2023-24"  # blank season on an unsupported plan does not wipe it
    assert s2["table"] == "player_season_stats"
    assert s2["topic"] == "scoring" and s2["stat_focus"] == ["PTS"]  # failed topic not carried


def test_accepts_plan_as_dict():
    s = cs.update_state(None, question="q", plan={"supported": True, "table": "t", "entities": ["A B"], "season_type": "Playoffs"})
    assert s["entities"] == ["A B"] and s["season_type"] == "Playoffs"


def test_last_answer_is_first_line_only_and_bounded():
    ans = "\n\n**Rajon Rondo** led the league with **11.7** assists.\n\n- bullet\n" + "x" * 5000
    s = cs.update_state(None, question="q", plan=_plan(entities=["Rajon Rondo"]), answer=ans)
    assert s["last_answer"] == "Rajon Rondo led the league with 11.7 assists."


def test_sanitize_rejects_garbage_and_bounds_sizes():
    assert cs.sanitize_state(None) is None
    assert cs.sanitize_state("nope") is None
    assert cs.sanitize_state({}) is None
    assert cs.sanitize_state({"turn": 3}) is None  # nothing usable
    raw = {
        "turn": "7",
        "entity_type": "alien",
        "entities": ["A"] * 3 + [f"P{i}" for i in range(20)] + [123, None],
        "season_from": "2023-24; DROP TABLE",
        "season_to": "2023-24",
        "season_type": "Summer League",
        "topic": "x" * 1000,
        "last_answer": "y" * 5000,
    }
    s = cs.sanitize_state(raw)
    assert s["turn"] == 7
    assert s["entity_type"] is None
    assert len(s["entities"]) == cs.MAX_ENTITIES and s["entities"][0] == "A"  # deduped, capped
    assert s["season_from"] is None and s["season_to"] == "2023-24"
    assert s["season_type"] is None
    assert len(s["topic"]) <= 60
    assert len(s["last_answer"]) <= cs.MAX_LAST_ANSWER


def test_state_round_trips_through_sanitize():
    s = cs.update_state(None, question="q", plan=_plan(entities=["Kevin Durant"], season_from="2016-17", season_to="2018-19"))
    again = cs.sanitize_state(s)
    for k in ("entities", "season_from", "season_to", "season_type", "topic", "stat_focus", "turn"):
        assert again[k] == s[k]


def test_router_context_block_is_compact_and_empty_without_state():
    assert cs.router_context_block(None) == ""
    s = cs.update_state(None, question="Curry 3P% 2015-16", plan=_plan(entities=["Stephen Curry"], season_from="2015-16", season_to="2015-16"))
    block = cs.router_context_block(s)
    assert block.startswith("CONVERSATION CONTEXT")
    assert '"entities": ["Stephen Curry"]' in block
    assert "Previous user question: Curry 3P% 2015-16" in block
    assert len(cs.context_block(s)) < 600  # stays small regardless of chat length


def test_context_size_does_not_grow_with_turns():
    s = None
    sizes = []
    for i in range(12):
        s = cs.update_state(s, question=f"question {i} " * 20, plan=_plan(entities=[f"Player {i}"]), answer="a " * 2000)
        sizes.append(len(cs.context_block(s)))
    assert max(sizes) < 1200  # bounded: 200-char question + 400-char answer + focus
    assert len(s["recent_entities"]) <= cs.MAX_ENTITIES


def test_resolved_question():
    plan = _plan(entities=["Nikola Jokić"], season_type="Playoffs", season_from="2022-23", season_to="2022-23")
    assert cs.resolved_question("how did he do?", plan) == "how did he do? (resolved: Nikola Jokić, 2022-23 Playoffs)"
    lb = _plan(entities=[], order_by="PTS", limit=5, season_from="2018-19", season_to="2018-19")
    assert "league leaders, 2018-19" in cs.resolved_question("top scorers", lb)
    assert cs.resolved_question("hi", None) == "hi"
    multi = _plan(entities=["Kevin Durant"], season_from="2016-17", season_to="2018-19")
    assert "2016-17 to 2018-19" in cs.resolved_question("trend", multi)
