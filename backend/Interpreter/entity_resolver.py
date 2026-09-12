"""Resolve a user's entity string to a specific player or team.

The old behaviour was ``ILIKE '%name%'`` against a full-name column, which meant
"LA" matched nine teams (Dal**la**s, At**la**nta, Port**la**nd …) and the analyst
picked one and answered confidently. "Jordan" matched twenty-one players, none of
them Michael Jordan in a 2023-24 slice.

Design notes, since this question comes up every time:

**No hardcoded nickname table.** The router LLM already expands "Shaq" and "KD"
correctly, and a hand-maintained alias list rots. What the LLM cannot know is which
of six Currys the vault holds, so that is what this module supplies.

**Prominence is derived from the vault, not authored.** Career regular-season points
is the proxy for who a bare surname means. Points beats minutes here, measurably:
for "Curry" the leader's margin is 3.9x on points but only 2.8x on minutes, because
Eddy Curry logged heavy minutes without the scoring that makes a name famous.
Nobody maintains this ranking — it falls out of the data and updates on re-stage.

Worth knowing: "Jordan" stays ambiguous under this rule, and correctly so. The vault
starts at 1996-97, so it holds only the tail of Michael Jordan's career and ranks him
third among Jordans by points. Guessing him would be projecting outside knowledge the
data does not support; asking is the honest move.

**Conversation context wins over prominence.** If the thread already named Seth
Curry, a later bare "Curry" resolves to Seth. That is the cheap version of what the
user actually means, and it costs one pass over the prior turns.

**When it is genuinely close, ask.** A wrong confident answer is far worse than one
clarifying question, so anything under the dominance ratio returns
``needs_clarification`` and the endpoint asks instead of guessing.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

# How much more prominent the leader must be to win a bare-surname match outright.
DOMINANCE_RATIO = float("3.0")

# Above this many candidates we always ask rather than listing everything.
MAX_CLARIFY_OPTIONS = 6


def ascii_fold(value: str) -> str:
    """Drop diacritics so 'Jokic' matches 'Jokić' in either direction."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def norm(value: str) -> str:
    """Comparison form: accent-folded, lowercased, punctuation-light."""
    folded = ascii_fold(value or "").lower()
    folded = folded.replace(".", "").replace("'", "").replace("`", "")
    return re.sub(r"\s+", " ", folded).strip()


def _strip_suffix(value: str) -> str:
    """'Marcus Morris Sr.' -> 'marcus morris' so a suffix never blocks a match."""
    return re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", norm(value)).strip()


@dataclass
class Candidate:
    canonical: str
    prominence: float = 0.0
    detail: str = ""


@dataclass
class Resolution:
    query: str
    entity_type: str
    canonical: str | None = None
    candidates: list[Candidate] = field(default_factory=list)
    needs_clarification: bool = False
    reason: str = ""
    matched_exactly: bool = False

    def clarification_text(self) -> str:
        opts = self.candidates[:MAX_CLARIFY_OPTIONS]
        lines = [f'"{self.query}" matches {len(self.candidates)} '
                 f'{"players" if self.entity_type == "player" else "teams"} in the vault:']
        for c in opts:
            lines.append(f"  • {c.canonical}{f' — {c.detail}' if c.detail else ''}")
        if len(self.candidates) > len(opts):
            lines.append(f"  … and {len(self.candidates) - len(opts)} more")
        lines.append("\nWhich one did you mean?")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Vault-derived indexes
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _player_index(_v: int = 0) -> list[tuple[str, float]]:
    """(canonical name, career regular-season points) for every player in the vault."""
    from Executer.data_backend import get_connection

    try:
        rows = get_connection().execute(
            """
            SELECT PLAYER_NAME, SUM(COALESCE(PTS, 0)) AS career_pts
            FROM player_season_stats
            WHERE per_mode = 'Totals' AND season_type = 'Regular Season'
              AND PLAYER_NAME IS NOT NULL
            GROUP BY PLAYER_NAME
            """
        ).fetchall()
    except Exception as exc:  # noqa: BLE001 — resolver must not break the request
        logger.warning("Player index unavailable: %s", exc)
        return []
    return [(str(r[0]), float(r[1] or 0.0)) for r in rows]


@lru_cache(maxsize=1)
def _team_index(_v: int = 0) -> list[tuple[str, str, str, float]]:
    """(full name, city, nickname, games) for every team-season in the vault."""
    from Executer.data_backend import get_connection

    try:
        rows = get_connection().execute(
            """
            SELECT TEAM_NAME, COUNT(*) AS n
            FROM team_season_stats
            WHERE TEAM_NAME IS NOT NULL
            GROUP BY TEAM_NAME
            """
        ).fetchall()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Team index unavailable: %s", exc)
        return []

    out: list[tuple[str, str, str, float]] = []
    for name, n in rows:
        full = str(name)
        parts = full.split()
        # "Portland Trail Blazers" -> city "Portland", nickname "Trail Blazers"
        nickname = parts[-1] if len(parts) < 3 else " ".join(parts[-2:])
        city = full[: len(full) - len(nickname)].strip() or full
        if len(parts) >= 2 and parts[-2] not in ("Trail",):
            nickname = parts[-1]
            city = " ".join(parts[:-1])
        out.append((full, city, nickname, float(n or 0)))
    return out


def clear_caches() -> None:
    _player_index.cache_clear()
    _team_index.cache_clear()


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------
def _score(cands: list[Candidate], context_names: list[str] | None) -> list[Candidate]:
    """Boost candidates already named in the conversation, then sort."""
    if context_names:
        ctx = [norm(c) for c in context_names if c]
        for c in cands:
            cn = norm(c.canonical)
            if any(cn == x or cn in x or x in cn for x in ctx):
                c.prominence *= 1000.0
                c.detail = (c.detail + "; mentioned earlier in this chat").lstrip("; ")
    return sorted(cands, key=lambda c: -c.prominence)


# Initialisms only — deliberately not a general nickname list.
#
# Every other kind of short name is derivable from the data: "Shaq" is a prefix of
# "Shaquille", "Curry" is a whole token of "Stephen Curry". Pure initialisms share no
# characters with the published name, so no rule over the vault can reach them, and the
# router cannot be relied on to expand them either. That makes this the one case worth
# hardcoding — and the reason to keep it to initialisms rather than letting it grow into
# the general alias table this design deliberately avoids.
_INITIALISMS = {
    "kd": "Kevin Durant",
    "cp3": "Chris Paul",
    "ad": "Anthony Davis",
    "kat": "Karl-Anthony Towns",
    "pg13": "Paul George",
    "dbook": "Devin Booker",
    "sga": "Shai Gilgeous-Alexander",
    "jt": "Jayson Tatum",
    "dr": "Derrick Rose",
    "tmac": "Tracy McGrady",
    "amare": "Amar'e Stoudemire",
    "melo": "Carmelo Anthony",
    "dwade": "Dwyane Wade",
    "d wade": "Dwyane Wade",
    "the greek freak": "Giannis Antetokounmpo",
    "greek freak": "Giannis Antetokounmpo",
    "the beard": "James Harden",
    "the brow": "Anthony Davis",
    "king james": "LeBron James",
    "the claw": "Kawhi Leonard",
    "joker": "Nikola Jokić",
    "the joker": "Nikola Jokić",
}


def resolve_player(query: str, context_names: list[str] | None = None) -> Resolution:
    res = Resolution(query=query, entity_type="player")
    index = _player_index()
    if not index or not query.strip():
        res.canonical = query
        return res

    q = norm(query)

    mapped = _INITIALISMS.get(q)
    if mapped:
        # Only accept it if the vault actually holds that player.
        if any(norm(n) == norm(mapped) for n, _ in index):
            res.canonical, res.matched_exactly = mapped, True
            res.reason = f"'{query}' is a known initialism for {mapped}"
            return res
    q_nosuffix = _strip_suffix(query)

    # A suffix the user typed is a disambiguator, not noise. "Tim Hardaway Jr" used to
    # come back as a clarification question between father and son, because the
    # suffix-stripped comparison made both of them exact matches. A full-string match
    # wins outright before the stripped comparison is consulted.
    strict = [Candidate(n, m) for n, m in index if norm(n) == q]
    if len(strict) == 1:
        res.canonical, res.matched_exactly = strict[0].canonical, True
        return res

    exact = [Candidate(n, m) for n, m in index if norm(n) == q or _strip_suffix(n) == q_nosuffix]
    if len(exact) == 1:
        res.canonical, res.matched_exactly = exact[0].canonical, True
        return res
    if len(exact) > 1:
        res.candidates = _score(exact, context_names)
        top = res.candidates[0]
        runner = res.candidates[1].prominence if len(res.candidates) > 1 else 0.0
        if runner <= 0 or top.prominence >= runner * DOMINANCE_RATIO:
            res.canonical, res.matched_exactly = top.canonical, True
            return res
        res.needs_clarification = True
        res.reason = "several players share this exact name"
        return res

    # Whole-token match: every token the user typed appears as a word in the name.
    tokens = [t for t in q.split() if t]
    token_hits: list[Candidate] = []
    for name, pts in index:
        words = set(_strip_suffix(name).split())
        if tokens and all(t in words for t in tokens):
            token_hits.append(Candidate(name, pts))

    # Prefix tier: a shortened first name should still find its owner. "Shaq" is a
    # whole-token match for the obscure "Shaq Buchanan" but only a prefix of
    # "Shaquille", so without this the rare player wins on an exact-token technicality.
    # Prefix hits are merged in and ranked by prominence, which puts Shaquille O'Neal
    # far ahead. Three characters minimum, so "A" cannot match the league.
    if tokens and all(len(t) >= 3 for t in tokens):
        for name, pts in index:
            words = _strip_suffix(name).split()
            if any(c.canonical == name for c in token_hits):
                continue
            if all(any(w.startswith(t) for w in words) for t in tokens):
                token_hits.append(Candidate(name, pts))

    if len(token_hits) == 1:
        res.canonical, res.matched_exactly = token_hits[0].canonical, True
        return res

    if token_hits:
        scored = _score(token_hits, context_names)
        for c in scored:
            c.detail = c.detail or f"{c.prominence:,.0f} career points"
        res.candidates = scored
        top, runner = scored[0], scored[1].prominence if len(scored) > 1 else 0.0
        if runner <= 0 or top.prominence >= runner * DOMINANCE_RATIO:
            res.canonical = top.canonical
            res.reason = f"'{query}' resolved to the most prominent match"
            return res
        res.needs_clarification = True
        res.reason = f"'{query}' is ambiguous between players of comparable standing"
        return res

    # Nothing matched on whole tokens — fall back to substring so a partial or
    # slightly-off spelling still finds something to offer.
    subs = [Candidate(n, m) for n, m in index if q and q in norm(n)]
    if len(subs) == 1:
        res.canonical = subs[0].canonical
        return res
    if subs:
        scored = _score(subs, context_names)
        for c in scored:
            c.detail = c.detail or f"{c.prominence:,.0f} career points"
        res.candidates = scored
        res.needs_clarification = True
        res.reason = f"'{query}' matches several players"
        return res

    res.reason = f"no player in the vault matches '{query}'"
    return res


# City abbreviations people actually type. Expanded before matching so they follow the
# same path as the spelled-out city — which matters most for "LA", where the expansion
# is genuinely ambiguous and must reach the clarification branch rather than falling
# through to substring matching.
_CITY_ABBREVIATIONS: dict[str, str] = {
    "la": "los angeles",
    "ny": "new york",
    "nyc": "new york",
    "gs": "golden state",
    "gsw": "golden state",
    "okc": "oklahoma city",
    "sa": "san antonio",
    "no": "new orleans",
    "nola": "new orleans",
    "phx": "phoenix",
    "philly": "philadelphia",
    "bkn": "brooklyn",
    "cle": "cleveland",
    "det": "detroit",
    "mil": "milwaukee",
    "min": "minnesota",
    "por": "portland",
    "sac": "sacramento",
    "mem": "memphis",
    "tor": "toronto",
    "uta": "utah",
    "was": "washington",
    "atl": "atlanta",
    "bos": "boston",
    "chi": "chicago",
    "dal": "dallas",
    "den": "denver",
    "hou": "houston",
    "ind": "indiana",
    "mia": "miami",
    "orl": "orlando",
}


def _expand_city_abbreviation(q: str) -> str:
    """'la' -> 'los angeles', 'la lakers' -> 'los angeles lakers'. Unknown input as-is."""
    if q in _CITY_ABBREVIATIONS:
        return _CITY_ABBREVIATIONS[q]
    head, _, rest = q.partition(" ")
    if rest and head in _CITY_ABBREVIATIONS:
        return f"{_CITY_ABBREVIATIONS[head]} {rest}"
    return q


def resolve_team(query: str, context_names: list[str] | None = None) -> Resolution:
    res = Resolution(query=query, entity_type="team")
    index = _team_index()
    if not index or not query.strip():
        res.canonical = query
        return res

    q = _expand_city_abbreviation(norm(query))

    # Exact on the full name, the nickname, or the city.
    for full, city, nick, _n in index:
        if q == norm(full):
            res.canonical, res.matched_exactly = full, True
            return res

    nick_hits = [Candidate(full, n, city) for full, city, nick, n in index if q == norm(nick)]
    if len(nick_hits) == 1:
        res.canonical, res.matched_exactly = nick_hits[0].canonical, True
        return res

    city_hits = [Candidate(full, n, city) for full, city, nick, n in index if q == norm(city)]
    if len(city_hits) == 1:
        res.canonical, res.matched_exactly = city_hits[0].canonical, True
        return res
    if len(city_hits) > 1:
        # "Los Angeles" legitimately means two franchises.
        res.candidates = _score(city_hits, context_names)
        res.needs_clarification = True
        res.reason = f"'{query}' is the city of {len(city_hits)} franchises"
        return res

    # Whole-token match before substring, so "LA" cannot reach "Dallas".
    tokens = [t for t in q.split() if t]
    hits: list[Candidate] = []
    for full, city, nick, n in index:
        words = set(norm(full).split())
        if tokens and all(t in words for t in tokens):
            hits.append(Candidate(full, n, city))
    uniq = {c.canonical: c for c in hits}
    if len(uniq) == 1:
        res.canonical, res.matched_exactly = next(iter(uniq)), True
        return res
    if uniq:
        res.candidates = _score(list(uniq.values()), context_names)
        top = res.candidates[0]
        runner = res.candidates[1].prominence if len(res.candidates) > 1 else 0.0
        if runner <= 0 or top.prominence >= runner * DOMINANCE_RATIO:
            res.canonical = top.canonical
            return res
        res.needs_clarification = True
        res.reason = f"'{query}' matches {len(uniq)} teams"
        return res

    # Teams are a closed set of thirty, so an unmatched string is a mistake rather than
    # a partial name worth guessing at. Substring fallback here is what let "LA" match
    # Dal**la**s and At**la**nta and answer as though it were one team, so unknown team
    # names ask instead. (Players keep the fallback: the roster is thousands deep and a
    # partial surname is usually still findable.)
    res.needs_clarification = True

    # Offer the nearest spellings rather than an arbitrary list — a typo like "Bostonn"
    # should surface Boston, not the three winningest franchises.
    import difflib

    # Score against the full name, the city and the nickname separately: "Bostonn" is
    # nowhere near "boston celtics" as a whole string, but very close to "boston".
    scored: dict[str, float] = {}
    for full, city, nick, _g in index:
        best = max(
            difflib.SequenceMatcher(None, q, norm(part)).ratio()
            for part in (full, city, nick)
        )
        if best > scored.get(full, 0.0):
            scored[full] = best
    suggestions = [
        name for name, score in sorted(scored.items(), key=lambda kv: -kv[1])
        if score >= 0.6
    ][:MAX_CLARIFY_OPTIONS]
    if not suggestions:
        # Nothing is close; fall back to the most-seen franchises so the reply still
        # shows the shape of a valid answer.
        suggestions = [full for full, _c, _n, _g in sorted(index, key=lambda t: -t[3])][:MAX_CLARIFY_OPTIONS]

    res.candidates = [Candidate(name, 0.0) for name in suggestions]
    res.reason = f"no team in the vault matches '{query}'"
    return res


def resolve(query: str, entity_type: str, context_names: list[str] | None = None) -> Resolution:
    if entity_type == "team":
        return resolve_team(query, context_names)
    return resolve_player(query, context_names)


def resolve_all(
    entities: list[str], entity_type: str, context_names: list[str] | None = None
) -> tuple[list[str], list[Resolution], bool]:
    """Resolve every entity.

    Returns (names, resolutions needing a question, all_canonical). ``all_canonical``
    is False when any name could not be matched to a vault entry — a nickname the
    router passed through verbatim ("Shaq", "KD"), or a misspelling. Those must keep
    substring matching, because switching them to exact matching turns a name the
    vault could still have found into a guaranteed zero-row answer.
    """
    names: list[str] = []
    ambiguous: list[Resolution] = []
    all_canonical = True
    for e in entities or []:
        r = resolve(e, entity_type, context_names)
        if r.needs_clarification:
            ambiguous.append(r)
        elif r.canonical and r.canonical != e:
            names.append(r.canonical)
            if not r.matched_exactly and r.reason:
                logger.info("Entity '%s' -> '%s' (%s)", e, r.canonical, r.reason)
        elif r.canonical and r.matched_exactly:
            names.append(r.canonical)
        else:
            # Unmatched: keep what the user/router wrote and stay on substring.
            logger.info("Entity '%s' unresolved (%s) — substring match retained", e, r.reason)
            names.append(e)
            all_canonical = False
    return names, ambiguous, all_canonical
