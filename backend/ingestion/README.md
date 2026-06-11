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

## Phases

| Phase | Tables | Notes |
|-------|--------|-------|
| 1 | season stats, standings, shot zones | Start here |
| 2 | player/team game logs | Builds `data/manifests/game_ids.txt` |
| 3 | game_context, game_advanced | Per game; slow |
| 4 | career JSON per player | After phase 1 |
| 5 | court_shots | Use `--max-shot-players 50` for pilot |

Resume via `data/manifests/pull_state.json`.

## Staging (raw → unified tables)

```powershell
python -m ingestion.stage_all --phase 1
python -m ingestion.stage_all --phase 2
python -m ingestion.stage_all --phase 3
python -m ingestion.stage_all --phase 4
python -m ingestion.stage_all --phase 5
python -m ingestion.stage_all --phase all
```

| Phase | Output parquet(s) |
|-------|-------------------|
| 1 | player/team season stats, standings, shot zones |
| 2 | player_game_logs, team_game_logs |
| 3 | game_context, player_game_advanced, team_game_advanced |
| 4 | player_career |
| 5 | court_shots |

Phase 3 and 5 are slow (many files). Phase 1 is safe while pull still runs.

## Layout

```text
data/raw/{table_name}/...
data/manifests/
data/logs/
data/staging/
```

Edit `START_SEASON` / `END_SEASON` in `ingestion/config.py`.
