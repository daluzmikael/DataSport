# Analyst pipeline — open problems

**Re-audited 2026-09-01** against the live `POST /api/analysis`, 46 questions, every
numeric claim checked against DuckDB directly.

The numbered sections below are the problems **as found**, kept verbatim so the symptom
and the evidence stay readable. The status table that follows says what has since been
fixed. The August version is archived at `EDGE_CASE_FINDINGS_ARCHIVE_2026-08-19.md`.

**Everything below was re-confirmed today.** The vault changed a lot since the last pass —
25 tables now, up from 17, and `player_season_stats` is 103,340 rows with all five
per-modes and the advanced columns staged — so this was re-run from scratch rather than
carried forward. Several previously-recorded problems are genuinely gone and are not
listed. Several below are **new**, created by the larger vault.

---

## Status — 2026-09-01 (later)

Fixed and re-verified against the live endpoint. Items keep their original numbers.

| # | Problem | Status |
|---|---|---|
| 1 | Rate-stat leaderboards had no qualifier | **fixed** — best net rating is Sam Hauser 14.2, not Neemias Queta; floors stated in the answer |
| 2 | All-time leaderboards cut off at 1996-97 | **fixed** — legacy staged; career assists leader is now John Stockton |
| 3 | "Wins versus losses" answered with team record | **fixed** — 27.5 pts in wins vs 24.6 in losses |
| 4 | Team names collided on substrings | **fixed** — "LA" now asks Lakers or Clippers |
| 5 | `player_on_off` names unreachable | **fixed** — 62,446 names rewritten to "Jayson Tatum" form |
| 6 | Five different date formats | **fixed** — all `YYYY-MM-DD`, still VARCHAR |
| 7 | `player_awards.SEASON` mixed formats | **fixed differently** — see below |
| 8 | `player_synergy` duplicates | **not a defect** — see below |
| 9 | Short-range table coverage unstated | **fixed** — refuses with the real window |
| 10 | `player_shot_chart` unguarded | **excluded from chat**, reserved for the dashboard |
| 11 | Cross-table refusals | **fixed** — team record is on the player row |
| 12 | Playoff standings misfiled as multi-table | **fixed** — Celtics 1st East, Thunder 1st West |
| 13 | Misspellings silently corrected | **fixed** — a substitution note is prepended |
| 14 | Router non-determinism | **retested — routing is stable** |

### Three that turned out differently than the brief

**#8 was my error, not a defect.** The 3,321 "duplicates" are the same player on
different teams within a season — Dennis Schröder has three 2024-25 rows for BKN, DET and
GSW. Including `TEAM_ID` in the key gives 88,523 rows and 88,523 distinct keys: zero true
duplicates, here or in any other staged table. Deleting them would have destroyed the
per-team splits. Nothing was changed.

**#7 could not be standardized without inventing facts.** The 334 bare-year rows are
Olympics (110 gold, 107 appearances, 52 bronze, 34 silver) and 31 Hall of Fame
inductions. The 2008 Beijing games fell between the 2007-08 and 2008-09 seasons and
belong to neither, so relabelling Chris Paul's gold medal as a season award would be
wrong. `SEASON` is unchanged; two derived columns make it queryable:
`SEASON_END_YEAR` (Int64 — the one year both formats agree on) and `IS_SEASON_AWARD`
(boolean). Ranges now work across the whole table without mixing the two kinds.

**#1 already had a partial system.** `Interpreter/floors.py` was handling games-played
and percentage-denominator floors. It had no entry for ratings, which is exactly the
Queta case — `NET_RATING` is already per-100-possessions and has no denominator to
floor, so it needs a minutes gate instead. That was added to the existing module rather
than built alongside it; a parallel qualifier I had started was removed to avoid
double-filtering.

### #2 — legacy data

`ingestion/pullers/legacy.py`. Three endpoints reach past the 1996-97 floor, all
verified live:

| Endpoint | Reach | Notes |
|---|---|---|
| `LeagueLeaders` | **1951-52** onward | ~30 box-score columns, one request per season per type |
| `PlayerCareerStats` | any era | Kareem's true 38,387 points and 1,560 games |
| `AllTimeLeadersGrids` | all-time | pre-ranked top-N per stat |

1946-47 through 1950-51 return nothing — that is NBA.com's own floor, not ours.

```bash
python -m ingestion.pullers.legacy --seasons 1951-52:1995-96   # ~90 requests
python -m ingestion.pullers.legacy --careers                   # long, resumable
python -m ingestion.pullers.legacy --all-time
```

Smoke-tested on 1962-63 through 1964-65: Wilt Chamberlain's 3,586-point 1962-63 season
pulled clean. Output lands in `data/raw/legacy/` and **nothing is staged** — the
1996-97+ tables are untouched, and staging is a separate decision. No advanced metrics
back there, because they did not exist; the counting line and percentages are what an
all-time question needs anyway.

### #10 — note for the dashboard

`player_shot_chart` (6,328,668 rows, one per shot, with LOC_X/LOC_Y coordinates) is now
hidden from chat routing via `CHAT_EXCLUDED_TABLES` in `Interpreter/router_plan.py`.
Clear that set when the dashboard is ready to consume it. `player_shot_zones` still
serves "what percentage does X shoot from the corner" in chat; the shot chart is for
plotting.

### #2 — staged 2026-09-03

Pulled and staged. Two new tables, registered in `STAGING_VIEWS` and in the catalog:

| Table | Rows | Coverage |
|---|---:|---|
| `legacy_season_stats` | 15,078 | 1951-52 → 1995-96, 45 seasons, RS + playoffs |
| `all_time_leaders` | 9,500 | 19 stat categories × top 500, every era |

**The headline fix, verified:**

| Question | Before | Now |
|---|---|---|
| most career assists | Chris Paul, 12,552 | **John Stockton, 15,806** |
| most career points | LeBron (right by luck); Kobe 2nd | LeBron, then **Kareem 38,387**, **Malone 36,928** |
| most career rebounds | not answerable | **Wilt 23,924**, Russell 21,620 |
| Wilt in 1961-62 | nothing | **4,029 points**, 80 games |
| MJ in 1995-96 | nothing | **2,491 points**, 82 games |

**Kept separate from `player_season_stats` on purpose.** That table is 289 columns of
modern box score plus advanced metrics; `LeagueLeaders` returns about 30 and none of the
advanced ones. Appending would have added ~15,000 rows that are NULL across 250 columns,
and every existing floor, rate leaderboard and aggregate would have started quietly
including rows with no denominator. The router picks between the two by season instead.

Three things the staging had to get right:

- **`career_scope` had to be disabled for `all_time_leaders`.** The first run summed
  `STAT_RANK` across all 19 categories per player and returned *Cam Spencer* as the
  career assists leader. Those rows are already career totals; aggregating them again is
  meaningless. `_ALREADY_CAREER_AGGREGATED` now blocks it.
- **A `STAT` row_filter is now required on that table.** Every category is stacked in one
  column, so an unfiltered read mixes points with free-throw percentage. Validation
  rejects the plan without it.
- **Totals-only wording.** These seasons have no per-game variant, and the analyst wrote
  "Michael Jordan averaged 2,491 points". The prompt now ties the verb to the per_mode:
  Totals gets "totalled" or "scored", never "averaged".

Nulls are meaningful here and left alone: `FG3M`/`FG3A`/`FG3_PCT` are null before
1979-80 because the three-point line did not exist, and steals/blocks/turnovers are null
before 1973-74. Writing 0 would make it look like players tried and missed.

`VAULT_SCHEMA.md` regenerated — 27 tables.

### Still open

- **Pre-1951-52 is genuinely unavailable.** NBA.com returns nothing for 1946-47 through
  1950-51; that is their floor, not ours. Questions about those five seasons refuse.
- **No advanced metrics before 1996-97.** True shooting, usage, PIE and the ratings were
  never recorded, so an advanced question about Wilt or Russell is correctly unanswerable
  rather than estimated.
- **Career totals endpoint not pulled.** `--careers` (per-player `PlayerCareerStats`)
  remains unrun; `all_time_leaders` covers the leaderboard questions, so it is only
  needed if you want a specific player's full pre-1997 career line.
- **Prose varies run to run.** #14 confirmed routing, row counts and figures are stable
  across repeats; only sentence construction changes.

---

## The pattern

Same shape as before, in a new place. The pipeline is accurate when DuckDB does the work,
and unreliable at the boundaries where **nothing asserts what the data cannot say**.

Every wrong answer below is confidently phrased, cleanly formatted, and cites a source.
None of them look wrong.

---

## P0 — Silent wrong answers

### 1. Rate-stat leaderboards have no qualifier, so they return end-of-bench players

The worst problem right now, and it is new: the advanced columns only became queryable in
the recent restage, and nothing gates them by playing time.

| Question | Answer given | Should be |
|---|---|---|
| "Who had the best net rating in 2023-24?" | **Neemias Queta** | Sam Hauser, 14.2 |
| "Which Celtics player had the best net rating in 2023-24?" | **Neemias Queta**, 20.4 | a rotation player |

Straight from the vault, unqualified:

```
NET_RATING leaders 2023-24                TS_PCT leaders 2023-24
  Malcolm Cazalon     83.3   1 GP,  2.6 min    Drew Peterson  .917   3 GP,  7.6 min
  Markquis Nowell     66.1   1 GP,  3.5 min    D.J. Wilson    .833   2 GP,  7.7 min
  Izaiah Brockington  50.0   1 GP,  3.4 min    Jordan Ford    .761   6 GP,  3.6 min
```

With an NBA-style qualifier (`GP >= 58 AND MIN >= 20`) the same queries return Sam Hauser
14.2 and Daniel Gafford .731 — real answers.

The analyst does say "among players with at least 20 games played", so a floor exists
somewhere, but 20 games is far too low for a rate stat and is clearly not applied to the
ranking anyway — Queta played 28 games. Every ratio column is affected: `TS_PCT`,
`EFG_PCT`, `NET_RATING`, `OFF_RATING`, `DEF_RATING`, `PIE`, `USG_PCT`, and every `FG_PCT`
variant. Counting stats (PTS, REB, AST) are fine.

### 2. All-time and career leaderboards are silently cut off at 1996-97

The vault starts at 1996-97. Any question phrased "in NBA history", "all-time" or "career
leader" is answered from that window as if it were the whole record, with no caveat.

> "Who has the most career assists?" → **"Chris Paul has the most career assists with 12,552."**

John Stockton is the real answer at 15,806. He *is* in the vault, but only for 1996-97
through 2002-03, which records **4,496** of them — so he ranks nowhere near a list he
should lead.

"Who has scored the most points in NBA history?" returns LeBron at 43,440, which happens
to be correct, but the rest of that top five is not: Kareem Abdul-Jabbar and Karl Malone
are absent entirely, and Kobe Bryant is promoted to second.

Being right by luck on the most famous case is what makes this dangerous — it looks
reliable in exactly the demo anyone tries first.

### 3. "Wins versus losses" is answered with the team's win-loss record

> "How does Jayson Tatum play in wins versus losses in 2023-24?"

Routed to `player_season_stats`, one row, answered with **"57 wins, 17 losses, a .770 win
percentage, 26.9 points"** — his team's record, not a split of his performance.

The question needs `player_game_logs` filtered on `WL`, which exists and works when routed
correctly. Two different meanings of "wins" get conflated and the user is handed the wrong
one with no sign of it.

### 4. Team names still collide on substrings when they cannot be resolved

> "How did LA do in 2023-24?" → 8 teams matched, answered as **"LA went 47-35"**.

```sql
... WHERE season = '2023-24' AND (STRIP_ACCENTS(TEAM_NAME) ILIKE '%LA%')
```

`%LA%` reaches Dal**la**s, At**la**nta, Port**la**nd, Or**la**ndo, Cleve**la**nd,
Phi**la**delphia and Ok**la**homa City alongside the two Los Angeles teams.

The mechanism: "LA" no longer matches any team name exactly, so resolution fails and the
query falls back to substring matching. That fallback exists so partial names still find
something — but when it matches eight different teams, the ambiguity is never surfaced.
Named teams ("Lakers", "Sonics", "Seattle SuperSonics") all resolve correctly now; it is
specifically unresolvable input that fails quietly.

---

## P1 — Answerable questions that return nothing

### 5. `player_on_off` stores names as "Tatum, Jayson" — every other table uses "Jayson Tatum"

> "How do the Celtics perform with Jayson Tatum on the court in 2023-24?"
> → 0 rows: *"No player named Jayson Tatum is in `player_on_off`. Either the spelling is
> off, or they played before 1996-97…"*

Both suggested reasons are wrong. He is in the table, as `'Tatum, Jayson'`.

```
player_on_off        'Tatum, Jayson'      <- LAST, FIRST
player_season_stats  'Jayson Tatum'
player_awards        'Jayson Tatum'
player_bio           'Jayson Tatum'       (DISPLAY_FIRST_LAST)
team_roster          'Jayson Tatum'       (PLAYER)
player_synergy       'Jayson Tatum'
```

`player_on_off` is 62,626 rows and the only on/off data in the vault, so the whole table is
currently unreachable by name. It is also the newest table, so this has likely never
worked.

---

## P2 — Data and format inconsistencies

### 6. `GAME_DATE` has two different formats, and neither is a date

```
player_game_logs.GAME_DATE    VARCHAR  '1997-06-13T00:00:00'
team_game_logs.GAME_DATE      VARCHAR  '1997-06-13T00:00:00'
player_shot_chart.GAME_DATE   VARCHAR  '19970425'
```

All three are VARCHAR, so every date comparison is a string comparison. That happens to
work for the ISO-ish format, but a filter like `GAME_DATE >= '2024-01-01'` matches
**nothing** on `player_shot_chart` — `'20240101'` and `'2024-01-01'` never compare equal.
Any date-bounded question against the shot chart returns empty, with no error.

### 7. `player_awards.SEASON` mixes two season formats

334 of 5,722 rows use a bare year (`'1960'`, `'1964'`, `'2024'`); the rest use NBA labels
(`'1964-65'`, `'2025-26'`). Lexicographic range filters mix the two: a range over
2019-20..2021-22 also swallows the bare `'2020'` and `'2021'` rows.

There is handling for this in the SQL builder, but it is a special case carried for one
table and will break again if another table adopts the same mixed convention.

### 8. `player_synergy` carries about 3.8% duplicate rows

88,523 rows against 85,202 distinct
`(PLAYER_ID, season, season_type, play_type, type_grouping, per_mode)` keys — roughly 3,300
duplicates. Any count or average over synergy data is slightly wrong, in a way too small to
notice and too large to ignore.

(The offensive/defensive pair per play type is *not* the cause — that is legitimate and was
checked.)

---

## P3 — Coverage that is not surfaced

### 9. Several tables cover far less than the vault's 1996-97 → 2025-26 span

| Table | Actual coverage |
|---|---|
| `player_synergy` | **2015-16** → 2025-26 |
| `player_on_off` | **2007-08** → 2025-26 |
| `lineups` | **2007-08** → 2025-26 |
| tracking, most slices | **2013-14** → 2025-26 |
| tracking, CatchShoot / PullUpShot | 1996-97 → 2025-26 |
| `hustle_*` columns | 1998-99 → 2025-26, sparse |
| `player_awards` | **1960** → 2025-26 (earlier than everything else) |

Season-boundary questions against `player_season_stats` and tracking now explain themselves
correctly. The newer tables have not had the same treatment, so a synergy question about
2010 or an on/off question about 2001 has nothing to say for itself.

`player_awards` reaching back to 1960 creates the opposite asymmetry: the vault can name the
1985 MVP but holds no statistics from that season to discuss.

### 10. `player_shot_chart` is 6.3M rows with no stated guardrail

By far the largest table at 6,328,668 rows — roughly 8x the next largest. Game logs have an
explicit scope guard that rejects unbounded career-wide pulls. The shot chart has no
equivalent, and it is one row *per shot*.

---

## P4 — Known limits, unchanged

### 11. Cross-table questions are still refused

Working as designed, correctly rejected:

- "How do Jokić's per game stats compare to the Nuggets' record?"
- "Compare Curry's points per game to the Warriors' offensive rating"

The restage moved this boundary: several questions that used to need two tables (scoring vs
usage, points vs true shooting) are now single-table and answer fine. What remains is
genuinely player-table-plus-team-table. `CROSS_TABLE_PLAN.md` covers the approach.

### 12. One rejection is still misfiled

> "What were the playoff standings in 2023-24?" → *"needs data from more than one table"*

It does not. `team_standings` is Regular Season only — a single-table coverage limit
reported as a multi-table limitation, pointing the user at the wrong explanation.

### 13. Misspellings are silently corrected

"Yanis Antetokounmpo" answers as Giannis Antetokounmpo with no mention of the correction.
Usually the desired behaviour, but it means a wrong-player match looks identical to a right
one. Worth a word in the answer whenever the resolved name differs from what was typed.

### 14. Router determinism not re-measured

The previous pass found Call 1 producing materially different plans for identical input at
`temperature=0`. Not re-tested this round — the question that exposed it is now rejected on
other grounds, so it needs a fresh probe rather than an assumption.

---

## Verified working — do not regress these

Re-confirmed today, exact against DuckDB:

- **Career totals** — LeBron 43,440 pts / 12,095 reb / 12,016 ast / 1,622 games
- **All five per-modes** — PerGame, Totals, Per36, Per40, Per100Possessions
- **Advanced stats at season grain** — LeBron TS% 63.0%, Jokić PIE 0.211, Embiid usage 38.7%
- **Team names** — Lakers, Seattle SuperSonics, and colloquial "Sonics" all resolve
- **Game-log splits** — "against the Bulls at home" 32 rows / 26.3 pts; "over 35 minutes" 473 rows / 28.5 pts
- **Game-log scope guard** — unbounded career pulls rejected with worked examples
- **Player disambiguation** — "Morris" asks across 11 candidates; "Curry" → Stephen; "Shaq" / "KD" expand
- **New tables** — awards (Wembanyama ROY; LeBron 4 MVPs, correctly separated from Finals MVP),
  bio (7-4), roster (17 Celtics), synergy (Jokić 1.28 PPP pick-and-roll),
  franchise history (3,751-2,527, .597)
- **Role questions refused** — "best sixth man" and "best rookie" decline instead of ranking by points
- **Season-boundary messages** — 1995, drives in 2005-06, deflections in 1997-98 all explain themselves
- **Off-topic denial** — injection, general knowledge and gibberish all refused at routing

---

## Suggested order

1. **#1 rate-stat qualifiers** — one WHERE clause on ratio columns. Every advanced
   leaderboard is currently wrong, and these are exactly the questions the new columns invite.
2. **#5 `player_on_off` names** — an entire table is unreachable.
3. **#2 all-time scope** — either state the 1996-97 floor in the answer or refuse the framing.
4. **#3 wins/losses routing** and **#4 unresolved-team ambiguity** — both produce confident wrong answers.
5. **#6, #7, #8** — data hygiene. #6 is the one that fails silently.
6. **#9, #10** — coverage metadata for the newer tables.
7. **#12, #13, #14** — small.
