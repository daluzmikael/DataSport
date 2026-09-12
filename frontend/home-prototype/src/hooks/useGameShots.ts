/** Every shot one player took in one game, at real coordinates.
 *
 * The game view used to draw `generateMockShots(player.id)` — a seeded random spray,
 * identical for every game that player appeared in. `player_shot_chart` is keyed on
 * GAME_ID, so a single game's shots are a real, exact answer.
 */
import { useEffect, useState } from "react"

import { USE_STAGING_API } from "../api/config"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { fetchPlayerShotChart } from "../api/stagingClient"
import { shotFromVaultRow, type ShotPoint } from "../data/schema/shots"
import { parseStagingGameId } from "../utils/stagingGameId"

/** `playerId` may be any resolvable form; `gameId` is the overlay id (`game-00223…`). */
export function useGameShots(playerId: string, gameId: string, season?: string | null) {
  const nbaId = resolveNbaPlayerId(playerId)
  const nbaGameId = parseStagingGameId(gameId)
  const [shots, setShots] = useState<ShotPoint[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!USE_STAGING_API || !nbaId || !nbaGameId || !season) {
      setShots([])
      return
    }
    let cancelled = false
    setLoading(true)
    ;(async () => {
      // Season type is unknown from the id alone, so both are tried; a playoff game
      // returns nothing from the regular-season slice and vice versa.
      const [regular, playoffs] = await Promise.all([
        fetchPlayerShotChart(nbaId, season, "Regular Season", { gameId: nbaGameId }),
        fetchPlayerShotChart(nbaId, season, "Playoffs", { gameId: nbaGameId }),
      ])
      if (cancelled) return
      const rows = [...(regular?.rows ?? []), ...(playoffs?.rows ?? [])]
      setShots(rows.map(shotFromVaultRow).filter((s): s is ShotPoint => s !== null))
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, nbaGameId, season])

  return { shots, loading }
}
