"""Quick smoke test for DuckDB staging backend."""
from Executer.data_backend import get_backend, use_duckdb_staging
from Executer.duckdb_store import get_connection, get_db_schema, list_registered_tables
from Executer.executor import execute_query, validate_and_normalize_sql


def main() -> None:
    print("backend:", get_backend(), "duckdb:", use_duckdb_staging())
    conn = get_connection()
    print("tables:", list_registered_tables(conn))
    print("schema length:", len(get_db_schema(conn)))
    sql = """
    SELECT PLAYER_ID, season, season_type, per_mode, PTS, PLAYER_NAME
    FROM player_season_stats
    WHERE season = '2024-25'
      AND season_type = 'Regular Season'
      AND per_mode = 'PerGame'
    ORDER BY PTS DESC
    LIMIT 5
    """
    sql = validate_and_normalize_sql(sql)
    df = execute_query(conn, sql)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
