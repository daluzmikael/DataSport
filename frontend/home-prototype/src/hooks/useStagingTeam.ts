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
import type { GameLogRow, GameLogTab } from "../data/playerGameLogMock"
import { getTeamSeasonGameLog, getTeamSeasonOptions } from "../data/teamSeasonGameLogBuilder"
import { leaderApiStat, mapLeaderRows } from "../api/teamLeaderStats"
import type { TeamLeaderStatId, TeamSeasonLeaderEntry } from "../data/teamSeasonLeadersMock"
import { getTeamFranchiseAccolades } from "../data/teamFranchiseFacts"
import { getTeamSeasonRoster } from "../data/teamSeasonRosterBuilder"
import type {
  TeamCurrentSeasonSnapshot,
  TeamHistorySeason,
  TeamProfile,
  TeamRosterPlayer,
} from "../types"

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
  const mockOptions = getTeamSeasonOptions(profile)
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
      setSeasons(sortSeasonsDesc([...apiSeasons, ...mockOptions]))
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId])

  const seasonList = fromApi && seasons ? seasons : mockOptions
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
  const [rows, setRows] = useState<ReturnType<typeof getTeamSeasonGameLog>["games"][GameLogTab] | null>(
    null,
  )
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

  const mock = getTeamSeasonGameLog(profile, season)
  const useVaultRows = fromApi && rows != null && (tab === "general" || tab === "advanced")
  return {
    rows: useVaultRows ? rows : mock.games[tab],
    averages: fromApi && averages && Object.keys(averages).length ? averages : mock.averages[tab],
    fromApi: useVaultRows || (fromApi && averages != null && Object.keys(averages).length > 0),
  }
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
  }, [nbaId, season, profile.currentSeason, profile.seasonLabel])

  const emptySnapshot: TeamCurrentSeasonSnapshot = {
    standing: "—",
    record: "—",
    bestPlayer: { name: "—", avgGameScore: 0 },
  }
  return {
    snapshot: snapshot ?? (nbaId ? emptySnapshot : profile.currentSeason),
    fromApi,
  }
}

export function useStagingTeamFranchiseAccolades(profile: TeamProfile) {
  return { accolades: getTeamFranchiseAccolades(profile.abbr) }
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
        standing: mapped.standing ?? profile.currentSeason.standing,
        record: mapped.record ?? profile.currentSeason.record,
      })
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, profile.currentSeason])

  return {
    currentSeason:
      fromApi && standing ? { ...profile.currentSeason, ...standing } : profile.currentSeason,
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
    history: fromApi && history ? history : profile.history,
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
    roster: fromApi && roster ? roster : getTeamSeasonRoster(profile, season),
    fromApi,
  }
}
