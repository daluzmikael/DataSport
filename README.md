# DataSport

DataSport is an NBA analytics platform that lets users explore basketball stats through natural-language questions, dashboards, and rich player/team profiles. The system can answer questions like “What was LeBron’s best season between 2003 and 2022?” or “Who are the top 10 scorers this season?” by generating SQL, querying the data layer, and returning analyst-style text or charts.

The project is built around a local **stats vault**: NBA.com data is ingested with `nba_api`, staged into unified Parquet tables, and queried at runtime through **DuckDB**. A legacy **PostgreSQL (RDS)** path remains for older deployments.

## What You Can Do

**Analyst mode** — chat-style Q&A with stat-backed answers.

**Dashboard mode** — generate charts (leaderboards, comparisons, trends, skill profiles, shot charts).

**Profiles & game data** — the home prototype loads real season stats, game logs, career data, standings, and leaders from the staging API when the backend is running.

Typical flow:

1. Open a frontend in the browser.
2. Choose Analyst, Dashboards, or browse player/team profiles.
3. Ask a question or open a detail view.
4. Review tables, summaries, or visualizations.
5. Continue the conversation or explore related stats.

## Architecture

```text
nba_api  →  data/raw/  →  ingestion/stage_all  →  data/staging/*.parquet
                                                          ↓
                                              DuckDB views (Executer/)
                                                          ↓
                    Interpreter (NL → SQL)  →  FastAPI  →  frontends
```

**AI layer (optional):** OpenAI generates SQL and natural-language analysis. Staging read endpoints and DuckDB queries work without an API key.

**Auth (optional):** Firebase powers signup, login, and saved chat history in the production-style frontend.

## Tech Stack

| Layer | Technologies |
|-------|----------------|
| Backend | Python, FastAPI, Uvicorn, Pandas, DuckDB, SQLGlot, OpenAI SDK |
| Data ingestion | `nba-api`, Parquet, checkpointed pull/stage pipeline |
| Data query | DuckDB over staging Parquet (default); PostgreSQL via psycopg2 (legacy) |
| Home prototype | Vite, React 19, TypeScript, Tailwind CSS |
| AI analyst app | Next.js 15, React 19, TypeScript, Tailwind, Radix UI, Recharts, Firebase |

## Project Structure

```text
DataSport/
  backend/
    main.py                 # FastAPI entrypoint
    api/                    # Staging read routes (/api/staging/...)
    Analyzer/               # Query results → user-facing analysis
    DashboardBackend/       # Dashboard query + chart generation
    Executer/               # SQL validation, DuckDB / PostgreSQL execution
    Interpreter/            # Natural language → SQL (staging + legacy RDS)
    ingestion/              # Pull from NBA API, stage into Parquet
    data/
      raw/                  # Per-endpoint pulls (gitignored)
      staging/              # Unified Parquet tables (gitignored)
      manifests/            # Pull checkpoints, game ID lists
  frontend/
    home-prototype/         # Vite UI — profiles wired to staging API
    ai_analyst/             # Next.js app — Analyst + Dashboards + Firebase auth
  README.md
```

## Staging Tables

After ingestion and staging, DuckDB exposes these views (when Parquet files exist):

| Phase | Tables |
|-------|--------|
| 1 | `player_season_stats`, `team_season_stats`, `team_standings`, `player_shot_zones`, `team_shot_zones` |
| 2 | `player_game_logs`, `team_game_logs` |
| 3 | `game_context`, `player_game_advanced`, `team_game_advanced` |
| 4 | `player_career` |
| 5 | `court_shots` |

See `backend/ingestion/README.md` for pull and stage commands.

## Requirements

- Python 3.11+ (3.13 recommended)
- Node.js 20+
- npm
- Git

**Backend** — virtual environment at `backend/.venv`, dependencies from `backend/requirements.txt`:

- fastapi, uvicorn, pandas, pyarrow, duckdb, nba-api, openai, sqlglot, psycopg2-binary, firebase-admin, pyrebase4, and others

**Optional services:**

- `OPENAI_API_KEY` — Analyst, Dashboards, and NL→SQL (not required for staging API alone)
- Firebase credentials — auth and chat history in `ai_analyst`
- PostgreSQL — only if `DATA_BACKEND=postgres` with `POSTGRES_*` env vars

## Running Locally

Use two terminals: backend first, then a frontend.

### 1. Backend setup

```powershell
cd DataSport\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Build staging data (start with phase 1; full pipeline takes time):

```powershell
python -m ingestion.stage_all --phase 1
```

Optional `.env` in `backend/`:

```env
DATA_BACKEND=duckdb
OPENAI_API_KEY=sk-...
STAGING_DATA_DIR=C:/path/to/DataSport/backend/data/staging
```

### 2. Start the backend

```powershell
cd DataSport\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000  
- Docs: http://127.0.0.1:8000/docs  
- Staging health: http://127.0.0.1:8000/api/staging/health  

The server starts without `OPENAI_API_KEY`; AI routes fail at request time until a key is set.

### 3. Home prototype (recommended for vault data)

```powershell
cd DataSport\frontend\home-prototype
npm install
copy .env.example .env
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173). Use **Continue as demo user** on the login screen.

With `VITE_USE_STAGING_API=true`, player/team profiles show a green **Vault** badge when live data loads.

### 4. AI analyst app (Analyst + Dashboards)

```powershell
cd DataSport\frontend\ai_analyst
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open http://127.0.0.1:3000. Requires OpenAI and Firebase configuration for full functionality.

## Data Ingestion (optional)

Pull raw NBA stats from stats.nba.com:

```powershell
cd DataSport\backend
python -m ingestion.pull_all --phase 1 --log-file
python -m ingestion.pull_all --phase all --log-file
```

Stage into unified tables:

```powershell
python -m ingestion.stage_all --phase all
```

After re-staging, restart the backend or `POST /api/staging/refresh`.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATA_BACKEND` | `duckdb` (default) or `postgres` |
| `STAGING_DATA_DIR` | Override path to staging Parquet folder |
| `OPENAI_API_KEY` | GPT for SQL generation and analysis |
| `STAGING_SQL_MODEL` | Model for staging SQL path (default `gpt-5.4-mini`) |
| `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Legacy RDS connection |
| `LOG_LEVEL` | Backend log level (default `INFO`) |

## API Overview

| Route | Description |
|-------|-------------|
| `POST /api/analysis` | Analyst chat — NL question → SQL → answer |
| `POST /api/dashboards` | Dashboard chart generation |
| `GET /api/staging/*` | Player/team search, stats, game logs, career, standings |
| `POST /api/signup`, `POST /api/login` | Firebase auth |
| `GET /api/history` | Saved conversations |

## Common Issues

**Backend crashes on import with OpenAI error** — set `OPENAI_API_KEY`, or use a build where the client is created lazily; staging routes do not need a key.

**No staging data** — run `python -m ingestion.stage_all --phase 1` and confirm `backend/data/staging/*.parquet` exists.

**Frontend stale Next.js chunks** — delete `.next` and restart:

```powershell
cd DataSport\frontend\ai_analyst
Remove-Item -Recurse -Force .next
npm run dev
```

**Port in use (Windows)** — find and stop the process using 8000 or 3000, or pick another port.

**Broken venv after moving the repo** — delete `backend/.venv` and recreate it.

## Further Reading

- `backend/ingestion/README.md` — pull phases, staging, data layout
- `backend/Executer/README.md` — DuckDB vs PostgreSQL backends
- `frontend/home-prototype/README.md` — prototype layout and vault wiring
