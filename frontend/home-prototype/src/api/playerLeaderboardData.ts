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

/** 2022-23 top scorers mock — includes Tatum for profile demos. */
export function mockScoringLeaderboard(highlightPlayerId?: string): LeaderboardEntry[] {
  const entries: LeaderboardEntry[] = [
    { rank: 1, playerId: "203954", playerName: "Joel Embiid", teamAbbr: "PHI", value: 33.1 },
    { rank: 2, playerId: "1629029", playerName: "Luka Dončić", teamAbbr: "DAL", value: 32.4 },
    { rank: 3, playerId: "203507", playerName: "Giannis Antetokounmpo", teamAbbr: "MIL", value: 31.1 },
    { rank: 4, playerId: "201939", playerName: "Stephen Curry", teamAbbr: "GSW", value: 29.4 },
    { rank: 5, playerId: "203999", playerName: "Nikola Jokić", teamAbbr: "DEN", value: 29.3 },
    { rank: 6, playerId: "1628369", playerName: "Jayson Tatum", teamAbbr: "BOS", value: 30.1 },
    { rank: 7, playerId: "201142", playerName: "Kevin Durant", teamAbbr: "PHX", value: 29.7 },
    { rank: 8, playerId: "1626164", playerName: "Devin Booker", teamAbbr: "PHX", value: 27.8 },
    { rank: 9, playerId: "2544", playerName: "LeBron James", teamAbbr: "LAL", value: 28.9 },
    { rank: 10, playerId: "1627759", playerName: "Jaylen Brown", teamAbbr: "BOS", value: 26.6 },
  ]
    .sort((a, b) => b.value - a.value)
    .map((entry, index) => ({ ...entry, rank: index + 1 }))

  if (!highlightPlayerId) return entries
  const hasHighlight = entries.some((e) => e.playerId === highlightPlayerId)
  if (hasHighlight) return entries
  return entries
}
