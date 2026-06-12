import { useEffect, useMemo, useRef, useState } from "react"
import { USE_STAGING_API } from "../api/config"
import { mergeShotZoneRows, shotsFromShotZoneRow } from "../api/playerShotChartData"
import { resolveNbaPlayerId } from "../api/nbaIds"
import {
  fetchPlayerGameLogSeasons,
  fetchPlayerShotZones,
} from "../api/stagingClient"
import { generateMockShots, type MockShot } from "../data/mockShots"
import { CAREER_LOG_VALUE, usePlayerGameLogSeasons } from "./useStagingPlayer"

/** Vault shot charts enabled for Tatum first; expand once validated. */
const VAULT_SHOT_CHART_PLAYER_IDS = new Set([
  "player-tatum",
  "1628369",
  "nba-1628369",
])

function vaultShotChartsEnabled(playerId: string, nbaId: string | null): boolean {
  if (!nbaId) return false
  return VAULT_SHOT_CHART_PLAYER_IDS.has(playerId) || VAULT_SHOT_CHART_PLAYER_IDS.has(nbaId)
}

export function usePlayerShotChartSeasons(playerId: string) {
  const { seasons, defaultSeason, seasonsLoading, seasonsReady } =
    usePlayerGameLogSeasons(playerId)
  const latestSeason = seasons[0] ?? defaultSeason
  const [season, setSeason] = useState(latestSeason)
  const activePlayer = useRef(playerId)

  useEffect(() => {
    if (!seasonsReady) return
    if (activePlayer.current !== playerId) {
      activePlayer.current = playerId
      setSeason(latestSeason)
      return
    }
    if (!seasons.includes(season) && season !== CAREER_LOG_VALUE) {
      setSeason(latestSeason)
    }
  }, [playerId, seasonsReady, seasons, latestSeason, season])

  return {
    seasons,
    season,
    setSeason,
    loading: seasonsLoading,
    isCareer: season === CAREER_LOG_VALUE,
  }
}

export function useStagingPlayerShotCharts(playerId: string, season: string) {
  const nbaId = resolveNbaPlayerId(playerId)
  const vaultEnabled = vaultShotChartsEnabled(playerId, nbaId)
  const [vaultShots, setVaultShots] = useState<MockShot[] | null>(null)
  const [fromApi, setFromApi] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!USE_STAGING_API || !nbaId || !vaultEnabled || !season) {
      setVaultShots(null)
      setFromApi(false)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setVaultShots(null)
    setFromApi(false)
    ;(async () => {
      let row: Record<string, unknown> | null = null

      if (season === CAREER_LOG_VALUE) {
        const seasons = (await fetchPlayerGameLogSeasons(nbaId)) ?? []
        const rows = await Promise.all(
          seasons.map((s) => fetchPlayerShotZones(nbaId, s, "Regular Season", "Totals")),
        )
        const valid = rows.filter((r): r is Record<string, unknown> => Boolean(r))
        row = valid.length ? mergeShotZoneRows(valid) : null
      } else {
        row = await fetchPlayerShotZones(nbaId, season, "Regular Season", "Totals")
      }

      if (cancelled) return
      if (!row) {
        setVaultShots(null)
        setFromApi(false)
        setLoading(false)
        return
      }
      const seed = season === CAREER_LOG_VALUE ? `${nbaId}-career` : `${nbaId}-${season}`
      const shots = shotsFromShotZoneRow(row, seed)
      setVaultShots(shots.length > 0 ? shots : null)
      setFromApi(shots.length > 0)
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, vaultEnabled])

  const mockShots = useMemo(() => generateMockShots(playerId), [playerId])

  return {
    shots: fromApi && vaultShots ? vaultShots : mockShots,
    fromApi,
    loading,
    vaultEnabled,
  }
}
