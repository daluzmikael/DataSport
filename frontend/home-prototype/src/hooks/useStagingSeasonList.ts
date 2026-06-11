import { useEffect, useState } from "react"
import { fetchStagingSeasons } from "../api/stagingClient"
import { USE_STAGING_API } from "../api/config"
import { FALLBACK_NBA_SEASONS } from "../utils/nbaSeasons"

const SEASON_LABEL_RE = /^\d{4}-\d{2}$/

function normalizeSeasonList(value: unknown): string[] | null {
  if (!Array.isArray(value) || value.length === 0) return null
  const seasons = value.filter(
    (s): s is string => typeof s === "string" && SEASON_LABEL_RE.test(s),
  )
  return seasons.length ? seasons : null
}

/** Distinct seasons in player_season_stats (newest first), or full 1996-97…2025-26 fallback. */
export function useStagingSeasonList() {
  const [seasons, setSeasons] = useState<string[]>(FALLBACK_NBA_SEASONS)
  const [fromApi, setFromApi] = useState(false)
  const [loading, setLoading] = useState(USE_STAGING_API)

  useEffect(() => {
    if (!USE_STAGING_API) {
      setLoading(false)
      setFromApi(false)
      return
    }

    let cancelled = false
    ;(async () => {
      const apiSeasons = await fetchStagingSeasons()
      if (cancelled) return
      const normalized = normalizeSeasonList(apiSeasons)
      if (normalized) {
        setSeasons(normalized)
        setFromApi(true)
      } else {
        setSeasons(FALLBACK_NBA_SEASONS)
        setFromApi(false)
      }
      setLoading(false)
    })()

    return () => {
      cancelled = true
    }
  }, [])

  return {
    seasons,
    loading,
    fromApi,
    defaultSeason: seasons[0] ?? FALLBACK_NBA_SEASONS[0],
  }
}
