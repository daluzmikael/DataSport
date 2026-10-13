# Cross-table querying — implementation plan

Deferred by design: single-table routing should feel right first. This is the plan for
when it does.

Today Call 1 returns `supported: false` for anything needing two tables, and the five
genuine cross-table questions in the edge-case battery were all correctly refused. The
machinery to *detect* the need already works — what is missing is the ability to act on it.

---

## Why it was taken out in the first place

Worth remembering before putting it back. The original design let the LLM write SQL
across a `measure_type` dimension and it produced binder errors against columns that
did not exist. The fix was to make the vault wide and the router pick exactly one table.

So the constraint that matters is not "never touch two tables" — it is **never let the
model write the join**. The plan below keeps SQL generation deterministic in Python and
only widens what the router is allowed to *ask for*.

---

## Shape of the change

Today's plan carries one table:

```json
{ "table": "player_season_stats", "entities": ["LeBron James"], ... }
```

Proposed: a list of **reads**, each of which is exactly the single-table plan that already
works, plus a declared join key.

```json
{
  "reads": [
    { "table": "player_season_stats",      "stat_focus": ["PTS", "REB", "AST"] },
    { "table": "player_estimated_metrics", "stat_focus": ["E_USG_PCT", "E_NET_RATING"] }
  ],
  "join_on": "player_season",
  "entities": ["LeBron James"],
  "season_from": "2023-24", "season_to": "2023-24"
}
```

Each read reuses `build_select_sql` unchanged. Nothing about the existing single-table
path changes; a one-read plan is the current behaviour.

## Join keys — a closed set, never free-form

The model picks a **named** join key from a fixed list. It never writes `ON` clauses.
Python owns the actual merge.

| Key | Columns | Joins |
|---|---|---|
| `player_season` | `PLAYER_ID`, `season`, `season_type` | season stats ↔ estimated metrics ↔ shot zones ↔ tracking |
| `team_season` | `TEAM_ID`, `season`, `season_type` | team stats ↔ standings ↔ estimated metrics ↔ shot zones |
| `player_game` | `PLAYER_ID`, `GAME_ID` | game logs ↔ game advanced |
| `team_game` | `TEAM_ID`, `GAME_ID` | team game logs ↔ team game advanced ↔ game context |
| `player_to_team_season` | `TEAM_ID`, `season`, `season_type` | a player's row ↔ their team's row (fan-out: many players → one team) |

Two constraints make this safe:

1. **Ids, never names.** `PLAYER_ID` / `TEAM_ID` are stable; joining on text would
   reintroduce every naming inconsistency the vault already has.
2. **Validate before executing.** Reject the plan if either table lacks the key columns,
   exactly as `validate_plan` already rejects bad `order_by`. A rejected join is a clear
   message, not a binder error.

## Execution

```
for each read:  build_select_sql  ->  DataFrame          (already works)
                       ↓
        pandas merge on the declared key columns
                       ↓
        one combined frame -> compute_bundle_aggregates  (already works)
                       ↓
                    analyst
```

`compute_bundle_aggregates` and the serializer need no changes — they take labelled
frames and do not care where the columns came from.

### Guards

- **Cap the fan-out.** `player_to_team_season` multiplies rows; cap the merged frame and
  carry `true_row_count` the way the single-table path now does.
- **Suffix collisions.** Both season tables have `GP`, `W`, `L`, `MIN`. Merge with
  `suffixes=("", f"__{table}")` so `GP` stays unambiguous, and teach
  `_select_analyst_columns` to keep suffixed forms.
- **Two reads maximum, at first.** Every question in the battery that needed a join
  needed exactly two. Three-table support can wait for a real example.

## Rollout

1. **`reads[]` accepting one element.** Pure refactor of the current path; the whole
   edge-case battery must produce identical answers. This is the risky step, so do it
   while nothing depends on it.
2. **`player_season` + `team_season` only.** Covers C1, C3, C5 from the battery
   (points vs usage, player vs team rating).
3. **Aggregate + serialize** over merged frames; extend the battery with cross-table
   cases and verify every number against DuckDB directly.
4. **Game-level keys** once season-level is trusted.
5. **Retire `unsupported_shapes`** entry by entry, only as each becomes genuinely
   supported. Keep rejecting what still is not.

## Definition of done

- Every existing single-table answer in the battery is byte-identical.
- C1–C5 answer correctly, each number verified against DuckDB.
- A join key missing from a table is refused with a specific message, not a stack trace.
- Merged-frame aggregates go through `compute_bundle_aggregates` — no LLM arithmetic,
  same rule as single-table.

## What this does not solve

Cross-table joins will not conjure stats the vault lacks. True shooting and PIE do not
exist at season grain in any table, so `STAT_NOT_IN_VAULT` stays the right answer for
those even after joins ship. The two failure modes need to stay distinct in the user-facing
message — conflating them is what made the original edge-case pass so misleading.
