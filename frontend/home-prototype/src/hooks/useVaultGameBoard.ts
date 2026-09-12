/** The right-rail games board, built from real completed games in the vault.
 *
 * There is no live endpoint yet (`/api/live/*` is unbuilt), and the board used to
 * paper over that with a hand-written Celtics–Heat game frozen at Q3 5:46, plus four
 * days of invented "past" results. Every score on the screen was fiction.
 *
 * The vault holds every game through the 2025-26 finals, so the board now shows real
 * results — the most recent nights the vault actually has, with real scores, real
 * quarter lines and real leaders. Live games will slot in above these once the live
 * endpoints exist; until then the "Live now" section is honestly empty.
 */
import { useEffect, useMemo, useState } from "react"

import {
  fetchGameDates,
  fetchGameLeaders,
  fetchGamesByDate,
  type BoardGame,
} from "../api/stagingClient"
import { USE_STAGING_API } from "../api/config"
import { stagingGameOverlayId } from "../utils/stagingGameId"
import type { CompactGame, LeaderLine, LiveFeedItem, TeamGameLive } from "../types"

export interface BoardDay {
  /** ISO date, e.g. "2026-05-30". */
  date: string
  /** "Thu, May 30" */
  label: string
  items: LiveFeedItem[]
}

const DAYS_TO_SHOW = 4
const FULL_CARDS_PER_DAY = 2

function dayLabel(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  })
}

function num(value: unknown): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function lineOf(side: BoardGame["away"]): TeamGameLive["away"]["line"] {
  const line = side.line ?? {}
  const out: TeamGameLive["away"]["line"] = {
    q1: num(line.q1),
    q2: num(line.q2),
    q3: num(line.q3),
  }
  if (line.q4 != null) out.q4 = num(line.q4)
  return out
}

function statsOf(side: BoardGame["away"]): TeamGameLive["awayGameStats"] {
  const s = side.stats ?? {}
  return {
    fg: String(s.fg ?? "—"),
    fg3: String(s.fg3 ?? "—"),
    ft: String(s.ft ?? "—"),
    reb: num(s.reb),
    ast: num(s.ast),
    tov: num(s.tov),
    pf: num(s.pf),
  }
}

function toCompact(game: BoardGame): CompactGame {
  return {
    id: stagingGameOverlayId(game.game_id),
    kind: "other-live",
    awayAbbr: game.away.abbr,
    homeAbbr: game.home.abbr,
    awayScore: num(game.away.score),
    homeScore: num(game.home.score),
    period: "Final",
    clock: "",
  }
}

function toFullCard(
  game: BoardGame,
  leaders?: { points: LeaderLine[]; assists: LeaderLine[]; rebounds: LeaderLine[] },
): TeamGameLive {
  return {
    id: stagingGameOverlayId(game.game_id),
    kind: "followed-team",
    away: {
      abbr: game.away.abbr,
      name: game.away.name,
      score: num(game.away.score),
      line: lineOf(game.away),
    },
    home: {
      abbr: game.home.abbr,
      name: game.home.name,
      score: num(game.home.score),
      line: lineOf(game.home),
    },
    period: "Final",
    clock: "",
    isLive: false,
    possession: "home",
    // Timeouts and team fouls are live-clock state; a finished game has none, and
    // showing a number here would be inventing one.
    homeTimeouts: 0,
    awayTimeouts: 0,
    homeTeamFouls: num(game.home.stats?.pf),
    awayTeamFouls: num(game.away.stats?.pf),
    homeGameStats: statsOf(game.home),
    awayGameStats: statsOf(game.away),
    topScorers: leaders?.points ?? [],
    topAssists: leaders?.assists ?? [],
    topRebounds: leaders?.rebounds ?? [],
  }
}

async function recentDates(limit: number): Promise<string[]> {
  // The vault's most recent games are playoff games, so both season types have to be
  // asked for; taking only the regular season stops the board months short.
  const [regular, playoffs] = await Promise.all([
    fetchGameDates({ seasonType: "Regular Season", limit }),
    fetchGameDates({ seasonType: "Playoffs", limit }),
  ])
  const merged = new Map<string, string>()
  for (const row of [...(regular ?? []), ...(playoffs ?? [])]) {
    if (row?.game_date) merged.set(row.game_date, row.game_date)
  }
  return [...merged.keys()].sort().reverse().slice(0, limit)
}

async function gamesOn(date: string): Promise<BoardGame[]> {
  const [regular, playoffs] = await Promise.all([
    fetchGamesByDate(date, "Regular Season"),
    fetchGamesByDate(date, "Playoffs"),
  ])
  return [...(regular ?? []), ...(playoffs ?? [])]
}

export function useVaultGameBoard(followedTeams: string[] = []) {
  const [days, setDays] = useState<BoardDay[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const followedKey = useMemo(
    () => followedTeams.map((t) => t.toUpperCase()).sort().join(","),
    [followedTeams],
  )

  useEffect(() => {
    if (!USE_STAGING_API) {
      setDays([])
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)

    ;(async () => {
      try {
        const dates = await recentDates(DAYS_TO_SHOW)
        if (cancelled) return
        if (!dates.length) {
          setDays([])
          setLoading(false)
          return
        }

        const followed = new Set(followedKey ? followedKey.split(",") : [])
        const built: BoardDay[] = []

        for (const date of dates) {
          const games = await gamesOn(date)
          if (cancelled) return
          if (!games.length) continue

          // Followed teams get the full card treatment; everything else is a row.
          const isFollowed = (g: BoardGame) =>
            followed.has(g.away.abbr.toUpperCase()) ||
            followed.has(g.home.abbr.toUpperCase())
          const ordered = [...games].sort(
            (a, b) => Number(isFollowed(b)) - Number(isFollowed(a)),
          )
          const fullCount = Math.max(
            ordered.filter(isFollowed).length,
            Math.min(FULL_CARDS_PER_DAY, ordered.length),
          )
          const full = ordered.slice(0, fullCount)
          const rest = ordered.slice(fullCount)

          const leaderSets = await Promise.all(
            full.map((g) => fetchGameLeaders(g.game_id)),
          )
          if (cancelled) return

          const items: LiveFeedItem[] = [
            ...full.map((g, i) => {
              const set = leaderSets[i]
              return toFullCard(
                g,
                set
                  ? {
                      points: set.points.map((p) => ({ name: p.name, value: num(p.value) })),
                      assists: set.assists.map((p) => ({ name: p.name, value: num(p.value) })),
                      rebounds: set.rebounds.map((p) => ({ name: p.name, value: num(p.value) })),
                    }
                  : undefined,
              )
            }),
            ...rest.map(toCompact),
          ]

          built.push({ date, label: dayLabel(date), items })
        }

        if (cancelled) return
        setDays(built)
        setLoading(false)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : "Could not load games")
        setDays([])
        setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [followedKey])

  return { days, loading, error }
}
