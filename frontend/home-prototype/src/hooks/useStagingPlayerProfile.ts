import { useEffect, useState } from "react"
import {
  fetchPlayerCareer,
  fetchPlayerGameLogSeasons,
  fetchPlayerImpactProfile,
  fetchPlayerSeasonStats,
} from "../api/stagingClient"
import { playerProfileFromSeasonStats, stubPlayerForStaging } from "../api/mappers"
import { USE_STAGING_API } from "../api/config"
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
    const [stats, impact] = await Promise.all([
      fetchPlayerSeasonStats(nbaId, s),
      fetchPlayerImpactProfile(nbaId, s),
    ])
    if (stats) {
      const profile = playerProfileFromSeasonStats(nbaId, stats)
      if (impact?.label) {
        profile.impactLabel = impact.label
        profile.impactHeadlineMetric = impact.headline_metric
        if (impact.headline_score != null) {
          profile.impactHeadlineScore = impact.headline_score
        }
      }
      return profile
    }
  }

  const career = await fetchPlayerCareer(nbaId)
  if (career?.length) {
    const name = career.map((r) => pickName(r)).find(Boolean) ?? "Player"
    const teamAbbr = career.map((r) => pickTeamAbbr(r)).find(Boolean) ?? "—"
    return stubPlayerForStaging(nbaId, name, teamAbbr)
  }

  // Every read failed (usually a busy/restarting backend) — let the caller retry.
  return null
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
  // Every profile is a vault read now. `getPlayerProfile` returned a fixture for a
  // handful of ids and short-circuited the API for exactly those players.
  const nbaId = playerId ? resolveNbaPlayerId(playerId) : null
  const useVault = Boolean(nbaId && USE_STAGING_API)

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
      let profile: PlayerLive | null = null
      for (let attempt = 0; attempt < 3 && !profile; attempt++) {
        if (attempt > 0) await new Promise((r) => setTimeout(r, 1500 * attempt))
        if (cancelled) return
        profile = await resolveVaultPlayerProfile(nbaId, preferredSeason)
      }
      if (cancelled) return
      setVaultProfile(profile ?? stubPlayerForStaging(nbaId, "Player", "—"))
      setLoading(false)
    })()

    return () => {
      cancelled = true
    }
  }, [useVault, nbaId, preferredSeason])

  const player = vaultProfile
  return {
    player: player ?? null,
    loading: useVault && loading && !player,
    fromVault: Boolean(vaultProfile),
  }
}
