"""Frame -> renderer rows, one shaper per chart kind.

The row contract per kind is the whole point of this module; the renderers are dumb and
read exactly these keys:

    leaderboard    {rank, name, teamAbbr, value}
    trend          {season, value}                  (matches TS TrendPoint)
    compare_trend  {season, "<entity>": number, ...}
    radar          {category, normalized, raw}      (matches TS SkillRadarCategory)
    compare_radar  {category, "<entity>": number, ...}
    scatter        {name, teamAbbr, x, y}
    shot_chart     {x, y, made, total}             (matches TS HexBin, SVG space)
    table          raw records, columns named by spec.y
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from Visualizer.benchmarks import normalize
from Visualizer.labels import base_label

# Identity and slice columns are never the "stat" a chart is about.
NON_STAT_COLUMNS: frozenset[str] = frozenset(
    {
        "PLAYER_ID", "TEAM_ID", "PERSON_ID", "GAME_ID", "SEASON_ID",
        "PLAYER_NAME", "TEAM_NAME", "TEAM_ABBREVIATION", "TEAM_CITY",
        "NICKNAME", "SEASON", "SEASON_TYPE", "PER_MODE", "MEASURE_TYPE",
        "PT_MEASURE_TYPE", "GROUP_QUANTITY", "GAME_DATE", "MATCHUP", "WL",
        "TEAM_COUNT", "GROUP_ID", "GROUP_NAME",
    }
)


def _find(df: pd.DataFrame, *candidates: str) -> str | None:
    """First matching column, compared case-insensitively."""
    lookup = {str(c).upper(): str(c) for c in df.columns}
    for cand in candidates:
        hit = lookup.get(cand.upper())
        if hit is not None:
            return hit
    return None


find_column = _find
"""Public alias — the selector needs it for the all-time leaders grid."""


def order_series(series: list[str], entity_order: list[str] | None) -> list[str]:
    """Put series in the order the question named them.

    Frame row order is whatever the SQL returned, so "compare Curry and Lillard" was
    coming back titled "Damian Lillard vs Stephen Curry".
    """
    if not entity_order:
        return series
    ranked: list[str] = []
    for wanted in entity_order:
        for name in series:
            if name in ranked:
                continue
            if name.strip().lower() == str(wanted).strip().lower():
                ranked.append(name)
    ranked.extend(n for n in series if n not in ranked)
    return ranked


def name_column(df: pd.DataFrame) -> str | None:
    return _find(df, "PLAYER_NAME", "TEAM_NAME", "GROUP_NAME", "FULL_NAME")


def season_column(df: pd.DataFrame) -> str | None:
    return _find(df, "SEASON", "GAME_DATE")


def team_column(df: pd.DataFrame) -> str | None:
    return _find(df, "TEAM_ABBREVIATION", "TEAM_NAME")


def numeric_stat_columns(df: pd.DataFrame, preferred: list[str] | None = None) -> list[str]:
    """Numeric columns that could be plotted, `preferred` (plan.stat_focus) first.

    Rank columns are excluded: NBA's *_RANK fields are numeric and would otherwise be
    charted as if 1 were a good score on the same axis as points.
    """
    numeric = [
        str(c)
        for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and str(c).upper() not in NON_STAT_COLUMNS
        and not str(c).upper().endswith("_RANK")
    ]
    if not preferred:
        return numeric
    upper = {c.upper(): c for c in numeric}
    ordered = [upper[p.upper()] for p in preferred if p.upper() in upper]
    rest = [c for c in numeric if c not in ordered]
    return ordered + rest


def _num(value: Any) -> float | None:
    """Safe float, treating NaN/inf as missing so JSON stays valid."""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _round(value: float, precision: int = 3) -> float:
    return round(value, precision)


def dedupe_rows(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """One row per key, preferring the one with the most games played.

    A traded player has a row per team on the season tables, so a trend line would
    zig-zag between partial seasons unless the fullest row wins.
    """
    if df.empty or not keys:
        return df
    gp = _find(df, "GP", "G")
    if gp is not None:
        ordered = df.sort_values(by=gp, ascending=False, kind="mergesort")
    else:
        ordered = df
    return ordered.drop_duplicates(subset=keys, keep="first")


# ---------------------------------------------------------------------------
# Shapers
# ---------------------------------------------------------------------------
def shape_leaderboard(df: pd.DataFrame, stat: str, limit: int) -> list[dict]:
    name_col = name_column(df)
    team_col = team_column(df)
    if name_col is None:
        return []
    # SQL already ordered by the ranked stat, so the first row per name is their best.
    frame = df.drop_duplicates(subset=[name_col], keep="first").head(limit)

    rows: list[dict] = []
    for i, (_, row) in enumerate(frame.iterrows(), start=1):
        value = _num(row.get(stat))
        if value is None:
            continue
        rows.append(
            {
                "rank": i,
                "name": str(row.get(name_col) or "—"),
                "teamAbbr": str(row.get(team_col) or "") if team_col else "",
                "value": _round(value),
            }
        )
    return rows


def shape_trend(df: pd.DataFrame, stat: str) -> list[dict]:
    season_col = season_column(df)
    if season_col is None:
        return []
    frame = dedupe_rows(df, [season_col]).sort_values(by=season_col, kind="mergesort")

    rows: list[dict] = []
    for _, row in frame.iterrows():
        value = _num(row.get(stat))
        if value is None:
            continue
        rows.append({"season": str(row.get(season_col)), "value": _round(value)})
    return rows


def shape_compare_trend(
    df: pd.DataFrame, stat: str, entity_order: list[str] | None = None
) -> tuple[list[dict], list[str]]:
    """Pivot to one row per season, one key per entity. Returns (rows, series names)."""
    season_col = season_column(df)
    name_col = name_column(df)
    if season_col is None or name_col is None:
        return [], []
    frame = dedupe_rows(df, [name_col, season_col])

    series = order_series(
        [str(n) for n in frame[name_col].dropna().unique()], entity_order
    )
    by_season: dict[str, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        season = str(row.get(season_col))
        value = _num(row.get(stat))
        if value is None:
            continue
        bucket = by_season.setdefault(season, {"season": season})
        bucket[str(row.get(name_col))] = _round(value)

    # Insert the entity keys in `series` order: the renderer derives its legend and its
    # colour assignment from row-key order, so building them in frame order made the
    # legend disagree with the title that was built from `series`.
    rows = [
        {"season": by_season[k]["season"], **{s: by_season[k][s] for s in series if s in by_season[k]}}
        for k in sorted(by_season)
    ]
    return rows, series


def shape_radar(df: pd.DataFrame, stats: list[str]) -> list[dict]:
    if df.empty:
        return []
    row = df.iloc[0]
    out: list[dict] = []
    for stat in stats:
        raw = _num(row.get(stat))
        if raw is None:
            continue
        scaled = normalize(raw, stat)
        if scaled is None:
            continue  # no ceiling for this column — see benchmarks.py
        out.append(
            {
                "category": base_label(stat),
                "normalized": scaled,
                "raw": _round(raw),
            }
        )
    return out


def shape_compare_radar(
    df: pd.DataFrame,
    stats: list[str],
    max_series: int = 2,
    entity_order: list[str] | None = None,
) -> tuple[list[dict], list[str]]:
    """One row per stat, one key per entity, all on the shared 0-100 scale."""
    name_col = name_column(df)
    if name_col is None or df.empty:
        return [], []
    frame = dedupe_rows(df, [name_col])
    series = order_series(
        [str(n) for n in frame[name_col].dropna().unique()], entity_order
    )[:max_series]

    rows: list[dict] = []
    for stat in stats:
        bucket: dict[str, Any] = {"category": base_label(stat)}
        filled = False
        for who in series:  # insertion order decides which polygon is which
            match = frame[frame[name_col].astype(str) == who]
            if match.empty:
                continue
            raw = _num(match.iloc[0].get(stat))
            if raw is None:
                continue
            scaled = normalize(raw, stat)
            if scaled is None:
                continue
            bucket[who] = scaled
            filled = True
        if filled:
            rows.append(bucket)
    return rows, series


def shape_scatter(df: pd.DataFrame, x_stat: str, y_stat: str, limit: int) -> list[dict]:
    name_col = name_column(df)
    team_col = team_column(df)
    if name_col is None:
        return []
    frame = df.drop_duplicates(subset=[name_col], keep="first").head(limit)

    rows: list[dict] = []
    for _, row in frame.iterrows():
        x = _num(row.get(x_stat))
        y = _num(row.get(y_stat))
        if x is None or y is None:
            continue
        rows.append(
            {
                "name": str(row.get(name_col) or "—"),
                "teamAbbr": str(row.get(team_col) or "") if team_col else "",
                "x": _round(x),
                "y": _round(y),
            }
        )
    return rows


def shape_table(df: pd.DataFrame, columns: list[str], limit: int) -> list[dict]:
    frame = df.head(limit)
    rows: list[dict] = []
    for _, row in frame.iterrows():
        record: dict[str, Any] = {}
        for col in columns:
            value = row.get(col)
            num = _num(value)
            record[col] = _round(num) if num is not None else (
                None if value is None or (isinstance(value, float) and math.isnan(value))
                else str(value)
            )
        rows.append(record)
    return rows


# ---------------------------------------------------------------------------
# Shot charts
# ---------------------------------------------------------------------------
# Hex centres are produced in the renderer's SVG space, so ShotChartCourt can draw the
# cells without a transform. Mirrors its buildHexBins():
#     cx = col * hexW * 0.75 ;  cy = row * hexH + (col even ? 0 : hexH / 2)
_HEX_H = math.sqrt(3) * 8.0
_COL_STEP = 12.0


def _is_raw_shots(df: pd.DataFrame) -> bool:
    return _find(df, "LOC_X") is not None and _find(df, "LOC_Y") is not None


def _bin_raw(df: pd.DataFrame) -> pd.DataFrame:
    """Bin shot-by-shot rows with the geometry build_shot_chart_sql uses in DuckDB."""
    x = _find(df, "LOC_X")
    y = _find(df, "LOC_Y")
    made = _find(df, "SHOT_MADE_FLAG", "made")
    out = pd.DataFrame(
        {
            "hex_col": ((df[x] + 270.0) / _COL_STEP).round().astype(int),
            "py": 442.0 - df[y],
            "made": df[made].fillna(0).astype(int),
        }
    )
    offset = (out["hex_col"] % 2 != 0).map({True: _HEX_H / 2, False: 0.0})
    out["hex_row"] = ((out["py"] - offset) / _HEX_H).round().astype(int)
    out["total"] = 1
    return out.groupby(["hex_col", "hex_row"], as_index=False)[["made", "total"]].sum()


def shape_shot_chart(df: pd.DataFrame) -> list[dict]:
    """Hex cells, from either form the query returns.

    A large scope arrives already binned by DuckDB; a small one arrives shot by shot so
    the makes-and-misses view is possible, and is binned here instead. Either way the
    hex modes see the same contract, and all four are computable from `made`/`total`.
    """
    if _is_raw_shots(df):
        grouped = _bin_raw(df)
        col_c, row_c, made_c, total_c = "hex_col", "hex_row", "made", "total"
    else:
        col_c = _find(df, "hex_col")
        row_c = _find(df, "hex_row")
        made_c = _find(df, "made")
        total_c = _find(df, "total")
        if not all((col_c, row_c, made_c, total_c)):
            return []
        grouped = df.groupby([col_c, row_c], as_index=False)[[made_c, total_c]].sum()

    rows: list[dict] = []
    for _, r in grouped.iterrows():
        col = int(r[col_c])
        row = int(r[row_c])
        total = int(r[total_c])
        if total <= 0:
            continue
        rows.append(
            {
                "x": round(col * _COL_STEP, 2),
                "y": round(row * _HEX_H + (0.0 if col % 2 == 0 else _HEX_H / 2), 2),
                "made": int(r[made_c]),
                "total": total,
            }
        )
    return rows


def shape_shot_points(df: pd.DataFrame) -> list[dict]:
    """Individual attempts, when the scope is small enough to draw them.

    Field names match the TS `ShotPoint` so they drop straight into ShotChartCourt.
    Empty for a binned frame — the individual shots are genuinely gone by then.
    """
    if not _is_raw_shots(df):
        return []
    x = _find(df, "LOC_X")
    y = _find(df, "LOC_Y")
    made = _find(df, "SHOT_MADE_FLAG", "made")

    rows: list[dict] = []
    for _, r in df.iterrows():
        px, py = _num(r[x]), _num(r[y])
        if px is None or py is None:
            continue
        rows.append(
            {
                "loc_x": int(px),
                "loc_y": int(py),
                "shot_made_flag": 1 if int(r[made] or 0) == 1 else 0,
            }
        )
    return rows


def shot_zone_summary(df: pd.DataFrame) -> list[dict]:
    """Per-zone attempts and accuracy — what the ANALYST is given instead of coordinates.

    Feeding 1,500 rows of LOC_X/LOC_Y into Call 2 would spend the budget on numbers the
    model cannot read. Seven zone rows it can actually write about.
    """
    zone_c = _find(df, "zone", "SHOT_ZONE_BASIC")
    if zone_c is None:
        return []

    if _is_raw_shots(df):
        made_src = _find(df, "SHOT_MADE_FLAG", "made")
        work = pd.DataFrame(
            {
                zone_c: df[zone_c],
                "made": df[made_src].fillna(0).astype(int),
                "total": 1,
            }
        )
        made_c, total_c = "made", "total"
    else:
        made_c = _find(df, "made")
        total_c = _find(df, "total")
        if not all((made_c, total_c)):
            return []
        work = df

    grouped = work.groupby(zone_c, as_index=False)[[made_c, total_c]].sum()
    grouped = grouped.sort_values(by=total_c, ascending=False)

    out: list[dict] = []
    for _, r in grouped.iterrows():
        total = int(r[total_c])
        if total <= 0:
            continue
        made = int(r[made_c])
        out.append(
            {
                "zone": str(r[zone_c]),
                "fgm": made,
                "fga": total,
                "fg_pct": round(made / total, 3),
            }
        )
    return out
