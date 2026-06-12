import { useEffect, useMemo, useState } from "react"
import { USE_STAGING_API } from "../api/config"
import {
  DEFAULT_SCATTER_SEASON,
  mockScatterAstTov,
  mockScatterPtsMin,
  scatterRowsFromApi,
  type ScatterPointRow,
} from "../api/playerScatterData"
import { fetchLeagueScatter } from "../api/stagingClient"

type ScatterKind = "pts-min" | "ast-tov"

function useScatterPair(season: string, xStat: string, yStat: string, kind: ScatterKind) {
  const [rows, setRows] = useState<Record<string, unknown>[] | null>(null)
  const [fromApi, setFromApi] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!USE_STAGING_API) {
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
      const data = await fetchLeagueScatter(season, xStat, yStat)
      if (cancelled) return
      setRows(data)
      setFromApi(Boolean(data?.length))
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [season, xStat, yStat])

  const points: ScatterPointRow[] = useMemo(() => {
    if (fromApi && rows?.length) {
      const parsed = scatterRowsFromApi(rows)
      if (parsed.length) return parsed
    }
    return kind === "pts-min" ? mockScatterPtsMin() : mockScatterAstTov()
  }, [rows, fromApi, kind])

  return { points, fromApi, loading }
}

export function useStagingLeagueScatter(season = DEFAULT_SCATTER_SEASON) {
  const ptsMin = useScatterPair(season, "MIN", "PTS", "pts-min")
  const astTov = useScatterPair(season, "TOV", "AST", "ast-tov")

  return {
    ptsMin: ptsMin.points,
    astTov: astTov.points,
    fromApi: ptsMin.fromApi || astTov.fromApi,
    loading: ptsMin.loading || astTov.loading,
    season,
  }
}
