"""
Edge-case tests for name normalisation, SQL validation, analyzer domain inference and
history heuristics.

The Team45 cross-season UNION builder (_build_dynamic_multitable_sql and friends) was
removed when the router pipeline landed (one table per plan, no UNIONs), so its tests
were dropped rather than resurrecting dead code.

Run from backend directory:
    python -m unittest discover -s tests -p "test_*.py" -v

"""

from __future__ import annotations

import os
import sys
import unittest

# Ensure backend package root is on path when tests are run from repo root.
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import pandas as pd

from Analyzer import query_analyzer as qa  # noqa: E402
from Executer.executor import validate_and_normalize_sql  # noqa: E402
from Interpreter import interpreter as intr  # noqa: E402


class TestNormalizePlayerCandidate(unittest.TestCase):
    def test_plain_two_part_name_kept(self):
        self.assertEqual(intr._normalize_player_candidate("LeBron James"), "LeBron James")

    def test_trailing_calendar_year_rejected(self):
        # Candidates must be capitalised alpha tokens only; a trailing year is not a name.
        self.assertEqual(intr._normalize_player_candidate("LeBron James 2012"), "")

    def test_offensively_not_chopped(self):
        out = intr._normalize_player_candidate("durant offensively")
        self.assertNotIn("offensivel", out.lower())


class TestValidateSql(unittest.TestCase):
    def test_plain_select_ok(self):
        out = validate_and_normalize_sql("SELECT 1 AS x FROM player_season_stats LIMIT 1")
        self.assertIn("SELECT", out.upper())

    def test_union_rejected(self):
        # Router v2 reads exactly one table per plan; UNION roots are refused.
        with self.assertRaises(ValueError):
            validate_and_normalize_sql("SELECT 1 AS a UNION ALL SELECT 2 AS a")


class TestAnalyzerInferDomain(unittest.TestCase):
    def test_infer_domain_defense_when_opp_pts_compare(self):
        d = qa.infer_domain("Compare them in depth", ["player", "pts", "opp_pts", "def_rtg"])
        self.assertEqual(d, "defense")

    def test_infer_domain_who_was_better_with_opp_pts(self):
        d = qa.infer_domain("Who was better when both were at their peak", ["player", "opp_pts", "def_rtg"])
        self.assertEqual(d, "defense")

    def test_infer_domain_between_with_opp_pts(self):
        d = qa.infer_domain("Between these two seasons who held up better defensively", ["player", "opp_pts"])
        self.assertEqual(d, "defense")

    def test_infer_domain_who_was_better_or_with_opp_pts(self):
        d = qa.infer_domain("Who was better LeBron 2012 or Durant 2015", ["player", "opp_pts", "def_rtg"])
        self.assertEqual(d, "defense")

    def test_infer_domain_which_one_is_better_or_with_opp_pts(self):
        d = qa.infer_domain(
            "Which one is better LeBron 2012 or Durant 2015 defensively",
            ["player", "opp_pts", "def_rtg"],
        )
        self.assertEqual(d, "defense")

    def test_infer_domain_which_had_better_season_or_with_opp_pts(self):
        d = qa.infer_domain(
            "Which had the better season: LeBron 2012 or Durant 2015?",
            ["player", "opp_pts", "def_rtg"],
        )
        self.assertEqual(d, "defense")


class TestHistoryHeuristic(unittest.TestCase):
    def test_compare_and_players_does_not_trigger_history(self):
        import main as app_main

        q = "Compare Lebron James 2012 and Kevin durant 2015 offensively"
        self.assertFalse(app_main._should_apply_history_context(q))

    def test_who_is_better_or_does_not_trigger_history(self):
        import main as app_main

        q = "Who is better Lebron James 2012 or Kevin durant 2015"
        self.assertFalse(app_main._should_apply_history_context(q))

    def test_who_was_better_or_wrapped_no_history(self):
        import main as app_main

        wrapped = (
            "Conversation context:\nUser: random\n\n"
            "Current question: Who was better Lebron James 2012 or Kevin durant 2015?"
        )
        self.assertFalse(app_main._should_apply_history_context(wrapped))

    def test_which_one_is_better_or_does_not_trigger_history(self):
        import main as app_main

        q = "Which one is better Lebron James 2012 or Kevin durant 2015?"
        self.assertFalse(app_main._should_apply_history_context(q))

    def test_which_had_better_season_or_does_not_trigger_history(self):
        import main as app_main

        q = "Which had the better season: Lebron James 2012 or Kevin durant 2015?"
        self.assertFalse(app_main._should_apply_history_context(q))

    def test_who_is_bare_followup_still_uses_history(self):
        import main as app_main

        self.assertTrue(app_main._should_apply_history_context("who is better?"))

    def test_and_alone_in_compare_not_marker(self):
        import main as app_main

        # Bare "and " removed from markers — compare uses grammatical "and".
        self.assertFalse(app_main._should_apply_history_context("Compare A and B in 2020"))

    def test_and_also_still_followup(self):
        import main as app_main

        self.assertTrue(app_main._should_apply_history_context("and also show rebounds"))


if __name__ == "__main__":
    unittest.main()
