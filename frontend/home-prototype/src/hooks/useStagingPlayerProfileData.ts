/** Vault reads for the player profile surfaces: bio, accolades, shot coordinates.
 *
 * Each of these replaced a mock module. They return `null` while loading and `null`
 * on failure — never a fabricated stand-in — so a surface with no data renders an
 * empty state rather than someone else's numbers.
 */
import { useEffect, useMemo, useState } from "react"

import {
  fetchPlayerAwards,
  fetchPlayerBio,
  fetchPlayerShotChart,
  fetchPlayerShotChartSeasons,
  type AwardSummaryEntry,
  type PlayerBio,
  type ShotChartMeta,
} from "../api/stagingClient"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { USE_STAGING_API } from "../api/config"
import {
  buildPlayerAccolades,
  type PlayerAccoladeStat,
} from "../api/playerAccolades"
import { shotFromVaultRow, type ShotPoint } from "../data/schema/shots"
import { useStagingPlayerCareerTotals } from "./useStagingPlayer"

export function useStagingPlayerBio(playerId: string) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [bio, setBio] = useState<PlayerBio | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!nbaId || !USE_STAGING_API) {
      setBio(null)
      return
    }
    let cancelled = false
    setLoading(true)
    ;(async () => {
      const row = await fetchPlayerBio(nbaId)
      if (cancelled) return
      setBio(row ?? null)
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId])

  return { bio, loading }
}

export function useStagingPlayerAwards(playerId: string) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null)
  const [summary, setSummary] = useState<AwardSummaryEntry[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!nbaId || !USE_STAGING_API) {
      setRows(null)
      setSummary([])
      return
    }
    let cancelled = false
    setLoading(true)
    ;(async () => {
      const payload = await fetchPlayerAwards(nbaId)
      if (cancelled) return
      setRows(payload?.data ?? null)
      setSummary(payload?.summary ?? [])
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId])

  /** Career honours only — weekly and monthly awards outnumber them 20 to 1. */
  const careerAwards = useMemo(
    () => summary.filter((entry) => !entry.periodic),
    [summary],
  )

  return { rows, summary, careerAwards, loading }
}

/** The eight tiles across the top of a player profile. */
export function usePlayerAccolades(playerId: string): {
  accolades: PlayerAccoladeStat[] | null
  loading: boolean
} {
  const { bio, loading: bioLoading } = useStagingPlayerBio(playerId)
  const { rows, summary, loading: awardsLoading } = useStagingPlayerAwards(playerId)
  const { careerTotals, loading: totalsLoading } = useStagingPlayerCareerTotals(playerId)

  const loading = bioLoading || awardsLoading || totalsLoading
  const accolades = useMemo(() => {
    if (loading) return null
    if (!rows && !bio && !careerTotals) return null
    return buildPlayerAccolades(summary, rows ?? [], bio, careerTotals)
  }, [loading, summary, rows, bio, careerTotals])

  return { accolades, loading }
}

export function useStagingPlayerShotChart(
  playerId: string,
  season: string | null,
  seasonType = "Regular Season",
) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [shots, setShots] = useState<ShotPoint[] | null>(null)
  const [meta, setMeta] = useState<ShotChartMeta>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!nbaId || !season || !USE_STAGING_API) {
      setShots(null)
      setMeta({})
      return
    }
    let cancelled = false
    setLoading(true)
    ;(async () => {
      const payload = await fetchPlayerShotChart(nbaId, season, seasonType)
      if (cancelled) return
      setShots(
        payload
          ? payload.rows
              .map(shotFromVaultRow)
              .filter((s): s is ShotPoint => s !== null)
          : null,
      )
      setMeta(payload?.meta ?? {})
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, seasonType])

  return { shots, meta, loading, fromApi: shots !== null }
}

/** Seasons this player actually has coordinate shot data for. */
export function useShotChartSeasons(playerId: string, seasonType = "Regular Season") {
  const nbaId = resolveNbaPlayerId(playerId)
  const [seasons, setSeasons] = useState<string[] | null>(null)

  useEffect(() => {
    if (!nbaId || !USE_STAGING_API) {
      setSeasons(null)
      return
    }
    let cancelled = false
    ;(async () => {
      const rows = await fetchPlayerShotChartSeasons(nbaId, seasonType)
      if (cancelled) return
      setSeasons(rows?.map((r) => r.season) ?? null)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, seasonType])

  return seasons
}
