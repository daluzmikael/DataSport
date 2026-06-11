import { useEffect, useState } from "react"
import {
  fetchTeamGameLogs,
  fetchTeamLeaders,
  fetchTeamSeasonStats,
  fetchTeamStandings,
} from "../api/stagingClient"
import { mapSeasonStatsToAverages, mapTeamGameLogRow } from "../api/mappers"
import { resolveNbaTeamId, teamAbbrFromProfileId } from "../api/nbaIds"
import type { GameLogTab } from "../data/playerGameLogMock"
import { getTeamSeasonGameLog } from "../data/teamSeasonGameLogBuilder"
import {
  getTeamSeasonLeaders,
  type TeamLeaderStatId,
  type TeamSeasonLeaderEntry,
} from "../data/teamSeasonLeadersMock"
import type { TeamProfile } from "../types"

export function useStagingTeamGameLog(profile: TeamProfile, season: string, tab: GameLogTab) {
  const nbaId = resolveNbaTeamId(teamAbbrFromProfileId(profile.id))
  const [rows, setRows] = useState<ReturnType<typeof getTeamSeasonGameLog>["games"][GameLogTab] | null>(null)
  const [averages, setAverages] = useState<Record<string, string | number> | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const [logs, stats] = await Promise.all([
        tab === "general" ? fetchTeamGameLogs(nbaId, season) : Promise.resolve(null),
        fetchTeamSeasonStats(nbaId, season),
      ])
      if (cancelled) return
      if (!logs?.length && !stats) {
        setFromApi(false)
        return
      }
      setRows((logs ?? []).map(mapTeamGameLogRow))
      setAverages(mapSeasonStatsToAverages(stats, tab))
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, tab])

  const mock = getTeamSeasonGameLog(profile, season)
  return {
    rows: fromApi && rows ? rows : mock.games[tab],
    averages: fromApi && averages ? averages : mock.averages[tab],
    fromApi,
  }
}

export function useStagingTeamLeaders(profile: TeamProfile, season: string) {
  const nbaId = resolveNbaTeamId(teamAbbrFromProfileId(profile.id))
  const [leaders, setLeaders] = useState<Record<TeamLeaderStatId, TeamSeasonLeaderEntry> | null>(
    null,
  )
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId) {
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const [pts, reb, ast] = await Promise.all([
        fetchTeamLeaders(nbaId, season, "PTS"),
        fetchTeamLeaders(nbaId, season, "REB"),
        fetchTeamLeaders(nbaId, season, "AST"),
      ])
      if (cancelled) return
      if (!pts?.length) {
        setFromApi(false)
        return
      }
      const base = getTeamSeasonLeaders(profile, season)
      const top = (rows: NonNullable<typeof pts>) => ({
        player: String(rows[0]?.PLAYER_NAME ?? "—"),
        value: Number(rows[0]?.value ?? 0),
      })
      setLeaders({
        ...base,
        pts: top(pts ?? []),
        reb: top(reb ?? []),
        ast: top(ast ?? []),
      })
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, profile])

  return {
    leaders: fromApi && leaders ? leaders : getTeamSeasonLeaders(profile, season),
    fromApi,
  }
}

export function useStagingTeamStandings(profile: TeamProfile, season: string) {
  const nbaId = resolveNbaTeamId(teamAbbrFromProfileId(profile.id))
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
      const wins = row.W ?? row.wins
      const losses = row.L ?? row.losses
      const record = wins != null && losses != null ? `${wins}-${losses}` : profile.currentSeason.record
      const conf = row.ConferenceRecord ?? row.PlayoffRank ?? row.Conference
      setStanding({
        standing: conf != null ? String(conf) : profile.currentSeason.standing,
        record: String(record),
      })
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, profile.currentSeason])

  return {
    currentSeason: fromApi && standing
      ? { ...profile.currentSeason, ...standing }
      : profile.currentSeason,
    fromApi,
  }
}
