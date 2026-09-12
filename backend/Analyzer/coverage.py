"""Flag players whose vault rows are only part of their career.

The vault starts at 1996-97. For anyone who debuted before that, "career" numbers read
from it are a tail, not a career — and nothing in the rows says so, because every row
present is real. The analyst duly reported *"Michael Jordan: 25.5 points"* in a career
comparison against LeBron. That is Jordan's 1996-97 onward, which is his last four
seasons including the two Wizards years. His actual career average is 30.1.

The prompt asks the model to caveat this. It does not reliably, and a silent 5-point
error on the most famous average in the sport is not something to leave to sampling.
`player_bio.FROM_YEAR` is the player's real first NBA season, so the check is exact:
FROM_YEAR < 1996 means the rows are truncated, full stop.
"""
from __future__ import annotations

import logging
import unicodedata

logger = logging.getLogger(__name__)

VAULT_FIRST_SEASON_START = 1996
VAULT_FIRST_SEASON = "1996-97"


def _fold(value: str) -> str:
    """Drop diacritics so 'Dončić' matches the folded column."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _debut_years(names: list[str]) -> dict[str, int]:
    """Map each name to the year they entered the NBA, per `player_bio.FROM_YEAR`."""
    if not names:
        return {}
    try:
        from Executer.data_backend import get_connection
        from Executer.duckdb_store import execute_query

        # Entities reaching the analyst are already canonical vault names, so an exact
        # accent-folded match is right — and it cannot match the wrong player, which a
        # substring match could.
        folded = ", ".join(
            "'" + _fold(n).replace("'", "''") + "'" for n in names if n and n.strip()
        )
        if not folded:
            return {}
        df = execute_query(
            get_connection(),
            f"""
            SELECT DISPLAY_FIRST_LAST AS name,
                   TRY_CAST(FROM_YEAR AS INTEGER) AS from_year
            FROM player_bio
            WHERE strip_accents(DISPLAY_FIRST_LAST) IN ({folded})
            """,
        )
        return {
            str(r["name"]): int(r["from_year"])
            for _, r in df.iterrows()
            if r.get("from_year") is not None and str(r["from_year"]).strip() != ""
        }
    except Exception as exc:  # noqa: BLE001 — a caveat is never worth failing a query over
        logger.debug("Debut-year lookup failed: %s", exc)
        return {}


def truncated_career_note(entities: list[str], season_from: str | None) -> str | None:
    """A hard instruction naming any subject whose career predates the vault.

    Only fires when the question is career-scoped (no explicit start season) — asking
    about Jordan in 1997-98 is a complete answer and needs no caveat.
    """
    if season_from or not entities:
        return None

    debuts = _debut_years(entities)
    truncated = {
        name: year for name, year in debuts.items() if year < VAULT_FIRST_SEASON_START
    }
    if not truncated:
        return None

    parts = [
        f"{name} (first NBA season {year}-{str(year + 1)[-2:]})"
        for name, year in sorted(truncated.items())
    ]
    logger.info("Truncated-career caveat for: %s", ", ".join(truncated))
    return (
        "COVERAGE WARNING — these rows do NOT cover a full career: "
        + "; ".join(parts)
        + f". The vault starts at {VAULT_FIRST_SEASON}, so every figure for them here "
        "is a PARTIAL career covering that season onward only. You MUST say so in the "
        "answer, and you must not call any of their numbers a career average or a "
        "career total.\n"
    )
