"""Cheap pre-router guard for greetings, small talk and keyboard mash.

Runs before Call 1 so "hello" / "asdfgh" / "" never cost an LLM call and never
fall through to the "needs more than one table" message. Deliberately conservative:
anything that might be a real (or follow-up) basketball question returns None and
goes through the router, which has its own `intent: off_topic` escape hatch.

Words like "yes" / "ok" / "sure" are NOT treated as small talk — they are
follow-ups to the previous answer and are handled by the history logic.
"""
from __future__ import annotations

import re

CAPABILITIES = (
    "I'm DataSport's NBA analyst. I answer questions from a stats vault of NBA "
    "player, team and game data. Try things like:\n"
    "- \"How many points did Jokic average in 2024-25?\"\n"
    "- \"Compare LeBron and Curry this season\"\n"
    "- \"Top 10 three-point shooters in 2024-25\"\n"
    "- \"Celtics record in 2024-25\"\n"
    "- \"Who led the league in rebounds in 2023-24?\""
)

_REPLIES = {
    "empty": "Ask me anything about NBA players, teams or games.\n\n" + CAPABILITIES,
    "greeting": "Hey! " + CAPABILITIES,
    "thanks": "Anytime! Ask another NBA question whenever you're ready.",
    "identity": CAPABILITIES,
    "help": CAPABILITIES,
    "joke": (
        "I'm better with box scores than punchlines, but here's one: the Clippers "
        "and a broken pencil walk into a bar — neither has a point in May.\n\n"
        + CAPABILITIES
    ),
    "gibberish": "I didn't catch that. " + CAPABILITIES,
    "off_topic": (
        "That's outside what I can help with — I only know NBA stats. " + CAPABILITIES
    ),
}

_GREETING = re.compile(
    r"^(hi+|hey+|hello+|hiya|yo+|sup|wass?up|what'?s up|howdy|greetings|hola|"
    r"good (morning|afternoon|evening)|gm)( there| datasport| bot)?$"
)
_THANKS = re.compile(r"^(thanks?( you)?|thx|ty|cheers|appreciate it)( so much| a lot)?$")
_IDENTITY = re.compile(
    r"^(who|what) (are|r) (you|u)$|^what is (this|datasport)$|^what can (you|u) do$|"
    r"^what do (you|u) do$|^how does this work$|^are you (a bot|an ai|human|real)$"
)
_HELP = re.compile(r"^(help|help me|\?+|menu|start|test|testing)$")
_JOKE = re.compile(r"\b(tell|give)( me)? (a |another )?joke\b|^joke$")
_OFF_TOPIC = re.compile(
    r"\b(weather|forecast|temperature outside|recipe|stock price|bitcoin|crypto|"
    r"horoscope|lottery|homework|write (me )?(a |an )?(poem|essay|story|song))\b"
)
_HOW_ARE_YOU = re.compile(r"^how (are|r) (you|u)( doing)?$|^how'?s it going$")

_KEYBOARD_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")


def _normalize(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[!.,?~]+$", "", t)  # trailing punctuation
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _is_keyboard_mash(t: str) -> bool:
    if " " in t or len(t) < 4 or not t.isalpha():
        return False
    if any(set(t) <= set(row) for row in _KEYBOARD_ROWS):
        return True
    vowels = sum(ch in "aeiouy" for ch in t)
    return vowels == 0


def classify_smalltalk(question: str) -> str | None:
    """Return a small-talk intent key, or None if the question should be routed."""
    raw = (question or "").strip()
    if not raw:
        return "empty"
    if not re.search(r"[A-Za-z0-9]", raw):  # "?", "!!!", "..." etc.
        return "help"

    t = _normalize(raw)
    if not t:
        return "empty"
    if _GREETING.match(t):
        return "greeting"
    if _HOW_ARE_YOU.match(t):
        return "greeting"
    if _THANKS.match(t):
        return "thanks"
    if _IDENTITY.match(t):
        return "identity"
    if _HELP.match(t):
        return "help"
    if _JOKE.search(t):
        return "joke"
    if _OFF_TOPIC.search(t):
        return "off_topic"
    if _is_keyboard_mash(t):
        return "gibberish"
    return None


def smalltalk_reply(intent: str) -> str:
    return _REPLIES.get(intent, _REPLIES["off_topic"])


__all__ = ["classify_smalltalk", "smalltalk_reply", "CAPABILITIES"]
