# SQL execution backends

## DuckDB + staging Parquet (default)

No RDS required. Views are created over `data/staging/*.parquet` at runtime.

```powershell
cd DataSport\backend
.\.venv\Scripts\Activate.ps1
pip install duckdb
python -m ingestion.stage_all --phase 1
```

Environment (optional):

```env
DATA_BACKEND=duckdb
STAGING_DATA_DIR=c:/Users/mikae/Coder/DataSport/DataSport/backend/data/staging
OPENAI_API_KEY=sk-...
STAGING_SQL_MODEL=gpt-5.4-mini
```

Test SQL without GPT:

```powershell
python -c "from Executer.duckdb_store import get_connection; from Executer.executor import execute_query, validate_and_normalize_sql; c=get_connection(); q=validate_and_normalize_sql(\"SELECT PLAYER_ID, season, season_type, per_mode, PTS FROM player_season_stats WHERE season='2024-25' AND season_type='Regular Season' AND per_mode='PerGame' LIMIT 3\"); print(execute_query(c,q))"
```

Flow: `Interpreter/staging_query.py` → GPT → `Executer/executor.validate_and_normalize_sql` → DuckDB → `pandas.DataFrame`.

After re-staging, restart the API process (or call `Executer.duckdb_store.refresh_views()`).

## PostgreSQL / RDS (legacy)

```env
DATA_BACKEND=postgres
POSTGRES_HOST=...
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
```

Uses the large `Interpreter/interpreter.py` RDS prompt and planner cost checks.
