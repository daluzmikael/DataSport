/** Live-game state, filled from the NBA live feed (`/api/live/*`).
 *
 * The app has surfaces that only make sense for a game in progress: a pulsing LIVE
 * badge, a game clock, a live box score. Those used to be filled by `mock.ts` with
 * one Celtics–Heat game frozen at Q3 5:46. Now `hooks/useLiveBoard.ts` polls the live
 * endpoints, writes today's games into `LIVE_FEED` and registers each game's detail
 * in `liveRegistry`. Until the first answer arrives (or when the API is unreachable)
 * everything here is empty and the live surfaces show their empty state; the
 * finished games from the vault still come from `hooks/useVaultGameBoard.ts`.
 */
import type { GameDetailView, LiveFeedItem } from "../types"
import { getLiveGameDetail } from "./liveRegistry"

/** Today's games from the live feed. Mutated in place by `useLiveBoard`. */
export const LIVE_FEED: LiveFeedItem[] = []

/** Full detail for a game the live feed has registered. */
export function getGameDetail(gameId: string): GameDetailView | undefined {
  return getLiveGameDetail(gameId)
}
