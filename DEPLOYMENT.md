# Deployment

Production layout:

```text
Vercel  (frontend/home-prototype, Vite + React)
   │  VITE_API_URL
   ▼
Render  (backend, FastAPI + DuckDB)          free web service
   │  STAGING_DATA_URI
   ▼
Cloudflare R2  (staging/*.parquet)           10 GB free, no egress fees
   ▲
   │  python -m scripts.upload_staging
Workstation  (ingestion: pull_all → stage_all)
```

## Current status (audited 2026-10-13)

| Component | Where | State |
|-----------|-------|-------|
| Frontend | Vercel project `datasport` → https://datasport-two.vercel.app | Deployed from `deploy-test`, but still with root dir `frontend/ai_analyst` (the old Team45 app). Must be switched to `frontend/home-prototype` — see step 4 |
| API | Render `datasport-api` → https://datasport-api.onrender.com | Created directly (not from the Blueprint) from `deploy-test`; secrets still need pasting |
| Data | R2 bucket `datasport-vault` | Exists; `staging/` uploaded with `upload_staging` |

Remaining steps are steps 3 and 4 below: paste the secrets on Render, switch the
Vercel root directory to `frontend/home-prototype`, set `VITE_API_URL` and redeploy,
and authorize `datasport-two.vercel.app` in Firebase.

Ingestion stays on the workstation. The server never calls stats.nba.com; it only
reads the staged parquet. Re-staging locally and re-running the upload is how
production data gets refreshed.

## Why R2 and not Supabase

The app queries parquet through DuckDB, so it needs a *file* store, not a relational
database. Loading the vault into Postgres would mean rewriting the whole query layer.

| Option | Free allowance | Verdict |
|--------|---------------|---------|
| Supabase Postgres | 500 MB | Too small, and would require porting DuckDB SQL to Postgres |
| Supabase Storage | 1 GB, 5 GB egress/mo | Too small; also pauses after 7 days idle |
| **Cloudflare R2** | **10 GB, unlimited egress** | Fits the architecture, no code rewrite |
| Backblaze B2 | 10 GB, 3x egress cap | Workable fallback; egress is metered |

DuckDB reads remote parquet with HTTP range requests, so a query pulls only the
columns and row groups it needs rather than the whole file.

## 1. Check the vault fits

On the workstation, before anything else:

```powershell
cd DataSport\backend
.\.venv\Scripts\Activate.ps1
python -m scripts.upload_staging --dry-run
```

This prints a per-table size breakdown, the total, and whether it fits in 10 GB.
Tables are listed smallest to largest, so the trim candidates are at the bottom
(`lineups` and the per-game tables are usually the largest by a wide margin).

If it does not fit, narrow `START_SEASON` in `ingestion/config.py` and re-stage, or
skip a phase entirely — the API degrades gracefully, registering views only for the
parquet files that exist.

## 2. Upload to R2

Create a bucket in the Cloudflare dashboard (R2 → Create bucket), then an R2 API
token with **Object Read & Write** scoped to it. Note the Account ID.

The upload needs `boto3`, which is in `requirements.txt` (workstation only —
the server reads from R2 and never uploads, so it is not in the Render image).

Put the three values in `backend/.env` (gitignored) — the script reads them from
there, so secrets never go on a command line:

```env
R2_ACCOUNT_ID=...
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
```

```powershell
python -m scripts.upload_staging --bucket datasport-vault --prefix staging
```

## 3. Backend on Render

Render → New → Blueprint → this repo, branch `deploy-test` (`render.yaml` is not on
`main` yet). It reads `render.yaml` and creates the
`datasport-api` service. Then set the secrets it left blank:

| Variable | Value |
|----------|-------|
| `STAGING_DATA_URI` | `r2://datasport-vault/staging` |
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `S3_ACCESS_KEY_ID` | R2 access key ID |
| `S3_SECRET_ACCESS_KEY` | R2 secret access key |
| `OPENAI_API_KEY` | OpenAI key |
| `FIREBASE_API_KEY` | Firebase Web API key |
| `CORS_ALLOW_ORIGINS` | `https://datasport-two.vercel.app` (the Vercel production domain) |

Verify:

```bash
curl https://datasport-api.onrender.com/healthz
curl https://datasport-api.onrender.com/api/staging/health
```

`/api/staging/health` reports the resolved source and the views that registered.

## 4. Frontend on Vercel

Vercel → Add New → Project → this repo. The one setting that matters:

- **Root Directory:** `frontend/home-prototype`

Set **Framework Preset** to Vite; build command (`npm run build`) and output
directory (`dist`) then follow. `frontend/ai_analyst` is the old Team45 Next.js app
and is not deployed.

Environment variables (all environments):

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://datasport-api.onrender.com` — no trailing slash |

Without it the app calls relative `/api` paths, which Vercel answers with 404s.
It is inlined at build time, so changing it requires a redeploy. Firebase is only
used by the backend (`FIREBASE_API_KEY` on Render); the frontend needs no key.

Once the Vercel domain exists, set `CORS_ALLOW_ORIGINS` on Render to it and let the
service redeploy. Add the domain to Firebase Authentication → Settings → Authorized
domains as well, or login will be rejected.

## Free-tier behaviour to expect

Render's free instance sleeps after 15 minutes of inactivity. The next request pays
roughly a minute of cold start, plus a few seconds for DuckDB to re-register views
against R2. Analyst answers also wait on two LLM calls. Worth knowing before you
demo it to someone cold.

512 MB RAM is the real ceiling. Queries that pull wide result sets into pandas are
what will push against it, not the size of the vault itself — DuckDB streams from
R2 rather than loading files whole.

## Refreshing data

```powershell
python -m ingestion.pull_all --phase all --log-file
python -m ingestion.stage_all --phase all
python -m scripts.upload_staging --bucket datasport-vault --prefix staging
```

Then `POST /api/staging/refresh` on the deployed API to drop the cached connection
and re-read the parquet footers.

## Local development is unchanged

With `STAGING_DATA_URI` unset, the backend reads `backend/data/staging` exactly as
before. Remote mode is opt-in.
