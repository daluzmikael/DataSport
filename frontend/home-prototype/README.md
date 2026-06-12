# DataSport Home Prototype

Standalone UI mock for the planned home / analyzer layout. No backend — all live scores and stats are hard-coded.

## Layout (left → right)

| Zone | Width | Purpose |
|------|-------|---------|
| Nav rail | 5% | Account, settings, page switcher (Analyzer, Following, Dashboard, Social) |
| Chat history | 10% | Past conversations / project folders |
| Analyzer | 50% | Main chat — ask anything about NBA (mock replies) |
| Live dashboard | 35% | Followed teams & players, then other live games |

Click any team game or player card on the right to open a full-screen detail view with an **Ask DataSport** bar at the bottom.

Use the **star icon** in the nav rail for **Following** — manage favorite teams and players, search to add follows, and open profiles for players not on the live board tonight.

## Run locally

```bash
cd DataSport/frontend/home-prototype
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). Use **Continue as demo user** on the login screen.

## Staged data (phases 1, 2, 4, 5)

With the backend running and staging parquet built, player/team profiles load real vault data where mapped.

```bash
# Terminal 1 — backend (from DataSport/backend)
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — prototype
cp .env.example .env   # optional; defaults to localhost:8000
npm run dev
```

**Wired to staging API** (green **Vault** badge when live):

- Player season stat bubbles + game log (general + advanced tabs) + career tab
- Team season panel: standings, record, best GS, per-game leaders (one season dropdown)
- Team game log (general + advanced), season history, roster

**Still mock:** logo, championships, conference titles, last championship/playoffs (needs `ClinchedPlayoffBirth`), live dashboard, box scores, shot charts, per36/per100 team tabs, AI copy, chat.

Demo players (`player-tatum`, etc.) map to NBA player IDs in `src/api/nbaIds.ts`.

After re-staging, hit `POST /api/staging/refresh` or restart the backend.

## Next steps

- Wire phase 3 (game context / advanced) when staging completes
- Live dashboard endpoint
- Analyzer chat → `/api/analysis`
