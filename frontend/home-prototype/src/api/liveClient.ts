import { API_URL } from "./config"

/** Shapes returned by backend/api/live.py (`/api/live/*`). */
export type LiveGameState = "scheduled" | "live" | "final"

export interface LiveTeam {
  teamId: number | null
  tricode: string
  name: string
  city: string
  score: number
  wins: number | null
  losses: number | null
  periods: number[]
  timeoutsRemaining: number | null
  inBonus: boolean
}

export interface LiveLeader {
  personId: number
  name: string
  points: number | null
  rebounds: number | null
  assists: number | null
}

export interface LiveGame {
  gameId: string
  date: string | null
  startTimeUTC: string | null
  status: number
  state: LiveGameState
  isLive: boolean
  isFinal: boolean
  statusText: string
  period: number
  periodText: string
  clock: string
  label: string
  subLabel: string
  home: LiveTeam
  away: LiveTeam
  leaders: { home: LiveLeader | null; away: LiveLeader | null }
  pointsLeader?: { personId: number; name: string; tricode: string; points: number }
}

export interface LivePlayerLine {
  personId: number
  name: string
  nameI: string
  firstName: string
  familyName: string
  jersey: string
  position: string
  teamTricode: string
  starter: boolean
  oncourt: boolean
  played: boolean
  status: string
  notPlayingReason: string
  minutes: number
  pts: number
  fgm: number
  fga: number
  fg3m: number
  fg3a: number
  ftm: number
  fta: number
  oreb: number
  dreb: number
  reb: number
  ast: number
  stl: number
  blk: number
  tov: number
  pf: number
  plusMinus: number
}

export interface LiveBoxTeam extends LiveTeam {
  statistics: Record<string, number | null>
  players: LivePlayerLine[]
}

export interface LiveBoxLeader {
  personId: number
  name: string
  familyName: string
  teamTricode: string
  value: number
}

export interface LiveBoxScore {
  game: LiveGame
  teams: { home: LiveBoxTeam; away: LiveBoxTeam }
  leaders: { points: LiveBoxLeader[]; rebounds: LiveBoxLeader[]; assists: LiveBoxLeader[] }
}

export interface LiveNextGame {
  gameId: string
  date: string
  startTimeUTC: string | null
  statusText: string
  opponent: string
  isHome: boolean
}

export interface LiveTrackedPlayer {
  query: string
  found: boolean
  teamTricode: string | null
  playsToday: boolean
  line:
    | (LivePlayerLine & {
        gameId: string
        date: string | null
        state: LiveGameState
        periodText: string
        clock: string
        opponentTricode: string
        isHome: boolean
      })
    | null
  nextGame: LiveNextGame | null
}

export interface LiveDay {
  date: string
  games: LiveGame[]
}

export interface LiveBoard {
  today: LiveDay & { hasLive: boolean }
  pastDays: LiveDay[]
  upcoming: LiveDay | null
  players: LiveTrackedPlayer[]
}

interface LiveResponse<T> {
  success: boolean
  data: T
  meta?: { message?: string | null; source?: string | null; cached?: boolean }
}

function liveUrl(path: string, params?: Record<string, string | number>): string {
  const base =
    API_URL && API_URL.length > 0
      ? API_URL
      : typeof window !== "undefined"
        ? window.location.origin
        : "http://localhost:8000"
  const url = new URL(`${base}/api/live${path}`)
  for (const [k, v] of Object.entries(params ?? {})) url.searchParams.set(k, String(v))
  return url.toString()
}

async function liveGet<T>(
  path: string,
  params?: Record<string, string | number>,
  signal?: AbortSignal,
): Promise<LiveResponse<T> | null> {
  try {
    const res = await fetch(liveUrl(path, params), { signal })
    if (!res.ok) return null
    return (await res.json()) as LiveResponse<T>
  } catch {
    return null
  }
}

/** Today + recent days + upcoming + tracked players. `null` when the API is unreachable. */
export async function fetchLiveBoard(
  players: { name: string; teamAbbr?: string }[],
  pastDays = 3,
  signal?: AbortSignal,
): Promise<LiveBoard | null> {
  const params: Record<string, string | number> = { past_days: pastDays }
  if (players.length) {
    params.players = players.map((p) => (p.teamAbbr ? `${p.name}:${p.teamAbbr}` : p.name)).join(",")
  }
  const res = await liveGet<LiveBoard>("/board", params, signal)
  if (!res?.success || !res.data) return null
  return res.data
}

export async function fetchLiveGame(gameId: string, signal?: AbortSignal): Promise<LiveBoxScore | null> {
  const res = await liveGet<LiveBoxScore | null>(`/game/${gameId}`, undefined, signal)
  return res?.success && res.data ? res.data : null
}
