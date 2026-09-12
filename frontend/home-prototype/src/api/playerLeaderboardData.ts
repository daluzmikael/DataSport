export interface LeaderboardEntry {
  rank: number
  playerId: string
  playerName: string
  teamAbbr: string
  value: number
}

export const DEFAULT_LEADERBOARD_SEASON = "2022-23"

export const LEADERBOARD_STAT_LABELS: Record<string, string> = {
  PTS: "Points per game",
  AST: "Assists per game",
  REB: "Rebounds per game",
}

function parseNum(raw: unknown): number {
  const n = typeof raw === "number" ? raw : parseFloat(String(raw ?? ""))
  return Number.isNaN(n) ? 0 : n
}

export function leaderboardFromRows(
  rows: Record<string, unknown>[] | null | undefined,
): LeaderboardEntry[] {
  if (!rows?.length) return []
  return rows
    .map((row, index) => ({
      rank: parseNum(row.rank) || index + 1,
      playerId: String(
        Math.trunc(parseNum(row.PLAYER_ID ?? row.player_id ?? 0)),
      ),
      playerName: String(row.PLAYER_NAME ?? row.player_name ?? row.full_name ?? "Unknown"),
      teamAbbr: String(row.TEAM_ABBREVIATION ?? row.team_abbreviation ?? ""),
      value: Math.round(parseNum(row.value ?? row.PTS) * 10) / 10,
    }))
    .sort((a, b) => b.value - a.value)
    .map((entry, index) => ({ ...entry, rank: index + 1 }))
}

/* A hard-coded 2022-23 top-ten used to be the fallback here — with the wrong values,
 * as it happens: it listed Tatum at 30.1 and Durant at 29.7 for a season where they
 * averaged 30.1 and 29.1. Leaderboards come from `/api/staging/league/leaders` now. */

