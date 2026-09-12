"""Keep a team named in the question from disappearing out of the plan.

*"Vancouver Grizzlies leading scorer 1997-98"* came back **"Michael Jordan led the
league at 28.7 points per game"**. The router built a league-wide player leaderboard,
dropped the franchise entirely, and the analyst — having no idea a team had ever been
asked about — narrated the rows it was handed. Nothing errored. The answer was fluent,
correct as a league leaderboard, and had nothing to do with the question.

`person_scope` handles the mirror case (a person question routed to a team table). This
handles the other direction: the plan is already on the right table, but the team scope
was silently lost. The guard is deliberately narrow — it only ever ADDS a filter, and
only when the plan has no team scope at all — because a wrong extra filter is just as
bad as a missing one.

Detection requires a CAPITALISED match in the original question. Team nicknames are
ordinary English words (Heat, Magic, Jazz, Kings, Nets, Thunder), so a case-insensitive
scan turns "show me his heat map" into a Miami filter. Proper nouns are capitalised;
"heat map" is not.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Column preference for expressing "this team" as a row filter, per table.
# TEAM_ID is stable across relocations and rebrands; the tricode is not (VAN -> MEM),
# so the id is preferred wherever it exists.
_TEAM_FILTER_COLUMNS = ("TEAM_ID", "TEAM_ABBREVIATION", "TeamID", "team_id")

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z.]*")
# Possessives are how people actually name teams — "the Sonics' best scorer" — and
# a trailing apostrophe blocked every one of them from matching.


def _candidates(question: str) -> list[str]:
    """Capitalised 1-3 word runs from the question, longest first.

    A lone three-letter token must be ALL CAPS to count. Tricodes are three letters and
    one of them is WAS, so "**Was** Stephen Curry a good defender in 2015-16?" matched
    the Washington Wizards and filtered Curry's own row out of his own question. A
    sentence-initial capital is not a tricode; "WAS" is.
    """
    tokens = _TOKEN_RE.findall(question or "")
    out: list[str] = []
    for size in (3, 2, 1):
        for i in range(len(tokens) - size + 1):
            window = tokens[i : i + size]
            if not window[0][:1].isupper():
                continue
            if size == 1:
                word = window[0]
                if len(word) <= 3 and not word.isupper():
                    continue
            out.append(" ".join(window))
    return out


def team_named_in(question: str, season: str | None = None):
    """The franchise identity named in the question, or None.

    Returns a `(team_id, TeamIdentity | None)` pair: the id always resolves, but the
    era-specific identity needs a season, and a franchise with several identities
    refuses to pick one without it.
    """
    from ingestion.team_identity import ALIAS_TO_ID, _norm, identity_for_id

    for phrase in _candidates(question):
        tid = ALIAS_TO_ID.get(_norm(phrase))
        if tid is None:
            continue
        return tid, identity_for_id(tid, season)
    return None, None


def era_for_alias(question: str):
    """The single era a name can only refer to — 'Sonics', 'Bullets', 'Bobcats'.

    A question naming a retired identity carries its own season range, which is how
    "Who was the best player on the Bobcats?" can be scoped without the user giving
    a year. Names still in use ('Lakers') match several eras and return None.
    """
    from ingestion.team_identity import COLLOQUIAL_NICKNAMES, ERAS, _norm

    phrases = {_norm(p) for p in _candidates(question)}
    # "Sonics" has to reach the era published as "SuperSonics".
    phrases |= {
        _norm(canonical)
        for alias, canonical in COLLOQUIAL_NICKNAMES.items()
        if _norm(alias) in phrases
    }

    # A full name ("Vancouver Grizzlies") pins one era; the bare nickname ("Grizzlies")
    # belongs to both the Vancouver and Memphis eras and pins nothing. Check the
    # specific form first so the general one cannot drown it out.
    full = [era for era in ERAS if _norm(era.full_name) in phrases]
    if len(full) == 1:
        return full[0]

    hits = [era for era in ERAS if _norm(era.nickname) in phrases]
    if len(hits) == 1:
        return hits[0]
    return None


def _has_team_scope(plan) -> bool:
    if getattr(plan, "entity_type", None) == "team" and getattr(plan, "entities", None):
        return True
    for f in getattr(plan, "row_filters", None) or []:
        col = str(f.get("column") or "").upper()
        if col.startswith("TEAM") or col == "TEAMID":
            return True
    return False


def apply_retired_era_seasons(plan, question: str) -> bool:
    """Pin the season window a retired franchise name implies.

    "Who was the best player on the Bobcats?" carries no year, and the tricode CHA
    belongs to both the Bobcats (2004-05..2013-14) and the Hornets who took it over in
    2014-15 — so a CHA filter alone answered with LaMelo Ball. The name itself is the
    date: nobody has been a Bobcat since 2014.

    Runs whether or not the plan already has a team filter, because the router usually
    gets the tricode right and the season wrong.
    """
    if getattr(plan, "season_from", None) or getattr(plan, "season_to", None):
        return False
    era = era_for_alias(question)
    if era is None or not (era.seasons_from or era.seasons_until):
        return False
    plan.season_from = era.seasons_from
    plan.season_to = era.seasons_until
    logger.info(
        "Scoped to the %s era: %s..%s", era.full_name, plan.season_from, plan.season_to
    )
    return True


def ensure_team_scope(plan, question: str) -> bool:
    """Re-attach a team filter the router dropped. Returns True if the plan changed."""
    from Interpreter.router_plan import resolve_column, table_has_column

    changed = apply_retired_era_seasons(plan, question)

    table = getattr(plan, "table", None)
    if not table or getattr(plan, "entity_type", None) != "player":
        return changed
    # A question about a NAMED player is already as scoped as it gets. Adding a team
    # filter on top can only remove their row — which is exactly what happened when a
    # false tricode match put Curry's question behind a Washington filter.
    if getattr(plan, "entities", None):
        return changed
    if _has_team_scope(plan):
        return changed

    season = getattr(plan, "season_from", None) or getattr(plan, "season_to", None)
    tid, identity = team_named_in(question, season)
    if tid is None:
        return changed

    column = next(
        (resolve_column(table, c) for c in _TEAM_FILTER_COLUMNS if table_has_column(table, c)),
        None,
    )
    if not column:
        logger.info(
            "Team %s named in the question but %s has no team column — plan unchanged",
            tid, table,
        )
        return changed

    value: object = tid if column.upper() in ("TEAM_ID", "TEAMID") else (
        identity.tricode if identity else None
    )
    if value is None:
        logger.info(
            "Team %s named but no era-specific tricode without a season — plan unchanged",
            tid,
        )
        return changed

    plan.row_filters = list(plan.row_filters or []) + [
        {"column": column, "op": "eq", "value": value}
    ]
    logger.info("Team scope restored: %s = %s on %s", column, value, table)
    return True


def correct_team_era_name(plan, question: str) -> bool:
    """Rewrite a team entity to the name that franchise used in the asked-for season.

    "How did the Charlotte Hornets do in 2010-11?" returns nothing, because in 2010-11
    Charlotte were the BOBCATS and the Hornets were in New Orleans. The franchise id is
    the same across the rename, so the season decides the name — exactly the mapping
    `team_identity` exists for. Rewriting the entity answers the question the user
    meant instead of reporting an empty slice.

    Only fires when the id resolves AND the era name differs from what was typed, so a
    correctly-named team is never touched.
    """
    if getattr(plan, "entity_type", None) != "team":
        return False
    entities = list(getattr(plan, "entities", None) or [])
    if not entities:
        return False
    season = getattr(plan, "season_from", None) or getattr(plan, "season_to", None)
    if not season:
        return False

    from ingestion.team_identity import ALIAS_TO_ID, _norm, identity_for_id

    changed = False
    rewritten: list[str] = []
    for name in entities:
        tid = ALIAS_TO_ID.get(_norm(name))
        identity = identity_for_id(tid, season) if tid is not None else None
        if identity and _norm(identity.full_name) != _norm(name):
            logger.info(
                "Era name correction for %s: %s -> %s", season, name, identity.full_name
            )
            rewritten.append(identity.full_name)
            changed = True
        else:
            rewritten.append(name)

    if changed:
        plan.entities = rewritten
    return changed
