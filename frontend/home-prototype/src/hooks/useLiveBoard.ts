import { useEffect, useMemo, useRef, useState } from "react"
import { fetchLiveBoard, fetchLiveGame, type LiveBoard, type LiveBoxScore, type LiveGame } from "../api/liveClient"
import {
  boxToGameDetail,
  boxToRows,
  boxToTeamTotals,
  dayLabel,
  gameToCompact,
  gameToDetail,
  nextGameLabel,
  shortDate,
  trackedToPlayerLive,
} from "../api/liveMappers"
import {
  markLiveDataLoaded,
  registerLiveGameDetail,
  setLivePlayerNextGame,
  setLiveTeams,
} from "../data/liveRegistry"
import { LIVE_FEED } from "../data/liveState"
import { buildOrderedDashboardFeed } from "../data/orderedDashboardFeed"
import type { FavoritePlayer, FavoriteTeam, LiveFeedItem } from "../types"
import { useFollowedPlayers, useFollowedTeams } from "./useFavorites"

const POLL_LIVE_MS = 30_000
const POLL_IDLE_MS = 120_000
const PAST_DAYS = 3

export interface LiveBoardSection {
  key: string
  label: string
  tone: "live" | "today" | "past" | "upcoming"
  items: LiveFeedItem[]
  emptyText?: string
}

export interface LiveBoardState {
  /** null until the first successful API answer — callers then show the vault board. */
  sections: LiveBoardSection[] | null
  hasLive: boolean
  loading: boolean
  updatedAt: Date | null
}

interface Follows {
  teams: Set<string>
  players: FavoritePlayer[]
}

function isFollowedGame(g: LiveGame, follows: Follows): boolean {
  return follows.teams.has(g.home.tricode) || follows.teams.has(g.away.tricode)
}

async function mapLimit<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length)
  let next = 0
  const worker = async () => {
    while (next < items.length) {
      const i = next++
      out[i] = await fn(items[i])
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker))
  return out
}

function buildDayItems(
  games: LiveGame[],
  dateIso: string,
  board: LiveBoard,
  boxes: Map<string, LiveBoxScore>,
  follows: Follows,
): LiveFeedItem[] {
  const followedFirst = [...games].sort(
    (a, b) => Number(isFollowedGame(b, follows)) - Number(isFollowedGame(a, follows)),
  )
  const raw: LiveFeedItem[] = []
  for (const g of followedFirst) {
    const followed = isFollowedGame(g, follows)
    const box = boxes.get(g.gameId)
    if (g.state !== "scheduled") {
      const detail = box ? boxToGameDetail(box, followed) : gameToDetail(g, followed)
      registerLiveGameDetail(
        detail,
        box ? boxToRows(box) : undefined,
        box ? boxToTeamTotals(box) : undefined,
      )
      if (followed && detail.kind === "followed-team") {
        raw.push(detail)
        continue
      }
    }
    raw.push(gameToCompact(g, followed))
  }
  for (const fav of follows.players) {
    const tracked = board.players.find((p) => p.query === fav.name)
    const line = tracked?.line
    if (!tracked || !line || line.date !== dateIso) continue
    if (!line.played && line.state !== "live") continue
    const player = trackedToPlayerLive(fav.id, tracked, fav.seasonAvgGameScore)
    if (player) raw.push(player)
  }
  return buildOrderedDashboardFeed(raw)
}

function buildSections(
  board: LiveBoard,
  boxes: Map<string, LiveBoxScore>,
  follows: Follows,
): LiveBoardSection[] {
  const { today } = board
  const sections: LiveBoardSection[] = []
  const todayItems = buildDayItems(today.games, today.date, board, boxes, follows)
  const allFinal = today.games.length > 0 && today.games.every((g) => g.state === "final")
  sections.push({
    key: `today-${today.date}`,
    label: today.hasLive
      ? "Live now"
      : today.games.length === 0
        ? `Today · ${shortDate(today.date)}`
        : allFinal
          ? "Today · Final"
          : `Tonight · ${today.games.length} game${today.games.length === 1 ? "" : "s"}`,
    tone: today.hasLive ? "live" : "today",
    items: todayItems,
    emptyText: today.games.length === 0 ? "No NBA games today." : undefined,
  })
  if (today.games.length === 0 && board.upcoming) {
    sections.push({
      key: `up-${board.upcoming.date}`,
      label: `Up next · ${dayLabel(board.upcoming.date, today.date)}`,
      tone: "upcoming",
      items: buildDayItems(board.upcoming.games, board.upcoming.date, board, boxes, follows),
    })
  }
  for (const day of board.pastDays) {
    sections.push({
      key: `past-${day.date}`,
      label: dayLabel(day.date, today.date),
      tone: "past",
      items: buildDayItems(day.games, day.date, board, boxes, follows),
    })
  }

  // Shared snapshot for overlays / status helpers that read LIVE_FEED + the registry.
  LIVE_FEED.splice(0, LIVE_FEED.length, ...todayItems)
  setLiveTeams(
    today.games.filter((g) => g.isLive).flatMap((g) => [g.home.tricode, g.away.tricode]),
    today.games.flatMap((g) => [g.home.tricode, g.away.tricode]),
  )
  for (const fav of follows.players) {
    const tracked = board.players.find((p) => p.query === fav.name)
    if (!tracked) continue
    const ids = [fav.id]
    if (tracked.line) ids.push(`nba-${tracked.line.personId}`, String(tracked.line.personId))
    setLivePlayerNextGame(ids, tracked.nextGame ? nextGameLabel(tracked.nextGame, today.date) : null)
  }
  markLiveDataLoaded()
  return sections
}

function followsKey(teams: FavoriteTeam[], players: FavoritePlayer[]): string {
  return JSON.stringify([
    teams.map((t) => t.abbr.toUpperCase()).sort(),
    players.map((p) => `${p.id}|${p.name}|${p.teamAbbr}`).sort(),
  ])
}

/** Real `/api/live/board` data for the right rail, polling while games are live. */
export function useLiveBoard(): LiveBoardState {
  const { teams } = useFollowedTeams()
  const { players } = useFollowedPlayers()
  const key = followsKey(teams, players)
  const follows = useMemo<Follows>(
    () => ({ teams: new Set(teams.map((t) => t.abbr.toUpperCase())), players }),
    // `key` captures every field the board reads from the follow lists.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key],
  )
  const [state, setState] = useState<LiveBoardState>({
    sections: null,
    hasLive: false,
    loading: true,
    updatedAt: null,
  })
  const boxes = useRef(new Map<string, LiveBoxScore>())

  useEffect(() => {
    let cancelled = false
    let timer: number | undefined
    const ctrl = new AbortController()

    const tick = async () => {
      const board = await fetchLiveBoard(
        follows.players.map((p) => ({ name: p.name, teamAbbr: p.teamAbbr })),
        PAST_DAYS,
        ctrl.signal,
      )
      if (cancelled) return
      if (!board) {
        setState((s) => ({ ...s, loading: false }))
        timer = window.setTimeout(tick, POLL_IDLE_MS)
        return
      }
      // Box scores: every started game we have not cached as final; live ones every tick.
      const started = [board.today, ...board.pastDays]
        .flatMap((d) => d.games)
        .filter((g) => g.state !== "scheduled")
        .filter((g) => g.state === "live" || boxes.current.get(g.gameId)?.game.state !== "final")
      await mapLimit(started, 6, async (g) => {
        const box = await fetchLiveGame(g.gameId, ctrl.signal)
        if (box) boxes.current.set(g.gameId, box)
      })
      if (cancelled) return
      setState({
        sections: buildSections(board, boxes.current, follows),
        hasLive: board.today.hasLive,
        loading: false,
        updatedAt: new Date(),
      })
      timer = window.setTimeout(tick, board.today.hasLive ? POLL_LIVE_MS : POLL_IDLE_MS)
    }

    void tick()
    return () => {
      cancelled = true
      ctrl.abort()
      if (timer) window.clearTimeout(timer)
    }
  }, [follows])

  return state
}
