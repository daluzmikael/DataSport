"""Correct team-table routing on questions whose subject is a PERSON.

"Who was the 2008 Celtics best scorer" routed to `team_season_stats` with entity
"Celtics" and answered *"the team as a whole at 100.9 points per game"*. The only name
in the sentence was a team, so the router made the team the subject — but "scorer" is a
person, and a team is never a scorer. Adding the word "player" fixed it, which is
exactly the tell that the model was pattern-matching on names rather than on what was
being asked for.

The reliable signal is the SUPERLATIVE'S NOUN, not the names present:

    best scorer      -> a person
    best team        -> a team
    who scored most  -> a person

So when a question asks for a superlative person and the plan picked a team table, the
plan is rewritten: swap to the player table, empty the entities, and push the team down
into a TEAM_ABBREVIATION row filter — the same subject-vs-scope split the router prompt
describes, enforced in Python because a prompt rule that silently fails produces a
confident wrong answer.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Nouns that can only describe a person. "scorer" is the one that broke; the rest are
# the same shape and would break identically.
_PERSON_ROLES = (
    "scorer", "rebounder", "passer", "shooter", "defender", "playmaker",
    "finisher", "creator", "closer", "sixth man", "starter", "big man",
    "point guard", "guard", "forward", "center", "centre", "rookie", "player",
)

_ROLE_ALT = "|".join(re.escape(r) for r in sorted(_PERSON_ROLES, key=len, reverse=True))

_SUPERLATIVE = r"(?:best|worst|top|leading|greatest|most\s+prolific|highest[- ]scoring)"

# "best scorer", "leading rebounder", "top 5 scorers"
_ROLE_SUPERLATIVE = re.compile(
    rf"\b{_SUPERLATIVE}\b[^.?!]{{0,30}}?\b(?:{_ROLE_ALT})s?\b", re.IGNORECASE
)

# "who scored the most", "which player averaged the most", "what player led the team in"
_WHO_VERB = re.compile(
    rf"\b(?:who|which\s+(?:{_ROLE_ALT})|what\s+(?:{_ROLE_ALT}))\b"
    r"[^.?!]{0,40}?\b(?:scored|averaged|led|shot|grabbed|dished|blocked|had|has)\b",
    re.IGNORECASE,
)

# Explicit team framing that must NOT be rewritten: "best team", "which franchise".
_TEAM_SUBJECT = re.compile(
    rf"\b{_SUPERLATIVE}\b[^.?!]{{0,20}}?\b(?:team|franchise|squad|roster|offense|defense)\b",
    re.IGNORECASE,
)

# team table -> its player-grain counterpart
_TEAM_TO_PLAYER = {
    "team_season_stats": "player_season_stats",
    "team_estimated_metrics": "player_estimated_metrics",
    "team_game_logs": "player_game_logs",
    "team_tracking": "player_tracking",
    "team_shot_zones": "player_shot_zones",
    "team_synergy": "player_synergy",
}


def asks_for_a_person(question: str) -> bool:
    q = question or ""
    if _TEAM_SUBJECT.search(q):
        return False
    return bool(_ROLE_SUPERLATIVE.search(q) or _WHO_VERB.search(q))


def _tricode_for(name: str, season: str | None) -> str | None:
    from ingestion.team_identity import identity_for_name

    ident = identity_for_name(name, season)
    return ident.tricode if ident else None


def correct_person_scope(plan, question: str) -> bool:
    """Rewrite a team-table plan whose real subject is a person. Returns True if changed."""
    table = getattr(plan, "table", None)
    if not table or table not in _TEAM_TO_PLAYER:
        return False
    if not asks_for_a_person(question):
        return False

    player_table = _TEAM_TO_PLAYER[table]
    from Interpreter.router_plan import table_has_column

    teams = list(getattr(plan, "entities", None) or [])
    season = getattr(plan, "season_from", None) or getattr(plan, "season_to", None)

    filters = list(getattr(plan, "row_filters", None) or [])
    scoped = []
    for name in teams:
        tri = _tricode_for(name, season)
        if tri and table_has_column(player_table, "TEAM_ABBREVIATION"):
            filters.append({"column": "TEAM_ABBREVIATION", "op": "eq", "value": tri})
            scoped.append(f"{name}->{tri}")
        else:
            # Cannot express the team as a filter on the player table; leaving the plan
            # alone beats producing a league-wide answer to a team-scoped question.
            logger.info(
                "Person-subject question about %s, but %s has no usable team filter "
                "— leaving plan on %s", name, player_table, table
            )
            return False

    plan.table = player_table
    plan.entity_type = "player"
    plan.entities = []
    plan.row_filters = filters

    logger.info(
        "Person-subject correction: %s -> %s, team(s) moved to scope [%s]",
        table, player_table, ", ".join(scoped) or "none",
    )
    return True
