import { useEffect, useMemo, useState } from "react"
import {
  fetchPlayerCareer,
  fetchPlayerGameLogSeasons,
  fetchPlayerSeasonStats,
} from "../api/stagingClient"
import { playerProfileFromSeasonStats, stubPlayerForStaging } from "../api/mappers"
import { USE_STAGING_API } from "../api/config"
import { getPlayerProfile } from "../data/mock"
import { resolveNbaPlayerId } from "../api/nbaIds"
import type { PlayerLive } from "../types"

function pickName(row: Record<string, unknown>): string | null {
  const name = row.PLAYER_NAME ?? row.player_name
  return name != null && String(name).trim() ? String(name) : null
}

function pickTeamAbbr(row: Record<string, unknown>): string | null {
  const abbr = row.TEAM_ABBREVIATION ?? row.team_abbreviation
  return abbr != null && String(abbr).trim() ? String(abbr) : null
}

async function resolveVaultPlayerProfile(
  nbaId: string,
  preferredSeason?: string | null,
): Promise<PlayerLive | null> {
  const seasonCandidates: string[] = []
  if (preferredSeason) seasonCandidates.push(preferredSeason)

  const logSeasons = await fetchPlayerGameLogSeasons(nbaId)
  if (logSeasons?.length) {
    for (const s of logSeasons) {
      if (!seasonCandidates.includes(s)) seasonCandidates.push(s)
    }
  }

  for (const s of seasonCandidates) {
    const stats = await fetchPlayerSeasonStats(nbaId, s)
    if (stats) return playerProfileFromSeasonStats(nbaId, stats)
  }

  const career = await fetchPlayerCareer(nbaId)
  if (career?.length) {
    const name = career.map((r) => pickName(r)).find(Boolean) ?? "Player"
    const teamAbbr = career.map((r) => pickTeamAbbr(r)).find(Boolean) ?? "—"
    return stubPlayerForStaging(nbaId, name, teamAbbr)
  }

  return stubPlayerForStaging(nbaId, "Player", "—")
}

/**
 * Resolve a player profile for the detail overlay.
 * Mock/demo players first; vault players load from season stats for the
 * requested season (e.g. library index season), then fall back to other seasons.
 */
export function useStagingPlayerProfile(
  playerId: string | null,
  preferredSeason?: string | null,
) {
  const mockProfile = useMemo(
    () => (playerId ? getPlayerProfile(playerId) : undefined),
    [playerId],
  )
  const nbaId = playerId ? resolveNbaPlayerId(playerId) : null
  const useVault = Boolean(nbaId && USE_STAGING_API && !mockProfile)

  const [vaultProfile, setVaultProfile] = useState<PlayerLive | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!useVault || !nbaId) {
      setVaultProfile(null)
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setVaultProfile(null)

    ;(async () => {
      const profile = await resolveVaultPlayerProfile(nbaId, preferredSeason)
      if (cancelled) return
      setVaultProfile(profile)
      setLoading(false)
    })()

    return () => {
      cancelled = true
    }
  }, [useVault, nbaId, preferredSeason])

  const player = mockProfile ?? vaultProfile
  return {
    player: player ?? null,
    loading: useVault && loading && !player,
    fromVault: Boolean(vaultProfile),
  }
}
