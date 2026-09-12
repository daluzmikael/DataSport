/** Shot charts, from real shot coordinates.
 *
 * What this replaced, in order of how wrong it was:
 *
 *  1. Charts were enabled for a hard-coded allow-list of one player (Tatum). Everyone
 *     else got `generateMockShots()` — a seeded random spray with no relationship to
 *     anything that happened.
 *  2. Even for Tatum the dots were synthetic: real per-zone FGA/FG% totals, then
 *     random placement inside each zone.
 *
 * `player_shot_chart` holds 6.3M real attempts (1996-97 → 2025-26), so every player
 * now gets their own shots, at the coordinates they were actually taken from. When a
 * season has no rows the hook returns an empty array and the chart says so.
 */
import { useEffect, useRef, useState } from "react"

import { USE_STAGING_API } from "../api/config"
import { resolveNbaPlayerId } from "../api/nbaIds"
import {
  fetchPlayerShotChart,
  fetchPlayerShotChartSeasons,
  type ShotChartMeta,
} from "../api/stagingClient"
import { shotFromVaultRow, type ShotPoint } from "../data/schema/shots"
import { CAREER_LOG_VALUE } from "../data/schema/gameLog"

/** Seasons this player has coordinate shot data for, newest first. */
export function usePlayerShotChartSeasons(playerId: string) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [seasons, setSeasons] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [season, setSeason] = useState<string>("")
  const activePlayer = useRef(playerId)

  useEffect(() => {
    if (!nbaId || !USE_STAGING_API) {
      setSeasons([])
      setSeason("")
      return
    }
    let cancelled = false
    setLoading(true)
    ;(async () => {
      const rows = await fetchPlayerShotChartSeasons(nbaId)
      if (cancelled) return
      const list = rows?.map((r) => r.season) ?? []
      setSeasons(list)
      setLoading(false)
      if (activePlayer.current !== playerId || !list.includes(season)) {
        activePlayer.current = playerId
        setSeason(list[0] ?? "")
      }
    })()
    return () => {
      cancelled = true
    }
    // `season` is intentionally omitted: it is set from inside this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nbaId, playerId])

  return {
    seasons,
    season,
    setSeason,
    loading,
    isCareer: season === CAREER_LOG_VALUE,
  }
}

/** Shots for one player-season. Career pulls every season this player has. */
export function useStagingPlayerShotCharts(playerId: string, season: string) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [shots, setShots] = useState<ShotPoint[]>([])
  const [meta, setMeta] = useState<ShotChartMeta>({})
  const [fromApi, setFromApi] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!USE_STAGING_API || !nbaId || !season) {
      setShots([])
      setMeta({})
      setFromApi(false)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setShots([])
    setFromApi(false)

    ;(async () => {
      let rows: Record<string, unknown>[] = []

      if (season === CAREER_LOG_VALUE) {
        const seasonRows = (await fetchPlayerShotChartSeasons(nbaId)) ?? []
        const payloads = await Promise.all(
          seasonRows.map((r) => fetchPlayerShotChart(nbaId, r.season)),
        )
        rows = payloads.flatMap((p) => p?.rows ?? [])
      } else {
        const payload = await fetchPlayerShotChart(nbaId, season)
        rows = payload?.rows ?? []
        if (payload) setMeta(payload.meta)
      }

      if (cancelled) return
      const points = rows
        .map(shotFromVaultRow)
        .filter((s): s is ShotPoint => s !== null)
      setShots(points)
      setFromApi(points.length > 0)
      setLoading(false)
    })()

    return () => {
      cancelled = true
    }
  }, [nbaId, season])

  return { shots, meta, fromApi, loading, vaultEnabled: Boolean(nbaId) }
}
