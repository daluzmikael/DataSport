import { useEffect, useMemo, useState } from "react"
import { USE_STAGING_API } from "../api/config"
import {
  DEFAULT_LEADERBOARD_SEASON,
  leaderboardFromRows,
  mockScoringLeaderboard,
  type LeaderboardEntry,
} from "../api/playerLeaderboardData"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { fetchLeagueLeaders } from "../api/stagingClient"

export function useStagingLeagueLeaderboard(
  profilePlayerId: string,
  season = DEFAULT_LEADERBOARD_SEASON,
  stat = "PTS",
) {
  const highlightNbaId = resolveNbaPlayerId(profilePlayerId)
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
      const data = await fetchLeagueLeaders(season, stat, {
        highlightPlayerId: highlightNbaId ?? undefined,
      })
      if (cancelled) return
      setRows(data)
      setFromApi(Boolean(data?.length))
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [season, stat, highlightNbaId])

  const entries: LeaderboardEntry[] = useMemo(() => {
    if (fromApi && rows?.length) {
      const parsed = leaderboardFromRows(rows)
      if (parsed.length) return parsed
    }
    return mockScoringLeaderboard(highlightNbaId ?? undefined)
  }, [rows, fromApi, highlightNbaId])

  return { entries, fromApi, loading, season }
}
