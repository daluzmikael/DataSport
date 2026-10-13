# Analyst-generated charts — how the Team45 dashboard worked, and what replaces it

**Status:** plan, nothing built yet.
**Scope:** the chart layer only. The router → SQL → analyst pipeline stays exactly as it is.

---

## 1. What the demo-day dashboard actually did

`backend/DashboardBackend/dashboardInterpreter.py` (1,358 lines, carried over from Team45).
One endpoint, `POST /api/dashboards`, running this loop:

```
question
  → _intent_hint(question)            # Python regex pre-pass: guesses chartType + mode,
  │                                   #   extracts player names from capitalised runs
  → _call_gpt_for_interpretation()    # ONE GPT call returns {chartType, sqlQuery, chartConfig}
  → _post_process_sql()               # a stack of regex SQL rewriters:
  │     _expand_player_name_filters_for_encoding   accent-safe ILIKE splitting
  │     _route_scatter_to_correct_table            moves a scatter to the table that has the stat
  │     _fix_text_storage_identifier_case          quotes "PLAYER_NAME" for text-typed tables
  │     _dedupe_single_player_trend_sql
  → cursor.execute(sqlQuery)          # raw model-written SQL, straight at Postgres
  → _validate_and_autofix()           # inspect returned COLUMNS, coerce chartType or fail
  │     ↳ on failure: one repair round-trip with a hand-written correction message
  → shape per chart type              # dedupe leaderboard, pivot radar, label series
  → {success, chartType, data, config}
```

Seven chart types, rendered by seven Recharts components in `frontend/ai_analyst/components/recharts/`:
`Leaderboard`, `SinglePlayerStat`, `CompareStats`, `CategoricalBreakdown`,
`CompareCategoricalBreakdown`, `Scatter`, `ShotChart`.

**It worked, and it demoed well.** Two things carried it: the intent pre-pass caught the
phrasings people actually type (`"hot zones"`, `"where can't he shoot"`, `"money spot"` —
about 30 synonyms just for shot charts), and `_validate_and_autofix` recovered a lot of
near-misses by looking at the returned columns instead of trusting the model's own label.

### What it cost

| | |
|---|---|
| **The model writes SQL.** | The whole reason DataSport moved to a router + Python SQL builder. Every fragile thing here is downstream of that decision: the accent regex, the identifier-case fixer, the scatter table-router. Each is a patch for a query the model got wrong. |
| **The chart type is chosen before the data is known.** | GPT picks `chartType` in the same breath as the SQL, so the label and the rows can disagree. `_validate_and_autofix` exists purely to catch that, and when it can't, a second model call runs. |
| **Charts and text are separate systems.** | `/api/dashboards` and `/api/analysis` share nothing — not the plan, not the rows, not the entity resolution. Ask the same question on both surfaces and you can get two different players back. |
| **It targets a schema that no longer exists.** | `all_players_regular_2023_2024`, one Postgres table per season, `nba_advanced_*`, `court_shots` with lowercase `loc_x`. |

### It is dead right now

```
POST /api/dashboards {"question": "Show me the top 10 scorers in 2023-24"}
→ 400  cursor(): incompatible function arguments …
       Invoked with: <_duckdb.DuckDBPyConnection>; kwargs: cursor_factory=RealDictCursor
```

`interpret_question` calls `Executer.executor.get_connection()`, which now returns a DuckDB
connection, and hands it to `psycopg2`'s `RealDictCursor`. **Every dashboard request fails.**
Not degraded — every one. So there is nothing to preserve in flight; the question is only what
to build.

---

## 2. The insight that changes the design

The old pipeline needed an LLM to choose the chart because it had nothing else to go on: the
model wrote the SQL, so only the model knew what the columns meant.

**DataSport already knows.** By the time the analyst is called, there is a validated
`RouterPlan` and a pandas DataFrame:

```python
plan.entities        # who
plan.season_from/to  # over what span
plan.stat_focus      # which columns
plan.order_by        # what it is ranked by
plan.is_leaderboard()
plan.is_career_leaderboard()
plan.applied_floors  # what was filtered out, and why
plan.table
df                   # the actual rows, with real dtypes
```

Choosing a chart from that is a **pure function**. No model call, no repair round-trip, no
shape mismatch — the shape is an input, not a guess.

That deletes `_intent_hint`, `_post_process_sql`, `_validate_and_autofix`, the repair retry,
and the entire second GPT call. It also makes the chart and the sentence agree by
construction, because they are built from the same frame.

---

## 3. Design

### 3.1 `ChartSpec` — one contract

New module `backend/Visualizer/chart_spec.py`.

```python
@dataclass(frozen=True)
class FieldSpec:
    column: str          # real vault column, e.g. "FG3_PCT"
    label: str           # broadcast name, e.g. "3P%"
    unit: str | None     # "pct" | "per_game" | "count" | None
    precision: int = 1

@dataclass(frozen=True)
class ChartSpec:
    kind: ChartKind      # see the table below
    title: str
    x: FieldSpec | None
    y: list[FieldSpec]
    series: str | None   # column whose values split the rows into series
    rows: list[dict]     # already shaped for the renderer
    citation: str        # plan.citation() — provenance travels WITH the picture
    notes: list[str]     # applied floors, SAMPLE ONLY, coverage windows
```

`notes` matters more than it looks. A leaderboard filtered to "minimum 20 games played and at
least 2 three-point attempts per game" is answering a narrower question than the one asked,
and the chart has to say so in its own footer — a reader who only looks at the picture must
not be misled by it.

### 3.2 Selection — deterministic

| Plan / frame shape | Chart |
|---|---|
| `is_leaderboard()` · one season · one ranked stat | **leaderboard** — horizontal bars |
| 1 entity · multi-season · 1 stat | **trend** — line |
| ≥2 entities · multi-season · 1 stat | **compare_trend** — multi-line |
| 1 entity · one season · ≥3 numeric `stat_focus` | **radar** |
| ≥2 entities · one season · ≥3 numeric `stat_focus` | **compare_radar** |
| `is_leaderboard()` · exactly 2 numeric `stat_focus` | **scatter** |
| `table == "player_shot_chart"` | **shot_chart** — hex bins over LOC_X/LOC_Y |
| `is_career_leaderboard()` | **leaderboard** (aggregated rows) |
| anything else | **table** |

~60 lines. Every branch is testable without a network call, which the old one never was.

`table` as the fallback is deliberate: a chart that cannot be chosen confidently should not be
invented. Rendering the rows is always honest.

### 3.3 No extra model call

Titles and axis labels come from `stat_focus` plus the display-name map already in
`Analyzer.query_analyzer._rename_columns_for_display` (the one that turns `FG3_PCT` into
"3P%" for the prose). Same map, same names in the sentence and on the axis.

**Cost of charts: zero additional tokens.**

### 3.4 API

Extend the existing response rather than adding a parallel endpoint:

```jsonc
POST /api/analysis
{
  "success": true,
  "analysis": "Among players with at least 20 games…",
  "data":  [ … ],          // unchanged
  "charts": [ ChartSpec ]  // new
}
```

`POST /api/dashboards` becomes a thin wrapper returning only `charts` — for the chart-first
Dashboard tab. One pipeline, two projections. The old interpreter is deleted.

### 3.5 Working charts into the text

This is the part worth getting right, and the old system never attempted it: the analyst had
no idea a chart existed.

Give Call 2 a one-line summary of the spec and three rules:

> A **{kind}** chart of **{y labels}** by **{x label}** is displayed beside this answer.
>
> - Do not re-list values the chart already shows. Name the top result and then explain what
>   the shape means — the dip, the crossover, the outlier, the cluster.
> - Refer to what the chart shows, never to "the chart above" or "the graph".
> - State every applied threshold once, in the text. It also appears in the chart footer.

The prompt already forbids describing rows and columns; this extends the same principle to
the picture. The reader gets a number and a reason, not a transcription.

---

## 4. Frontend

`home-prototype` has most of this already:

- `components/ShotChartCourt.tsx` — hex binning, four colour modes (volume / accuracy /
  hotspots / coldspots), correct court geometry. Now fed by **real** `LOC_X`/`LOC_Y` from
  `player_shot_chart` instead of the seeded random spray it used to draw.
- Recharts is installed and `components/charts/` already renders trends, radars, scatters and
  leaderboards against staging data.

What is missing is one switchboard:

```
components/charts/AnalystChart.tsx     // switch (spec.kind) → the right renderer
```

The seven `ai_analyst` Recharts components are a reasonable starting point, but they take
`Record<string, unknown>[]` and read magic keys (`stat_value`, `x_value`, `full_name`). Re-type
them against `ChartSpec` so the renderer cannot silently look for a column that isn't there.

### Where charts appear

1. **Analyzer thread** — inline above the answer. The main one.
2. **`ChartDashboardSearch`** — currently renders "Soon". This is the chart-only path.
3. **Player / team profiles** — the surface already knows its subject, so it can seed a
   question ("Curry's 3P% by season") and render the chart with nothing typed.
4. **Game view** — already a shot chart; this makes it question-driven too.

---

## 5. Rollout

| Phase | Work | Done when |
|---|---|---|
| 1 | `ChartSpec` + selection + `charts[]` on `/api/analysis`. Render **leaderboard**, **trend**, **table** only. | "Who led the league in scoring in 2023-24?" shows bars beside the answer |
| 2 | `compare_trend`, `radar`, `compare_radar`, `scatter` | "Compare Jokic and Embiid in 2022-23" shows a radar |
| 3 | `shot_chart` from `player_shot_chart` | "Where does Curry shoot from?" draws his real 2015-16 attempts |
| 4 | Analyst prompt integration (§3.5) | The text points at the chart instead of restating it |
| 5 | Delete `DashboardBackend/`, repoint `/api/dashboards` | `psycopg2` gone from the runtime path |

---

## 6. Open questions

1. **More than one chart per answer?** `ChartSpec` is a list already. "Who led in points and
   who led in rebounds?" is naturally two leaderboards. Start with one; the contract allows
   two without a change.
2. **Does a chart need pinning?** Team45 had no persistence — every chart vanished on
   navigation. A saved-dashboard feature is a product decision, not a rendering one, and is
   out of scope here.
3. **Per-mode on charts.** A leaderboard on `Totals` and one on `PerGame` are different
   pictures. The plan carries `per_modes`; the spec should surface it in the subtitle so two
   screenshots are never confusable.
