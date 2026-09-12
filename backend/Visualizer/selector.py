"""Deterministic chart choice from a router plan and the frame it produced.

Team45 asked GPT for the chart type in the same breath as the SQL, then spent
`_validate_and_autofix` and a repair round-trip catching the cases where the label and
the rows disagreed. It had to: the model wrote the SQL, so only the model knew what the
columns meant. Here the plan is validated and the frame is typed before this runs, so
the shape is an INPUT, not a guess — no model call, no repair, no mismatch.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pandas as pd

from Visualizer import benchmarks, shaping
from Visualizer.chart_spec import ChartSpec, FieldSpec
from Visualizer.labels import base_label, field
from Visualizer.labels import unit_for as label_unit

if TYPE_CHECKING:  # keeps this package importable without a live DuckDB
    from Interpreter.router_plan import RouterPlan

logger = logging.getLogger(__name__)

LEADERBOARD_ROWS = 15
SCATTER_ROWS = 750  # Team45's HARD_RENDER_CAP — past this the dots stop being readable
TABLE_ROWS = 20
COMPARE_RADAR_SERIES = 2  # PlayerSkillRadarCompare renders exactly two series
MIN_RADAR_AXES = 3
MAX_RADAR_AXES = 6  # a 12-spoke polygon is noise, and the count must not vary per question

# What a radar is FOR: the five counting stats that describe how someone plays. The router
# pads a "profile" question's stat_focus with whatever the table happens to hold — for Kobe
# 2005-06 that was GP, MIN and every made/attempted/percentage shooting split, and no REB,
# AST, STL or BLK — so taking stat_focus at face value drew a shooting chart and called it a
# skill profile. The frame is SELECT *, so these are always there to be read directly.
CORE_RADAR_AXES: tuple[str, ...] = ("PTS", "REB", "AST", "STL", "BLK")
_CORE_SET = frozenset(CORE_RADAR_AXES)

# A stat_focus this short, naming something outside the core five, is the reader asking for
# those particular stats. Anything longer is the router's generic padding.
EXPLICIT_FOCUS_MAX = 4

# Canonical spoke order, so the same shape means the same thing on every profile. Anything
# not listed keeps its plan order and goes after these.
CANONICAL_RADAR_ORDER: tuple[str, ...] = (
    "PTS", "REB", "AST", "STL", "BLK",
    "TS_PCT", "EFG_PCT", "FG_PCT", "FG3_PCT", "FT_PCT",
    "USG_PCT", "PIE", "NET_RATING", "OFF_RATING", "DEF_RATING",
)

# Made and attempted move together, so carrying both triples the weight of shot volume on
# the polygon. Keep the percentage when it is present, else the made column.
_SHOT_GROUPS: tuple[tuple[str, str, str], ...] = (
    ("FGM", "FGA", "FG_PCT"),
    ("FG3M", "FG3A", "FG3_PCT"),
    ("FTM", "FTA", "FT_PCT"),
)

# The router adds these to stat_focus on almost every plan as supporting context for the
# analyst's prose, not because the user asked about them. Counting them would make the
# "exactly two stats" scatter rule unreachable: "true shooting vs usage for the top 25"
# arrives as [PTS, TS_PCT, USG_PCT, GP, MIN], which is five.
CONTEXT_STATS: frozenset[str] = frozenset({"GP", "MIN", "W", "L"})


def _primary_bundle(bundles: dict[str, pd.DataFrame]) -> tuple[str, pd.DataFrame]:
    """Largest bundle, matching what `data` on the response carries.

    Deliberately not importing `sql_builder.primary_bundle_for_frontend`: that module
    pulls in the DuckDB connection at import time, and this package is pure so its
    tests need no database.
    """
    if not bundles:
        return "", pd.DataFrame()
    label = max(bundles, key=lambda k: len(bundles[k]))
    return label, bundles[label]


def _per_mode_from_label(label: str, plan: Any) -> str | None:
    """`bundle_label` joins with '__' and puts per_mode last."""
    if label and "__" in label:
        return label.rsplit("__", 1)[-1]
    modes = getattr(plan, "per_modes", None) or []
    return modes[0] if modes else None


def _subtitle(plan: Any, per_mode: str | None, *, show_per_mode: bool = True) -> str:
    bits: list[str] = []
    season = plan.season_label() if hasattr(plan, "season_label") else None
    if season:
        bits.append(season)
    season_type = getattr(plan, "season_type", None)
    if season_type:
        bits.append(str(season_type))
    # A career total of 43,440 points labelled "PerGame" is simply false. The all-time
    # grid carries no per_mode of its own, so the plan's default must not be printed.
    if per_mode and show_per_mode:
        bits.append(str(per_mode))
    return " · ".join(bits)


# Kinds whose rows map one-to-one onto source rows, so counting them against the frame
# is meaningful. A pivoted kind turns 12 player-season rows into 6 season rows, and
# reporting that as "showing 6 of 12" claims a truncation that never happened.
ROW_PER_RECORD_KINDS: frozenset[str] = frozenset({"leaderboard", "scatter", "table"})


def _exact_game_date(plan: Any) -> str | None:
    """The single date this plan pins, if any."""
    for f in getattr(plan, "row_filters", None) or []:
        if str(f.get("column", "")).upper() == "GAME_DATE" and str(f.get("op", "")) == "eq":
            value = str(f.get("value", "")).strip()
            if value:
                return value
    return None


def _citation(plan: Any, show_per_mode: bool, game_date: str | None = None) -> str:
    """Provenance, minus any slice that was not actually applied.

    `player_shot_chart` has no per_mode column, so the plan's default "PerGame" never
    reaches the query — printing it in the source line would claim a slice that was
    never used.
    """
    text = plan.citation() if hasattr(plan, "citation") else ""
    if not text:
        return text
    parts = text.split(" | ")
    if not show_per_mode:
        parts = [p for p in parts if not p.strip().startswith("per_mode=")]
    if game_date:
        # The season and season_type were dropped from the query in favour of the date,
        # so the source line must not report them as filters that were applied.
        parts = [
            p for p in parts
            if not p.strip().startswith(("seasons=", "season_type="))
        ]
        parts.append(f"game_date={game_date}")
    return " | ".join(parts)


def _notes(plan: Any, shown: int, available: int) -> list[str]:
    """Everything that narrowed the question, in the chart's own footer.

    A reader who only looks at the picture must not be misled by it.
    """
    notes: list[str] = []

    for floor in (getattr(plan, "applied_floors", None) or []):
        phrase = floor.get("phrase")
        column = floor.get("column")
        value = floor.get("value")
        if phrase:
            notes.append(f"Minimum applied: {phrase}")
        elif column is not None and value is not None:
            notes.append(f"Minimum applied: {column} >= {value:g}")

    for corr in (getattr(plan, "name_corrections", None) or []):
        asked = corr.get("asked") or corr.get("from")
        used = corr.get("resolved") or corr.get("to")
        if asked and used and str(asked) != str(used):
            notes.append(f"Showing {used} (asked for {asked})")

    if getattr(plan, "career_scope", False):
        notes.append("Career totals summed across every season in the vault")

    if available > shown > 0:
        notes.append(f"Showing {shown} of {available} rows")

    return notes


def _resolve(column: Any, candidates: list[str]) -> str | None:
    if not column:
        return None
    for col in candidates:
        if col.upper() == str(column).upper():
            return col
    return None


def _core_axes_in_frame(df: pd.DataFrame) -> list[str]:
    """The core five as they are actually spelled in this frame, where they carry values."""
    found: list[str] = []
    for name in CORE_RADAR_AXES:
        col = shaping.find_column(df, name)
        if col is None:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]) or not df[col].notna().any():
            continue
        found.append(col)
    return found


def radar_axes(df: pd.DataFrame, focus: list[str]) -> list[str]:
    """The spokes worth drawing, in canonical order, capped.

    The core five are the DEFAULT, read from the frame rather than from stat_focus. A
    short stat_focus naming something outside them is treated as a deliberate request and
    honoured instead; a long one is the router padding a generic profile question.
    """
    subject = [c for c in focus if c.upper() not in CONTEXT_STATS]

    # An explicit request means the reader asked for stats that are NOT the core five.
    # The moment a core stat appears alongside, it is the router padding a generic
    # question — "compare Shaq and Duncan" arrives as [PTS, REB, AST, FG_PCT, MIN], which
    # is not a request for field-goal percentage.
    explicit = (
        bool(subject)
        and all(c.upper() not in _CORE_SET for c in subject)
        and len(subject) <= EXPLICIT_FOCUS_MAX
    )
    if explicit:
        candidates = subject
    else:
        core = _core_axes_in_frame(df)
        candidates = core if len(core) >= MIN_RADAR_AXES else subject

    kept = [
        c
        for c in candidates
        if c.upper() not in CONTEXT_STATS and benchmarks.has_benchmark(c)
    ]

    upper = {c.upper() for c in kept}
    drop: set[str] = set()
    for made, attempted, pct in _SHOT_GROUPS:
        present = [x for x in (made, attempted, pct) if x in upper]
        if len(present) < 2:
            continue
        keep = pct if pct in upper else made
        drop.update(x for x in present if x != keep)
    kept = [c for c in kept if c.upper() not in drop]

    rank = {name: i for i, name in enumerate(CANONICAL_RADAR_ORDER)}
    kept.sort(key=lambda c: rank.get(c.upper(), len(CANONICAL_RADAR_ORDER)))
    return kept[:MAX_RADAR_AXES]


def subject_stats(focus: list[str], order_by: Any = None) -> list[str]:
    """Focus columns with the router's boilerplate context dropped.

    A context column is promoted back to a subject only when the question RANKED by it.
    "Top 30 by minutes per game and plus-minus" arrives as [MIN, PLUS_MINUS, GP] with
    order_by=MIN, so minutes is what was asked about. "Who led the league in scoring"
    arrives as [PTS, GP] with order_by=PTS, where GP is only the qualifying floor — an
    earlier version restored it whenever fewer than two stats survived, which turned every
    plain leaderboard into a "Games played vs Points" scatter.
    """
    ranked = str(order_by or "").upper()
    return [
        c
        for c in focus
        if c.upper() not in CONTEXT_STATS or c.upper() == ranked
    ]


def _scatter_axes(a: str, b: str) -> tuple[str, str]:
    """Volume on x, rate on y — otherwise the convention flips question to question."""
    a_rate = label_unit(a) in ("pct", "rating")
    b_rate = label_unit(b) in ("pct", "rating")
    if a_rate and not b_rate:
        return b, a
    return a, b


def _ranked_stat(plan: Any, focus: list[str], all_stats: list[str]) -> str | None:
    """The column a leaderboard's bars represent: the one the rows were ordered by.

    When `order_by` is set but is not chartable — a *_RANK field, a string — the honest
    outcome is NO leaderboard. Substituting the next numeric column draws bars that are
    not what the ranking was, which is the label/rows mismatch this whole module exists
    to prevent.
    """
    order_by = getattr(plan, "order_by", None)
    if order_by:
        return _resolve(order_by, all_stats)
    if focus:
        return focus[0]
    return all_stats[0] if all_stats else None


def _series_stat(plan: Any, focus: list[str], all_stats: list[str]) -> str | None:
    """The stat a trend line follows.

    `stat_focus` leads here, because `order_by` on a trend is usually the season — the
    thing the line is ordered ALONG, not the thing it plots.
    """
    if focus:
        return focus[0]
    resolved = _resolve(getattr(plan, "order_by", None), all_stats)
    if resolved:
        return resolved
    return all_stats[0] if all_stats else None


def _spec(
    kind: str,
    title: str,
    plan: Any,
    per_mode: str | None,
    *,
    rows: list[dict],
    x: FieldSpec | None = None,
    y: list[FieldSpec] | None = None,
    series: str | None = None,
    available: int = 0,
    extra_notes: list[str] | None = None,
    show_per_mode: bool = True,
    mode: str | None = None,
    points: list[dict] | None = None,
    subtitle_override: str | None = None,
) -> ChartSpec:
    comparable = available if kind in ROW_PER_RECORD_KINDS else 0
    notes = list(extra_notes or [])

    # A rising defensive-rating line looks like improvement and is the opposite. The radar
    # already inverts these; a line or a bar cannot, so it has to be said in words.
    if kind in {"trend", "compare_trend", "leaderboard", "scatter"}:
        for f in y or []:
            if benchmarks.is_inverted(f.column):
                notes.append(f"Lower is better for {f.label.lower()}")

    return ChartSpec(
        kind=kind,  # type: ignore[arg-type]
        title=title,
        subtitle=subtitle_override or _subtitle(plan, per_mode, show_per_mode=show_per_mode) or None,
        x=x,
        y=y or [],
        series=series,
        mode=mode,
        points=points or [],
        rows=rows,
        citation=_citation(plan, show_per_mode, subtitle_override),
        notes=_notes(plan, len(rows), comparable) + notes,
    )


def select_charts(
    plan: "RouterPlan | None", bundles: dict[str, pd.DataFrame]
) -> list[ChartSpec]:
    """Zero or one chart for this answer. A list because two is a later, additive change."""
    if plan is None or not getattr(plan, "supported", False) or not bundles:
        return []

    label, df = _primary_bundle(bundles)
    if df is None or df.empty:
        return []

    try:
        return _select(plan, label, df)
    except Exception as exc:  # noqa: BLE001
        # A chart is a garnish. It must never take down an answer that is otherwise fine.
        logger.warning("Chart selection failed, answering without one: %s", exc)
        return []


def _select(plan: Any, label: str, df: pd.DataFrame) -> list[ChartSpec]:
    per_mode = _per_mode_from_label(label, plan)
    available = int(df.attrs.get("true_row_count", len(df)))

    focus = shaping.numeric_stat_columns(df, getattr(plan, "stat_focus", None) or [])
    stat_focus_upper = {s.upper() for s in (getattr(plan, "stat_focus", None) or [])}
    focus_only = [c for c in focus if c.upper() in stat_focus_upper]
    all_stats = focus

    entities = getattr(plan, "entities", None) or []
    is_leaderboard = plan.is_leaderboard() if hasattr(plan, "is_leaderboard") else False
    multi_season = plan.is_multi_season() if hasattr(plan, "is_multi_season") else False

    season_col = shaping.season_column(df)
    distinct_seasons = int(df[season_col].nunique()) if season_col else 0

    # --- shot chart -----------------------------------------------------------
    # First, because a shot-chart plan has no ranked stat and would otherwise fall
    # through to the table. The frame arrives pre-binned from build_shot_chart_sql.
    if str(getattr(plan, "table", "") or "") == "player_shot_chart":
        cells = shaping.shape_shot_chart(df)
        if cells:
            points = shaping.shape_shot_points(df)
            # An exact GAME_DATE overrides the season slice in the query, so the label
            # must not keep it either: Tatum's 30 April 2021 game came back captioned
            # "2020-21 · Playoffs" when it was a regular-season night.
            game_date = _exact_game_date(plan)
            attempts = sum(c["total"] for c in cells)
            made = sum(c["made"] for c in cells)
            who = entities[0] if entities else "The league"
            pct = (made / attempts * 100) if attempts else 0.0
            # "attempts plotted", not "attempts": shots beyond the half-court bounds
            # cannot be drawn and are excluded, so claiming a season total would
            # overstate by the handful of heaves (0.1-0.8% of a player's attempts).
            note = f"{attempts:,} attempts plotted · {pct:.1f}% shooting"
            if points:
                # Every attempt is on the chart at this size, so it can be exact.
                note = f"{attempts:,} attempts · {made} made, {attempts - made} missed · {pct:.1f}%"
            return [
                _spec(
                    "shot_chart",
                    f"{who}: shot chart",
                    plan,
                    per_mode,
                    rows=cells,
                    points=points,
                    series=entities[0] if entities else None,
                    # Markers when every shot is present, heat when it is a sample.
                    mode="makes" if points else "volume",
                    show_per_mode=False,  # per_mode is meaningless for shot locations
                    subtitle_override=game_date,
                    extra_notes=[note],
                )
            ]

    # --- all-time leaders grid ------------------------------------------------
    # A different table from the season path: PLAYER_NAME / STAT / VALUE / STAT_RANK, with
    # order_by set to the rank. `_ranked_stat` rightly refuses to draw bars from a *_RANK
    # column, but the figure being ranked is sitting in VALUE, so chart that.
    order_by = str(getattr(plan, "order_by", "") or "")
    if is_leaderboard and order_by.upper().endswith("_RANK"):
        value_col = shaping.find_column(df, "VALUE")
        if value_col is not None and pd.api.types.is_numeric_dtype(df[value_col]):
            rows = shaping.shape_leaderboard(df, value_col, LEADERBOARD_ROWS)
            if rows:
                stat_col = shaping.find_column(df, "STAT")
                stat_name = str(df.iloc[0][stat_col]) if stat_col is not None else ""
                what = base_label(stat_name).lower() if stat_name else "value"
                return [
                    _spec(
                        "leaderboard",
                        f"All-time {what} leaders",
                        plan,
                        per_mode,
                        rows=rows,
                        y=[FieldSpec(column=value_col, label=base_label(stat_name) or "Total", precision=0)],
                        available=available,
                        show_per_mode=False,  # a career total is not a per-game figure
                    )
                ]

    # --- scatter: a ranking whose question named exactly two numbers ----------
    # Two stats means a relationship was asked about; three or more means a ranking with
    # supporting columns, which is a leaderboard.
    subjects = subject_stats(focus_only, getattr(plan, "order_by", None))
    if is_leaderboard and len(subjects) == 2:
        x_stat, y_stat = _scatter_axes(subjects[0], subjects[1])
        rows = shaping.shape_scatter(df, x_stat, y_stat, SCATTER_ROWS)
        if rows:
            return [
                _spec(
                    "scatter",
                    f"{base_label(y_stat)} vs {base_label(x_stat)}",
                    plan,
                    per_mode,
                    rows=rows,
                    x=field(x_stat, per_mode),
                    y=[field(y_stat, per_mode)],
                    available=available,
                )
            ]

    # --- leaderboard: ranked rows, career or single season --------------------
    if is_leaderboard:
        stat = _ranked_stat(plan, focus_only, all_stats)
        if stat:
            rows = shaping.shape_leaderboard(df, stat, LEADERBOARD_ROWS)
            if rows:
                career = (
                    plan.is_career_leaderboard()
                    if hasattr(plan, "is_career_leaderboard")
                    else False
                )
                lead = "All-time " if career else ""
                title = f"{lead}{base_label(stat).lower()} leaders"
                return [
                    _spec(
                        "leaderboard",
                        title[0].upper() + title[1:],
                        plan,
                        per_mode,
                        rows=rows,
                        y=[field(stat, per_mode)],
                        available=available,
                    )
                ]

    # --- trend / compare_trend: a stat moving over seasons --------------------
    if multi_season and distinct_seasons >= 2:
        stat = _series_stat(plan, focus_only, all_stats)
        if stat and len(entities) == 1:
            rows = shaping.shape_trend(df, stat)
            if rows:
                return [
                    _spec(
                        "trend",
                        f"{entities[0]}: {base_label(stat)}",
                        plan,
                        per_mode,
                        rows=rows,
                        x=FieldSpec(column=season_col or "SEASON", label="Season", precision=0),
                        y=[field(stat, per_mode)],
                        available=available,
                    )
                ]
        if stat and len(entities) >= 2:
            rows, series = shaping.shape_compare_trend(df, stat, entity_order=entities)
            if rows and len(series) >= 2:
                return [
                    _spec(
                        "compare_trend",
                        f"{' vs '.join(series[:3])}: {base_label(stat)}",
                        plan,
                        per_mode,
                        rows=rows,
                        x=FieldSpec(column=season_col or "SEASON", label="Season", precision=0),
                        y=[field(stat, per_mode)],
                        series=shaping.name_column(df),
                        available=available,
                    )
                ]

    # --- radar / compare_radar: a profile across three or more axes -----------
    axes = radar_axes(df, focus_only)
    if not multi_season and len(axes) >= MIN_RADAR_AXES:
        if len(entities) == 1:
            rows = shaping.shape_radar(df, axes)
            if len(rows) >= MIN_RADAR_AXES:
                return [
                    _spec(
                        "radar",
                        f"{entities[0]}: skill profile",
                        plan,
                        per_mode,
                        rows=rows,
                        y=[field(c, per_mode) for c in axes],
                        series=entities[0],  # bare name; the title already says "profile"
                        available=available,
                    )
                ]
        if len(entities) >= 2:
            rows, series = shaping.shape_compare_radar(
                df, axes, COMPARE_RADAR_SERIES, entity_order=entities
            )
            if len(rows) >= MIN_RADAR_AXES and len(series) >= 2:
                # Two overlaid polygons is the readable limit, and the renderer takes
                # exactly two — so when more were asked about, the chart has to say
                # whose numbers are missing from it.
                dropped = [e for e in entities if e not in series]
                extra = (
                    [f"Charted {' and '.join(series)} only; {', '.join(dropped)} not shown"]
                    if dropped
                    else []
                )
                return [
                    _spec(
                        "compare_radar",
                        " vs ".join(series),
                        plan,
                        per_mode,
                        rows=rows,
                        y=[field(c, per_mode) for c in axes],
                        series=shaping.name_column(df),
                        available=available,
                        extra_notes=extra,
                    )
                ]

    # --- table: the honest fallback ------------------------------------------
    # A chart that cannot be chosen confidently should not be invented. Rendering the
    # rows is always truthful, and it means no question ever renders a blank frame.
    name_col = shaping.name_column(df)
    columns: list[str] = []
    if name_col:
        columns.append(name_col)
    if season_col and season_col != name_col:
        columns.append(season_col)

    # A table shows rows, so it is not held to the chartable rules: a *_RANK column is
    # meaningless as a bar but perfectly honest as a cell, and is often exactly what was
    # asked for. Take the plan's own stat_focus verbatim where the frame has it.
    present = {str(c).upper(): str(c) for c in df.columns}
    requested = [
        present[s.upper()]
        for s in (getattr(plan, "stat_focus", None) or [])
        if s.upper() in present
    ]
    # A column the vault has no values for is a column of dashes. The tracking tables
    # return whole slices as NULL for seasons they do not cover, and printing those as
    # empty cells reads as a rendering failure rather than as missing data.
    candidates = [c for c in (requested or focus_only or all_stats) if df[c].notna().any()]
    columns.extend(c for c in candidates[:5] if c not in columns)
    if not columns:
        return []

    rows = shaping.shape_table(df, columns, TABLE_ROWS)
    if not rows:
        return []
    topic = getattr(plan, "topic", None)
    return [
        _spec(
            "table",
            str(topic).strip().capitalize() if topic else "Results",
            plan,
            per_mode,
            rows=rows,
            y=[field(c, per_mode) for c in columns],
            available=available,
        )
    ]


def chart_hint_line(charts: list[ChartSpec]) -> str | None:
    """One line telling the analyst a picture exists, so the prose stops transcribing it."""
    if not charts:
        return None
    spec = charts[0]
    y_labels = ", ".join(f.label for f in spec.y) or "the values"
    x_label = spec.x.label if spec.x else "rank"
    return f"{spec.kind} chart of {y_labels} by {x_label}"
