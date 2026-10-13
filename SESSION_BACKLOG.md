# SESSION-BACKLOG

> **For the agent:** When the user says "continue tomorrow" or references this backlog, read this file first.  
> Related: `frontend/home-prototype/src/components/playerChartsAiTodo.ts` (chart AI wiring).

**Site:** https://team45seniordesign.vercel.app/ (`weblink.txt`) — `ai_analyst` (Next.js) deploys to Vercel.  
**Prototype:** `frontend/home-prototype` (Vite) — local/new UI shell; confirm which app gets deployed when staging.

**Analyst pipeline (2026):** `/api/analysis` defaults to `INTERPRETER_PIPELINE=router` — Call 1 JSON router → Python SQL builder → Call 2 multi-table analyst. Set `legacy` for old LLM SQL path. Firebase re-setup is a separate parallel task (`FIREBASE_API_KEY`, new project config in `auth.py` + frontend).

---

## 0. Prompt rework for the new wide schema — DONE (needs edge-case testing)

Call 1 and Call 2 were rewritten against the **actual** staged parquet schema (17 wide tables).

> **SUPERSEDED 2026-08-19 by the restage — see §0b below.** The paragraph immediately
> following was true of the *staged file*, not of the pull. TS%, eFG%, USG% and PIE had
> been pulled into raw the day after staging last ran, and are now columns on
> `player_season_stats` / `team_season_stats`. Kept for the history of the decision.

**Schema finding that changed the design:** `player_season_stats` / `team_season_stats` have
**no `measure_type` column** — the new schema merged base + `clutch_*` + `hustle_*` + `*_RANK`
into one wide row. So season-level **TS%, eFG%, USG%, PIE, OFF/DEF/NET rating, PACE do not
exist**. Season-level advanced lives in `player_estimated_metrics` / `team_estimated_metrics`
(`E_` prefixed); the full classic advanced set only exists on `lineups` (5-man) and at game
level in `player_game_advanced`. The old `category_map.yaml` claimed otherwise and was the
source of the `measure_type not found` binder errors.

**What the router does now:** exactly ONE table per question (no joins, no unions);
season *ranges* via `season_from`/`season_to` (multi-season is one read, which is what used
to break); `supported:false` + reason for genuine two-table questions; `stat_focus` names the
columns in question and prunes what Call 2 reads; one repair retry on SQL error, then logs
the error and returns empty.

**Debug terminal output (kept, as requested):**
- `ROUTER PLAN` block per question — table, seasons, per_modes, entities, stat_focus, order_by
- `[ROUTER SQL] <label>` + the full SQL
- `TABLES ACCESSED: <table>` + `label -> N rows x M cols`
- `Routed query OK | <citation> | bundles=N`

- [ ] **Artifact idea:** a viewer for the `TABLES ACCESSED` / router-plan log so routing is
      inspectable without scrolling the terminal.
- [ ] Edge-case pass on the new prompts (weird seasons, playoffs, obscure players, team vs player ambiguity)
- [ ] Tune analyst answer length once the shape feels right
- [ ] Then: fold dashboard/chart generation into the text answers

**Now-unused, left on disk (untracked, so deleting is unrecoverable):**
`backend/Interpreter/category_map.yaml` and `backend/tests/fixtures/paint_defender_plan.json`
both describe the OLD schema — superseded by `backend/Interpreter/table_catalog.yaml`.

---

## 0b. Season tables restaged with advanced columns — DONE (2026-08-19)

The staged season tables were built on 2026-06-10 from a **Base-only** pull. An extended
pull the next day wrote Advanced / Usage / Misc / Scoring / Defense into
`data/raw/<table>/<season>/`, and staging never ran again. So TS%/eFG%/USG%/PIE were on
disk for two months while the app reported them as missing. **No re-pull was needed.**

`_merge_season_folder` (`backend/ingestion/stagers/phase1.py`) was rewritten from
"concat every dash file as a row" to "**Base spine + column-wise left joins**", which is
what keeps the wide grain. Run with:

```powershell
cd c:\Users\mikae\Coder\DataSport\DataSport\backend
.\.venv\Scripts\Activate.ps1
python -m scripts.restage_season_stats --dry-run   # inspect first
python -m scripts.restage_season_stats             # backs up, then rewrites
```

| | Before | After |
|---|---|---|
| `player_season_stats` | 41,336 × 162 | **41,336 × 289** |
| `team_season_stats` | 2,741 × 129 | **2,741 × 209** |

Grain unchanged, no `measure_type`, `per_mode` still PerGame/Totals only. Only these two
tables were touched — phases 2–6, standings and shot zones were not restaged.

**Now answerable from ONE row:** `TS_PCT`, `EFG_PCT`, `USG_PCT`, `PIE`, `OFF_RATING`,
`DEF_RATING`, `NET_RATING`, `PACE`, `POSS`, `AST_PCT`, `AST_TO`, `AST_RATIO`, `OREB_PCT`,
`DREB_PCT`, `REB_PCT`, `TM_TOV_PCT`, the `E_*` twins, the `PCT_*` usage-share family
(player only — NBA publishes no team Usage slice), Misc points breakdowns, Scoring
distribution, and `DEF_WS`. Each with its `*_RANK`.

Team identity is canonical on write: `LA Clippers` → `Los Angeles Clippers`. Historical
franchises are era-protected — a 2005-06 row still says Seattle SuperSonics.

**Two traps found the hard way, both now handled in code:**

1. Legacy `dash_<st>_<pm>.parquet` files are *usually* byte-identical to the canonical
   `dash_<st>_base_<pm>.parquet`, but not always — 2016-17 team playoffs totals is 15
   rows canonically vs 16 legacy, missing Utah. The loader unions them. Never glob
   `dash_*.parquet`; that double-counts every Base row.
2. Normalizing team names by `TEAM_ID` alone rewrites history, because a franchise keeps
   its id through relocation. `ingestion/team_identity.py` is era-aware for this reason.

**Still deferred:** Per36 / Per40 / Per100Possessions are pulled and sitting in raw. They
mean extra *rows*, so that is a separate per_mode decision — see the `_PER_MODES` constant
in `phase1.py`.

**Docs updated to match:** `table_catalog.yaml`, `VAULT_SCHEMA.md` (regenerate with
`python -m scripts.generate_vault_schema`), the router prompt in `router_plan.py`, and the
legacy prompt in `staging_query.py` (it was telling the model to filter
`measure_type = 'Advanced'`, which is now a binder error).

---

## 1. Pull → stage → deploy → next pull

**Goal:** Ship current work, verify on live site, then pick up the next PR/branch.

- [ ] `git pull` / review open PRs and CI
- [ ] When PR is ready: merge or finish review, then **stage** changes for deploy
- [ ] **Deploy / upload to site** (Vercel — `frontend/ai_analyst`; backend if separate)
- [ ] Smoke-test production URL
- [ ] Check for **next pull** / next branch and repeat

*No automated deploy config in repo root — confirm Vercel project + env vars (`FIREBASE_*`, `NEXT_PUBLIC_API_URL`) before push.*

---

## 2. Team page — layout, tabs, linking

**Goal:** Reorganize team profile; tab nav at top; deep links everywhere.

### Current state (`frontend/home-prototype`)

| File | What it does today |
|------|-------------------|
| `src/components/TeamDetail.tsx` | Single scroll: header → leaders → game log → history → roster + top GS grid |
| `src/components/TeamSeasonLeadersSection.tsx` | Standing, record, best GS, season leaders |
| `src/components/TeamSeasonGameLogTable.tsx` | Season game log |
| `src/components/TeamRosterSection.tsx` | Roster by season |
| `TeamDetail` inline section | **Top game scores** (mock `profile.gameScoreLeaders`) |

Player/team names mostly use `ReferencedLabel` → **AI reference only**, not navigation.

### To do

- [ ] **Top tab nav** on team profile (e.g. Overview · Leaders · Game log · Roster · Top game scores · Charts?)
- [ ] Move **top game scores** and **roster** into tabs (or agreed layout)
- [ ] Add **team-relevant chart types** (mirror player charts / `TeamGameChartsSection` patterns where useful)
- [ ] **Link every player name** → `onOpenPlayer(id)` / `DetailTarget { type: "player", id }`  
  - Use `resolveNbaPlayerId` / `mockPlayerIdFromNba` from `src/api/nbaIds.ts`
- [ ] **Link every game log row** → `onOpenGame(gameId)`  
  - Pattern exists on `TeamSeasonGameLogTable` (`onOpenGame`) — wire through `TeamDetail` props from `DetailOverlay`
- [ ] Pass `onOpenPlayer`, `onOpenGame`, `onOpenTeam` through `TeamDetail` (today only `onOpenGame` + `onReference`)

---

## 3. Game screens — linking, charts, live readiness

**Goal:** Full navigation mesh; relevant charts; stub live pipeline.

### Current state

| File | Notes |
|------|--------|
| `src/components/DetailOverlay.tsx` | Game / player-game / team / player overlays; has `onOpenPlayer`, `onOpenTeam`, `onOpenGame` |
| `src/components/GameScoreboard.tsx` | Scoreboard |
| `src/components/TeamBoxScoreTable.tsx` | Box score |
| `src/components/charts/TeamGameChartsSection.tsx` | Team game charts |
| `src/components/charts/TeamGameShotChart.tsx` | Shot chart |
| `src/components/PlayerGameDetail.tsx` | Player single-game view |
| `src/hooks/useStagingGame.ts` | Vault game reads |

Names often **not** clickable to profiles; teams not linked to team pages.

### To do

- [ ] **All player names** in box scores, PBP, charts → player profile overlay
- [ ] **All team names** → team profile (`teamProfileIdFromAbbr` in `src/data/liveDashboardFeed.ts`)
- [ ] **Add chart types** relevant to game context (shot chart, compare radar, paint/FT scatter — extend `TeamGameChartsSection`)
- [ ] **Live endpoint prep** (no live API in `backend/api` yet):
  - [ ] Define staging/live routes (e.g. `GET /api/live/scoreboard`, `GET /api/live/games/{id}`)
  - [ ] Hook shape in `useStagingGame` or new `useLiveGame` with polling/WebSocket placeholder
  - [ ] **Player live game pages** — same hook contract when game is live
  - [ ] **Live dashboard** (`LiveDashboard.tsx`, `buildLiveDashboardFeed`) — swap mock `LIVE_FEED` for API when ready

---

## 4. Saved chats + sign-in (Firebase)

**Goal:** Real auth and persisted chats in `home-prototype`, aligned with existing backend.

### Existing infrastructure

| Layer | Location |
|-------|----------|
| Backend auth + RTDB | `backend/auth.py` — `hq-users` Firebase, `histories/{uid}/{conversationId}` |
| Backend API | `backend/main.py` — `conversationId`, `list_conversations`, `get_conversation_messages`, analyze with history |
| ai_analyst (working reference) | `frontend/ai_analyst/context/auth-context.tsx`, `components/app-sidebar.tsx`, `app/chat/[id]/page.tsx` |
| home-prototype (mock) | `LoginGate.tsx` — fake submit; `ChatSidebar.tsx` + `data/mock.ts` threads; **no Firebase** |

### To do

- [ ] Create/configure **new Firebase key** (or separate RTDB path) for DataSport prototype if needed
- [ ] Wire `LoginGate` → `sign_up` / `log_in` backend endpoints (or client Firebase Auth like ai_analyst)
- [ ] Replace mock `CHAT_THREADS` / `SAMPLE_MESSAGES` with `list_conversations` + message load/save
- [ ] Port sidebar behavior from `ai_analyst/components/app-sidebar.tsx` (new chat, delete, title)
- [ ] Env: `FIREBASE_API_KEY`, `NEXT_PUBLIC_*` equivalents for Vite (`import.meta.env`)

---

## 5. Past games stream in sidebar

**Goal:** Full past season of games in live board sidebar — prove vault scale.

### Current state

- `LiveDashboard.tsx` — "Live now" + `PAST_DASHBOARD_DAYS` from `data/pastDashboardMock.ts` (few mock days)
- Followed teams/players prioritized via `buildLiveDashboardFeed` + `favoritesMock` / `FavoritesPage`

### To do

- [ ] Load **whole past season** (or configurable range) from staging — team game logs / schedule API
- [ ] Prefer **followed teams + players only** (filter client- or server-side)
- [ ] Group by date in sidebar (keep sticky day headers pattern)
- [ ] Virtualize or paginate if list is long
- [ ] Verify tap → `DetailOverlay` game view with vault data

---

## 6. AI integration across pages

**Goal:** Every surface that should talk to the analyzer actually does.

### Current patterns

| Pattern | File | Status |
|---------|------|--------|
| Footer ask bar | `DetailOverlay` → `onAsk` / `askDraft` | Mock replies in `App.tsx` `handleSend` |
| Reference magnifying glass | `AskReferenceButton` / `ReferencedLabel` | Prefills `[label]` in ask draft |
| Per-chart AI search | `ChartDashboardSearch.tsx` | Read-only, **Soon** badge |
| Chart AI backlog | `playerChartsAiTodo.ts` | Wire → `POST /api/dashboards` |
| Analyzer panel | `AnalyzerPanel.tsx` | Mock `pickMockReply` |

### To do

- [ ] Audit **team, game, player** pages for missing ask/reference entry points
- [ ] Wire `ChartDashboardSearch` → `/api/dashboards` (and `/api/analyze` for chat) per `playerChartsAiTodo.ts`
- [ ] Connect `AnalyzerPanel` to real backend (same as `ai_analyst` chat flow)
- [ ] Context passing: open analyzer with overlay context (player name, game id, team) when user asks from detail view
- [ ] Map `DetailTarget` → prefill / `conversationId` / history context on backend

---

## Quick file index (home-prototype)

```
App.tsx                    — nav, detail state, mock chat send
DetailOverlay.tsx          — all profile/game overlays
TeamDetail.tsx             — team page (needs tabs + links)
PlayerProfileDetail.tsx    — player page + PlayerChartsSection
PlayerChartsSection.tsx    — chart tabs (profile/shots/trends/leaderboards/scatter)
LiveDashboard.tsx          — right sidebar live + past games
ChatSidebar.tsx            — mock saved chats
LoginGate.tsx              — mock login
api/stagingClient.ts       — vault reads
hooks/useStaging*.ts       — data hooks
```

## Quick file index (ai_analyst — reference for AI + auth)

```
app/dashboards/page.tsx    — POST /api/dashboards, chart router
app/chat/[id]/page.tsx     — real chat + Firebase save
components/app-sidebar.tsx — saved chats list
context/auth-context.tsx   — Firebase token refresh
```
