"""Route SQL execution to DuckDB (staging parquet) or PostgreSQL (legacy RDS)."""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def get_backend() -> str:
    explicit = os.getenv("DATA_BACKEND", "").strip().lower()
    if explicit in ("duckdb", "staging", "parquet"):
        return "duckdb"
    if explicit in ("postgres", "postgresql", "rds"):
        return "postgres"
    if os.getenv("POSTGRES_HOST", "").strip():
        return "postgres"
    return "duckdb"


def use_duckdb_staging() -> bool:
    return get_backend() == "duckdb"


def sql_dialect() -> str:
    return "duckdb" if use_duckdb_staging() else "postgres"


def get_connection() -> Any:
    if use_duckdb_staging():
        from Executer.duckdb_store import get_connection as get_duckdb_connection

        return get_duckdb_connection()
    from Executer import executor as pg

    return pg._postgres_connection()


def get_db_schema(conn: Any | None = None) -> str:
    if use_duckdb_staging():
        from Executer.duckdb_store import get_db_schema as duck_schema

        return duck_schema(conn)
    from Executer import executor as pg

    conn = conn or get_connection()
    return pg._postgres_get_db_schema(conn)


def execute_query(
    conn: Any,
    sql_query: str,
    max_cost: Optional[float] = None,
    timeout_ms: int = 60000,
) -> pd.DataFrame:
    if use_duckdb_staging():
        from Executer.duckdb_store import execute_query as duck_execute

        return duck_execute(conn, sql_query, timeout_ms=timeout_ms)
    from Executer import executor as pg

    return pg._postgres_execute_query(conn, sql_query, max_cost, timeout_ms)
