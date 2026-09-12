/** Live-game state — deliberately empty, because there is no live source yet.
 *
 * The app has surfaces that only make sense for a game in progress: a pulsing LIVE
 * badge, a game clock, possession, timeouts remaining, a running play-by-play. Those
 * were filled by `mock.ts` with one Celtics–Heat game frozen at Q3 5:46, and by
 * `otherLiveGamesMock.ts` with four more, complete with invented play-by-play strings.
 * Every number on the home screen was fiction, and it looked exactly like the real
 * vault numbers next to it.
 *
 * The live endpoints (`/api/live/*`, step 6 of the ingestion roadmap) do not exist. So
 * rather than fabricate a game, this module returns nothing and the live surfaces show
 * their empty state. The finished games in the right-hand board are real — see
 * `hooks/useVaultGameBoard.ts`.
 *
 * When the live API lands, this is the one file that has to change: fill `LIVE_FEED`
 * from `/api/live/scoreboard` and the rest of the app already knows what to do.
 */
import type { GameDetailView, LiveFeedItem } from "../types"

/** Games in progress right now. Empty until `/api/live/*` exists. */
export const LIVE_FEED: LiveFeedItem[] = []

/** Full detail for a live game. No live source, so nothing to return. */
export function getGameDetail(_gameId: string): GameDetailView | undefined {
  return undefined
}

/** Play-by-play for a live game. Requires `playbyplayv3`, which is not wired. */
export const PLAY_BY_PLAY: Record<string, string[]> = {}

export const HAS_LIVE_SOURCE = false
