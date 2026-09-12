/** Which stats the team season-leaders panel can rank by.
 *
 * The old module also shipped a `generateSeasonLeaders()` that INVENTED leaders for
 * any team it had no fixture for — plausible names attached to plausible numbers,
 * indistinguishable from real ones on screen. Leaders now come from
 * `/api/staging/teams/{id}/leaders`.
 */
export type TeamLeaderStatId =
  | "pts"
  | "reb"
  | "ast"
  | "stl"
  | "blk"
  | "fg3m"
  | "ts_pct"
  | "usg_pct"
  | "fg_pct"
  | "fg3_pct"
  | "tov"
  | "min"

export interface TeamLeaderStatOption {
  id: TeamLeaderStatId
  label: string
}

export interface TeamSeasonLeaderEntry {
  player: string
  value: string | number
}

export const TEAM_LEADER_STAT_OPTIONS: TeamLeaderStatOption[] = [
  { id: "pts", label: "PTS" },
  { id: "reb", label: "REB" },
  { id: "ast", label: "AST" },
  { id: "stl", label: "STL" },
  { id: "blk", label: "BLK" },
  { id: "fg3m", label: "3PM" },
  { id: "ts_pct", label: "TS%" },
  { id: "usg_pct", label: "USG%" },
  { id: "fg_pct", label: "FG%" },
  { id: "fg3_pct", label: "3P%" },
  { id: "tov", label: "TOV" },
  { id: "min", label: "MIN" },
]

export const DEFAULT_LEADER_COLUMN_STATS: TeamLeaderStatId[] = ["pts", "reb", "ast"]

export function leaderStatLabel(statId: TeamLeaderStatId): string {
  return TEAM_LEADER_STAT_OPTIONS.find((o) => o.id === statId)?.label ?? statId.toUpperCase()
}
