import { getGameDetail } from "../data/mock"
import { getPlayerNextGame } from "../data/playerScheduleMock"
import type { CompactGame, LiveFeedItem, PlayerLive, TeamGameLive, GameDetailView } from "../types"

/** City names for matchup headers (prototype; replace with API labels later). */
const TEAM_CITY: Record<string, string> = {
  MIA: "Miami",
  BOS: "Boston",
  PHX: "Phoenix",
  DAL: "Dallas",
  LAL: "Los Angeles",
  DEN: "Denver",
  NYK: "New York",
  CLE: "Cleveland",
}

export function cityMatchup(awayAbbr: string, homeAbbr: string): string {
  const away = TEAM_CITY[awayAbbr] ?? awayAbbr
  const home = TEAM_CITY[homeAbbr] ?? homeAbbr
  return `${away} vs ${home}`
}

export function findTeamGameForPlayer(
  player: PlayerLive,
  feed: LiveFeedItem[],
): TeamGameLive | undefined {
  return feed.find(
    (i): i is TeamGameLive =>
      i.kind === "followed-team" &&
      ((i.home.abbr === player.teamAbbr && i.away.abbr === player.opponentAbbr) ||
        (i.away.abbr === player.teamAbbr && i.home.abbr === player.opponentAbbr)),
  )
}

/** Feed game id when this player is in a tracked live game (e.g. game-celtics). */
export function resolvePlayerGameId(
  player: PlayerLive,
  feed: LiveFeedItem[],
): string | undefined {
  if (player.gameId) {
    const linked = feed.find(
      (i) => i.id === player.gameId && i.kind === "followed-team",
    )
    if (linked) return linked.id
  }
  return findTeamGameForPlayer(player, feed)?.id
}

export function isPlayerInLiveGame(player: PlayerLive, feed: LiveFeedItem[]): boolean {
  if (player.period === "Final") return false
  return resolvePlayerGameId(player, feed) != null
}

export type PlayerStatusTone =
  | "court"
  | "bench"
  | "gameover"
  | "offnight"

export interface PlayerStatusView {
  statusLabel: string
  statusTone: PlayerStatusTone
  metaLine: string
}

const STATUS_TONE_CLASS: Record<PlayerStatusTone, string> = {
  court: "text-ds-accent",
  bench: "text-ds-warn",
  gameover: "text-ds-live",
  offnight: "text-ds-nba",
}

export function playerStatusClass(tone: PlayerStatusTone): string {
  return STATUS_TONE_CLASS[tone]
}

function isTonightsFeedGame(gameId: string | undefined, feed: LiveFeedItem[]): boolean {
  if (!gameId) return false
  return feed.some((i) => i.id === gameId)
}

function gameClockMeta(player: PlayerLive): string {
  const metaBase = `${player.minutes} min`
  const clockPart =
    player.period === "Final"
      ? player.clock
        ? `Final · ${player.clock}`
        : "Final"
      : `${player.period} ${player.clock}`.trim()
  return `${metaBase} · ${clockPart}`
}

function isGameLive(gameId: string): boolean {
  const game = getGameDetail(gameId)
  if (!game) return false
  if ("isLive" in game) return Boolean(game.isLive)
  return game.period !== "Final"
}

/** Historical game log page — always finished. */
export function resolveHistoricalGamePageStatus(
  minutes: number,
  gameDateLabel: string,
  wl: string,
): PlayerStatusView {
  const wlPart = wl === "W" || wl === "L" ? ` · ${wl}` : ""
  return {
    statusLabel: "Game finished",
    statusTone: "gameover",
    metaLine: `${minutes} min · Final · ${gameDateLabel}${wlPart}`,
  }
}

/** Player game page: on court, on bench, or game over (red) only. */
export function resolvePlayerGamePageStatus(
  player: PlayerLive,
  gameId: string,
): PlayerStatusView {
  const metaLine = gameClockMeta(player)
  if (player.period === "Final" || !isGameLive(gameId)) {
    return { statusLabel: "Game over", statusTone: "gameover", metaLine }
  }
  const onBench = player.status === "bench"
  return {
    statusLabel: onBench ? "On bench" : "On court",
    statusTone: onBench ? "bench" : "court",
    metaLine,
  }
}

/** Player profile: live status, game over, or not playing tonight (orange) + next game. */
/** Compact status for live-board player cards (live, final, or off-night). */
export function resolvePlayerCardStatus(
  player: PlayerLive,
  feed: LiveFeedItem[],
): PlayerStatusView {
  if (isPlayerInLiveGame(player, feed)) {
    return resolvePlayerProfileStatus(player, feed)
  }
  if (player.period === "Final") {
    return {
      statusLabel: "Game over",
      statusTone: "gameover",
      metaLine: gameClockMeta(player),
    }
  }
  return resolvePlayerProfileStatus(player, feed)
}

export function resolvePlayerProfileStatus(
  player: PlayerLive,
  feed: LiveFeedItem[],
): PlayerStatusView {
  if (isPlayerInLiveGame(player, feed)) {
    const onBench = player.status === "bench"
    return {
      statusLabel: onBench ? "On bench" : "On court",
      statusTone: onBench ? "bench" : "court",
      metaLine: gameClockMeta(player),
    }
  }

  const onTonightsBoard = feed.some(
    (i) => i.kind === "followed-player" && i.id === player.id,
  )
  if (
    player.period === "Final" &&
    (isTonightsFeedGame(player.gameId, feed) || onTonightsBoard)
  ) {
    return {
      statusLabel: "Game over",
      statusTone: "gameover",
      metaLine: gameClockMeta(player),
    }
  }

  if (!player.gameId) {
    const next = getPlayerNextGame(player.id)
    return {
      statusLabel: "Not playing tonight",
      statusTone: "offnight",
      metaLine: next ? `Next: ${next.label} · ${next.when}` : "No game scheduled tonight",
    }
  }

  const next = getPlayerNextGame(player.id)
  return {
    statusLabel: "Not playing tonight",
    statusTone: "offnight",
    metaLine: next
      ? `Last vs ${player.opponentAbbr} · Next: ${next.label} · ${next.when}`
      : gameClockMeta(player),
  }
}

export function trackedGameTitle(
  feed: LiveFeedItem[],
  game: GameDetailView | CompactGame | null,
  player: PlayerLive | null,
): string {
  if (game && "home" in game && "away" in game) {
    return cityMatchup(game.away.abbr, game.home.abbr)
  }
  if (game?.kind === "other-live") {
    return cityMatchup(game.awayAbbr, game.homeAbbr)
  }
  if (player) {
    if (player.gameId) {
      const linked = feed.find(
        (i): i is TeamGameLive => i.id === player.gameId && i.kind === "followed-team",
      )
      if (linked) return cityMatchup(linked.away.abbr, linked.home.abbr)
    }
    const matched = findTeamGameForPlayer(player, feed)
    if (matched) return cityMatchup(matched.away.abbr, matched.home.abbr)
    return cityMatchup(player.opponentAbbr, player.teamAbbr)
  }
  return "Game"
}
