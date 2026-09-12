"""Deterministic aggregates computed in pandas, not by the LLM.

The analyst used to be handed a printed table and asked to total or average it.
It got that arithmetic wrong — "LeBron's career totals" came back as 1,541 games
and 42,184 points when the vault says 1,622 and 43,440 — and two phrasings of the
same question disagreed with each other.

So the maths happens here, over the FULL result frame, and the numbers are handed
to the analyst as finished facts it is forbidden to recompute.

Two rules drive the design:

* **Per-game columns are averages, so they cannot be summed.** A career scoring
  average is the games-weighted mean ``sum(PTS * GP) / sum(GP)``, never
  ``mean(PTS)``. Both are reported when they differ so the difference is visible.
* **Rate columns cannot be averaged either.** FG_PCT is recomputed from its
  underlying makes and attempts when both are present, because the mean of thirty
  season percentages is not the career percentage.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import re

import pandas as pd

logger = logging.getLogger(__name__)

# Columns that count something and are therefore summable when per_mode is Totals.
_COUNTING = {
    "GP", "W", "L", "MIN", "PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
    "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "BLKA", "PF", "PFD",
    "DD2", "TD3", "PLUS_MINUS",
}

# Rate columns rebuilt from their components rather than averaged.
_RATIO_PARTS = {
    "FG_PCT": ("FGM", "FGA"),
    "FG3_PCT": ("FG3M", "FG3A"),
    "FT_PCT": ("FTM", "FTA"),
    "W_PCT": ("W", "L"),
}

# Columns that are identity/slice context, never statistics.
_NON_STAT = {
    "season", "season_type", "per_mode", "pt_measure_type", "measure_type",
    "group_quantity", "PLAYER_ID", "TEAM_ID", "player_id", "team_id",
    "GAME_ID", "GAME_DATE", "MATCHUP", "WL", "AGE", "TeamID", "SeasonID",
    "LeagueID", "GROUP_ID", "NICKNAME", "TeamSlug", "teamSlug",
}

_NAME_COLUMNS = (
    "PLAYER_NAME", "player_name", "TEAM_NAME", "team_name", "TeamName",
    "teamName", "GROUP_NAME",
)


def _name_column(df: pd.DataFrame) -> str | None:
    for c in _NAME_COLUMNS:
        if c in df.columns:
            return c
    return None


def _numeric_stat_columns(df: pd.DataFrame, stat_focus: list[str] | None) -> list[str]:
    """Numeric columns worth aggregating, preferring the router's stat_focus."""
    numeric = [
        c for c in df.columns
        if c not in _NON_STAT
        and not str(c).endswith("_RANK")
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    if stat_focus:
        focus_lower = {s.lower() for s in stat_focus}
        preferred = [c for c in numeric if c.lower() in focus_lower]
        # Keep the weighting/context columns even when not explicitly in focus.
        for extra in ("GP", "MIN", "W", "L"):
            if extra in df.columns and extra not in preferred and extra in numeric:
                preferred.append(extra)
        if preferred:
            return preferred
    return numeric


def _fmt(v: Any) -> str:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "n/a"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    f = float(v)
    if abs(f) < 1 and f != 0:
        return f"{f:.3f}"
    if f == int(f) and abs(f) >= 1000:
        return f"{int(f):,}"
    return f"{f:,.1f}"


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float | None:
    mask = values.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        return None
    w = weights[mask].astype(float)
    if w.sum() == 0:
        return None
    return float((values[mask].astype(float) * w).sum() / w.sum())


# Numbers the question compares against: "over 25 points", "at least 30", "40+".
# The old threshold block only counted _PCT columns against a fixed 0.40 / 0.50, so
# "How many seasons has LeBron averaged over 25 points?" had no computed count to quote
# and the analyst counted the 23 printed rows itself — answering 18 where the vault
# says 19.
_THRESHOLD_RE = re.compile(
    r"\b(?:over|above|more\s+than|greater\s+than|at\s+least|no\s+fewer\s+than|"
    r"minimum(?:\s+of)?)\s+(\d+(?:\.\d+)?)\b"
    r"|\b(\d+(?:\.\d+)?)\s*\+",
    re.IGNORECASE,
)


def thresholds_in(question: str | None) -> list[float]:
    """Every numeric threshold the question asks to compare against."""
    if not question:
        return []
    out: list[float] = []
    for m in _THRESHOLD_RE.finditer(question):
        raw = m.group(1) or m.group(2)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value not in out:
            out.append(value)
    return out[:4]


def _threshold_counts(
    df: pd.DataFrame, cols: list[str], question: str | None
) -> list[str]:
    """Exact row counts above each threshold named in the question."""
    values = thresholds_in(question)
    if not values or df.empty:
        return []

    label_col = "season" if "season" in df.columns else _name_column(df)
    n = len(df)
    out: list[str] = []

    # Only the columns the question is ABOUT. Counting every numeric column produced
    # "rows with GP above 25", "rows with MIN above 25", "rows with W above 25" beside
    # the one that mattered, and the analyst picked its own number out of the noise —
    # answering 18 where the computed PTS line said 19.
    unit = "seasons" if "season" in df.columns else "rows"

    for col in cols:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        for raw in values:
            # A percentage column stores 0.406, but people say "over 40%".
            candidates = [raw]
            if series.max() <= 1.5 and raw > 1.5:
                candidates.append(raw / 100.0)
            for threshold in candidates:
                hits = df[pd.to_numeric(df[col], errors="coerce") > threshold]
                # `len(hits) == n` is not a reason to stay quiet — it usually means the
                # SQL already applied the filter, so the row count IS the answer. The
                # earlier guard suppressed the line in exactly that case and left the
                # analyst counting: handed 19 pre-filtered seasons, it said 14.
                if not hits.shape[0]:
                    continue
                detail = ""
                if label_col and label_col in hits.columns:
                    labels = sorted(str(v) for v in hits[label_col].dropna().unique())
                    if len(labels) <= 25:
                        detail = f" ({', '.join(labels)})"
                out.append(
                    f"  EXACT COUNT — {unit} where {col} > {_fmt(threshold)}: "
                    f"{len(hits)}{detail}"
                )
    return out[:3]


def _aggregate_group(
    df: pd.DataFrame,
    per_mode: str,
    stat_focus: list[str] | None,
) -> list[str]:
    """Aggregate one entity's rows into deterministic lines."""
    lines: list[str] = []
    n = len(df)
    cols = _numeric_stat_columns(df, stat_focus)
    if not cols:
        return lines

    gp = df["GP"] if "GP" in df.columns else None
    is_per_game = per_mode.lower() in ("pergame", "per36", "per40", "per100possessions")

    # Span of the rows being aggregated.
    if "season" in df.columns:
        seasons = sorted(str(s) for s in df["season"].dropna().unique())
        if seasons:
            span = seasons[0] if len(seasons) == 1 else f"{seasons[0]} → {seasons[-1]}"
            lines.append(f"  rows aggregated: {n} ({len(seasons)} seasons, {span})")
        else:
            lines.append(f"  rows aggregated: {n}")
    else:
        lines.append(f"  rows aggregated: {n}")

    if gp is not None and gp.notna().any():
        lines.append(f"  total games (sum of GP): {_fmt(int(gp.sum()))}")

    for col in cols:
        series = df[col]
        if series.notna().sum() == 0:
            continue

        # Rate columns: rebuild from components when we can.
        if col in _RATIO_PARTS:
            made_col, att_col = _RATIO_PARTS[col]
            if made_col in df.columns and att_col in df.columns:
                if col == "W_PCT":
                    w, l = df[made_col].sum(), df[att_col].sum()
                    if (w + l) > 0:
                        lines.append(f"  {col}: {_fmt(w / (w + l))} (recomputed from {_fmt(w)}W / {_fmt(l)}L)")
                        continue
                else:
                    made, att = df[made_col].sum(), df[att_col].sum()
                    if att and att > 0:
                        if is_per_game and gp is not None:
                            wm = _weighted_mean(series, gp)
                            if wm is not None:
                                lines.append(f"  {col}: {_fmt(wm)} (games-weighted)")
                                continue
                        lines.append(f"  {col}: {_fmt(made / att)} (recomputed {_fmt(made)}/{_fmt(att)})")
                        continue
            # Fall through to weighted mean when components are absent.

        if is_per_game:
            # A per-game column is an average: weight by games, never sum.
            if gp is not None and gp.notna().any():
                wm = _weighted_mean(series, gp)
                naive = float(series.mean())
                if wm is not None:
                    if abs(wm - naive) >= 0.05:
                        lines.append(
                            f"  {col}: {_fmt(wm)} games-weighted average "
                            f"(unweighted mean of the {n} rows is {_fmt(naive)})"
                        )
                    else:
                        lines.append(f"  {col}: {_fmt(wm)} games-weighted average")
                    continue
            lines.append(f"  {col}: {_fmt(series.mean())} average of {n} rows")
        else:
            # Totals: summing is correct.
            if col in _COUNTING:
                lines.append(f"  {col}: {_fmt(series.sum())} total")
            else:
                lines.append(f"  {col}: {_fmt(series.mean())} average of {n} rows")

    # Threshold counts. "Every season Curry shot over 40% from three" is a counting
    # question, and the analyst miscounted it (11 when the answer is 13). Counting is
    # arithmetic, so it belongs here too.
    if "season" in df.columns and n > 2:
        for col in cols:
            if not col.endswith("_PCT") or df[col].notna().sum() < 3:
                continue
            for threshold in (0.40, 0.50):
                hits = df[df[col] > threshold]
                if 0 < len(hits) < n:
                    seasons = sorted(str(s) for s in hits["season"].dropna().unique())
                    lines.append(
                        f"  seasons with {col} above {threshold:.2f}: {len(hits)} "
                        f"({', '.join(seasons)})"
                    )

    # Peaks — the analyst is repeatedly asked for best/worst season.
    focus = [c for c in cols if c not in ("GP", "W", "L")][:4]
    label_col = "season" if "season" in df.columns else None
    for col in focus:
        s = df[col]
        if s.notna().sum() < 2:
            continue
        try:
            hi, lo = s.idxmax(), s.idxmin()
        except (ValueError, TypeError):
            continue
        if label_col:
            lines.append(
                f"  {col} peak: {_fmt(s.loc[hi])} in {df.loc[hi, label_col]}; "
                f"low: {_fmt(s.loc[lo])} in {df.loc[lo, label_col]}"
            )
        else:
            lines.append(f"  {col} peak: {_fmt(s.loc[hi])}; low: {_fmt(s.loc[lo])}")
    return lines


# Columns whose VALUES are the thing being counted rather than measured. "How many
# All-Star selections does LeBron have" is a row count per DESCRIPTION, and counting is
# arithmetic — which the analyst is forbidden from doing and, left to itself, gets
# wrong: handed 25 award rows (22 "NBA All-Star" + 3 "NBA All-Star Most Valuable
# Player", because the router filtered on `contains "All-Star"`), it answered
# "25 All-Star selections" while noting in the next line that 3 of them were a
# different award.
_CATEGORICAL_COUNT_COLUMNS = ("DESCRIPTION", "play_type", "COURT_STATUS", "POSITION")


def _categorical_counts(df: pd.DataFrame) -> list[str]:
    """Exact row counts per distinct value, for the columns worth counting."""
    out: list[str] = []
    for col in _CATEGORICAL_COUNT_COLUMNS:
        if col not in df.columns:
            continue
        counts = df[col].dropna().astype(str).str.strip()
        counts = counts[counts != ""].value_counts()
        if counts.empty or len(counts) > 40:
            continue
        out.append(f"  {col} — exact row counts:")
        for value, n in counts.items():
            out.append(f"    {value}: {n}")
    return out


# Low-cardinality columns worth splitting a result on. A "wins versus losses" or
# "home versus away" question is answered by comparing two subsets of the same rows,
# and the analyst was reading the rows but reporting only a single combined line —
# "the loss split is not separately available here" — when both halves were in front
# of it. Splitting deterministically removes the judgement call.
_SPLIT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("WL", "result"),
    ("COURT_STATUS", "on/off court"),
    ("type_grouping", "offense/defense"),
)

# Phrases that mean the user asked for a comparison ACROSS one of those splits.
_SPLIT_PHRASES = (
    "vs", "versus", "compared to", "against", "split", "difference between",
    "wins and losses", "wins versus losses", "home and away", "home or away",
    "home vs", "on and off", "when winning", "when losing", "better in",
)


def _venue_series(df: pd.DataFrame) -> pd.Series | None:
    """Home/away derived from MATCHUP: 'LAL vs. CHI' is home, 'LAL @ CHI' is away."""
    if "MATCHUP" not in df.columns:
        return None
    m = df["MATCHUP"].astype(str)
    if not m.str.contains("@", na=False).any():
        return None
    return m.str.contains("@", na=False).map({True: "Away", False: "Home"})


def _split_blocks(
    df: pd.DataFrame, per_mode: str, stat_focus: list[str] | None, question: str | None
) -> list[str]:
    """Per-subset aggregates when the question compares across a split."""
    q = (question or "").lower()
    if not any(phrase in q for phrase in _SPLIT_PHRASES):
        return []

    candidates: list[tuple[str, pd.Series]] = []
    for col, label in _SPLIT_COLUMNS:
        if col in df.columns and 1 < df[col].nunique(dropna=True) <= 4:
            candidates.append((label, df[col]))
    venue = _venue_series(df)
    if venue is not None and venue.nunique() > 1:
        candidates.append(("venue", venue))

    lines: list[str] = []
    for label, series in candidates[:2]:
        values = [v for v in series.dropna().unique()]
        if len(values) < 2:
            continue
        lines.append(f"  SPLIT BY {label.upper()} — each subset aggregated separately:")
        for value in sorted(values, key=str):
            sub = df[series == value]
            if sub.empty:
                continue
            lines.append(f"    [{label} = {value}]  ({len(sub)} rows)")
            lines.extend("    " + ln for ln in _aggregate_group(sub, per_mode, stat_focus))
    return lines


def compute_bundle_aggregates(
    bundles: dict[str, pd.DataFrame],
    stat_focus: list[str] | None = None,
    *,
    question: str | None = None,
    max_entities: int = 12,
) -> str:
    """Build the COMPUTED TOTALS block handed to the analyst.

    Every number here is produced by pandas over the complete frame. The analyst
    is instructed to quote these verbatim rather than doing its own arithmetic.
    """
    if not bundles:
        return ""

    blocks: list[str] = []
    for label, df in sorted(bundles.items()):
        if df is None or df.empty or len(df) < 2:
            # A single row needs no aggregation — the row IS the answer.
            continue

        per_mode = "PerGame"
        if "per_mode" in df.columns and df["per_mode"].notna().any():
            per_mode = str(df["per_mode"].dropna().iloc[0])
        elif "__" in label:
            per_mode = label.rsplit("__", 1)[-1]

        name_col = _name_column(df)
        section: list[str] = [f"--- {label} (per_mode={per_mode}) ---"]
        # Always state the size of the result set. Every "how many …" question is
        # answered by a count, and the analyst must never arrive at one by counting the
        # printed rows — which may be a sample.
        section.append(f"  TOTAL ROWS IN THE COMPLETE RESULT SET: {len(df)}")
        section.extend(_categorical_counts(df))
        focus_cols = [c for c in (stat_focus or []) if c in df.columns]
        section.extend(
            _threshold_counts(
                df, focus_cols or _numeric_stat_columns(df, stat_focus)[:2], question
            )
        )
        section.extend(_split_blocks(df, per_mode, stat_focus, question))

        if name_col and df[name_col].nunique() > 1:
            names = list(df[name_col].dropna().unique())
            if len(names) > max_entities:
                section.append(
                    f"  ({len(names)} distinct subjects; aggregating the first {max_entities})"
                )
                names = names[:max_entities]
            for name in names:
                sub = df[df[name_col] == name]
                if len(sub) < 2:
                    continue
                section.append(f"  [{name}]")
                section.extend("  " + ln for ln in _aggregate_group(sub, per_mode, stat_focus))
        else:
            subject = ""
            if name_col and df[name_col].notna().any():
                subject = str(df[name_col].dropna().iloc[0])
            if subject:
                section.append(f"  [{subject}]")
            section.extend(_aggregate_group(df, per_mode, stat_focus))

        if len(section) > 1:
            blocks.append("\n".join(section))

    if not blocks:
        return ""

    return (
        "=== COMPUTED TOTALS (calculated in pandas over the COMPLETE result set) ===\n"
        "These are authoritative. Quote them exactly. Do NOT add, average, COUNT or\n"
        "derive your own figures from the sample rows below — the sample may be\n"
        "partial, and counting rows yourself is how 19 seasons became 14.\n"
        "Any 'how many …' answer must come from a TOTAL ROWS or EXACT COUNT line.\n\n"
        + "\n\n".join(blocks)
    )
