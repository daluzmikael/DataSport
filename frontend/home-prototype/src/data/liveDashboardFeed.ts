import type { LiveFeedItem } from "../types"
import { getGameDetail, LIVE_FEED } from "./mock"
import { buildOrderedDashboardFeed, detailToCompact } from "./orderedDashboardFeed"

export function buildLiveDashboardFeed(base: LiveFeedItem[] = LIVE_FEED): LiveFeedItem[] {
  return buildOrderedDashboardFeed(base, (gameId) =>
    detailToCompact(gameId, getGameDetail),
  )
}

export function teamProfileIdFromAbbr(abbr: string): string {
  return `team-${abbr.toLowerCase()}`
}

export { buildOrderedDashboardFeed } from "./orderedDashboardFeed"
