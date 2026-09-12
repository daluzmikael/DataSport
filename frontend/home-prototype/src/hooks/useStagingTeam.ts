import { useEffect, useMemo, useState } from "react"
import {
  fetchTeamBestPlayer,
  fetchTeamGameLogSeasons,
  fetchTeamGameLogs,
  fetchTeamLeaders,
  fetchTeamRoster,
  fetchTeamSeasonHistory,
  fetchTeamSeasonStats,
  fetchTeamStandings,
} from "../api/stagingClient"
import {
  averagesFromGameLogRows,
  mapSeasonStatsToAverages,
  mapTeamGameLogAdvancedRow,
  mapTeamGameLogRow,
  mapTeamHistoryRow,
  mapTeamRosterRow,
  mapTeamStandingsSnapshot,
} from "../api/mappers"
import { resolveNbaTeamId, teamAbbrFromProfileId } from "../api/nbaIds"
import type { GameLogRow, GameLogTab } from "../data/schema/gameLog"
import { leaderApiStat, mapLeaderRow, mapLeaderRows } from "../api/teamLeaderStats"
import {
  TEAM_LEADER_STAT_OPTIONS,
  type TeamLeaderStatId,
  type TeamSeasonLeaderEntry,
} from "../data/schema/teamLeaders"
import { fetchTeamFranchise } from "../api/stagingClient"
import type {
  TeamCurrentSeasonSnapshot,
  TeamFranchiseAccolades,
  TeamHistorySeason,
  TeamProfile,
  TeamRosterPlayer,
  TeamSeasonGameRow,
} from "../types"

/** What a team surface shows before the vault answers, and when it has nothing.
 *  Dashes, never a plausible-looking record. */
const EMPTY_SNAPSHOT: TeamCurrentSeasonSnapshot = {
  standing: "—",
  record: "—",
  bestPlayer: { name: "—", avgGameScore: 0 },
}

function teamNbaId(profile: TeamProfile): string | null {
  return resolveNbaTeamId(teamAbbrFromProfileId(profile.id))
}

function sortSeasonsDesc(seasons: string[]): string[] {
  return [...new Set(seasons)].sort((a, b) => {
    const ya = parseInt(a.split("-")[0] ?? "0", 10)
    const yb = parseInt(b.split("-")[0] ?? "0", 10)
    return yb - ya
  })
}

export function useStagingTeamSeasons(profile: TeamProfile) {
  const nbaId = teamNbaId(profile)
  const [seasons, setSeasons] = useState<string[] | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setSeasons(null)
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const apiSeasons = await fetchTeamGameLogSeasons(nbaId)
      if (cancelled) return
      if (!apiSeasons?.length) {
        setSeasons(null)
        setFromApi(false)
        return
      }
      setSeasons(sortSeasonsDesc(apiSeasons))
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId])

  const seasonList = fromApi && seasons ? seasons : []
  return {
    seasons: seasonList,
    latestSeason: seasonList[0] ?? profile.seasonLabel,
    fromApi,
  }
}

/** Season dropdown synced to vault newest season when available. */
export function useTeamVaultSeason(profile: TeamProfile) {
  const { seasons, latestSeason, fromApi } = useStagingTeamSeasons(profile)
  const [season, setSeason] = useState(profile.seasonLabel)

  useEffect(() => {
    setSeason(fromApi ? latestSeason : profile.seasonLabel)
  }, [profile.id, profile.seasonLabel, fromApi, latestSeason])

  return useMemo(
    () => ({ season, setSeason, seasons, latestSeason, fromApi }),
    [season, seasons, latestSeason, fromApi],
  )
}

export function useStagingTeamGameLog(profile: TeamProfile, season: string, tab: GameLogTab) {
  const nbaId = teamNbaId(profile)
  const [rows, setRows] = useState<TeamSeasonGameRow[] | null>(null)
  const [averages, setAverages] = useState<Record<string, string | number> | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const needsAdvancedRows = tab === "advanced"
      const measureType = tab === "advanced" ? "Advanced" : "Base"
      const [logs, stats] = await Promise.all([
        fetchTeamGameLogs(nbaId, season, "Regular Season", {
          includeAdvanced: needsAdvancedRows,
        }),
        fetchTeamSeasonStats(nbaId, season, "Regular Season", measureType),
      ])
      if (cancelled) return
      if (!logs?.length && !stats) {
        setFromApi(false)
        return
      }
      const mapped =
        tab === "advanced"
          ? (logs ?? []).map(mapTeamGameLogAdvancedRow)
          : tab === "general"
            ? (logs ?? []).map(mapTeamGameLogRow)
            : null
      if (mapped) {
        setRows(mapped)
      } else {
        setRows(null)
      }
      const seasonAvgs = mapSeasonStatsToAverages(stats, tab)
      if (Object.keys(seasonAvgs).length) {
        setAverages(seasonAvgs)
      } else if (mapped?.length && tab === "advanced") {
        setAverages(
          averagesFromGameLogRows(
            mapped.map((r) => ({ ...r, isLive: r.isLive ?? false })) as GameLogRow[],
            tab,
          ),
        )
      } else {
        setAverages(null)
      }
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, tab])

  // Per-36 and per-100 team game logs are not staged, so those tabs are genuinely
  // empty rather than filled from the general tab with different-looking numbers.
  const useVaultRows = fromApi && rows != null && (tab === "general" || tab === "advanced")
  return {
    rows: useVaultRows ? rows : [],
    averages: fromApi && averages && Object.keys(averages).length ? averages : null,
    fromApi: useVaultRows || (fromApi && averages != null && Object.keys(averages).length > 0),
  }
}

/** A leader slot the vault has no answer for. The module this replaced INVENTED one —
 *  a real roster name attached to a generated number, for any team without a fixture. */
function blankLeaders(): Record<TeamLeaderStatId, TeamSeasonLeaderEntry> {
  const out = {} as Record<TeamLeaderStatId, TeamSeasonLeaderEntry>
  for (const { id } of TEAM_LEADER_STAT_OPTIONS) {
    out[id] = { player: "—", value: "—" }
  }
  return out
}

const EMPTY_LEADERS: TeamSeasonLeaderEntry[] = [
  { player: "—", value: "—" },
  { player: "—", value: "—" },
  { player: "—", value: "—" },
]

export function useStagingTeamLeaders(
  profile: TeamProfile,
  season: string,
  statId: TeamLeaderStatId,
  limit = 3,
) {
  const nbaId = teamNbaId(profile)
  const [leaders, setLeaders] = useState<TeamSeasonLeaderEntry[]>(EMPTY_LEADERS)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setLeaders(EMPTY_LEADERS.slice(0, limit))
      setFromApi(false)
      return
    }
    setLeaders(EMPTY_LEADERS.slice(0, limit))
    setFromApi(false)
    let cancelled = false
    ;(async () => {
      const apiStat = leaderApiStat(statId)
      if (!apiStat) {
        if (!cancelled) {
          setLeaders(EMPTY_LEADERS.slice(0, limit))
          setFromApi(false)
        }
        return
      }
      const rows = await fetchTeamLeaders(nbaId, season, apiStat)
      if (cancelled) return
      setLeaders(mapLeaderRows(statId, rows, limit))
      setFromApi(Boolean(rows?.length))
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, statId, limit])

  return {
    leaders,
    fromApi,
  }
}

/** All 12 per-stat leaders in one shot, for the full Season Leaders table. */
export function useStagingTeamAllLeaders(profile: TeamProfile, season: string) {
  const nbaId = teamNbaId(profile)
  const [leaders, setLeaders] = useState<Record<TeamLeaderStatId, TeamSeasonLeaderEntry>>(
    () => blankLeaders(),
  )
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setLeaders(blankLeaders())
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const entries = await Promise.all(
        TEAM_LEADER_STAT_OPTIONS.map(async ({ id }) => {
          const apiStat = leaderApiStat(id)
          if (!apiStat) return [id, null] as const
          const rows = await fetchTeamLeaders(nbaId, season, apiStat)
          return [id, rows?.[0] ?? null] as const
        }),
      )
      if (cancelled) return
      const anyResolved = entries.some(([, row]) => row != null)
      const result = blankLeaders()
      for (const [id, row] of entries) {
        if (row) result[id] = mapLeaderRow(id, row)
      }
      setLeaders(result)
      setFromApi(anyResolved)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, profile.id])

  return { leaders, fromApi }
}

export function useStagingTeamSeasonSnapshot(profile: TeamProfile, season: string) {
  const nbaId = teamNbaId(profile)
  const [snapshot, setSnapshot] = useState<TeamCurrentSeasonSnapshot | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setSnapshot(null)
      setFromApi(false)
      return
    }
    setSnapshot(null)
    setFromApi(false)
    let cancelled = false
    ;(async () => {
      const [standings, bestPlayer] = await Promise.all([
        fetchTeamStandings(nbaId, season),
        fetchTeamBestPlayer(nbaId, season),
      ])
      if (cancelled) return

      const standingsMapped = standings ? mapTeamStandingsSnapshot(standings) : null
      const hasStandings =
        standingsMapped != null &&
        (standingsMapped.standing != null || standingsMapped.record != null)
      const hasBest = bestPlayer?.PLAYER_NAME != null

      if (!hasStandings && !hasBest) {
        setSnapshot(null)
        setFromApi(false)
        return
      }

      setSnapshot({
        standing: standingsMapped?.standing ?? "—",
        record: standingsMapped?.record ?? "—",
        bestPlayer: hasBest
          ? {
              name: String(bestPlayer!.PLAYER_NAME),
              avgGameScore: Math.round(Number(bestPlayer!.game_score ?? 0) * 10) / 10,
            }
          : { name: "—", avgGameScore: 0 },
      })
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, profile.seasonLabel])

  return {
    snapshot: snapshot ?? EMPTY_SNAPSHOT,
    fromApi,
  }
}

/** Championships, conference titles and all-time record, from `franchise_history`.
 *
 * The module this replaced kept a hand-typed founding year per team and derived the
 * rest — and it had no championship data at all, so every team showed 0 titles. The
 * vault has had `LEAGUE_TITLES` since the phase-7 pull. */
export function useStagingTeamFranchiseAccolades(profile: TeamProfile) {
  const nbaId = teamNbaId(profile)
  const [accolades, setAccolades] = useState<TeamFranchiseAccolades | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setAccolades(null)
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const payload = await fetchTeamFranchise(nbaId)
      if (cancelled) return
      const row = payload?.overall
      if (!row) {
        setFromApi(false)
        return
      }
      const wins = Number(row.WINS ?? 0)
      const losses = Number(row.LOSSES ?? 0)
      const start = Number(row.START_YEAR ?? 0)
      setAccolades({
        allTimeRecord: `${wins}-${losses}`,
        championships: Number(row.LEAGUE_TITLES ?? 0),
        conferenceTitles: Number(row.CONF_TITLES ?? 0),
        // The endpoint gives counts, not dates. Claiming a year would be inventing one.
        lastChampionship: "—",
        lastPlayoffs: "—",
        founded: start ? String(start) : "—",
        yearsInAssociation: Number(row.YEARS ?? 0),
      })
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId])

  return { accolades, fromApi }
}

export function useStagingTeamStandings(profile: TeamProfile, season: string) {
  const nbaId = teamNbaId(profile)
  const [standing, setStanding] = useState<{ standing: string; record: string } | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const row = await fetchTeamStandings(nbaId, season)
      if (cancelled) return
      if (!row) {
        setFromApi(false)
        return
      }
      const mapped = mapTeamStandingsSnapshot(row)
      setStanding({
        standing: mapped.standing ?? "—",
        record: mapped.record ?? "—",
      })
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season])

  return {
    currentSeason: fromApi && standing ? { ...EMPTY_SNAPSHOT, ...standing } : EMPTY_SNAPSHOT,
    fromApi,
  }
}

export function useStagingTeamHistory(profile: TeamProfile) {
  const nbaId = teamNbaId(profile)
  const [history, setHistory] = useState<TeamHistorySeason[] | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const rows = await fetchTeamSeasonHistory(nbaId)
      if (cancelled) return
      if (!rows?.length) {
        setFromApi(false)
        return
      }
      setHistory(rows.map(mapTeamHistoryRow))
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId])

  return {
    history: fromApi && history ? history : [],
    fromApi,
  }
}

export function useStagingTeamRoster(profile: TeamProfile, season: string) {
  const nbaId = teamNbaId(profile)
  const [roster, setRoster] = useState<TeamRosterPlayer[] | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const rows = await fetchTeamRoster(nbaId, season)
      if (cancelled) return
      if (!rows?.length) {
        setFromApi(false)
        return
      }
      setRoster(rows.map(mapTeamRosterRow))
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season])

  return {
    roster: fromApi && roster ? roster : [],
    fromApi,
  }
}
