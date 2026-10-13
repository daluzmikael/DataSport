# Shot charts in chat answers — plan

**Status:** plan. The radar default fix is done and verified; this is the next step.

## Context

The chart layer is live: `backend/Visualizer/` picks a `ChartSpec` from the router plan with
no extra model call, `/api/analysis` returns `charts[]`, and `AnalystChart.tsx` renders it.
Six kinds ship today — leaderboard, trend, compare_trend, radar, compare_radar, scatter, plus
a table fallback. Shot charts are the one Team45 kind still missing.

**Most of this already exists.** The work is smaller than it looks:

| Piece | State |
|---|---|
| `player_shot_chart` | **Staged**, 6,328,668 rows, **1996-97 → 2025-26** — the full vault range |
| `ShotChartCourt.tsx` | **Complete** — real hexbin, correct court geometry, 4 modes, interactive toggle |
| `ShotPoint` / `HexBin` types | **Defined** (`src/data/schema/shots.ts`, `ShotChartCourt.tsx`) |
| Wiring into chat | **Missing** — this plan |

The vault columns are `LOC_X, LOC_Y, SHOT_MADE_FLAG, SHOT_ZONE_BASIC, SHOT_ZONE_AREA,
SHOT_DISTANCE, ACTION_TYPE, SHOT_TYPE, PERIOD, GAME_DATE, season, season_type`. Coordinates
run x ∈ [-250, 250], y ∈ [-51, 842] (tenths of a foot, origin at the basket) — exactly the
frame `ShotChartCourt` already draws.

### "Shot chart" and "heatmap" are one renderer, not two

`ShotChartCourt` bins shots into hexes and colours them by one of four modes:

| Mode | `chartKind` | Question it answers |
|---|---|---|
| `volume` | heatmap | Where does he shoot from? |
| `accuracy` | heatmap | How well does he shoot from each spot? |
| `hotspots` | zones | Where is he best? |
| `coldspots` | zones | Where does he struggle? |

So there is **one new `ChartSpec` kind** (`shot_chart`), not two. The mode is a presentation
toggle the component already owns.

---

## The three real problems

### 1. The router cannot reach the table

`player_shot_chart` is in `CHAT_EXCLUDED_TABLES` (`Interpreter/router_plan.py:220`), which
`chat_visible_tables()` filters out of the router prompt and `validate_plan()` rejects. The
comment there anticipates exactly this moment:

> *Reinstate by clearing this set once the dashboard/chart integration lands and there is a
> real consumer for it.*

Removing it is one line. What it was protecting against is problem 2.

### 2. Scope — solved by binning server-side, not by refusing

An earlier draft of this plan proposed refusing unscoped requests. That was wrong, and the
measurement says why. The hex grid has a **fixed ceiling**: a half court divided by
`HEX_RADIUS = 8` is about 1,200 cells, no matter how many shots land in it.

| Scope | Shots | Hex cells | Payload |
|---|---|---|---|
| Curry, 2015-16 | 1,936 | 534 | ~15 KB |
| Kobe, entire career | 30,699 | 983 | ~27 KB |
| LeBron, entire career | 37,669 | 1,057 | ~29 KB |
| **Whole league, 2023-24** | **232,540** | **1,200** | **~33 KB** |

Binning in SQL/pandas before the response makes a 232,540-shot read cost *less on the wire*
than a single season of raw rows, and it removes the `ENTITY_ROW_CAP` truncation problem
entirely — nothing is truncated, because nothing large is ever sent.

Nothing is lost by binning early. `buildHexBins` produces `{x, y, made, total}` per cell, and
**all four modes are computed from `made` and `total`** — volume from `total`, accuracy from
`made/total`, hotspots/coldspots from the top and bottom 35% of qualified cells. The aggregate
is sufficient for every view.

The only guard still worth having is on the *read*, not the answer: bin inside the query so
DuckDB aggregates 6.3M rows down to ~1,200 rather than materialising them in pandas.

### 3. Coordinates must never reach the analyst prompt

`_serialize_bundles_for_analyst` (`Analyzer/query_analyzer.py:1914`) would feed 1,598 rows of
`LOC_X/LOC_Y` into Call 2. That is expensive and useless — the model cannot read coordinates,
and it would burn the budget that should go to the answer.

**Fix:** intercept `player_shot_chart` bundles and pass a computed summary instead, built in
pandas (which is where all arithmetic already happens, per the analyst prompt's own rules):

```
Shot profile — Stephen Curry, 2015-16 Regular Season
  Total FGA 1,598 · FG% 50.4
  Restricted Area      264 FGA  ·  67.4%
  Above the Break 3    646 FGA  ·  45.4%
  Mid-Range            141 FGA  ·  41.8%
  ...
```

Seven zone rows from `SHOT_ZONE_BASIC` instead of 1,598 coordinate rows. The analyst can
actually write about that, and the chart and the prose again come from the same frame.

---

## Design

### ChartSpec

Add one kind and one field:

```python
ChartKind = Literal[..., "shot_chart"]

class ChartSpec(BaseModel):
    ...
    mode: str | None = None   # volume | accuracy | hotspots | coldspots
```

**Row contract** — one hex cell per row, already aggregated:

```
shot_chart   {x, y, made, total}
```

These are court coordinates, not SVG pixels: the renderer keeps its own `toSvg` transform so
the court geometry stays in one place.

### Selection

One rule, checked **first** in `_select` (before the leaderboard/scatter branches, since a
shot-chart plan has no ranked stat):

| Condition | Kind |
|---|---|
| `plan.table == "player_shot_chart"` and the frame has `LOC_X`/`LOC_Y`/`SHOT_MADE_FLAG` | `shot_chart` |

`mode` defaults to `volume`. **No mode inference from the question** — Team45 carried ~30
regex synonyms just for shot charts (`"hot zones"`, `"money spot"`, `"where can't he shoot"`),
and that is precisely the guessing this architecture removed. Instead the component shows all
four toggles (see below), so the reader gets every view without anyone parsing phrasing.
Deriving a *default* mode from `plan.topic` is a later refinement, not a prerequisite.

`notes` carries the season/season-type scope and the FGA count, as every other kind does.

### Frontend

`AnalystChart.tsx` gains one case:

```tsx
case "shot_chart": {
  const bins = spec.rows as unknown as HexBin[]
  return (
    <ShotChartCourt
      bins={bins}
      playerName={spec.series ?? ""}
      subtitle={spec.subtitle ?? undefined}
      defaultMode={(spec.mode as ShotChartMode) ?? "volume"}
      modes={["volume", "accuracy", "hotspots", "coldspots"]}
    />
  )
}
```

Three small, backwards-compatible edits to `ShotChartCourt.tsx`:

1. **Accept pre-binned cells.** Split `buildHexBins(shots, radius, mode)` into `binShots()`
   and `applyMode()`, and add a `bins?: HexBin[]` prop taken instead of `shots` when present.
   `applyMode` still runs client-side, so the mode toggle stays instant. The header's FGA and
   FG% come from `sum(total)` / `sum(made)` rather than `shots.length`. Existing callers pass
   `shots` and are unaffected.
2. **New optional `modes?: ShotChartMode[]` prop.** Today `modeOptions` is derived from
   `chartKind` and offers only two of the four. Chat should offer all four, since we are
   deliberately not inferring which one was wanted. Defaults to current behaviour.
3. **Theme tokens.** It hardcodes `rgba(255,255,255,…)` in 4 places and the app is now a
   single light theme (`--color-ds-text: #201f1d`), so its labels are invisible — the same
   bug fixed in the other five chart components. Swap to `var(--color-ds-*)`.

Edit 3 also fixes the shot charts already on the player-profile and game-detail surfaces
(`PlayerChartsSection.tsx`, `PlayerGameDetail.tsx`), which have the invisible-label bug today.

---

## Steps

1. `Visualizer/chart_spec.py` — add `shot_chart` to `ChartKind`, add `mode`.
2. `Visualizer/shaping.py` — `shape_shot_chart(df)` → hex cells. Bin with the same
   geometry the renderer uses (`HEX_RADIUS = 8`, `toSvg`), so server and client agree.
3. `Visualizer/selector.py` — the branch, first.
4. `Interpreter/router_plan.py` — empty `CHAT_EXCLUDED_TABLES`; make sure the table's catalog
   entry in `table_catalog.yaml` describes it usefully for the router prompt.
5. `Interpreter/sql_builder.py` — bin inside the SELECT for `player_shot_chart` (GROUP BY the
   hex column/row expression) so DuckDB returns ~1,200 rows instead of up to 6.3M, and
   `ENTITY_ROW_CAP` never bites.
6. `Analyzer/query_analyzer.py` (or `Analyzer/aggregates.py`) — zone summary instead of raw
   coordinate rows.
7. `src/api/chartSpec.ts` — `shot_chart` kind, `mode` field, `ShotChartRow`.
8. `src/components/ShotChartCourt.tsx` — `modes` prop + theme tokens.
9. `src/components/charts/AnalystChart.tsx` — the case.
10. `tests/test_chart_selector.py` — selection, the hex row contract, and that binning a known
    set of coordinates lands in the cells the renderer would have chosen.

## Verification

```powershell
cd c:\Users\mikae\Coder\DataSport\DataSport\backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -q --ignore=tests/test_compare_edge_cases.py
```

Then, live:

| Question | Expected |
|---|---|
| "Where does Stephen Curry shoot from in 2015-16?" | `shot_chart`, ~1,598 rows, hexes over the arc |
| "Show me Curry's hot zones in 2015-16" | `shot_chart`; hotspots reachable from the toggle |
| "Where does LeBron James shoot from?" (no season) | Career chart, ~1,057 cells — **works**, as it did in Team45 |
| "Where did the league shoot from in 2023-24?" | ~1,200 cells from 232,540 shots |
| "Where does Curry shoot from in the 2016 playoffs?" | `season_type=Playoffs` honoured in the scope |

Visual checks in the browser: labels legible on the light theme, all four mode toggles
switch, the arc and restricted area look right for a known shooter (Curry should be heavy
above the break; Giannis heavy in the restricted area), and the prose talks about zones
rather than restating coordinates.

## Not in this pass

- **`player_shot_zones`** (41,326 rows, pre-aggregated into the same seven zones) is the
  honest answer for career-scope questions where XY is too big to read — "which zone is Curry
  best from all-time". A natural follow-on once the XY path is solid, and it reuses the zone
  summary from step 6.
- **Team shot charts** — `team_shot_zones` is staged (2,744 rows) but there is no team XY
  table, so team questions would need the zone renderer above.
- **Mode inference** from `plan.topic`, once there is evidence the four-way toggle is not
  enough.
