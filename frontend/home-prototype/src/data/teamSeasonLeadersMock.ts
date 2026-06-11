import type { TeamProfile } from "../types"
import { getTeamSeasonRoster } from "./teamSeasonRosterBuilder"

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

/** 2024-25 Celtics season leaders (per-game averages · mock) */
const BOS_2024_25_LEADERS: Record<TeamLeaderStatId, TeamSeasonLeaderEntry> = {
  pts: { player: "Jayson Tatum", value: 27.1 },
  reb: { player: "Jayson Tatum", value: 8.7 },
  ast: { player: "Derrick White", value: 5.4 },
  stl: { player: "Jayson Tatum", value: 1.2 },
  blk: { player: "Kristaps Porzingis", value: 1.8 },
  fg3m: { player: "Sam Hauser", value: 2.9 },
  ts_pct: { player: "Kristaps Porzingis", value: ".632" },
  usg_pct: { player: "Jayson Tatum", value: "31.2" },
  fg_pct: { player: "Kristaps Porzingis", value: ".512" },
  fg3_pct: { player: "Sam Hauser", value: ".421" },
  tov: { player: "Jayson Tatum", value: 2.8 },
  min: { player: "Jayson Tatum", value: 36.2 },
}

const BOS_2023_24_LEADERS: Record<TeamLeaderStatId, TeamSeasonLeaderEntry> = {
  pts: { player: "Jayson Tatum", value: 26.9 },
  reb: { player: "Jayson Tatum", value: 8.1 },
  ast: { player: "Jayson Tatum", value: 4.9 },
  stl: { player: "Jrue Holiday", value: 1.1 },
  blk: { player: "Kristaps Porzingis", value: 1.9 },
  fg3m: { player: "Derrick White", value: 2.7 },
  ts_pct: { player: "Kristaps Porzingis", value: ".628" },
  usg_pct: { player: "Jayson Tatum", value: "30.8" },
  fg_pct: { player: "Kristaps Porzingis", value: ".508" },
  fg3_pct: { player: "Sam Hauser", value: ".415" },
  tov: { player: "Jaylen Brown", value: 2.6 },
  min: { player: "Jayson Tatum", value: 35.8 },
}

const BOS_SEASON_LEADERS: Record<string, Record<TeamLeaderStatId, TeamSeasonLeaderEntry>> = {
  "2024-25": BOS_2024_25_LEADERS,
  "2023-24": BOS_2023_24_LEADERS,
}

function seededRandom(seed: string): () => number {
  let h = 0
  for (let i = 0; i < seed.length; i++) {
    h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0
  }
  return () => {
    h = (Math.imul(1103515245, h) + 12345) | 0
    return (h >>> 0) / 4294967296
  }
}

function statValue(stat: TeamLeaderStatId, rng: () => number, playerIndex: number): string | number {
  switch (stat) {
    case "pts":
      return +(18 + rng() * 14 - playerIndex * 1.5).toFixed(1)
    case "reb":
      return +(4 + rng() * 8 - playerIndex * 0.8).toFixed(1)
    case "ast":
      return +(2 + rng() * 6 - playerIndex * 0.5).toFixed(1)
    case "stl":
      return +(0.5 + rng() * 1.5).toFixed(1)
    case "blk":
      return +(0.3 + rng() * 2).toFixed(1)
    case "fg3m":
      return +(1 + rng() * 3).toFixed(1)
    case "ts_pct":
      return `.${Math.floor(520 + rng() * 100)}`.replace("..", ".")
    case "usg_pct":
      return (18 + rng() * 16).toFixed(1)
    case "fg_pct":
      return `.${Math.floor(420 + rng() * 80)}`.replace("..", ".")
    case "fg3_pct":
      return `.${Math.floor(340 + rng() * 80)}`.replace("..", ".")
    case "tov":
      return +(1.5 + rng() * 2).toFixed(1)
    case "min":
      return +(22 + rng() * 16).toFixed(1)
  }
}

function generateSeasonLeaders(
  profile: TeamProfile,
  season: string,
): Record<TeamLeaderStatId, TeamSeasonLeaderEntry> {
  const roster = getTeamSeasonRoster(profile, season)
  const rng = seededRandom(`${profile.id}-leaders-${season}`)
  const result = {} as Record<TeamLeaderStatId, TeamSeasonLeaderEntry>

  for (const opt of TEAM_LEADER_STAT_OPTIONS) {
    const leaderIdx = Math.floor(rng() * Math.min(5, roster.length))
    const player = roster[leaderIdx]?.name ?? roster[0]?.name ?? "—"
    result[opt.id] = {
      player,
      value: statValue(opt.id, rng, leaderIdx),
    }
  }

  return result
}

export function getTeamSeasonLeaders(
  profile: TeamProfile,
  season: string,
): Record<TeamLeaderStatId, TeamSeasonLeaderEntry> {
  if (profile.id === "team-bos" && BOS_SEASON_LEADERS[season]) {
    return BOS_SEASON_LEADERS[season]
  }
  return generateSeasonLeaders(profile, season)
}

export function leaderStatLabel(statId: TeamLeaderStatId): string {
  return TEAM_LEADER_STAT_OPTIONS.find((o) => o.id === statId)?.label ?? statId.toUpperCase()
}
