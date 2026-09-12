import { useEffect, useMemo, useState } from "react"
import { USE_STAGING_API } from "../api/config"
import {
  trendPointsFromRows,
  type TrendPoint,
  type TrendStatKey,
} from "../api/playerTrendData"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { fetchPlayerSeasonTrends } from "../api/stagingClient"

/* Trends were gated to an allow-list of one player (Tatum); every other player got a
 * hash-seeded career arc. `player_season_stats` covers everyone, so the gate is gone. */
function vaultTrendsEnabled(_playerId: string, nbaId: string | null): boolean {
  return Boolean(nbaId)
}

function resolveTrendPoints(
  rows: Record<string, unknown>[] | null,
  fromApi: boolean,
  statKey: TrendStatKey,
): TrendPoint[] {
  if (fromApi && rows?.length) return trendPointsFromRows(rows, statKey)
  return []
}

export function useStagingPlayerSeasonTrends(playerId: string) {
  const nbaId = resolveNbaPlayerId(playerId)
  const vaultEnabled = vaultTrendsEnabled(playerId, nbaId)
  const [rows, setRows] = useState<Record<string, unknown>[] | null>(null)
  const [fromApi, setFromApi] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!USE_STAGING_API || !nbaId || !vaultEnabled) {
      setRows(null)
      setFromApi(false)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setRows(null)
    setFromApi(false)
    ;(async () => {
      const data = await fetchPlayerSeasonTrends(nbaId)
      if (cancelled) return
      setRows(data)
      setFromApi(Boolean(data?.length))
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, vaultEnabled])

  const pts = useMemo(
    () => resolveTrendPoints(rows, fromApi, "PTS"),
    [playerId, rows, fromApi],
  )
  const ast = useMemo(
    () => resolveTrendPoints(rows, fromApi, "AST"),
    [playerId, rows, fromApi],
  )

  return { pts, ast, fromApi, loading, vaultEnabled }
}
