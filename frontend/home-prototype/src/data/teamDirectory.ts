/** Team identity, from the vault.
 *
 * Replaces the identity half of `teamProfileMock` and the `SEARCHABLE_TEAMS` list in
 * `favoritesMock`. Names and tricodes come from `/api/staging/teams`, which reads
 * `team_season_stats` for the requested season — so asking for 1996-97 returns the
 * Seattle SuperSonics and the Washington Bullets, not their modern successors.
 *
 * The fetch is cached at module scope: the directory is 30 rows and every surface in
 * the app needs it, so re-fetching per component would be pure waste.
 */
import { useEffect, useState } from "react"

import { fetchTeamsDirectory, type TeamDirectoryEntry } from "../api/stagingClient"
import type { TeamProfile } from "../types"

export type { TeamDirectoryEntry }

let cache: Promise<TeamDirectoryEntry[]> | null = null

export function loadTeamDirectory(): Promise<TeamDirectoryEntry[]> {
  if (!cache) {
    cache = fetchTeamsDirectory().then((rows) => rows ?? [])
  }
  return cache
}

export function teamProfileIdFromAbbr(abbr: string): string {
  return `team-${abbr.toLowerCase()}`
}

export function abbrFromTeamProfileId(profileId: string): string {
  return profileId.replace(/^team-/, "").toUpperCase()
}

export function entryToProfile(
  entry: TeamDirectoryEntry,
  seasonLabel: string,
): TeamProfile {
  return {
    id: teamProfileIdFromAbbr(entry.abbr),
    abbr: entry.abbr,
    city: entry.city,
    name: entry.nickname,
    seasonLabel,
  }
}

export function useTeamDirectory() {
  const [teams, setTeams] = useState<TeamDirectoryEntry[] | null>(null)

  useEffect(() => {
    let cancelled = false
    loadTeamDirectory().then((rows) => {
      if (!cancelled) setTeams(rows)
    })
    return () => {
      cancelled = true
    }
  }, [])

  return teams
}

/** One team's identity as a `TeamProfile`, or null while loading / when unknown. */
export function useTeamProfile(
  teamProfileId: string | null,
  seasonLabel: string,
): TeamProfile | null {
  const teams = useTeamDirectory()
  if (!teamProfileId || !teams) return null
  const abbr = abbrFromTeamProfileId(teamProfileId)
  const entry = teams.find((t) => t.abbr.toUpperCase() === abbr)
  return entry ? entryToProfile(entry, seasonLabel) : null
}
