"""Shared staging helpers."""
from __future__ import annotations

import ast
import logging
import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_ID_COLS = {
    "PLAYER_ID",
    "PLAYER_NAME",
    "NICKNAME",
    "TEAM_ID",
    "TEAM_ABBREVIATION",
    "TEAM_NAME",
    "AGE",
    "GROUP_SET",
    "CFID",
    "CFPARAMS",
}

_RAW_FILE_RE = re.compile(
    r"^(dash|clutch|hustle)_(regular_season|playoffs)_(pergame|totals)\.parquet$",
    re.IGNORECASE,
)


def parse_raw_slice_filename(path: Path) -> tuple[str, str, str] | None:
    """Return (kind, season_type, per_mode) from dash/clutch/hustle filename."""
    m = _RAW_FILE_RE.match(path.name)
    if not m:
        return None
    kind, season_slug, per_slug = m.groups()
    season_type = "Regular Season" if season_slug == "regular_season" else "Playoffs"
    per_mode = "PerGame" if per_slug == "pergame" else "Totals"
    return kind, season_type, per_mode


def reorder_slice_context_columns(
    df: pd.DataFrame,
    *,
    id_col: str,
    context_cols: tuple[str, ...] = ("season", "season_type", "per_mode"),
) -> pd.DataFrame:
    """Place slice context columns immediately after the primary id column."""
    cols = list(df.columns)
    id_actual = next((c for c in cols if c.upper() == id_col.upper()), None)
    if id_actual is None:
        return df
    ctx = [c for c in context_cols if c in cols]
    rest = [c for c in cols if c not in [id_actual, *ctx]]
    return df[[id_actual, *ctx, *rest]]


def prefix_columns(df: pd.DataFrame, prefix: str, join_keys: list[str]) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        if col in join_keys or col in _ID_COLS:
            continue
        rename[col] = f"{prefix}{col.lower()}"
    return df.rename(columns=rename)


def flatten_shot_zone_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Turn NBA multi-header string columns into snake_case names."""
    out = df.copy()
    new_names: dict[str, str] = {}
    for col in out.columns:
        if not isinstance(col, str) or not col.startswith("("):
            new_names[col] = col
            continue
        try:
            parts = ast.literal_eval(col)
        except (ValueError, SyntaxError):
            new_names[col] = col
            continue
        if len(parts) != 2:
            new_names[col] = col
            continue
        zone, metric = parts
        zone_slug = (
            str(zone)
            .lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "")
            .replace("__", "_")
        )
        if zone_slug in ("", "player_id", "player_name", "team_id", "team_abbreviation", "age", "nickname"):
            key = zone_slug or metric.lower()
            new_names[col] = key if key else col
        else:
            new_names[col] = f"{zone_slug}_{metric.lower()}"
    out = out.rename(columns=new_names)
    # Normalize identity columns
    identity_map = {
        "player_id": "player_id",
        "player_name": "player_name",
        "team_id": "team_id",
        "team_abbreviation": "team_abbreviation",
        "age": "age",
        "nickname": "nickname",
    }
    for old, new in identity_map.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})
    return out


def concat_parquet_tree(root: Path, season_from_parent: bool = True) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(root.rglob("*.parquet")):
        df = pd.read_parquet(path)
        if season_from_parent and path.parent.name not in ("player_shot_zones", "team_shot_zones"):
            # season folder is parent of file when layout is {table}/{season}/file.parquet
            if path.parent.parent == root:
                df["season"] = path.parent.name
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _escape_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def concat_parquet_files_batched(
    files: list[Path],
    out_path: Path,
    *,
    enrich: Callable[[pd.DataFrame, Path], None],
    batch_size: int = 500,
    log_label: str = "parquet",
) -> int:
    """Read many small parquet files in batches, merge parts with DuckDB."""
    import duckdb

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not files:
        return 0

    part_paths: list[Path] = []
    total_rows = 0
    for start in range(0, len(files), batch_size):
        chunk = files[start : start + batch_size]
        frames = []
        for path in chunk:
            df = pd.read_parquet(path)
            enrich(df, path)
            frames.append(df)
        batch = pd.concat(frames, ignore_index=True)
        total_rows += len(batch)
        part_path = out_path.with_name(f"{out_path.stem}.part{len(part_paths):04d}.parquet")
        batch.to_parquet(part_path, index=False)
        part_paths.append(part_path)
        logger.info(
            "%s staging progress: %s/%s files (%s rows so far)",
            log_label,
            min(start + batch_size, len(files)),
            len(files),
            total_rows,
        )

    out_sql = _escape_path(out_path)
    parts_sql = ", ".join(f"'{_escape_path(p)}'" for p in part_paths)
    conn = duckdb.connect()
    try:
        conn.execute("SET enable_progress_bar=false")
        conn.execute(
            f"""
            COPY (
                SELECT * FROM read_parquet([{parts_sql}], union_by_name=true)
            ) TO '{out_sql}' (FORMAT PARQUET)
            """
        )
    finally:
        conn.close()

    for part_path in part_paths:
        part_path.unlink(missing_ok=True)
    return total_rows


def season_type_from_slug(slug: str) -> str:
    return "Regular Season" if slug == "regular_season" else "Playoffs"
