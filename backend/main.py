import logging
import os
import json
import sys

# Windows consoles default to cp1252, which cannot encode accented player names
# ("Dončić", "Jokić") or curly quotes. Without this, a single print() of such a
# question raises UnicodeEncodeError and the request 500s.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):  # not a reconfigurable text stream
        pass

# Align root log level with env before importing Interpreter/Executor (uvicorn may configure logging first).
logging.getLogger().setLevel(
    getattr(logging, (os.getenv("LOG_LEVEL") or "INFO").upper(), logging.INFO)
)

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Set
# DashboardBackend is the retired Postgres chart interpreter — importing it pulls in
# psycopg2 and a schema the vault no longer has. See DASHBOARD_PLAN.md.
from Analyzer.query_analyzer import analyze_question_with_data, analyze_bundled_data
from auth import (
    sign_up,
    log_in,
    verify_token,
    save_history_message,
    get_conversation_messages,
    list_conversations,
)
from Interpreter.interpreter import run_query, debug_query_routing, use_router_pipeline
from Interpreter.pipeline import run_routed_query, EntityAmbiguity, GameLogScopeError
from Interpreter.sql_builder import bundles_to_records, primary_bundle_for_frontend
from Visualizer import chart_hint_line, select_charts
from llm.client import LLMNotConfiguredError
from openai import OpenAI
import numpy as np
import pandas as pd
import re

logger = logging.getLogger(__name__)

app = FastAPI()

from api.staging_reads import router as staging_router

app.include_router(staging_router)

from llm.client import openai_base_url

context_client = (
    OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=openai_base_url())
    if os.getenv("OPENAI_API_KEY")
    else None
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "API is running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    conversationId: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None

class AuthRequest(BaseModel):
    email: str
    password: str

class DebugRoutingRequest(BaseModel):
    question: str
    model_sql: Optional[str] = None


class HistoryMessageRequest(BaseModel):
    conversationId: str
    role: str
    content: str


def get_uid_from_authorization(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    id_token = authorization.replace("Bearer ", "", 1).strip()
    if not id_token:
        raise HTTPException(status_code=401, detail="Missing token")

    verified = verify_token(id_token)
    if not verified.get("success"):
        raise HTTPException(status_code=401, detail="Invalid token")

    uid = verified.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return uid


def _build_contextual_question(
    current_question: str, history_messages: List[Dict[str, Any]], max_messages: int = 8
) -> str:
    """
    Build a compact context wrapper so follow-up questions can resolve references
    (e.g., "him", "that season", "those two players") using recent chat turns.
    """
    if not history_messages:
        return current_question

    recent = history_messages[-max_messages:]
    context_lines: List[str] = []
    for msg in recent:
        role = str(msg.get("role", "")).strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        content = content.replace("\n", " ").strip()
        if len(content) > 300:
            content = content[:300] + "..."
        speaker = "User" if role == "user" else "Assistant"
        context_lines.append(f"{speaker}: {content}")

    if not context_lines:
        return current_question

    context_block = "\n".join(context_lines)
    return (
        "Use the recent conversation context below only to resolve references in the current question.\n"
        "Do not answer from chat text; still query the database as needed.\n\n"
        f"Conversation context:\n{context_block}\n\n"
        f"Current question: {current_question}"
    )


def _compact_history_for_context_ai(
    history_messages: List[Dict[str, Any]], max_messages: int = 8, max_chars: int = 450
) -> str:
    recent = history_messages[-max_messages:]
    context_lines: List[str] = []
    for msg in recent:
        role = str(msg.get("role", "")).strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        content = re.sub(r"\s+", " ", content)
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        speaker = "User" if role == "user" else "Assistant"
        context_lines.append(f"{speaker}: {content}")
    return "\n".join(context_lines)


def _json_object_from_text(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _resolve_followup_with_ai(
    current_question: str, history_messages: List[Dict[str, Any]]
) -> Optional[Dict[str, str]]:
    """
    Ask a small model to convert a sequential chat turn into a standalone NBA
    analytics question before SQL generation. This keeps pronoun/entity/time
    resolution flexible without putting raw assistant prose into the SQL prompt.
    """
    if context_client is None or not history_messages:
        return None

    history_block = _compact_history_for_context_ai(history_messages)
    if not history_block:
        return None

    system_prompt = (
        "You rewrite NBA analytics chat follow-ups into standalone database questions.\n"
        "Return ONLY a JSON object with these string/boolean fields:\n"
        "standalone_question, analysis_question, needs_history, reason.\n\n"
        "Rules:\n"
        "- Use history only to resolve references like he, him, they, them, that season, those teams, or same stat.\n"
        "- Do not answer the question and do not write SQL.\n"
        "- Preserve the user's latest requested metric, season, season type, opponent, and entity type.\n"
        "- If the latest user asks 'what about X' or 'how about X', carry the relevant prior metric/timeframe and replace the subject with X.\n"
        "- If pronouns refer to teams/franchises, write team names as teams, not players.\n"
        "- If pronouns refer to players, write player names as players.\n"
        "- If the user says yes/sure/ok/do it, infer the specific follow-up from the last assistant offer and prior user question.\n"
        "- If the current question is already standalone, set needs_history to false and repeat it exactly.\n"
        "- analysis_question should be the same as standalone_question unless a shorter natural wording is clearer for the final explanation.\n"
        "- Never invent a player, team, or season that is not present in the current question or recent history.\n"
    )
    user_prompt = (
        f"Recent conversation:\n{history_block}\n\n"
        f"Current user question:\n{current_question}\n\n"
        "JSON only:"
    )

    try:
        response = context_client.chat.completions.create(
            model=os.getenv("CONTEXT_RESOLVER_MODEL", "gpt-5.4-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_completion_tokens=500,
        )
        parsed = _json_object_from_text(response.choices[0].message.content or "")
        if not parsed:
            return None

        standalone = str(parsed.get("standalone_question", "")).strip()
        analysis_question = str(parsed.get("analysis_question", "")).strip() or standalone
        if not standalone:
            return None

        needs_raw = parsed.get("needs_history", True)
        if isinstance(needs_raw, bool):
            needs_history = needs_raw
        else:
            needs_history = str(needs_raw).strip().lower() not in {"false", "0", "no"}
        if not needs_history and standalone.lower() == (current_question or "").strip().lower():
            return {
                "effective_question": current_question,
                "analysis_question": current_question,
                "reason": "already_standalone",
            }

        return {
            "effective_question": standalone,
            "analysis_question": analysis_question,
            "reason": str(parsed.get("reason", "ai_context_rewrite")).strip() or "ai_context_rewrite",
        }
    except Exception as context_error:
        print(f"AI context rewrite skipped: {context_error}")
        return None


def _is_affirmative_followup(question: str) -> bool:
    q = re.sub(r"[^\w\s]", "", (question or "").strip().lower())
    if not q:
        return False
    tokens = q.split()
    if not tokens:
        return False
    if tokens[0] in {"yes", "yeah", "yep", "yup", "yah", "ya", "sure", "ok", "okay", "k", "kk"}:
        return True
    return q in {"do it", "go ahead", "go for it", "lets go", "lets do it", "please do"}


_COMPARISON_FOLLOWUP_MARKERS = (
    "better", "worse", "compare", "vs ", " vs.",
    "between them", "of the two", "of those two",
    "who was better", "who is better", "who's better",
    " or ", "as well as",
    # Comparative phrasing requires "than" — bare "more" / "less" matches
    # too aggressively (e.g. "tell me more about X" is a drill-down, not
    # a comparison).
    "more than", "less than", "greater than",
)

def _looks_like_comparison_followup(question: str) -> bool:
    raw = (question or "").strip().lower()
    # Strip a leading discourse "or " — when "Or what about KD?" comes after a
    # prior turn, that's a drill-down on KD, not a comparison.
    if raw.startswith("or "):
        raw = raw[3:].strip()
    q = " " + raw + " "
    return any(m in q for m in _COMPARISON_FOLLOWUP_MARKERS)


# Phrases that signal the user wants a deeper look at a SPECIFIC entity from
# the prior turn. When combined with a named player in the question, this lets
# us scope the response to that one player.
_DRILLDOWN_MARKERS = (
    "more in-depth", "more in depth", "more detail", "more details",
    "deeper", "deep dive", "deep-dive", "drill down", "drill-down",
    "tell me more", "tell me about",
    "breakdown of", "break down",
    "more on", "more about", "expand on", "elaborate on",
    "what about", "how about",
    "focus on", "just ",
)

def _looks_like_single_player_drilldown(question: str) -> bool:
    """True when the question has a 'tell me more / drill down' shape.
    Used to scope a follow-up to one named player (not a comparison)."""
    raw = (question or "").strip().lower()
    if raw.startswith("or "):
        raw = raw[3:].strip()
    q = " " + raw + " "
    if any(m in q for m in _COMPARISON_FOLLOWUP_MARKERS):
        return False
    return any(m in q for m in _DRILLDOWN_MARKERS)


# Match 1-3 word capitalized names. Allows internal uppercase (LeBron, McGee).
# Trailing 's (possessive) is stripped before matching. Sentence-start filter
# keeps common question words from leaking through.
_QUESTION_NAME_RE = re.compile(r"\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z\.\-']*){0,2})\b")

def _extract_named_players_from_question(question: str) -> List[str]:
    """Pull capitalized 1-3 word names from the user's question.
    Conservative — drops obvious section-header / stat-phrase / common-word
    false positives via _NAME_STOPWORDS and a sentence-start filter."""
    if not question:
        return []
    found: List[str] = []
    seen: Set[str] = set()
    # Strip possessive 's so "Curry's" → "Curry"
    cleaned = re.sub(r"['\u2019]s\b", "", question)
    # Skip common sentence-start capitalized words that look like names
    sentence_start_blocklist = {
        "what", "who", "where", "when", "why", "how", "show", "give",
        "tell", "compare", "find", "list", "rank", "between", "statistically",
        "analyze", "break", "more", "yes", "yeah", "ok", "sure",
        "deeper", "deep", "expand", "elaborate", "focus", "just",
        "describe", "explain", "summarize", "look", "looking",
    }
    for cand in _QUESTION_NAME_RE.findall(cleaned):
        key = cand.lower()
        first_word = key.split()[0] if key else ""
        if first_word in sentence_start_blocklist:
            continue
        if any(stop in key for stop in _NAME_STOPWORDS):
            continue
        if key in seen:
            continue
        seen.add(key)
        found.append(cand)
    return found


# Stop words to filter out of name candidates pulled from prior assistant text.
_NAME_STOPWORDS = {
    "regular season", "per game", "playoffs", "playoff", "field goal",
    "free throw", "double double", "triple double", "double-double",
    "triple-double", "plus minus", "plus-minus", "western conference",
    "eastern conference", "all star", "all-star",
}

_NAME_CANDIDATE_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z\.\-']+){1,2})\b")

def _extract_player_names_from_history(
    history_messages: List[Dict[str, Any]], limit: int = 4
) -> List[str]:
    names: List[str] = []
    seen = set()
    for msg in reversed(history_messages or []):
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        for cand in _NAME_CANDIDATE_RE.findall(content):
            key = cand.lower()
            if any(stop in key for stop in _NAME_STOPWORDS):
                continue
            if key in seen:
                continue
            seen.add(key)
            names.append(cand)
            if len(names) >= limit:
                return names
    return names


def _extract_latest_player_and_season_from_history(
    history_messages: List[Dict[str, Any]]
) -> tuple[Optional[str], Optional[str]]:
    player: Optional[str] = None
    season: Optional[str] = None
    season_pattern = re.compile(r"\b((?:19|20)\d{2}-\d{2})\s+season\b", re.IGNORECASE)
    requested_pattern = re.compile(r"([A-Za-z][A-Za-z\.\- ]+?)'s requested season was", re.IGNORECASE)
    heading_pattern = re.compile(r"\*\*([A-Za-z][A-Za-z\.\- ]+)\*\*")

    for msg in reversed(history_messages or []):
        content = str(msg.get("content", "")).strip()
        if not content:
            continue

        if season is None:
            season_match = season_pattern.search(content)
            if season_match:
                season = season_match.group(1)

        if player is None:
            requested_match = requested_pattern.search(content)
            if requested_match:
                player = requested_match.group(1).strip()
            else:
                heading_match = heading_pattern.search(content)
                if heading_match:
                    player = heading_match.group(1).strip()

        if player and season:
            break

    return player, season


def _should_apply_history_context(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False

    # Only inject history for likely follow-up/ellipsis prompts.
    followup_markers = [
        "what about",
        "how about",
        "and what",
        "and how",
        "and him",
        "and her",
        "and them",
        "and those",
        "and that",
        "and defensively",
        "and offensively",
        "also",
        "same ",
        "that ",
        "those ",
        "them",
        "they",
        "him",
        "his ",
        "her ",
        "their ",
        " it ",
        "its ",
        "that team",
        "those teams",
        "same team",
        "same stat",
        "same question",
        "offensively",
        "defensively",
        "break that down",
        "which one",
        "who is better",
        "who's better",
        "who was better",
        "yes",
        "yeah",
        "yep",
        "yup",
        "ok",
        "okay",
        "sure",
        # Drill-down phrasings — user is asking for more detail on something
        # established earlier in the conversation.
        "more in-depth",
        "more in depth",
        "more detail",
        "tell me more",
        "tell me about",
        "breakdown of",
        "break down",
        "more on",
        "more about",
        "expand on",
        "elaborate",
        "deeper",
        "deep dive",
        "drill down",
        "focus on",
        # Single-pronoun follow-ups — implicitly reference the prior subject.
        "how was he",
        "how is he",
        "how was she",
        "how is she",
        "was he",
        "was she",
        "is he",
        "is she",
        "did he",
        "did she",
        "does he",
        "does she",
        " he ",
        " she ",
    ]
    if any(marker in q for marker in followup_markers):
        return True

    # Very short prompts are often dependent on prior context.
    token_count = len(re.findall(r"\w+", q))
    return token_count <= 4


def _analysis_debug_enabled() -> bool:
    # Dev-focused: enabled by default; disable by setting ANALYSIS_DEBUG=0
    return os.getenv("ANALYSIS_DEBUG", "1").strip() not in {"0", "false", "False"}


def _sanitize_history_messages(history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    if not isinstance(history, list):
        return []

    sanitized: List[Dict[str, str]] = []
    for msg in history:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        sanitized.append({"role": role, "content": content})
    return sanitized


def _entity_context_names(history_messages: List[Dict[str, str]]) -> List[str]:
    """Capitalised multi-word names already used in this thread.

    Feeds the entity resolver so a bare surname keeps referring to whoever the
    conversation was already about — after "Seth Curry", a later plain "Curry"
    should not jump to Stephen just because he scored more career points.
    Most recent turns first, so recency wins.
    """
    if not history_messages:
        return []

    names: List[str] = []
    seen = set()
    for msg in reversed(history_messages[-8:]):
        for match in re.findall(
            r"\b[A-ZÀ-Ž][\w'’.-]+(?:\s+[A-ZÀ-Ž][\w'’.-]+)+", msg.get("content", "")
        ):
            key = match.lower()
            if key not in seen:
                seen.add(key)
                names.append(match)
    return names[:12]


def _extract_explicit_season_start(question: str) -> tuple[Optional[int], bool]:
    q = (question or "").lower()
    is_playoffs = "playoff" in q or "postseason" in q

    season_match = re.search(r"\b(19\d{2}|20\d{2})\s*[-/]\s*(\d{2}|19\d{2}|20\d{2})\b", q)
    if season_match:
        return int(season_match.group(1)), is_playoffs

    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", q)
    if not year_match:
        return None, is_playoffs

    year = int(year_match.group(1))
    if is_playoffs:
        return year - 1, True
    return year, False


def _unsupported_specialty_message(question: str) -> Optional[str]:
    q = (question or "").lower()
    hustle_terms = [
        "hustle",
        "deflection",
        "deflections",
        "contested shot",
        "contested shots",
        "charge",
        "charges",
        "screen assist",
        "screen assists",
        "box out",
        "box outs",
        "loose ball",
        "loose balls",
    ]
    if not any(term in q for term in hustle_terms):
        return None

    season_start, is_playoffs = _extract_explicit_season_start(question)
    if season_start is None:
        return None

    season_label = f"{season_start}-{str(season_start + 1)[-2:]}"
    season_type = "Playoffs" if is_playoffs else "Regular Season"

    # Coverage is read from the vault rather than hardcoded. The previous version
    # pinned playoffs to `range(2015, 2025)`, which went stale the moment 2025-26
    # was staged and told users a season they could query was unavailable.
    available = _hustle_seasons(season_type)
    if not available:
        return None  # cannot prove absence — let the router try
    if season_label in available:
        return None

    return (
        f"Hustle stats ({season_type.lower()}) are not available for {season_label} "
        f"in this database.\n\nAvailable {season_type.lower()} hustle seasons: "
        f"{_summarize_seasons(available)}."
    )


@lru_cache(maxsize=4)
def _hustle_seasons(season_type: str) -> frozenset:
    """Seasons that actually carry non-null hustle data, read from the vault."""
    try:
        from Executer.data_backend import get_connection

        rows = get_connection().execute(
            """
            SELECT DISTINCT season FROM player_season_stats
            WHERE season_type = ?
              AND hustle_deflections IS NOT NULL
            ORDER BY season
            """,
            [season_type],
        ).fetchall()
        return frozenset(str(r[0]) for r in rows)
    except Exception as exc:  # noqa: BLE001 — never block a question on this probe
        logger.debug("Hustle coverage probe failed: %s", exc)
        return frozenset()


def _summarize_seasons(seasons) -> str:
    """'2015-16 through 2025-26' rather than listing eleven labels."""
    ordered = sorted(seasons)
    if not ordered:
        return "none"
    if len(ordered) <= 3:
        return ", ".join(ordered)

    runs, start, prev = [], ordered[0], ordered[0]
    for s in ordered[1:]:
        if int(s[:4]) == int(prev[:4]) + 1:
            prev = s
            continue
        runs.append((start, prev))
        start = prev = s
    runs.append((start, prev))
    return ", ".join(a if a == b else f"{a} through {b}" for a, b in runs)


def _build_effective_question_from_history(
    current_question: str, history_messages: List[Dict[str, Any]]
) -> tuple[str, str, str]:
    """
    Return (sql_question, analyzer_question, strategy). Prefer an AI rewrite
    into a standalone question; fall back to the old context wrapper plus
    targeted deterministic constraints when the rewrite is unavailable.
    """
    ai_resolution = _resolve_followup_with_ai(current_question, history_messages)
    if ai_resolution:
        return (
            ai_resolution["effective_question"],
            ai_resolution["analysis_question"],
            f"ai_standalone_rewrite: {ai_resolution['reason']}",
        )

    effective_question = _build_contextual_question(current_question, history_messages)
    analysis_question = current_question

    if _is_affirmative_followup(current_question):
        player_name, season_label = _extract_latest_player_and_season_from_history(history_messages)
        if player_name and season_label:
            effective_question += (
                "\n\nFollow-up constraint: keep the SAME player and SAME season as the last answer. "
                f"Use player_name ILIKE '%{player_name}%' and season_label '{season_label}' context "
                "(do not advance to a different season)."
            )

    # Comparison continuity. If the follow-up is comparison-shaped but the user
    # dropped one or both names, pull the missing entities from history.
    if _looks_like_comparison_followup(current_question):
        prior_names = _extract_player_names_from_history(history_messages)
        current_lower = current_question.lower()
        missing = [n for n in prior_names if n.lower() not in current_lower]
        if missing:
            names_clause = " and ".join(missing[:2])
            effective_question += (
                f"\n\nFollow-up constraint: this is a CONTINUATION of an earlier comparison. "
                f"Include {names_clause} alongside any players named in the current question. "
                f"Treat as a multi-player comparison and return one row per player."
            )
            analysis_question = (
                f"{analysis_question} (continuing comparison with {names_clause})"
            )

    # Single-player drill-down. If the follow-up explicitly names one player and
    # is not comparison-shaped, scope the SQL and narrative to that one player.
    elif _looks_like_single_player_drilldown(current_question):
        named = _extract_named_players_from_question(current_question)
        if len(named) == 1:
            only_player = named[0]
            effective_question += (
                f"\n\nFollow-up constraint: this drill-down is about {only_player} ONLY. "
                f"Filter SQL to player_name ILIKE '%{only_player}%' and do NOT include "
                f"any other players from the prior conversation. The narrative must focus "
                f"exclusively on {only_player}."
            )
            analysis_question = (
                f"{analysis_question} (single-player drill-down: {only_player})"
            )

    return effective_question, analysis_question, "deterministic_context_wrapper"

@app.post("/api/dashboards")
async def dashboard_endpoint(request: QueryRequest):
    """Chart generation — not wired to the vault yet. See DASHBOARD_PLAN.md.

    This used to call `DashboardBackend.interpret_question`, which writes Postgres SQL
    against the old per-season schema (`all_players_regular_2023_2024`) and hands a
    DuckDB connection to psycopg2. Every request failed — and worse, it closed the
    SHARED DuckDB connection in its `finally`, so one dashboard request took the entire
    staging API down until the backend was restarted.

    Failing honestly is strictly better than that. The replacement derives a chart spec
    from the router plan the analyst already produces, with no second model call and no
    model-written SQL.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "Chart generation is being rebuilt on the router pipeline and is not "
            "available yet. Ask the same question through /api/analysis for the "
            "numbers in the meantime."
        ),
    )

@app.post("/api/analysis")
async def analysis_endpoint(
    request: QueryRequest,
    authorization: Optional[str] = Header(default=None),
):
    if not (request.question or "").strip():
        # A bare ValueError from the router used to reach the catch-all below and
        # come back as 500 "Analysis failed: Question is empty".
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        print("----HIT----- /api/analysis")
        print(f"Question: {request.question}")

        effective_question = request.question
        analysis_question = request.question
        history_context_applied = False
        history_context_reason = "no_history_available"
        history_messages: List[Dict[str, Any]] = _sanitize_history_messages(request.history)

        # Prefer history passed by the frontend (works for both guest and auth chats).
        if history_messages and _should_apply_history_context(request.question):
            effective_question, analysis_question, context_strategy = _build_effective_question_from_history(
                request.question, history_messages
            )
            history_context_applied = True
            history_context_reason = f"request_history_used/{context_strategy}"
        # Fallback for older clients: load persisted history for authenticated users.
        elif request.conversationId and authorization and _should_apply_history_context(request.question):
            try:
                uid = get_uid_from_authorization(authorization)
                history_result = get_conversation_messages(uid, request.conversationId.strip())
                if history_result.get("success"):
                    fetched_history = history_result.get("messages", [])
                    if isinstance(fetched_history, list) and fetched_history:
                        effective_question, analysis_question, context_strategy = _build_effective_question_from_history(
                            request.question, _sanitize_history_messages(fetched_history)
                        )
                        history_context_applied = True
                        history_context_reason = f"stored_history_used/{context_strategy}"
                    else:
                        history_context_reason = "stored_history_empty"
                else:
                    history_context_reason = "history_lookup_failed"
            except Exception as history_error:
                # Keep analysis available even if history lookup fails.
                print(f"History context skipped: {history_error}")
                history_context_reason = "history_lookup_exception"
        elif history_messages:
            history_context_reason = "history_not_needed_for_standalone_question"
        elif request.conversationId and authorization:
            history_context_reason = "stored_history_not_needed_for_standalone_question"
        elif request.conversationId and not authorization:
            history_context_reason = "guest_without_request_history"

        unsupported_message = _unsupported_specialty_message(effective_question)
        if unsupported_message:
            payload = {
                "success": True,
                "analysis": unsupported_message,
                "data": [],
                "question": analysis_question,
            }
            if _analysis_debug_enabled():
                payload["debug"] = {
                    "historyContextApplied": history_context_applied,
                    "historyContextReason": history_context_reason,
                    "conversationId": request.conversationId,
                    "originalQuestion": request.question,
                    "effectiveQuestion": effective_question,
                    "analysisQuestion": analysis_question,
                    "unsupportedReason": "specialty_table_unavailable",
                }
            return payload

        # Run query: router pipeline (multi-table) or legacy single-DataFrame path
        router_mode = use_router_pipeline()
        router_plan = None
        table_bundles: Dict[str, Any] = {}

        # Names already mentioned in this thread break ties for a bare surname:
        # after "Seth Curry", a later plain "Curry" should stay Seth.
        context_names = _entity_context_names(history_messages)

        try:
            if router_mode:
                table_bundles, router_plan = run_routed_query(
                    effective_question, context_names
                )
                query_result = primary_bundle_for_frontend(table_bundles)
            else:
                query_result = run_query(effective_question)
        except GameLogScopeError as scope_error:
            # Not a failure — the user asked the game-log table something only the
            # season table can answer well. Tell them how to ask it properly.
            payload = {
                "success": True,
                "analysis": scope_error.message,
                "data": [],
                "question": analysis_question,
                "needsNarrowerScope": True,
            }
            if _analysis_debug_enabled():
                payload["debug"] = {"unsupportedReason": "game_log_scope_too_broad"}
            return payload
        except EntityAmbiguity as ambiguous:
            # Ask rather than guess — a confident answer about the wrong player is
            # worse than one clarifying question.
            payload = {
                "success": True,
                "analysis": ambiguous.message,
                "data": [],
                "question": analysis_question,
                "needsClarification": True,
                "clarificationOptions": [
                    [c.canonical for c in r.candidates[:6]] for r in ambiguous.resolutions
                ],
            }
            if _analysis_debug_enabled():
                payload["debug"] = {
                    "unsupportedReason": "entity_ambiguous",
                    "ambiguousQueries": [r.query for r in ambiguous.resolutions],
                    "contextNames": context_names,
                }
            return payload
        except LLMNotConfiguredError as llm_exc:
            raise HTTPException(
                status_code=503,
                detail=f"LLM API key not configured for router: {llm_exc}",
            ) from llm_exc

        # Call 1 rejected the question. The reason decides which answer the user gets —
        # the old code called everything a multi-table limitation, which told people
        # asking for true shooting percentage to wait for a feature that would never
        # help them, and said the same thing to someone typing gibberish.
        if router_mode and router_plan is not None and not getattr(router_plan, "supported", True):
            reason = (getattr(router_plan, "unsupported_reason", "") or "").strip()

            if reason.upper().startswith("NOT_BASKETBALL"):
                # Refused at Call 1, so no analyst call is made and this costs nothing
                # beyond the routing token spend already incurred.
                detail = reason.split(":", 1)[-1].strip() if ":" in reason else ""
                message = (
                    "I only answer questions about NBA statistics from this vault.\n\n"
                    "Try something like:\n"
                    "  • \"What did Nikola Jokic average in 2023-24?\"\n"
                    "  • \"Who led the league in three-pointers last season?\"\n"
                    "  • \"Compare Jayson Tatum and Jaylen Brown on scoring.\""
                )
                payload = {
                    "success": True,
                    "analysis": message,
                    "data": [],
                    "question": analysis_question,
                    "offTopic": True,
                }
                if _analysis_debug_enabled():
                    payload["debug"] = {"unsupportedReason": "not_basketball", "detail": detail}
                return payload

            if reason.upper().startswith("ROLE_NOT_IN_VAULT"):
                # "Best sixth man" is not a multi-table problem and never will be — the
                # vault has no column that says who came off the bench. Saying "wait for
                # multi-table analysis" promises a feature that would not help.
                detail = reason.split(":", 1)[-1].strip() if ":" in reason else ""
                message = (
                    "The vault records what players DID, not what role they were given, "
                    "so it can't rank a role it doesn't store.\n\n"
                    f"{detail}\n\n"
                    "Two things it can do instead:\n"
                    "  • the award itself — \"Who won Sixth Man of the Year in 2023-24?\"\n"
                    "  • the underlying stat, ranked openly — \"Who scored the most points "
                    "per game in 2023-24?\""
                )
                payload = {
                    "success": True,
                    "analysis": message,
                    "data": [],
                    "question": analysis_question,
                    "roleUnavailable": True,
                }
                if _analysis_debug_enabled():
                    payload["debug"] = {"unsupportedReason": "role_not_in_vault", "detail": detail}
                return payload

            if reason.upper().startswith("STAT_NOT_IN_VAULT") or "not in the vault" in reason.lower():
                # This paragraph used to say TS%, eFG% and PIE existed "only for five-man
                # lineups and per individual game". The 2026-08-19 restage folded the
                # advanced dash slices into the season tables as columns, so the
                # explanation had been contradicting the data for a day.
                message = (
                    "That stat isn't in the vault at the level you asked for.\n\n"
                    f"{reason}\n\n"
                    "The vault covers 1996-97 onward. Season box score, advanced "
                    "(true shooting, eFG%, usage, PIE, offensive/defensive/net rating, "
                    "pace) and clutch splits all live on the season tables. Play-type "
                    "data starts in 2015-16, tracking in 2013-14, and hustle in 2015-16."
                )
                payload = {
                    "success": True,
                    "analysis": message,
                    "data": [],
                    "question": analysis_question,
                    "statUnavailable": True,
                }
                if _analysis_debug_enabled():
                    payload["debug"] = {"unsupportedReason": "stat_not_in_vault", "detail": reason}
                return payload

            # Only call it a multi-table limitation when the router actually said two
            # tables were needed. This message was also being shown for "Who is the
            # GOAT?" and "What happened in the 2011 lockout season?", promising a
            # feature that has nothing to do with why either was refused.
            multi_table = "table" in reason.lower()
            if multi_table:
                message = (
                    "That question needs data from more than one table at once, which the "
                    "analyzer can't do yet — multi-table analysis is still a work in progress."
                )
                tail = (
                    "\n\nTry asking about one area at a time — for example season box-score "
                    "stats on their own, or tracking data on their own."
                )
            else:
                message = "I couldn't answer that one from the vault."
                tail = (
                    "\n\nNaming a specific stat and season usually gets there — "
                    "\"Compare LeBron and Jordan on points and true shooting.\""
                )
            if reason:
                # The prefix is a routing code for the API, not something to show a
                # reader — "Why: NEEDS_GAME_LOOKUP: identifying a game by..." reads
                # as a leaked internal error.
                explanation = re.sub(r"^[A-Z][A-Z0-9_]{3,}:\s*", "", reason).strip()
                if explanation:
                    nl = chr(10) * 2
                    message += f"{nl}Why: {explanation[:1].upper()}{explanation[1:]}"
            message += tail
            payload = {
                "success": True,
                "analysis": message,
                "data": [],
                "question": analysis_question,
            }
            if _analysis_debug_enabled():
                payload["debug"] = {
                    "historyContextApplied": history_context_applied,
                    "historyContextReason": history_context_reason,
                    "conversationId": request.conversationId,
                    "originalQuestion": request.question,
                    "effectiveQuestion": effective_question,
                    "analysisQuestion": analysis_question,
                    "interpreterPipeline": "router",
                    "unsupportedReason": "multi_table_question",
                    "routerReason": reason,
                }
            return payload

        # Handle empty or failed queries with a helpful message instead of crashing
        if router_mode:
            empty = not table_bundles
        else:
            empty = query_result is None or (
                isinstance(query_result, pd.DataFrame) and query_result.empty
            )

        if empty:
            # The pipeline works out WHICH filter emptied the result and retries once
            # against the schema before giving up, so prefer its specific explanation
            # over the old catch-all that covered five different causes identically.
            specific = getattr(router_plan, "empty_reason", None) if router_plan else None
            payload = {
                "success": True,
                "analysis": specific or (
                    "No data was found for this query. This could mean:\n"
                    "- The player or team did not appear in the requested season/playoffs.\n"
                    "- The player or team name may be misspelled or not recognized.\n"
                    "- Try specifying a season year, e.g. 'Giannis 2023 playoff performance'."
                ),
                "data": [],
                "question": analysis_question
            }
            if _analysis_debug_enabled():
                payload["debug"] = {
                    "historyContextApplied": history_context_applied,
                    "historyContextReason": history_context_reason,
                    "conversationId": request.conversationId,
                    "originalQuestion": request.question,
                    "effectiveQuestion": effective_question,
                    "analysisQuestion": analysis_question,
                    "interpreterPipeline": "router" if router_mode else "legacy",
                }
            return payload

        # Clean NaN before JSON serialization
        if router_mode:
            clean_data = (
                query_result.replace({np.nan: None}).to_dict(orient="records")
                if not query_result.empty
                else []
            )
            tables_payload = bundles_to_records(table_bundles)
            # Chart choice is a pure function of the plan and the frame, so it costs no
            # tokens and cannot disagree with the prose. Selected BEFORE the analyst runs
            # so Call 2 can be told a picture exists and stop transcribing it.
            charts = select_charts(router_plan, table_bundles)
            analysis_result = analyze_bundled_data(
                analysis_question,
                table_bundles,
                router_plan,
                chart_hint=chart_hint_line(charts),
            )
        else:
            clean_data = query_result.replace({np.nan: None}).to_dict(orient="records")
            tables_payload = None
            charts = []  # the legacy pipeline has no plan to select from
            analysis_result = analyze_question_with_data(analysis_question, query_result)

        payload = {
            "success": True,
            "analysis": analysis_result,
            "data": clean_data,
            "question": analysis_question,
        }
        if tables_payload is not None:
            payload["tables"] = tables_payload
        if charts:
            payload["charts"] = [c.model_dump() for c in charts]
        if _analysis_debug_enabled():
            debug_info: Dict[str, Any] = {
                "historyContextApplied": history_context_applied,
                "historyContextReason": history_context_reason,
                "conversationId": request.conversationId,
                "originalQuestion": request.question,
                "effectiveQuestion": effective_question,
                "analysisQuestion": analysis_question,
                "interpreterPipeline": "router" if router_mode else "legacy",
            }
            if router_mode and router_plan is not None:
                debug_info["routerPlan"] = router_plan.model_dump()
                debug_info["bundleRowCounts"] = {
                    k: len(v) for k, v in table_bundles.items()
                }
            payload["debug"] = debug_info
        return payload

    except HTTPException:
        raise  # already a deliberate, user-facing status
    except Exception as e:
        # Log the detail; do not echo internal exception text back to the client.
        logger.exception("Analysis failed for question: %s", request.question[:200])
        raise HTTPException(
            status_code=500,
            detail="Analysis failed while processing that question. Please try again.",
        )

@app.post("/api/signup")
async def signup_endpoint(request: AuthRequest):
    result = sign_up(request.email, request.password)
    if result["success"]:
        return result
    raise HTTPException(status_code=400, detail=result["error"])

@app.post("/api/login")
async def login_endpoint(request: AuthRequest):
    result = log_in(request.email, request.password)
    if result["success"]:
        return result
    raise HTTPException(status_code=400, detail=result["error"])


@app.post("/api/history/message")
async def save_history_message_endpoint(
    request: HistoryMessageRequest,
    authorization: Optional[str] = Header(default=None),
):
    uid = get_uid_from_authorization(authorization)

    if request.role not in {"user", "assistant"}:
        raise HTTPException(status_code=400, detail="role must be 'user' or 'assistant'")

    if not request.conversationId.strip():
        raise HTTPException(status_code=400, detail="conversationId is required")
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    result = save_history_message(
        uid=uid,
        conversation_id=request.conversationId.strip(),
        role=request.role,
        content=request.content.strip(),
    )
    if result.get("success"):
        return {"success": True}
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to save message"))


@app.get("/api/history")
async def list_history_endpoint(authorization: Optional[str] = Header(default=None)):
    uid = get_uid_from_authorization(authorization)
    result = list_conversations(uid)
    if result.get("success"):
        return result
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to load history list"))


@app.get("/api/history/{conversation_id}")
async def get_history_endpoint(
    conversation_id: str,
    authorization: Optional[str] = Header(default=None),
):
    uid = get_uid_from_authorization(authorization)
    result = get_conversation_messages(uid, conversation_id)
    if result.get("success"):
        return result
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to load history"))


@app.post("/api/debug/routing")
async def debug_routing_endpoint(request: DebugRoutingRequest):
    try:
        if not request.model_sql:
            raise HTTPException(
                status_code=400,
                detail="model_sql is required so routing can be validated against a real generated query."
            )
        return {
            "success": True,
            "debug": debug_query_routing(request.question, request.model_sql)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug routing failed: {str(e)}")
