"""Router → SQL builder → bundled DataFrames pipeline.

One table per question. On a SQL failure the router gets exactly one repair attempt;
if that also fails the error is logged to the terminal and empty data is returned.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from Executer.data_backend import get_connection
from Interpreter.router import route_question
from Interpreter.router_plan import RouterPlan
from Interpreter.sql_builder import execute_plan

logger = logging.getLogger(__name__)


def _log_plan(question: str, plan: RouterPlan, *, attempt: str = "initial") -> None:
    """Terminal block describing the routing decision (kept for debugging)."""
    lines = [
        "",
        "=" * 62,
        f"ROUTER PLAN ({attempt})",
        "=" * 62,
        f"  question    : {question.strip()[:200]}",
        f"  supported   : {plan.supported}",
    ]
    if not plan.supported:
        lines.append(f"  reason      : {plan.unsupported_reason}")
    else:
        lines.extend(
            [
                f"  table       : {plan.table}",
                f"  seasons     : {plan.season_label()}",
                f"  season_type : {plan.season_type}",
                f"  per_modes   : {', '.join(plan.per_modes)}",
                f"  entity_type : {plan.entity_type}",
                f"  entities    : {', '.join(plan.entities) or '(leaderboard)'}",
                f"  topic       : {plan.topic or '-'}",
                f"  stat_focus  : {', '.join(plan.stat_focus) or '-'}",
                f"  order_by    : {plan.order_by or '-'} {plan.sort_dir if plan.order_by else ''}".rstrip(),
                f"  limit       : {plan.limit if plan.limit else '-'}",
            ]
        )
        if plan.pt_measure_type:
            lines.append(f"  pt_measure  : {plan.pt_measure_type}")
        if plan.measure_type:
            lines.append(f"  measure     : {plan.measure_type}")
    lines.append("=" * 62)
    logger.info("\n".join(lines))


def _log_tables_accessed(plan: RouterPlan, bundles: dict[str, pd.DataFrame]) -> None:
    lines = ["", f"TABLES ACCESSED: {plan.table or 'none'}"]
    for label, df in bundles.items():
        lines.append(f"  {label} -> {df.shape[0]} rows x {df.shape[1]} cols")
    if not bundles:
        lines.append("  (no rows returned)")
    lines.append("")
    logger.info("\n".join(lines))


def run_routed_query(question: str) -> tuple[dict[str, pd.DataFrame], RouterPlan]:
    """Full interpreter path: route → execute → (one repair on SQL failure)."""
    plan = route_question(question)
    _log_plan(question, plan)

    if not plan.supported:
        logger.info("TABLES ACCESSED: none (multi-table question rejected at Call 1)")
        return {}, plan

    conn = get_connection()
    bundles, errors = execute_plan(plan, conn)

    if not bundles and errors:
        logger.warning("Router SQL failed, attempting one repair: %s", "; ".join(errors))
        try:
            repaired = route_question(
                question,
                _repair_errors=(
                    "The generated SQL failed against DuckDB with: "
                    + "; ".join(errors)
                    + ". Pick columns and slices that actually exist on the table."
                ),
            )
        except Exception as exc:  # noqa: BLE001 — repair routing itself failed
            logger.error("Router repair attempt failed: %s", exc)
            _log_tables_accessed(plan, {})
            return {}, plan

        _log_plan(question, repaired, attempt="repair")
        if not repaired.supported:
            return {}, repaired

        bundles, repair_errors = execute_plan(repaired, conn)
        plan = repaired
        if not bundles:
            logger.error(
                "Router SQL failed after one repair — returning empty. Errors: %s",
                "; ".join(repair_errors or errors),
            )
            _log_tables_accessed(plan, {})
            return {}, plan

    _log_tables_accessed(plan, bundles)
    logger.info(
        "Routed query OK | %s | bundles=%d", plan.citation(), len(bundles)
    )
    return bundles, plan
