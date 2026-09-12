"""Canonical team city / nickname / tricode, keyed on team id AND season.

The vault carries two naming conventions and they disagree:

* full-name tables (`team_season_stats.TEAM_NAME`) held "LA Clippers"
* split tables (`team_standings`) hold TeamCity="LA", TeamName="Clippers"
* `game_context` held BOTH "Los Angeles Clippers" and "LA Clippers" for the same
  `teamId` (1610612746), in the same column, in the same table

That inconsistency is what made "How did the Lakers do in 2023-24?" return nothing:
the router expanded "Lakers" to "Los Angeles Lakers" and matched it against a column
that only ever holds "Lakers".

**Season is part of the key, not an optional extra.** A franchise keeps its `TEAM_ID`
across relocations and rebrands, so id alone is not enough to name it. Resolving the
Sonics by id gives "Oklahoma City Thunder" — the same row, silently falsified.

Worse, some ids carry THREE identities, so a single "last correct season" cutoff is
also not enough. `1610612766` is the original Charlotte Hornets (1996-97..2001-02),
then the Bobcats (2004-05..2013-14), then the Hornets again (2014-15..). A cutoff-only
model rewrites the 1990s Hornets into Bobcats. Hence explicit `seasons_from`/`seasons_until`
ranges, derived from what the vault actually contains rather than from memory.

Scope note: of the seven franchises with multiple identities, exactly ONE is wrong in
the data — the Clippers, stored as "LA Clippers" from 2015-16 on. Everything else is
correct for its era and is left untouched.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamIdentity:
    team_id: int
    city: str
    nickname: str
    tricode: str
    seasons_from: str | None = None   # first season this identity was correct
    seasons_until: str | None = None  # last season this identity was correct

    @property
    def full_name(self) -> str:
        return f"{self.city} {self.nickname}"

    def covers(self, season: str) -> bool:
        if self.seasons_from and season < self.seasons_from:
            return False
        if self.seasons_until and season > self.seasons_until:
            return False
        return True

    @property
    def _span(self) -> int:
        """Length of the era in seasons. Narrower wins, so a nested era beats its parent.

        The Hornets' 2005-07 Oklahoma City displacement sits inside their New Orleans
        era, and both match those two seasons — the shorter range is the right answer.
        Open-ended eras score high so a bounded range always beats them.
        """
        if not (self.seasons_from and self.seasons_until):
            return 10_000
        try:
            return int(self.seasons_until[:4]) - int(self.seasons_from[:4])
        except ValueError:
            return 10_000


# Franchises whose identity never changed across the vault's span (1996-97 → 2025-26).
CURRENT: tuple[TeamIdentity, ...] = (
    TeamIdentity(1610612737, "Atlanta", "Hawks", "ATL"),
    TeamIdentity(1610612738, "Boston", "Celtics", "BOS"),
    TeamIdentity(1610612741, "Chicago", "Bulls", "CHI"),
    TeamIdentity(1610612739, "Cleveland", "Cavaliers", "CLE"),
    TeamIdentity(1610612742, "Dallas", "Mavericks", "DAL"),
    TeamIdentity(1610612743, "Denver", "Nuggets", "DEN"),
    TeamIdentity(1610612765, "Detroit", "Pistons", "DET"),
    TeamIdentity(1610612744, "Golden State", "Warriors", "GSW"),
    TeamIdentity(1610612745, "Houston", "Rockets", "HOU"),
    TeamIdentity(1610612754, "Indiana", "Pacers", "IND"),
    TeamIdentity(1610612747, "Los Angeles", "Lakers", "LAL"),
    TeamIdentity(1610612748, "Miami", "Heat", "MIA"),
    TeamIdentity(1610612749, "Milwaukee", "Bucks", "MIL"),
    TeamIdentity(1610612750, "Minnesota", "Timberwolves", "MIN"),
    TeamIdentity(1610612752, "New York", "Knicks", "NYK"),
    TeamIdentity(1610612753, "Orlando", "Magic", "ORL"),
    TeamIdentity(1610612755, "Philadelphia", "76ers", "PHI"),
    TeamIdentity(1610612756, "Phoenix", "Suns", "PHX"),
    TeamIdentity(1610612757, "Portland", "Trail Blazers", "POR"),
    TeamIdentity(1610612758, "Sacramento", "Kings", "SAC"),
    TeamIdentity(1610612759, "San Antonio", "Spurs", "SAS"),
    TeamIdentity(1610612761, "Toronto", "Raptors", "TOR"),
    TeamIdentity(1610612762, "Utah", "Jazz", "UTA"),
)

# Franchises with more than one identity across the vault's span. Ranges are taken
# from the seasons the data actually contains, not from recollection.
#
# The ONLY correction any of these encodes is the Clippers: both eras resolve to
# "Los Angeles Clippers", which rewrites the 2015-16+ "LA Clippers" spelling. Every
# other entry exists so its era is recognised and therefore left alone.
ERAS: tuple[TeamIdentity, ...] = (
    # New Orleans — the 2005-07 Oklahoma City displacement is nested inside the
    # Hornets era, so it must win on specificity.
    TeamIdentity(1610612740, "New Orleans", "Hornets", "NOH", "2002-03", "2012-13"),
    TeamIdentity(1610612740, "New Orleans/Oklahoma City", "Hornets", "NOK", "2005-06", "2006-07"),
    TeamIdentity(1610612740, "New Orleans", "Pelicans", "NOP", "2013-14", None),
    # Clippers — the one genuine defect. Both eras canonicalise to the spelled-out city.
    TeamIdentity(1610612746, "Los Angeles", "Clippers", "LAC", None, "2014-15"),
    TeamIdentity(1610612746, "Los Angeles", "Clippers", "LAC", "2015-16", None),
    # Nets
    TeamIdentity(1610612751, "New Jersey", "Nets", "NJN", None, "2011-12"),
    TeamIdentity(1610612751, "Brooklyn", "Nets", "BKN", "2012-13", None),
    # Sonics / Thunder
    TeamIdentity(1610612760, "Seattle", "SuperSonics", "SEA", None, "2007-08"),
    TeamIdentity(1610612760, "Oklahoma City", "Thunder", "OKC", "2008-09", None),
    # Grizzlies
    TeamIdentity(1610612763, "Vancouver", "Grizzlies", "VAN", None, "2000-01"),
    TeamIdentity(1610612763, "Memphis", "Grizzlies", "MEM", "2001-02", None),
    # Bullets / Wizards
    TeamIdentity(1610612764, "Washington", "Bullets", "WAS", None, "1996-97"),
    TeamIdentity(1610612764, "Washington", "Wizards", "WAS", "1997-98", None),
    # Charlotte — three identities on one id, and the reason a cutoff-only model fails.
    TeamIdentity(1610612766, "Charlotte", "Hornets", "CHH", None, "2001-02"),
    TeamIdentity(1610612766, "Charlotte", "Bobcats", "CHA", "2004-05", "2013-14"),
    TeamIdentity(1610612766, "Charlotte", "Hornets", "CHA", "2014-15", None),
)

BY_ID: dict[int, TeamIdentity] = {t.team_id: t for t in CURRENT}

_ERAS_BY_ID: dict[int, list[TeamIdentity]] = {}
for _e in ERAS:
    _ERAS_BY_ID.setdefault(_e.team_id, []).append(_e)


def _norm(v: str) -> str:
    return " ".join(str(v or "").lower().replace(".", "").split())


ALIAS_TO_ID: dict[str, int] = {}
for _t in CURRENT + ERAS:
    for _alias in (_t.full_name, _t.nickname, _t.tricode):
        ALIAS_TO_ID.setdefault(_norm(_alias), _t.team_id)
# What people actually type. The published nickname is "SuperSonics" and "Trail
# Blazers"; nobody writes either. Read-only additions — they map a name to an id and
# never take part in normalising a stored row, so era ranges are untouched.
COLLOQUIAL_NICKNAMES: dict[str, str] = {
    "sonics": "SuperSonics",
    "blazers": "Trail Blazers",
    "wolves": "Timberwolves",
    "cavs": "Cavaliers",
    "mavs": "Mavericks",
    "sixers": "76ers",
    "dubs": "Warriors",
    "wizzards": "Wizards",
}

for _alias, _tid in {
    "la clippers": 1610612746,
    "la lakers": 1610612747,
    "golden state": 1610612744,
    "sixers": 1610612755,
    "sonics": 1610612760,
    "seattle sonics": 1610612760,
    "blazers": 1610612757,
    "wolves": 1610612750,
    "cavs": 1610612739,
    "mavs": 1610612742,
    "dubs": 1610612744,
}.items():
    ALIAS_TO_ID[_norm(_alias)] = _tid


def identity_for_id(
    team_id: int | float | str | None, season: str | None = None
) -> TeamIdentity | None:
    """Canonical identity for a franchise in a given season.

    Returns None when `season` is absent and the franchise has had more than one
    identity — guessing there is what rewrote the Sonics into the Thunder. Callers
    that cannot supply a season should not be normalising those rows at all.
    """
    try:
        tid = int(team_id)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

    eras = _ERAS_BY_ID.get(tid)
    if eras:
        if not season:
            return None  # ambiguous without a season — refuse rather than guess
        matches = [e for e in eras if e.covers(str(season))]
        if not matches:
            return None
        return min(matches, key=lambda e: e._span)  # narrowest range wins

    return BY_ID.get(tid)


def identity_for_name(name: str | None, season: str | None = None) -> TeamIdentity | None:
    tid = ALIAS_TO_ID.get(_norm(name or ""))
    return identity_for_id(tid, season) if tid else None


def canonical_full_name(team_id=None, name: str | None = None, season: str | None = None) -> str | None:
    ident = identity_for_id(team_id, season) or identity_for_name(name, season)
    return ident.full_name if ident else None
