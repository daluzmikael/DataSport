"""Work out WHY a query matched nothing, and say so specifically.

Every empty result used to produce the same paragraph — "No data was found for this
query. This could mean: the player or team did not appear in the requested season…" —
regardless of whether the season was outside the vault, the stat was never tracked that
far back, the name was misspelled, or the table simply has no playoff rows.

The system knows which it is. Each filter in the plan is dropped one at a time and
re-counted; whichever one is responsible for the zero is the answer.

Returns both a machine-readable retry hint (fed back into the router for one
reassessment) and a plain sentence for the user.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from Interpreter.router_plan import RouterPlan, table_has_column

logger = logging.getLogger(__name__)


@dataclass
class EmptyDiagnosis:
    summary: str                 # for the log
    user_message: str            # shown to the user
    retry_hint: str | None = None  # fed to the router for one reassessment


def _count(conn, table: str, where: list[str]) -> int:
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    try:
        row = conn.execute(sql).fetchone()
        return int(row[0]) if row else 0
    except Exception as exc:  # noqa: BLE001
        logger.debug("Empty-result probe failed: %s", exc)
        return -1


def _esc(v: str) -> str:
    return str(v).replace("'", "''")


def diagnose_empty_result(plan: RouterPlan, conn: Any) -> EmptyDiagnosis:
    """Drop one filter at a time to find which one emptied the result."""
    table = plan.table
    if not table:
        return EmptyDiagnosis("no table on plan", "I couldn't work out which table to read for that question.")

    per_mode = (plan.per_modes or ["PerGame"])[0]

    # Build the filters that the SQL used, each tagged so we can name the culprit.
    filters: list[tuple[str, str, str]] = []  # (tag, sql, human description)

    if plan.season_from or plan.season_to:
        if table_has_column(table, "season", conn):
            lo = plan.season_from or plan.season_to
            hi = plan.season_to or plan.season_from
            clause = (f"season = '{_esc(lo)}'" if lo == hi
                      else f"season >= '{_esc(lo)}' AND season <= '{_esc(hi)}'")
            filters.append(("season", clause, f"season {plan.season_label()}"))

    if table_has_column(table, "season_type", conn):
        filters.append(("season_type", f"season_type = '{_esc(plan.season_type)}'",
                        plan.season_type.lower()))

    if table_has_column(table, "per_mode", conn):
        filters.append(("per_mode", f"per_mode = '{_esc(per_mode)}'", f"per_mode {per_mode}"))

    if plan.pt_measure_type and table_has_column(table, "pt_measure_type", conn):
        filters.append(("pt_measure_type",
                        f"pt_measure_type = '{_esc(plan.pt_measure_type)}'",
                        f"tracking slice {plan.pt_measure_type}"))

    if plan.measure_type and table_has_column(table, "measure_type", conn):
        filters.append(("measure_type", f"measure_type = '{_esc(plan.measure_type)}'",
                        f"measure type {plan.measure_type}"))

    entity_clause = None
    if plan.entities:
        from Interpreter.sql_builder import _entity_filter

        entity_clause = _entity_filter(plan, conn)
        if entity_clause:
            names = ", ".join(plan.entities)
            filters.append(("entity", entity_clause, f"name {names}"))

    all_clauses = [c for _, c, _ in filters]
    if _count(conn, table, all_clauses) > 0:
        return EmptyDiagnosis("filters match rows after all", "No data was found for that question.")

    # Which single filter is responsible? Drop each and see if rows come back.
    culprits: list[tuple[str, str]] = []
    for tag, clause, human in filters:
        others = [c for _, c, _ in filters if c != clause]
        if _count(conn, table, others) > 0:
            culprits.append((tag, human))

    # Nothing matched even one at a time — the combination is the problem.
    if not culprits:
        return EmptyDiagnosis(
            f"no rows on {table} for any single-filter relaxation",
            f"The vault has no rows in `{table}` matching that combination "
            f"({plan.season_label()}, {plan.season_type}).",
        )

    # Prefer the most specific explanation. A tracking question for 2005-06 empties on
    # BOTH season and pt_measure_type, but blaming the season is misleading — the table
    # does cover 2005-06, just not for that slice.
    priority = {"pt_measure_type": 0, "measure_type": 1, "per_mode": 2,
                "entity": 3, "season": 4, "season_type": 5}
    culprits.sort(key=lambda c: priority.get(c[0], 99))
    tag, human = culprits[0]

    if tag == "season":
        lo = _count(conn, table, []) and conn.execute(
            f"SELECT MIN(season), MAX(season) FROM {table}").fetchone()
        span = f"{lo[0]} to {lo[1]}" if lo else "unknown"
        return EmptyDiagnosis(
            f"season {plan.season_label()} outside {table} coverage ({span})",
            f"The vault doesn't cover {plan.season_label()} for that data — "
            f"`{table}` runs from {span}.",
            retry_hint=(
                f"The query returned 0 rows because season {plan.season_label()} is "
                f"outside the coverage of {table}, which spans {span}. If the question "
                f"can be answered from a season in range, pick it; otherwise set "
                f"supported=false with unsupported_reason "
                f"'STAT_NOT_IN_VAULT: no data for that season'."
            ),
        )

    if tag == "entity":
        detail = _entity_detail(conn, plan, filters, table)
        if detail is not None:
            return detail
        return EmptyDiagnosis(
            f"no rows for entity {plan.entities} on {table}",
            f"I couldn't find {', '.join(plan.entities)} in the vault for that slice. "
            f"The name may be spelled differently, or they may not have played then.",
            retry_hint=(
                f"The query returned 0 rows: no row on {table} matches "
                f"{plan.entities}. Check the entity is a real published NBA name and "
                f"that the table can be filtered by name; if the name is right, the "
                f"player may not exist in this season range."
            ),
        )

    if tag in ("pt_measure_type", "measure_type"):
        cov = []
        try:
            cov = conn.execute(
                f"SELECT MIN(season), MAX(season) FROM {table} WHERE {tag} = "
                f"'{_esc(plan.pt_measure_type or plan.measure_type)}'"
            ).fetchone()
        except Exception:  # noqa: BLE001
            pass
        span = f"{cov[0]} to {cov[1]}" if cov and cov[0] else "a narrower range"
        return EmptyDiagnosis(
            f"{human} not available for {plan.season_label()}",
            f"That data ({human}) isn't tracked for {plan.season_label()} — "
            f"it only covers {span}.",
            retry_hint=(
                f"0 rows: the {tag} '{plan.pt_measure_type or plan.measure_type}' on "
                f"{table} only covers {span}, not {plan.season_label()}. Either pick a "
                f"season in that range or set supported=false with "
                f"'STAT_NOT_IN_VAULT: not tracked in that season'."
            ),
        )

    if tag == "per_mode":
        available = [r[0] for r in conn.execute(
            f"SELECT DISTINCT per_mode FROM {table}").fetchall()]
        return EmptyDiagnosis(
            f"per_mode {per_mode} not staged on {table}",
            f"That per-mode isn't in the vault. `{table}` has: {', '.join(available)}.",
            retry_hint=(
                f"0 rows: per_mode '{per_mode}' does not exist on {table}. The only "
                f"values staged are {', '.join(available)}. Re-plan with one of those."
            ),
        )

    if tag == "season_type":
        return EmptyDiagnosis(
            f"{table} has no {plan.season_type} rows",
            f"`{table}` doesn't hold {plan.season_type} data.",
            retry_hint=(
                f"0 rows: {table} has no rows with season_type='{plan.season_type}'. "
                f"Use the season_type this table actually carries, or pick another table."
            ),
        )

    return EmptyDiagnosis(f"empty because of {human}", f"No data was found — {human} has no rows.")


# The vault's first season. A famous name that returns nothing is far more often a
# coverage boundary than a typo, and "the name may be spelled differently" sends the
# user off to re-check a spelling that was never wrong.
VAULT_FIRST_SEASON = "1996-97"


def _entity_detail(conn: Any, plan: RouterPlan, filters, table: str):
    """Say something specific about WHY this name has no rows in this slice.

    Three cases worth separating, in descending usefulness:

    1. A near-namesake DOES have rows here. "Gary Payton's stats in 2021-22" resolved
       to Gary Payton — correctly, he is the prominent one — and returned nothing,
       because the Gary Payton who played that season was Gary Payton II.
    2. The name is in the table, just not in this slice. Then the answer is the range
       of seasons it does appear in, not a spelling hint.
    3. The name is nowhere in the table. For anyone who played before 1996-97 that is
       a coverage boundary, and saying so is the whole answer.
    """
    from Interpreter.sql_builder import entity_name_column

    col = entity_name_column(plan, conn)
    if not col or not plan.entities:
        return None

    others = [c for tag, c, _ in filters if tag != "entity"]
    slice_where = (" AND " + " AND ".join(others)) if others else ""
    name = plan.entities[0]
    surname = name.strip().split()[-1] if name.strip() else ""

    def _rows(sql: str):
        try:
            return conn.execute(sql).fetchall()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Entity-detail probe failed: %s", exc)
            return []

    # 1. A different spelling of the SAME person, or a relative, present in this slice.
    # The first name has to match too. Matching on surname alone turned "What was Magic
    # Johnson's assist average?" into "did you mean Wesley Johnson, Nick Johnson?" —
    # they share a surname and nothing else, and Magic simply predates the vault.
    first = name.strip().split()[0] if name.strip() else ""
    if len(surname) >= 3 and len(first) >= 2:
        near = _rows(
            f"SELECT DISTINCT {col} FROM {table} "
            f"WHERE strip_accents({col}) ILIKE '{_esc(first)}%' "
            f"AND strip_accents({col}) ILIKE '%{_esc(surname)}%'{slice_where} LIMIT 6"
        )
        options = [str(r[0]) for r in near if str(r[0]).lower() != name.lower()]
        if options:
            listed = ", ".join(options[:4])
            return EmptyDiagnosis(
                f"{name} absent from slice; near matches present: {listed}",
                f"{name} has no rows for {plan.season_label()}. "
                f"The vault does have {listed} in that slice — did you mean one of them?",
                retry_hint=(
                    f"0 rows: '{name}' has no row on {table} for {plan.season_label()}, "
                    f"but these near-identical names do: {listed}. If one of them is who "
                    f"the question meant, re-plan with that exact name."
                ),
            )

    # 2. The name exists on this table, in other seasons.
    span = _rows(
        f"SELECT MIN(season), MAX(season) FROM {table} "
        f"WHERE strip_accents({col}) ILIKE '{_esc(name)}'"
    ) if table_has_column(table, "season", conn) else []
    if span and span[0] and span[0][0]:
        lo, hi = span[0][0], span[0][1]
        return EmptyDiagnosis(
            f"{name} present on {table} for {lo}..{hi}, not {plan.season_label()}",
            f"{name} is in the vault, but not for {plan.season_label()} — "
            f"their `{table}` rows run from {lo} to {hi}.",
            retry_hint=(
                f"0 rows: '{name}' exists on {table} but only for {lo}..{hi}, not "
                f"{plan.season_label()}. Re-plan inside that range, or set supported=false."
            ),
        )

    # 3. Not in this table at all. Could be a misspelling or could be a player who
    # predates the vault, and guessing wrong sends the user to fix the wrong thing —
    # so name both, and hand the router a hint so one reassessment can try a
    # corrected spelling before the user ever sees this.
    return EmptyDiagnosis(
        f"{name} not present anywhere on {table}",
        f"No player named {name} is in `{table}`. Either the spelling is off, or they "
        f"played before {VAULT_FIRST_SEASON}, which is where the vault starts.",
        retry_hint=(
            f"0 rows: no row on {table} matches '{name}' in any season. If that is a "
            f"misspelling of a real NBA player, re-plan with the correct published "
            f"spelling. If the player's career ended before {VAULT_FIRST_SEASON}, set "
            f"supported=false with 'STAT_NOT_IN_VAULT: player predates the vault'."
        ),
    )
