/**
 * PLAYER-CHARTS-AI-TODO
 *
 * Backlog before player profile charts match the dashboard (`ai_analyst`) AI behavior.
 * Defaults below use staging vault reads; search bars are placeholders until wired.
 *
 * Broader session plan: ../../../../SESSION_BACKLOG.md (grep SESSION-BACKLOG)
 */
export const PLAYER_CHARTS_AI_TODO = {
  scatter: [
    "Wire ChartDashboardSearch → POST /api/dashboards; swap in results with chartType Scatter + ./recharts/Scatter",
    "Today: fixed pairs PTS vs MIN and AST vs TOV for 2023-24 via GET /api/staging/league/scatter",
    "Dashboard also supports: arbitrary stat pairs, single-axis distribution (y only), playoffs filters, cross-table joins (e.g. TS% vs PPG), custom min GP / limits",
    "Highlight profile player on scatter; drive default season from the section season dropdown",
  ],
  trends: [
    "Wire search → /api/dashboards (SinglePlayerStat, CompareStats); consider shared Recharts SinglePlayerStat vs custom SVG defaults",
  ],
  leaderboards: [
    "Wire search → /api/dashboards (Leaderboard chart type); today fixed top-10 PTS 2022-23",
  ],
  profile: [
    "Wire compare/solo search → dashboard skill-profile or custom AI queries",
  ],
  shots: [
    "Wire heatmap/zones search → dashboard ShotChart; real loc_x/loc_y when available in vault",
  ],
} as const
