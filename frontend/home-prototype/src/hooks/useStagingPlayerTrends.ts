import { useEffect, useMemo, useState } from "react"
import { USE_STAGING_API } from "../api/config"
import {
  mockTrendPoints,
  trendPointsFromRows,
  type TrendPoint,
  type TrendStatKey,
} from "../api/playerTrendData"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { fetchPlayerSeasonTrends } from "../api/stagingClient"

/** Vault trends enabled for Tatum first; expand once validated. */
const VAULT_TREND_PLAYER_IDS = new Set([
  "player-tatum",
  "1628369",
  "nba-1628369",
])

function vaultTrendsEnabled(playerId: string, nbaId: string | null): boolean {
  if (!nbaId) return false
  return VAULT_TREND_PLAYER_IDS.has(playerId) || VAULT_TREND_PLAYER_IDS.has(nbaId)
}

function resolveTrendPoints(
  playerId: string,
  rows: Record<string, unknown>[] | null,
  fromApi: boolean,
  statKey: TrendStatKey,
): TrendPoint[] {
  if (fromApi && rows?.length) {
    const parsed = trendPointsFromRows(rows, statKey)
    if (parsed.length) return parsed
  }
  return mockTrendPoints(playerId, statKey)
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
    () => resolveTrendPoints(playerId, rows, fromApi, "PTS"),
    [playerId, rows, fromApi],
  )
  const ast = useMemo(
    () => resolveTrendPoints(playerId, rows, fromApi, "AST"),
    [playerId, rows, fromApi],
  )

  return { pts, ast, fromApi, loading, vaultEnabled }
}
