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
  "row_filters": [{"column": "<COLUMN>", "op": "<OP>", "value": <VALUE>}],
  "stat_focus": ["<COLUMN_1>", "<COLUMN_2>"],
  "order_by": "<COLUMN>" | null,
  "sort_dir": "desc" | "asc",
  "limit": <int> | null,
  "career_scope": false
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

   EXCEPTION — "the <YYYY> <TEAM>" names a team by the season it FINISHED, because that
   is how titles and eras are talked about. "The 2008 Celtics" is the 2007-08 team, not
   2008-09. Apply this only when the year directly qualifies a team or a roster:
     "the 2008 Celtics", "the 2016 Warriors", "the 2008 Celtics' best scorer"
        -> season_from = season_to = "2007-08" / "2015-16"
     "in 2008 LeBron averaged", "the 2008 season", "who led the league in 2008"
        -> "2008-09" as usual
   Be consistent: the same phrasing must always map to the same season. If the question
   is genuinely ambiguous, pick this rule and let the answer state the season used.
5. Leaderboards ("top N ...", "who led ..."): leave entities empty, set order_by to the
   ranking column and set limit. Use sort_dir "asc" only when lowest is best.
6. Named players or teams: put every name in entities and leave order_by/limit null.
   Two cases, and getting them the right way round matters:

   (a) NICKNAME OR INITIALS that are not part of the published name — ALWAYS expand to
       the full published name, because the vault stores only published names:
         "Shaq"  -> "Shaquille O'Neal"      "KD"    -> "Kevin Durant"
         "Greek Freak" -> "Giannis Antetokounmpo"   "CP3" -> "Chris Paul"
         "The Beard"   -> "James Harden"            "AD"  -> "Anthony Davis"

   (b) A REAL FRAGMENT of the name — a bare surname, first name, or city — copy it
       EXACTLY as written and do NOT expand it:
         "Curry" stays "Curry"        (never "Stephen Curry")
         "Jordan" stays "Jordan"      "LA" stays "LA"
       A resolver matches these against the vault, weighs who is most likely meant,
       uses the conversation for context, and asks the user when genuinely ambiguous.
       Expanding here destroys that and silently picks the wrong person.

   Test: could the string appear inside a published name? If yes, copy it. If it is a
   nickname that appears nowhere in the real name, expand it.

   (c) A CITY OR ABBREVIATION SHARED BY TWO FRANCHISES. "LA" and "Los Angeles" each
       cover the Lakers AND the Clippers, and the vault holds both. Never guess. Put
       the ambiguous form in entities exactly as written and let the resolver ask:
         "How did LA do?"           -> entities ["LA"]
         "How did Los Angeles do?"  -> entities ["Los Angeles"]
       If the user names the team, use it: "LA Lakers" -> ["Lakers"], "LA Clippers" ->
       ["Clippers"]. If an EARLIER TURN in this conversation established which LA team
       is being discussed, carry that forward and use the specific team.
       "LA" NEVER means Dallas, Atlanta, Portland, Orlando, Cleveland, Philadelphia or
       Oklahoma City — those merely contain the letters.

   SUBJECT vs SCOPE. `entities` is for the thing being ASKED ABOUT, matched against the
   table's name column. A team named to narrow WHICH players is scope, not subject, and
   belongs in row_filters instead:
     "Which CELTICS player had the best net rating" -> entity_type player, entities [],
        row_filters [{"column":"TEAM_ABBREVIATION","op":"eq","value":"BOS"}],
        order_by NET_RATING, limit 5
     "How did the CELTICS do" -> entity_type team, entities ["Celtics"]
   Putting a team in `entities` on a player table searches for a PLAYER of that name and
   finds nobody. Use the tricode (BOS, LAL, GSW) for TEAM_ABBREVIATION filters.

   DECIDE entity_type FROM THE NOUN BEING RANKED, NOT FROM THE NAMES PRESENT. This is
   the single most common routing mistake. A superlative like "best", "top" or "led"
   attaches to a noun, and that noun decides the table:
     "best SCORER"    -> a person  -> player table
     "best TEAM"      -> a team    -> team table
     "who SCORED most"-> a person  -> player table
   Person nouns: scorer, rebounder, passer, shooter, defender, playmaker, guard,
   forward, center, rookie. Team nouns: team, franchise, offense, defense, squad.
     "Who was the 2008 Celtics best scorer?"
        -> entity_type player, table player_season_stats, entities [],
           row_filters [{"column":"TEAM_ABBREVIATION","op":"eq","value":"BOS"}],
           order_by PTS, limit 5
     WRONG: entity_type team with entities ["Celtics"] — that answers with the team's
     own points per game, which is not a scorer.
   The team being the only name in the sentence does NOT make it the subject.

   A ROLE IS NOT A LEADERBOARD. "Best rookie", "best sixth man", "best defensive
   player" name an AWARD or a roster status, and no column in player_season_stats
   records either. Ranking by points and calling the winner "the best sixth man" is a
   false answer, and it was produced verbatim: *"Joel Embiid was the best sixth man in
   2023-24."* Route these to what actually holds them:
     "best rookie / sixth man / most improved / defensive player of the year in YYYY"
        -> table player_awards, entities [],
           row_filters [{"column":"DESCRIPTION","op":"contains","value":"Rookie of the Year"}],
           season_from/season_to set to that season
     "how did the rookies do this season" (no award implied)
        -> table player_season_stats with a rookie filter is NOT possible; there is no
           experience column there. Use player_bio (SEASON_EXP, FROM_YEAR) or say so.
   If the question wants a stat leaderboard *among* a role the vault cannot identify,
   set supported=false with a reason naming the role — do not hand back an unfiltered
   leaderboard.

   AN ALL-TIME LEADERBOARD IS NOT A SEASON LEADERBOARD. "Who has scored the most points
   ever", "most career playoff points", "who has the most All-Star selections" ranks
   players by a total ACROSS seasons. One row per player-season cannot answer it: the
   top row is the best single season, which is a different question. Set
   `career_scope: true` on the plan for these so Python aggregates per player before
   ranking. Use it only for leaderboards with no named entity, where the question says
   ever / all-time / career / most in history.

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
12. row_filters narrow to specific ROWS. Leave it [] for ordinary season questions.
    Use it whenever the question contains a game-level condition, which is what the
    game-log tables exist for. Ops: eq, ne, gt, gte, lt, lte, contains, not_contains.
    Only use columns listed for the table you picked; an unknown column is dropped.

    On player_game_logs / team_game_logs, MATCHUP carries opponent AND venue:
      "LAL vs. CHI" means HOME, "LAL @ CHI" means AWAY.

      "against the Bulls at home"  -> [{"column":"MATCHUP","op":"contains","value":"CHI"},
                                       {"column":"MATCHUP","op":"contains","value":"vs."}]
      "on the road versus Boston"  -> [{"column":"MATCHUP","op":"contains","value":"BOS"},
                                       {"column":"MATCHUP","op":"contains","value":"@"}]
      "in wins"                    -> [{"column":"WL","op":"eq","value":"W"}]
      "when he played over 35 min" -> [{"column":"MIN","op":"gt","value":35}]
      "when he scored 40+"         -> [{"column":"PTS","op":"gte","value":40}]
      "since January 2024"         -> [{"column":"GAME_DATE","op":"gte","value":"2024-01-01"}]

    A game-log question WITHOUT any such condition is rejected downstream, so if the
    user asks for plain career or season averages use player_season_stats instead.

13. SPLIT PHRASING ALWAYS MEANS GAME LOGS. If the question compares a player's
    performance ACROSS a game-level condition, it is a game-log question no matter how
    it is worded. The giveaway is a contrast: "in X versus Y", "when ...", "at home vs
    on the road", "before/after the break".

      "How does Tatum play in WINS VERSUS LOSSES?"
         -> table player_game_logs, entities ["Jayson Tatum"],
            row_filters []   (no filter: the analyst needs BOTH sides to compare,
                              and WL is in the rows so it can split them)
      "Is Curry better at home or on the road?"     -> player_game_logs, MATCHUP in rows
      "How does Jokic do against winning teams?"    -> player_game_logs
      "Does Embiid score more in the second half of the season?" -> player_game_logs

    NEVER answer these from player_season_stats. That table has W and L columns holding
    the player's TEAM RECORD, and using them produces "57 wins, 17 losses" — the team's
    season record dressed up as a performance split. It reads like an answer and is not
    one. If the question contrasts performance across a condition, the rows must be
    games.

    When BOTH sides of the contrast are wanted, leave row_filters empty and let the
    analyst split the rows; use row_filters only to narrow to ONE side ("in wins").
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

    # A basketball question refused as "not basketball" is the worst failure the router
    # can produce: it tells the user they asked the wrong thing. One corrected pass.
    if _repair_errors is None:
        from Interpreter.scope_guard import is_wrongly_refused

        evidence = is_wrongly_refused(plan, question)
        if evidence:
            return route_question(
                question,
                _repair_errors=(
                    f"You returned NOT_BASKETBALL, but this question mentions {evidence}, "
                    "so it IS a basketball question. NOT_BASKETBALL is only for questions "
                    "with nothing to do with the NBA. Route it to a real table and answer "
                    "what the vault can, or — if it truly needs two tables — return "
                    "supported=false with a reason naming the two tables. Do not refuse it "
                    "as off-topic again."
                ),
            )

    try:
        validate_plan(plan, conn)
        return plan
    except PlanValidationError as exc:
        if _repair_errors is not None:
            raise ValueError(f"Router plan invalid after repair: {exc}") from exc
        logger.warning("Router plan validation failed, retrying once: %s", exc)
        return route_question(question, _repair_errors=f"Plan validation errors: {exc}")


__all__ = ["route_question", "LLMNotConfiguredError"]
