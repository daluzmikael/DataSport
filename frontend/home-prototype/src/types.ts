export type NavPage = "analyzer" | "dashboard" | "social" | "favorites" | "players"

export type FollowKind = "team" | "player"

export interface FavoriteTeam {
  id: string
  abbr: string
  name: string
  city: string
  isLive?: boolean
}

export interface FavoritePlayer {
  id: string
  name: string
  teamAbbr: string
  position?: string
  isLive?: boolean
  seasonAvgGameScore?: number
}

export type DetailTarget =
  | { type: "game"; id: string }
  | { type: "player"; id: string; season?: string }
  | { type: "player-game"; playerId: string; gameId: string }
  | { type: "team"; id: string }
  | null

export interface TeamSeasonGameRow {
  id: string
  game: string
  isLive?: boolean
  values: Record<string, string | number>
}

export interface TeamHistorySeason {
  season: string
  wl: string
  values: Record<string, string | number>
}

export interface TeamRosterPlayer {
  id: string
  name: string
  position: string
  number: string
  height: string
}

export interface TeamGameScoreLeader {
  rank: number
  player: string
  season: string
  opponent: string
  gameScore: number
}

export interface TeamFranchiseAccolades {
  allTimeRecord: string
  championships: number
  conferenceTitles: number
  lastChampionship: string
  lastPlayoffs: string
  founded: string
  yearsInAssociation: number
}

export interface TeamCurrentSeasonSnapshot {
  standing: string
  record: string
  bestPlayer: {
    name: string
    avgGameScore: number
  }
}

export interface TeamSeasonGameLogBundle {
  season: string
  games: {
    general: TeamSeasonGameRow[]
    advanced: TeamSeasonGameRow[]
    per36: TeamSeasonGameRow[]
    per100: TeamSeasonGameRow[]
  }
  averages: {
    general: Record<string, string | number>
    advanced: Record<string, string | number>
    per36: Record<string, string | number>
    per100: Record<string, string | number>
  }
}

export interface TeamProfile {
  id: string
  abbr: string
  city: string
  name: string
  seasonLabel: string
  seasonGames: {
    general: TeamSeasonGameRow[]
    advanced: TeamSeasonGameRow[]
    per36: TeamSeasonGameRow[]
    per100: TeamSeasonGameRow[]
  }
  seasonAverages: {
    general: Record<string, string | number>
    advanced: Record<string, string | number>
    per36: Record<string, string | number>
    per100: Record<string, string | number>
  }
  history: TeamHistorySeason[]
  roster: TeamRosterPlayer[]
  gameScoreLeaders: TeamGameScoreLeader[]
  accolades: TeamFranchiseAccolades
  currentSeason: TeamCurrentSeasonSnapshot
}

export interface LineScore {
  q1: number
  q2: number
  q3: number
  q4?: number
}

export interface LeaderLine {
  name: string
  value: number
  unit?: string
}

export interface TeamGameStatsLine {
  fg: string
  fg3: string
  ft: string
  reb: number
  ast: number
  tov: number
  pf: number
}

export interface TeamGameLive {
  id: string
  kind: "followed-team"
  home: { abbr: string; name: string; score: number; line: LineScore }
  away: { abbr: string; name: string; score: number; line: LineScore }
  period: string
  clock: string
  isLive: boolean
  possession: "home" | "away"
  homeTimeouts: number
  awayTimeouts: number
  homeTeamFouls: number
  awayTeamFouls: number
  /** @deprecated Use gameStatsByTab — kept for quick refs */
  homeGameStats: TeamGameStatsLine
  awayGameStats: TeamGameStatsLine
  topScorers: LeaderLine[]
  topAssists: LeaderLine[]
  topRebounds: LeaderLine[]
}

/** Full live game detail for non-followed teams (same layout as followed-team). */
export type OtherLiveGame = Omit<TeamGameLive, "kind"> & { kind: "other-live" }

export type GameDetailView = TeamGameLive | OtherLiveGame

export interface PlayerLive {
  id: string
  kind: "followed-player"
  name: string
  /** Live game these stats belong to (matches a feed game id when known). */
  gameId?: string
  teamAbbr: string
  opponentAbbr: string
  minutes: number
  status: "on court" | "bench"
  period: string
  clock: string
  pts: number
  fg: string
  fgPct: string
  fg3: string
  fg3Pct: string
  ft: string
  ftPct: string
  oreb: number
  dreb: number
  reb: number
  ast: number
  tov: number
  stl: number
  blk: number
  pf: number
  plusMinus: string
  gameScore: number
  /** Season-to-date average game score (vault metric). */
  seasonAvgGameScore: number
  /** NBA-native impact tier from Advanced / estimated metrics (not Game Score). */
  impactLabel?: string
  impactHeadlineScore?: number
  impactHeadlineMetric?: string
  /** Rank among qualified players by season average game score (1 = best). */
  seasonGameScoreRank: number
  seasonGameScoreRankTotal?: number
  tsPct: string
  efgPct: string
  usgPct: string
  astPct: string
  astToTov: string
  orebPct: string
  drebPct: string
  pie: string
  contestedShots: number
  contestedShots2pt: number
  contestedShots3pt: number
  deflections: number
  screenAssists: number
  screenAssistPoints: number
  boxOuts: number
  offensiveBoxOuts: number
  defensiveBoxOuts: number
  looseBallsRecoveredTotal: number
  looseBallsRecoveredOffensive: number
  looseBallsRecoveredDefensive: number
  chargesDrawn: number
  boxOutPlayerTeamRebounds: number
  boxOutPlayerRebounds: number
}

export interface CompactGame {
  id: string
  kind: "other-live"
  awayAbbr: string
  homeAbbr: string
  awayScore: number
  homeScore: number
  period: string
  clock: string
}

export type LiveFeedItem = TeamGameLive | PlayerLive | CompactGame

export interface ChatThread {
  id: string
  title: string
  updatedAt: string
  folder?: string
}

export interface ChatFolder {
  id: string
  name: string
  threadIds: string[]
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
}
