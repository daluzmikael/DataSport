"""Stop real basketball questions from being refused as "not basketball".

The router's cheapest exit is `NOT_BASKETBALL`, and it reaches for it whenever a
question is hard rather than off-topic. In one 102-question battery it fired on:

    "How many MVPs has the all-time leading scorer won?"
    "How tall is the player who led the league in blocks in 2023-24?"
    "Is Nikola Jokic overrated?"
    "What happened in the 2011 lockout season?"

All four are basketball. The first two are answerable in two reads, the last two are
answerable with caveats. Telling that user *"I only answer questions about NBA
statistics"* is worse than any of the honest failures — it accuses them of asking
something they did not ask.

The prompt already forbids this. Prompts do not hold, so the refusal is checked in
Python: if the question carries basketball evidence, the refusal is downgraded and the
router gets one corrected pass.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Vocabulary that marks a question as being about this vault. It errs generous —
# "season", "career", "stats" — because the only consequence of a false positive is one
# extra routing pass that then refuses for the RIGHT reason. A false negative tells
# someone their NBA question is not an NBA question. Bare "game" and "points" are still
# excluded: they carry no sport at all.
_NBA_TERMS = (
    "nba", "basketball", "mvp", "all-star", "all star", "all-nba", "all nba",
    "playoff", "playoffs", "finals", "championship", "champions", "ring", "rings",
    "rookie", "draft", "drafted", "roster", "franchise", "conference", "division",
    "points per game", "ppg", "rpg", "apg", "rebound", "rebounds", "assist", "assists",
    "steal", "steals", "block", "blocks", "turnover", "turnovers", "field goal",
    "three-point", "three point", "3-point", "3pt", "free throw", "dunk", "layup",
    "true shooting", "usage rate", "net rating", "offensive rating", "defensive rating",
    "pace", "efficiency", "double-double", "triple-double", "sixth man", "starter",
    "bench", "lineup", "isolation", "pick and roll", "post up", "spot up", "transition",
    "shot chart", "heat map", "box score", "game log", "standings", "seed",
    "scorer", "scoring", "shooter", "shooting", "defender", "rebounder", "playmaker",
    "lockout", "bubble", "goat", "hall of fame", "coach", "traded", "trade",
    "per game", "per 36", "per 100", "regular season", "postseason", "clutch",
    "season", "seasons", "last season", "this season", "career", "averaged",
    "led the league", "leaderboard", "stat", "stats", "box score",
)

_TERM_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in sorted(_NBA_TERMS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Instructions aimed at the system rather than the data. These stay refused even when
# they happen to mention basketball, because answering them is not the job.
_META_PATTERNS = (
    r"\bignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
    r"\b(?:print|show|reveal|repeat|output)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?prompt\b",
    r"\byou\s+are\s+now\b",
    r"\bdrop\s+table\b",
    r"\bwrite\s+(?:me\s+)?(?:a|some)\s+(?:python|javascript|sql|code|script)\b",
)
_META_RE = re.compile("|".join(_META_PATTERNS), re.IGNORECASE)


def basketball_evidence(question: str) -> str | None:
    """Why this question IS about basketball, or None if there is no sign of it."""
    q = question or ""
    if _META_RE.search(q):
        return None

    hit = _TERM_RE.search(q)
    if hit:
        return f"the phrase '{hit.group(0)}'"

    # A named player or franchise is evidence on its own — "What did Doncic average?"
    # contains no stat vocabulary at all.
    try:
        from Interpreter.team_scope import team_named_in

        tid, _ = team_named_in(q)
        if tid is not None:
            return "a named NBA team"
    except Exception:  # noqa: BLE001 — evidence gathering must never break routing
        pass

    try:
        from Interpreter.entity_resolver import resolve_player

        for phrase in _capitalised_runs(q):
            res = resolve_player(phrase)
            if res.canonical and res.matched_exactly:
                return f"the player {res.canonical}"
    except Exception:  # noqa: BLE001
        pass

    return None


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'.À-ɏ-]*")


def _capitalised_runs(question: str) -> list[str]:
    tokens = _TOKEN_RE.findall(question or "")
    out: list[str] = []
    for size in (3, 2):
        for i in range(len(tokens) - size + 1):
            window = tokens[i : i + size]
            if all(t[:1].isupper() for t in window):
                out.append(" ".join(window))
    return out[:8]


def is_wrongly_refused(plan, question: str) -> str | None:
    """Evidence that a NOT_BASKETBALL refusal is wrong, or None if it stands."""
    if getattr(plan, "supported", True):
        return None
    reason = (getattr(plan, "unsupported_reason", "") or "").strip().upper()
    if not reason.startswith("NOT_BASKETBALL"):
        return None
    evidence = basketball_evidence(question)
    if evidence:
        logger.info(
            "Router refused as NOT_BASKETBALL, but the question contains %s — retrying",
            evidence,
        )
    return evidence
