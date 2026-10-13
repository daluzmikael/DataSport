import type { LiveFeedItem, PlayerLive } from "../types"

function gameIdForPlayer(player: PlayerLive, base: LiveFeedItem[]): string | undefined {
  if (player.gameId) return player.gameId
  const opponent = player.opponentAbbr
  const team = player.teamAbbr
  for (const item of base) {
    if (item.kind === "followed-team") {
      const { home, away } = item
      if (
        (home.abbr === team && away.abbr === opponent) ||
        (away.abbr === team && home.abbr === opponent)
      ) {
        return item.id
      }
    }
    if (item.kind === "other-live") {
      if (
        (item.homeAbbr === team && item.awayAbbr === opponent) ||
        (item.awayAbbr === team && item.homeAbbr === opponent)
      ) {
        return item.id
      }
    }
  }
  return undefined
}

/** Followed teams & players first; also surface live games for followed players. */
export function buildOrderedDashboardFeed(base: LiveFeedItem[]): LiveFeedItem[] {
  const out: LiveFeedItem[] = []
  const seenGames = new Set<string>()

  const pushGame = (item: LiveFeedItem | undefined) => {
    if (!item || item.kind === "followed-player") return
    if (seenGames.has(item.id)) return
    seenGames.add(item.id)
    out.push(item)
  }

  for (const item of base) {
    if (item.kind === "followed-team") pushGame(item)
  }

  for (const item of base) {
    if (item.kind === "followed-player") out.push(item)
  }

  for (const item of base) {
    if (item.kind !== "followed-player") continue
    const gameId = gameIdForPlayer(item, base)
    if (gameId) {
      pushGame(
        base.find(
          (i) => i.id === gameId && (i.kind === "followed-team" || i.kind === "other-live"),
        ),
      )
    }
  }

  for (const item of base) {
    if (item.kind === "other-live") pushGame(item)
  }

  return out
}
