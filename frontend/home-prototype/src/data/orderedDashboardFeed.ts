import type { CompactGame, LiveFeedItem, PlayerLive } from "../types"

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

function resolveGameItem(
  gameId: string,
  base: LiveFeedItem[],
  resolveExtra?: (gameId: string) => LiveFeedItem | null,
): LiveFeedItem | null {
  const fromFeed = base.find(
    (i) =>
      i.id === gameId && (i.kind === "followed-team" || i.kind === "other-live"),
  )
  if (fromFeed) return fromFeed
  return resolveExtra?.(gameId) ?? null
}

/** Followed teams & players first; also surface live games for followed players. */
export function buildOrderedDashboardFeed(
  base: LiveFeedItem[],
  resolveExtraGame?: (gameId: string) => LiveFeedItem | null,
): LiveFeedItem[] {
  const out: LiveFeedItem[] = []
  const seenGames = new Set<string>()

  const pushGame = (item: LiveFeedItem | null) => {
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
    if (gameId) pushGame(resolveGameItem(gameId, base, resolveExtraGame))
  }

  for (const item of base) {
    if (item.kind === "other-live") pushGame(item)
  }

  return out
}

export function detailToCompact(
  id: string,
  getDetail: (gameId: string) => { id: string; away: { abbr: string; score: number }; home: { abbr: string; score: number }; period: string; clock: string } | undefined,
): CompactGame | null {
  const d = getDetail(id)
  if (!d || !("home" in d)) return null
  return {
    id: d.id,
    kind: "other-live",
    awayAbbr: d.away.abbr,
    homeAbbr: d.home.abbr,
    awayScore: d.away.score,
    homeScore: d.home.score,
    period: d.period,
    clock: d.clock,
  }
}
