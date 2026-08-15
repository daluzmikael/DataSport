"""Call 1: natural language → RouterPlan JSON (no SQL, exactly one table)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from Executer.data_backend import get_connection
from Interpreter.router_plan import (
    PlanValidationError,
    RouterPlan,
    plan_from_dict,
    table_catalog_prompt_text,
    validate_plan,
)
from llm.client import LLMNotConfiguredError, router_completion

logger = logging.getLogger(__name__)

_ROUTER_SYSTEM = """You are the query router for an NBA analytics vault. You read a user
question and return ONE JSON object describing which single staged table to read and how
to filter it.

You do NOT write SQL. You do NOT answer the question. You do NOT analyse statistics.
Python builds the SQL from your JSON.

Return ONLY valid JSON in exactly this shape:
{
  "supported": true,
  "unsupported_reason": null,
  "entity_type": "player" | "team" | "league",
  "entities": ["<NAME_1>", "<NAME_2>"],
  "season_from": "<YYYY-YY>" | null,
  "season_to": "<YYYY-YY>" | null,
  "season_type": "Regular Season" | "Playoffs",
  "table": "<one table name from the catalog>",
  "per_modes": ["PerGame"],
  "measure_type": null,
  "pt_measure_type": null,
  "group_quantity": null,
  "topic": "<short label, e.g. scoring / rim defense / standings>",
  "stat_focus": ["<COLUMN_1>", "<COLUMN_2>"],
  "order_by": "<COLUMN>" | null,
  "sort_dir": "desc" | "asc",
  "limit": <int> | null
}

HARD RULES
1. Exactly ONE table. Never join, never union, never list a second table. The vault is
   deliberately wide — one row already carries base, clutch, hustle and rank columns.
2. If the question genuinely needs two different tables at once, return
   {"supported": false, "unsupported_reason": "<one short sentence naming the two things
   that live in different tables>"} and leave the other fields at their defaults.
   Do not guess or half-answer with one table when the question clearly needs two.
3. Multiple seasons are NOT multiple queries. A span is one table read: set season_from
   to the earliest season and season_to to the latest. For a single season set both to
   the same value. For an all-time question leave both null.
4. season labels are hyphenated NBA seasons: a bare calendar year <YYYY> means the season
   starting that year, so <YYYY> becomes "<YYYY>-<YY+1>". A playoff question about
   calendar year <YYYY> means the season starting <YYYY>-1.
5. Leaderboards ("top N ...", "who led ..."): leave entities empty, set order_by to the
   ranking column and set limit. Use sort_dir "asc" only when lowest is best.
6. Named players or teams: put every name in entities and leave order_by/limit null.
7. stat_focus lists the columns the question is actually about, using exact column names
   from the catalog. It steers which columns the analyst reads — keep it tight and
   relevant, not the whole table.
8. Only use column names that appear in the catalog for the table you picked. Never
   invent a column. If the stat the user asked for is not in any single table, reject
   with supported=false rather than substituting a different stat.
9. Always set season_type, table and topic so the answer can cite its source.
10. per_modes is usually ["PerGame"]. Add "Totals" only when the question is about
    volume, counting totals or a full-season sum. Never more than two.
11. Tables whose slice list includes pt_measure_type REQUIRE a pt_measure_type value.
    Tables whose name column is NONE cannot be filtered by a person's name.
"""

# Few-shot uses placeholder tokens on purpose: concrete names make small models copy the
# example's shape verbatim. These teach structure only.
_FEW_SHOT = """SHAPE EXAMPLES (placeholders, not real questions — copy the structure, not the values)

Question shape: "top <N> <COUNTING_STAT> leaders in <YEAR>"
{"supported":true,"unsupported_reason":null,"entity_type":"player","entities":[],"season_from":"<YEAR>-<YY>","season_to":"<YEAR>-<YY>","season_type":"Regular Season","table":"player_season_stats","per_modes":["PerGame"],"measure_type":null,"pt_measure_type":null,"group_quantity":null,"topic":"<TOPIC>","stat_focus":["<STAT_COL>","GP","MIN"],"order_by":"<STAT_COL>","sort_dir":"desc","limit":<N>}

Question shape: "how has <ENTITY_A>'s <STAT> changed from <YEAR_1> to <YEAR_2>"
{"supported":true,"unsupported_reason":null,"entity_type":"player","entities":["<ENTITY_A>"],"season_from":"<YEAR_1>-<YY>","season_to":"<YEAR_2>-<YY>","season_type":"Regular Season","table":"player_season_stats","per_modes":["PerGame"],"measure_type":null,"pt_measure_type":null,"group_quantity":null,"topic":"<TOPIC>","stat_focus":["<STAT_COL>","<SUPPORTING_COL>","GP"],"order_by":null,"sort_dir":"desc","limit":null}

Question shape: "compare <ENTITY_A> and <ENTITY_B> on <TOPIC> in <YEAR>"
{"supported":true,"unsupported_reason":null,"entity_type":"player","entities":["<ENTITY_A>","<ENTITY_B>"],"season_from":"<YEAR>-<YY>","season_to":"<YEAR>-<YY>","season_type":"Regular Season","table":"<TABLE_COVERING_TOPIC>","per_modes":["PerGame","Totals"],"measure_type":null,"pt_measure_type":null,"group_quantity":null,"topic":"<TOPIC>","stat_focus":["<STAT_COL_1>","<STAT_COL_2>","<STAT_COL_3>"],"order_by":null,"sort_dir":"desc","limit":null}

Question shape: "<TOPIC_IN_TABLE_X> combined with <TOPIC_IN_TABLE_Y> for <ENTITY_A>"
{"supported":false,"unsupported_reason":"<TOPIC_IN_TABLE_X> and <TOPIC_IN_TABLE_Y> live in different tables and cannot be read together yet.","entity_type":"player","entities":["<ENTITY_A>"],"season_from":null,"season_to":null,"season_type":"Regular Season","table":null,"per_modes":["PerGame"],"measure_type":null,"pt_measure_type":null,"group_quantity":null,"topic":"<TOPIC>","stat_focus":[],"order_by":null,"sort_dir":"desc","limit":null}
"""


def _json_from_text(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _build_user_prompt(question: str, conn: Any | None = None) -> str:
    return (
        f"{table_catalog_prompt_text(conn)}\n\n"
        f"{_FEW_SHOT}\n\n"
        f"User question:\n{question.strip()}\n\n"
        "JSON only:"
    )


def route_question(question: str, *, _repair_errors: str | None = None) -> RouterPlan:
    """Route a question to a validated RouterPlan. One repair attempt on failure."""
    if not question.strip():
        raise ValueError("Question is empty")

    try:
        conn = get_connection()
    except Exception:  # noqa: BLE001 — prompt still builds from the catalog file
        conn = None

    user_prompt = _build_user_prompt(question, conn)
    if _repair_errors:
        user_prompt += (
            f"\n\nYour previous JSON failed:\n{_repair_errors}\n"
            "Fix the problem and return corrected JSON only. If the question cannot be "
            "answered from a single table, return supported=false with a reason."
        )

    raw = router_completion(_ROUTER_SYSTEM, user_prompt)

    parsed = _json_from_text(raw)
    if not parsed:
        raise ValueError(f"Router did not return valid JSON: {raw[:300]}")

    plan = plan_from_dict(parsed)

    try:
        validate_plan(plan, conn)
        return plan
    except PlanValidationError as exc:
        if _repair_errors is not None:
            raise ValueError(f"Router plan invalid after repair: {exc}") from exc
        logger.warning("Router plan validation failed, retrying once: %s", exc)
        return route_question(question, _repair_errors=f"Plan validation errors: {exc}")


__all__ = ["route_question", "LLMNotConfiguredError"]
