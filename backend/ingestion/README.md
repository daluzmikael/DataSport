# NBA data ingestion

Pulls raw NBA.com stats via [nba_api](https://github.com/swar/nba_api) into `DataSport/backend/data/raw/` (gitignored).

## Setup

```powershell
cd c:\Users\mikae\Coder\DataSport\DataSport\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Overnight run

```powershell
python -m ingestion.pull_all --phase all --log-file
```

## In-season refresh (nightly / weekly)

One command pulls everything new for the season being played and stages it:

```powershell
python -m scripts.update_vault                       # current season, all tables (~1-2 h)
python -m scripts.update_vault --skip shots,lineups  # quicker nightly run
python -m scripts.update_vault --weekly              # + awards, franchise history, all-time leaders
python -m scripts.update_vault --dry-run             # show what would be re-pulled
```

`pull_all` alone will not refresh a season in progress: the checkpoint marks each
slice completed and skips it forever. `update_vault` un-marks the current season's
slices (and the careers of players in it), pulls only games not fetched yet, stages
all phases, then calls `POST /api/staging/refresh` on a local API if one is running.
Logs go to `data/logs/update_vault_*.log`.

## Phases

| Phase | Tables | Notes |
|-------|--------|-------|
| 1 | season stats, standings, shot zones | Extended measure types + per modes |
| 2 | player/team game logs | Builds `data/manifests/game_ids.txt` |
| 3 | game_context, game_advanced | Per game; slow |
| 4 | career JSON per player | Scans all dash slices for player IDs |
| 5 | court_shots | Use `--max-shot-players 50` for pilot; `--retry-failed-court-shots` to backfill |
| 6 | tracking, lineups, on/off, estimated metrics | New gap-fill endpoints |

Resume via `data/manifests/pull_state.json`.

### Season dash filename pattern

```
dash_{regular_season|playoffs}_{measure}_{permode}.parquet
```

Legacy Base files without measure slug (`dash_regular_season_pergame.parquet`) are still read by staging.

**Measure types (player dash):** Base, Advanced, Usage, Misc, Scoring, Defense  
**Per modes:** PerGame, Totals, Per100Possessions, Per36, Per40

## Staging (raw → unified tables)

```powershell
python -m ingestion.stage_all --phase 1
python -m ingestion.stage_all --phase 6
python -m ingestion.stage_all --phase all
```

| Phase | Output parquet(s) |
|-------|-------------------|
| 1 | player/team season stats, standings, shot zones |
| 2 | player_game_logs, team_game_logs |
| 3 | game_context, player_game_advanced, team_game_advanced |
| 4 | player_career |
| 5 | court_shots |
| 6 | player/team_tracking, lineups, player_on_off, estimated metrics |

## Third-party metrics (DARKO / EPM / LEBRON / RAPTOR)

Not on stats.nba.com. See `data/raw/third_party_metrics/README.md` for Phase F research notes.

## Layout

```text
data/raw/{table_name}/...
data/manifests/
data/logs/
data/staging/
```

Edit `START_SEASON` / `END_SEASON` in `ingestion/config.py`.
