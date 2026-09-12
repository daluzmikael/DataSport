"""Router → SQL builder → bundled DataFrames pipeline.

One table per question. On a SQL failure the router gets exactly one repair attempt;
if that also fails the error is logged to the terminal and empty data is returned.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from Executer.data_backend import get_connection
from Interpreter.person_scope import correct_person_scope
from Interpreter.team_scope import correct_team_era_name, ensure_team_scope
from Interpreter.router import route_question
from Interpreter.router_plan import RouterPlan
from Interpreter.empty_result import diagnose_empty_result
from Interpreter.sql_builder import execute_plan

logger = logging.getLogger(__name__)


def _log_plan(question: str, plan: RouterPlan, *, attempt: str = "initial") -> None:
    """Terminal block describing the routing decision (kept for debugging)."""
    lines = [
        "",
        "=" * 62,
        f"ROUTER PLAN ({attempt})",
        "=" * 62,
        f"  question    : {question.strip()[:200]}",
        f"  supported   : {plan.supported}",
    ]
    if not plan.supported:
        lines.append(f"  reason      : {plan.unsupported_reason}")
    else:
        lines.extend(
            [
                f"  table       : {plan.table}",
                f"  seasons     : {plan.season_label()}",
                f"  season_type : {plan.season_type}",
                f"  per_modes   : {', '.join(plan.per_modes)}",
                f"  entity_type : {plan.entity_type}",
                f"  entities    : {', '.join(plan.entities) or '(leaderboard)'}",
                f"  topic       : {plan.topic or '-'}",
                f"  stat_focus  : {', '.join(plan.stat_focus) or '-'}",
                f"  order_by    : {plan.order_by or '-'} {plan.sort_dir if plan.order_by else ''}".rstrip(),
                f"  limit       : {plan.limit if plan.limit else '-'}",
            ]
        )
        if plan.pt_measure_type:
            lines.append(f"  pt_measure  : {plan.pt_measure_type}")
        if plan.measure_type:
            lines.append(f"  measure     : {plan.measure_type}")
    lines.append("=" * 62)
    logger.info("\n".join(lines))


def _log_tables_accessed(plan: RouterPlan, bundles: dict[str, pd.DataFrame]) -> None:
    lines = ["", f"TABLES ACCESSED: {plan.table or 'none'}"]
    for label, df in bundles.items():
        lines.append(f"  {label} -> {df.shape[0]} rows x {df.shape[1]} cols")
    if not bundles:
        lines.append("  (no rows returned)")
    lines.append("")
    logger.info("\n".join(lines))


class EntityAmbiguity(Exception):
    """Raised when an entity name matches several vault entries too closely to pick.

    Carries the question to put to the user instead of guessing.
    """

    def __init__(self, message: str, resolutions: list) -> None:
        super().__init__(message)
        self.message = message
        self.resolutions = resolutions


def _substitutions_vs_question(plan: RouterPlan, question: str) -> list[dict]:
    """Entities whose name never appears in what the user actually typed.

    Comparing the resolver's input to its output is not enough: the router fixes many
    misspellings itself at Call 1, so "Yanis Antetokounmpo" arrives already corrected
    and the resolver sees no change to report. Checking against the raw question
    catches both, and it is the question the user will compare the answer against.

    Matching is on the surname only — "LeBron" alone, or "Giannis", should not be
    flagged as a substitution just because the answer prints the full name.
    """
    from Interpreter.entity_resolver import norm

    q = norm(question or "")
    if not q:
        return []

    import difflib

    q_tokens = [t for t in q.split() if len(t) > 2]
    out: list[dict] = []

    for name in plan.entities or []:
        tokens = [t for t in norm(name).split() if len(t) > 2]
        if not tokens:
            continue

        # Nothing recognisable in the question at all — a full substitution.
        if not any(t in q for t in tokens):
            out.append({"asked": question.strip()[:80], "used": name})
            continue

        # Partly recognisable, but one part was misspelled: "Yanis Antetokounmpo" keeps
        # the surname and loses the first name. Look for a question word that is close
        # to a name token without matching it — that is the corrected fragment. A short
        # form like "LeBron" for "LeBron James" is NOT this: "james" has no near-miss in
        # the question, it is simply absent, and absence is not a correction.
        for token in tokens:
            if token in q:
                continue
            near = [
                w for w in q_tokens
                if w not in tokens
                and difflib.SequenceMatcher(None, w, token).ratio() >= 0.6
            ]
            if near:
                out.append({"asked": near[0], "used": name})
                break
    return out


def _resolve_entities(plan: RouterPlan, context_names: list[str] | None) -> None:
    """Map plan entities to canonical vault names, or raise EntityAmbiguity."""
    if not plan.entities:
        return

    from Interpreter.entity_resolver import resolve_all

    original = list(plan.entities)
    names, ambiguous, all_canonical = resolve_all(
        plan.entities, plan.entity_type, context_names
    )

    if ambiguous:
        text = "\n\n".join(r.clarification_text() for r in ambiguous)
        logger.info("Entity ambiguity, asking user: %s", "; ".join(r.query for r in ambiguous))
        raise EntityAmbiguity(text, ambiguous)

    if names != plan.entities:
        logger.info("Entities resolved: %s -> %s", plan.entities, names)
    plan.entities = names
    # Exact matching only when every name is a real vault entry; otherwise a
    # nickname the router left alone would match nothing at all.
    plan.entities_are_canonical = all_canonical

    # A silently-corrected name looks identical to a correct one, so a wrong match is
    # indistinguishable from a right one. Record any substitution so the answer can
    # say which player it actually read.
    # Only a genuine SUBSTITUTION is worth announcing. Expanding a partial name to the
    # published one is not: "LeBron" -> "LeBron James" and "Steph" -> "Stephen Curry"
    # are what the resolver is for, and prefacing every answer with "not 'LeBron' as
    # written" is noise. The test is whether every word the user typed survives into
    # the resolved name — "Yanis" does not survive into "Giannis Antetokounmpo".
    from Interpreter.entity_resolver import norm

    corrections = []
    for typed, resolved in zip(original, names):
        typed_tokens = [t for t in norm(typed).split() if t]
        resolved_norm = norm(str(resolved))
        if typed_tokens and all(t in resolved_norm for t in typed_tokens):
            continue  # pure expansion, nothing was changed
        if norm(typed) == resolved_norm:
            continue
        corrections.append((typed, resolved))
    if corrections:
        plan.name_corrections = [
            {"asked": typed, "used": resolved} for typed, resolved in corrections
        ]
        logger.info("Name substitutions: %s", plan.name_corrections)


class GameLogScopeError(Exception):
    """Raised when a game-log question has no filter to make it a game-log question.

    The game-log tables exist for the nitpicking questions — splits by opponent,
    home/away, minute thresholds, date ranges, streaks. "Show me his entire career
    game log" is not one of those: it is 1,622 rows the analyst cannot usefully read,
    and the season table already answers what the user probably meant.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# Words that turn a game-log pull into a real game-level question.
_GAME_LOG_QUALIFIERS = (
    "vs", "versus", "against", "opponent", "home", "away", "road",
    "when", "more than", "at least", "over", "under", "fewer",
    "streak", "streaks", "consecutive", "in a row", "back to back",
    "last ", "recent", "since", "between", "during", "before", "after",
    "high", "highest", "best game", "worst game", "career high", "40-point",
    "triple double", "double double", "won", "lost", "win", "loss",
    "month", "january", "february", "march", "april", "may", "june",
    "october", "november", "december", "playoff run", "date",
)

_UNBOUNDED_MARKERS = ("career", "every game", "all games", "entire", "whole", "all-time")


def _guard_game_log_scope(question: str, plan: RouterPlan) -> None:
    """Refuse an unfiltered career-wide game-log pull, with instructions."""
    if plan.table not in ("player_game_logs", "team_game_logs"):
        return

    q = (question or "").lower()

    # A row filter is exactly what makes this a real game-log question.
    if getattr(plan, "row_filters", None):
        return

    # A single season, or an explicit leaderboard/limit, is already bounded.
    single_season = bool(
        plan.season_from and plan.season_to and plan.season_from == plan.season_to
    )
    if single_season or plan.limit:
        return

    if any(w in q for w in _GAME_LOG_QUALIFIERS):
        return

    if not any(m in q for m in _UNBOUNDED_MARKERS) and (plan.season_from or plan.season_to):
        return

    raise GameLogScopeError(
        "Game logs are one row per game, so a career-wide pull is thousands of rows "
        "and won't give you a useful answer.\n\n"
        "That table is for **specific** game-level questions — ask it something it can "
        "actually narrow down:\n"
        "  • \"LeBron's career averages against the Bulls at home\"\n"
        "  • \"Curry's numbers when he plays over 35 minutes\"\n"
        "  • \"Jokic's best games in the 2023-24 season\"\n"
        "  • \"Tatum's last 20 games\"\n\n"
        "For career averages or season-by-season trends, just ask directly — "
        "\"What are LeBron's career averages?\" — and it will read the season table "
        "instead, which is what you want."
    )


def _apply_floor(plan: RouterPlan, question: str, conn) -> None:
    """Attach minimum-volume floors to ranking queries.

    Applied as ordinary row_filters so they go through the same validated SQL path as
    every other condition — nothing here writes SQL. There can be more than one: a
    percentage leaderboard needs a floor on the DENOMINATOR as well as on games, since
    100% on zero attempts clears any games minimum. Each floor is recorded on the plan
    so the analyst can state all of them.
    """
    from Interpreter.floors import floors_for_plan, soften_if_empty

    applied: list[dict] = []
    for floor in floors_for_plan(plan, question):
        plan.row_filters = list(plan.row_filters or []) + [floor.as_row_filter()]
        if soften_if_empty(plan, conn, floor) is None:
            # Rolled back: the floor emptied the result and it was only a default.
            plan.row_filters = [f for f in plan.row_filters if f != floor.as_row_filter()]
            continue
        applied.append(
            {
                "column": floor.column,
                "value": floor.value,
                "label": floor.label,
                "source": floor.source,
                "phrase": floor.phrase(),
            }
        )
        logger.info("Applied %s floor: %s (%s)", floor.source, floor.phrase(), plan.table)

    if applied:
        plan.applied_floor = applied[0]
        plan.applied_floors = applied


def run_routed_query(
    question: str, context_names: list[str] | None = None
) -> tuple[dict[str, pd.DataFrame], RouterPlan]:
    """Full interpreter path: route → resolve entities → execute → (one repair)."""
    plan = route_question(question)
    _log_plan(question, plan)

    if not plan.supported:
        logger.info("TABLES ACCESSED: none (multi-table question rejected at Call 1)")
        return {}, plan

    # A superlative about a PERSON must not be answered from a team table, even when
    # the only name in the question is a team. Runs before entity resolution so the
    # team name is moved to scope rather than resolved as a subject.
    correct_person_scope(plan, question)

    # ...and the mirror case: a team named in the question that never made it onto the
    # plan. Dropping it turns a team question into a league leaderboard that reads as a
    # confident answer to something else entirely.
    ensure_team_scope(plan, question)

    # A franchise keeps its id across a rename, so the season decides the name. Asking
    # about "the Charlotte Hornets in 2010-11" means the Bobcats.
    correct_team_era_name(plan, question)

    # Resolve before building SQL: a wrong entity produces a confident wrong answer,
    # which is worse than one clarifying question.
    _resolve_entities(plan, context_names)

    # Router-level substitutions are detected in the analyzer instead, which is the one
    # place holding both the original question and the final plan — the scope-correction
    # passes above rewrite the plan, and a value set here did not survive them.

    _guard_game_log_scope(question, plan)

    conn = get_connection()
    _apply_floor(plan, question, conn)
    bundles, errors = execute_plan(plan, conn)

    # Zero rows is a first-class outcome, not a success. The SQL ran fine, so the old
    # `if not bundles and errors` repair never fired and the user got a blank answer
    # with no reason. Reassess the plan against the schema and try once more.
    if not bundles and not errors:
        diagnosis = diagnose_empty_result(plan, conn)
        logger.warning("Query returned 0 rows. Diagnosis: %s", diagnosis.summary)

        if diagnosis.retry_hint:
            logger.info("Reassessing the plan against the schema and retrying once")
            try:
                retried = route_question(question, _repair_errors=diagnosis.retry_hint)
            except Exception as exc:  # noqa: BLE001
                logger.error("Empty-result reassessment failed to route: %s", exc)
                retried = None

            if retried is not None and retried.supported:
                _log_plan(question, retried, attempt="empty-result reassessment")
                try:
                    _resolve_entities(retried, context_names)
                except EntityAmbiguity:
                    raise
                retry_bundles, _ = execute_plan(retried, conn)
                if retry_bundles:
                    _log_tables_accessed(retried, retry_bundles)
                    logger.info("Reassessment recovered %d bundle(s)", len(retry_bundles))
                    return retry_bundles, retried
                # Second read also empty — the data genuinely is not there.
                diagnosis = diagnose_empty_result(retried, conn)
                plan = retried

        plan.empty_reason = diagnosis.user_message
        _log_tables_accessed(plan, {})
        return {}, plan

    if not bundles and errors:
        logger.warning("Router SQL failed, attempting one repair: %s", "; ".join(errors))
        try:
            repaired = route_question(
                question,
                _repair_errors=(
                    "The generated SQL failed against DuckDB with: "
                    + "; ".join(errors)
                    + ". Pick columns and slices that actually exist on the table."
                ),
            )
        except Exception as exc:  # noqa: BLE001 — repair routing itself failed
            logger.error("Router repair attempt failed: %s", exc)
            _log_tables_accessed(plan, {})
            return {}, plan

        _log_plan(question, repaired, attempt="repair")
        if not repaired.supported:
            return {}, repaired

        bundles, repair_errors = execute_plan(repaired, conn)
        plan = repaired
        if not bundles:
            logger.error(
                "Router SQL failed after one repair — returning empty. Errors: %s",
                "; ".join(repair_errors or errors),
            )
            _log_tables_accessed(plan, {})
            return {}, plan

    _log_tables_accessed(plan, bundles)
    logger.info(
        "Routed query OK | %s | bundles=%d", plan.citation(), len(bundles)
    )
    return bundles, plan
