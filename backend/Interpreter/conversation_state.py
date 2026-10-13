"""Compact conversation state for multi-turn analyst chats.

Instead of shipping the raw transcript to the context resolver on every turn, the
backend keeps a small structured "state" describing what the conversation is
currently about (players/teams, seasons, season type, stat focus, and the names
a leaderboard just returned). It is derived deterministically from the router's
JSON plan after each answer — no extra LLM call — and round-trips through the
client: /api/analysis returns it as `conversationState`, the frontend sends it
back on the next turn.

The state is advisory context only. The current question always wins: it is
used to resolve pronouns and ellipsis ("his rebounds", "and the playoffs?",
"compare him to Embiid", "how many did he average?"), never to override
entities or seasons the user states explicitly.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

STATE_VERSION = 1

MAX_ENTITIES = 6
MAX_STAT_FOCUS = 6
MAX_TOP_RESULTS = 5
MAX_TEXT = 200
MAX_LAST_ANSWER = 400

_SEASON_RE = re.compile(r"^\d{4}-\d{2}$")
_ENTITY_TYPES = {"player", "team", "league"}
_SEASON_TYPES = {"Regular Season", "Playoffs", "PlayIn", "Pre Season", "All Star"}
# Name columns seen across the staged tables (catalog name_column values plus the
# common defaults), checked case-insensitively when no hint is given.
_NAME_COLUMNS = (
    "PLAYER_NAME",
    "TEAM_NAME",
    "player_name",
    "team_name",
    "TeamName",
    "teamName",
    "GROUP_NAME",
)


def _clip(value: Any, limit: int = MAX_TEXT) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _str_list(values: Any, limit: int) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        s = _clip(v, 80)
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _season(value: Any) -> str | None:
    s = _clip(value, 10)
    return s if _SEASON_RE.match(s) else None


def empty_state() -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "turn": 0,
        "entity_type": None,
        "entities": [],
        "recent_entities": [],
        "season_from": None,
        "season_to": None,
        "season_type": None,
        "topic": None,
        "stat_focus": [],
        "table": None,
        "leaderboard": False,
        "top_results": [],
        "last_question": None,
        "last_answer": None,
        "summary": "",
    }


def sanitize_state(raw: Any) -> dict[str, Any] | None:
    """Validate a client-supplied state. Returns None when absent or unusable.

    Clients echo back what the server sent, but the payload is untrusted: every
    field is type-checked and size-bounded so it cannot bloat the prompt.
    """
    if not isinstance(raw, Mapping) or not raw:
        return None
    state = empty_state()
    try:
        state["turn"] = max(0, min(int(raw.get("turn") or 0), 10_000))
    except (TypeError, ValueError):
        state["turn"] = 0
    et = raw.get("entity_type")
    state["entity_type"] = et if et in _ENTITY_TYPES else None
    state["entities"] = _str_list(raw.get("entities"), MAX_ENTITIES)
    state["recent_entities"] = _str_list(raw.get("recent_entities"), MAX_ENTITIES)
    state["season_from"] = _season(raw.get("season_from"))
    state["season_to"] = _season(raw.get("season_to"))
    st = raw.get("season_type")
    state["season_type"] = st if st in _SEASON_TYPES else None
    state["topic"] = _clip(raw.get("topic"), 60) or None
    state["stat_focus"] = _str_list(raw.get("stat_focus"), MAX_STAT_FOCUS)
    state["table"] = _clip(raw.get("table"), 60) or None
    state["leaderboard"] = bool(raw.get("leaderboard"))
    state["top_results"] = _str_list(raw.get("top_results"), MAX_TOP_RESULTS)
    state["last_question"] = _clip(raw.get("last_question")) or None
    state["last_answer"] = _clip(raw.get("last_answer"), MAX_LAST_ANSWER) or None
    if not (state["entities"] or state["season_from"] or state["topic"] or state["top_results"]):
        return None
    state["summary"] = summarize(state)
    return state


def _plan_get(plan: Any, key: str, default: Any = None) -> Any:
    if plan is None:
        return default
    if isinstance(plan, Mapping):
        return plan.get(key, default)
    return getattr(plan, key, default)


def _name_column(df: Any, hint: str | None) -> str | None:
    cols = [str(c) for c in getattr(df, "columns", [])]
    lower = {c.lower(): c for c in cols}
    for cand in ((hint,) if hint else ()) + _NAME_COLUMNS:
        if cand and cand.lower() in lower:
            return lower[cand.lower()]
    return None


def top_names_from_bundles(
    bundles: Mapping[str, Any] | None, name_column: str | None = None, limit: int = MAX_TOP_RESULTS
) -> list[str]:
    """Distinct entity names from the first non-empty bundle, in row order."""
    for df in (bundles or {}).values():
        if df is None or getattr(df, "empty", True):
            continue
        col = _name_column(df, name_column)
        if not col:
            continue
        return _str_list([v for v in df[col].tolist() if v is not None], limit)
    return []


def _first_answer_line(answer: str | None) -> str | None:
    """The analyst leads with the answer, so its first non-empty line is the gist."""
    if not answer:
        return None
    for line in str(answer).splitlines():
        line = line.strip().lstrip("#*-> ").strip()
        if line:
            return _clip(line.replace("**", ""), MAX_LAST_ANSWER)
    return None


def update_state(
    prev: Mapping[str, Any] | None,
    *,
    question: str,
    plan: Any = None,
    bundles: Mapping[str, Any] | None = None,
    name_column: str | None = None,
    answer: str | None = None,
) -> dict[str, Any]:
    """Fold one finished turn into the state. Pure function, no I/O.

    * The router has already resolved the follow-up, so its plan IS the new
      focus: entities/seasons/topic are replaced wholesale, not merged.
    * Entities that drop out of focus move to `recent_entities` (most recent
      first) so "both of them", "between them" and "add X" can reach back.
    * Leaderboard turns record the top names so "how many did HE average?"
      resolves to the leader.
    * An unsupported plan that still named entities updates the focus (the
      user's referents changed even if that question could not be answered);
      a turn with no plan at all keeps the previous focus.
    """
    state = dict(sanitize_state(prev) or empty_state())
    state["turn"] = int(state.get("turn") or 0) + 1

    supported = bool(_plan_get(plan, "supported", False)) and bool(_plan_get(plan, "table"))
    entities = _str_list(_plan_get(plan, "entities", []), MAX_ENTITIES)
    if plan is not None and (supported or entities):
        order_by = _plan_get(plan, "order_by") if supported else None
        limit = _plan_get(plan, "limit") if supported else None
        leaderboard = not entities and bool(order_by or limit)
        found = top_names_from_bundles(bundles, name_column) if supported else []
        if entities and len(found) == len(entities):
            # Prefer the vault's canonical spelling ("Nikola Jokić") when the rows
            # came back for exactly the named entities.
            entities = found
        et = _plan_get(plan, "entity_type")
        st = _plan_get(plan, "season_type")
        stat_focus = _str_list(_plan_get(plan, "stat_focus", []), MAX_STAT_FOCUS)
        if order_by and order_by not in stat_focus:
            stat_focus = ([order_by] + stat_focus)[:MAX_STAT_FOCUS]
        current = {e.lower() for e in entities}
        recent = _str_list(
            [
                e
                for e in (state.get("entities") or [])
                + (state.get("top_results") or [])[:1]
                + (state.get("recent_entities") or [])
                if e.lower() not in current
            ],
            MAX_ENTITIES,
        )
        state.update(
            {
                "entity_type": et if et in _ENTITY_TYPES else state.get("entity_type"),
                "entities": entities,
                "recent_entities": recent,
                # An unsupported plan often leaves seasons blank; do not let it
                # wipe the season the conversation was already on.
                "season_from": _season(_plan_get(plan, "season_from"))
                if supported or _plan_get(plan, "season_from")
                else state.get("season_from"),
                "season_to": _season(_plan_get(plan, "season_to"))
                if supported or _plan_get(plan, "season_to")
                else state.get("season_to"),
                "season_type": st if st in _SEASON_TYPES else "Regular Season",
                # An unsupported plan's topic is usually the failed combination
                # ("standings + offensive rating"); carrying it would make the
                # next follow-up fail the same way, so keep the last good one.
                "topic": (_clip(_plan_get(plan, "topic"), 60) or None) if supported else state.get("topic"),
                "stat_focus": stat_focus if supported else (state.get("stat_focus") or []),
                "table": (_clip(_plan_get(plan, "table"), 60) or None) if supported else state.get("table"),
                "leaderboard": leaderboard,
                "top_results": found if leaderboard else [],
            }
        )

    state["last_question"] = _clip(question) or None
    state["last_answer"] = _first_answer_line(answer)
    state["summary"] = summarize(state)
    return state


def _season_text(state: Mapping[str, Any]) -> str:
    sf, stt = state.get("season_from"), state.get("season_to")
    if sf and stt and sf != stt:
        return f"{sf} to {stt}"
    return sf or stt or "all seasons"


def summarize(state: Mapping[str, Any]) -> str:
    """Deterministic one-sentence summary of the current focus."""
    if not state:
        return ""
    season = _season_text(state)
    stype = state.get("season_type") or "Regular Season"
    topic = state.get("topic") or "stats"
    if state.get("leaderboard"):
        lead = ", ".join((state.get("top_results") or [])[:3]) or "n/a"
        stat = (state.get("stat_focus") or [topic])[0]
        return f"Last turn ranked league {state.get('entity_type') or 'player'}s by {stat} ({season} {stype}); top: {lead}."
    ents = ", ".join(state.get("entities") or [])
    if not ents:
        return f"Last turn looked at {topic} ({season} {stype})." if state.get("topic") else ""
    return f"Discussing {ents} — {topic}, {season} {stype}."


def context_block(state: Mapping[str, Any] | None, *, include_last_exchange: bool = True) -> str:
    """Compact text describing the state (what the router sees instead of the transcript)."""
    if not state:
        return ""
    compact = {
        k: state.get(k)
        for k in (
            "entity_type",
            "entities",
            "recent_entities",
            "season_from",
            "season_to",
            "season_type",
            "topic",
            "stat_focus",
            "top_results",
        )
        if state.get(k) not in (None, [], "")
    }
    lines = [f"Summary: {state.get('summary') or summarize(state)}", "Active focus: " + json.dumps(compact, ensure_ascii=False)]
    if include_last_exchange:
        if state.get("last_question"):
            lines.append(f"Previous user question: {state['last_question']}")
        if state.get("last_answer"):
            lines.append(f"Previous answer (first line): {state['last_answer']}")
    return "\n".join(lines)


ROUTER_CONTEXT_RULES = """CONVERSATION CONTEXT (state of this chat so far). Use it ONLY to resolve references in
the user question; whatever the question states explicitly always wins.
- "what about X?" / "and X?" / "how about X?" naming a new player/team: swap the subject to X and
  keep the prior stat focus, seasons and season_type.
- "compare him/them to X", "add X", "X too": keep the current entities AND add X.
- "both of them", "between them", "which of them": the current entities; if only one is current,
  pair it with the first name in recent_entities.
- he/his/him/they/their/them: the current entities. Right after a leaderboard they mean the FIRST
  name in top_results.
- "that season", "that year", "those years": the current season range. "the season before" /
  "the following season" / "same thing for <season>": shift the season, keep entities and stat.
- A stat named in the question REPLACES the prior stat focus/topic — never combine the old topic
  with the new stat. With no stat named ("compare them to X", "and the playoffs?") keep the prior one.
- season_type carries over unless the question says playoffs / regular season.
- A new leaderboard ("top 5 scorers that season", "and the best shot blocker?") has NO entities;
  carry only the season and season_type.
- A question that names its own subject and season is standalone: ignore the context."""


def router_context_block(state: Mapping[str, Any] | None) -> str:
    """Rules + compact state for the router prompt; empty string when no state."""
    block = context_block(state)
    return f"{ROUTER_CONTEXT_RULES}\n{block}" if block else ""


def resolved_question(question: str, plan: Any) -> str:
    """Question for the analyst with the router's resolution appended.

    With state-based routing there is no rewritten standalone question, so the
    analyst sees e.g. "what about his rebounds? (resolved: Nikola Jokić, 2023-24
    Regular Season)" and does not have to guess who "his" is.
    """
    q = (question or "").strip()
    if plan is None or not _plan_get(plan, "supported", False):
        return q
    ents = ", ".join(_plan_get(plan, "entities", []) or []) or "league leaders"
    sf, stt = _plan_get(plan, "season_from"), _plan_get(plan, "season_to")
    season = f"{sf} to {stt}" if sf and stt and sf != stt else (sf or stt or "all seasons")
    stype = _plan_get(plan, "season_type") or "Regular Season"
    return f"{q} (resolved: {ents}, {season} {stype})"


__all__ = [
    "STATE_VERSION",
    "context_block",
    "empty_state",
    "resolved_question",
    "router_context_block",
    "sanitize_state",
    "summarize",
    "top_names_from_bundles",
    "update_state",
]
