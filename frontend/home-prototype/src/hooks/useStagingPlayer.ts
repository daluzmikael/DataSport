import { useEffect, useMemo, useRef, useState } from "react"
import {
  fetchPlayerCareer,
  fetchPlayerGameLogSeasons,
  fetchPlayerGameLogSingle,
  fetchPlayerGameLogsWithMeta,
  fetchPlayerSeasonStats,
} from "../api/stagingClient"
import {
  averagesFromGameLogRows,
  filterGameLogRecords,
  mapPlayerCareerToRows,
  mapPlayerGameLogAdvancedRow,
  mapPlayerGameLogRow,
  mapPlayerGameLogToSnapshot,
  mapSeasonStatsToAverages,
  mapSeasonStatsToBubbles,
  stubPlayerForStaging,
  type PlayerGameSnapshot,
} from "../api/mappers"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { USE_STAGING_API } from "../api/config"
import {
  CAREER_LOG_VALUE,
  SEASON_OPTIONS,
  type GameLogRow,
  type GameLogTab,
} from "../data/playerGameLogMock"
import type { PlayerLive } from "../types"
import type { SeasonBubbleSet } from "../data/playerSeasonAverages"
import { getSeasonAverages, getSeasonLogs } from "../data/playerGameLogMock"
import { getCareerLogs } from "../data/playerCareerLogMock"
import { getPlayerSeasonBubbles } from "../data/playerSeasonAverages"

export type PlayerGameLogTab = "general" | "advanced"

type LoadStatus = "idle" | "loading" | "ready" | "error"

export function usePlayerGameLogSeasons(playerId: string) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [seasons, setSeasons] = useState<string[] | null>(null)
  const [status, setStatus] = useState<LoadStatus>("idle")

  useEffect(() => {
    if (!nbaId || !USE_STAGING_API) {
      setSeasons(null)
      setStatus(nbaId ? "error" : "idle")
      return
    }

    let cancelled = false
    setStatus("loading")
    setSeasons(null)

    ;(async () => {
      const apiSeasons = await fetchPlayerGameLogSeasons(nbaId)
      if (cancelled) return

      if (apiSeasons?.length) {
        setSeasons(apiSeasons)
        setStatus("ready")
      } else {
        setSeasons(null)
        setStatus("error")
      }
    })()

    return () => {
      cancelled = true
    }
  }, [nbaId])

  const mockSeasons = SEASON_OPTIONS.map((o) => o.value)
  const useApi = Boolean(nbaId && USE_STAGING_API && status === "ready" && seasons?.length)
  const resolvedSeasons = useApi ? seasons! : mockSeasons

  return {
    seasons: resolvedSeasons,
    seasonsLoading: Boolean(nbaId && USE_STAGING_API && status === "loading"),
    seasonsReady: !nbaId || !USE_STAGING_API || status === "ready" || status === "error",
    fromApi: useApi,
    defaultSeason: resolvedSeasons[0] ?? mockSeasons[0],
  }
}

export function useStagingPlayerGameLog(
  playerId: string,
  season: string,
  tab: PlayerGameLogTab,
  isCareer: boolean,
  seasonsReady: boolean,
) {
  const nbaId = resolveNbaPlayerId(playerId)
  const useStaging = Boolean(nbaId && USE_STAGING_API)

  const [rawLogs, setRawLogs] = useState<Record<string, unknown>[]>([])
  const [careerData, setCareerData] = useState<Record<string, unknown>[] | null>(null)
  const [seasonStats, setSeasonStats] = useState<Record<string, unknown> | null>(null)
  const [logsStatus, setLogsStatus] = useState<LoadStatus>("idle")
  const [statsStatus, setStatsStatus] = useState<LoadStatus>("idle")

  const requestKey = useRef(0)

  useEffect(() => {
    if (!useStaging || !seasonsReady) {
      setRawLogs([])
      setCareerData(null)
      setSeasonStats(null)
      setLogsStatus("idle")
      setStatsStatus("idle")
      return
    }

    const reqId = ++requestKey.current
    let cancelled = false

    ;(async () => {
      if (isCareer) {
        setLogsStatus("loading")
        setStatsStatus("idle")
        setRawLogs([])
        setSeasonStats(null)
        setCareerData(null)

        const career = await fetchPlayerCareer(nbaId!)
        if (cancelled || reqId !== requestKey.current) return

        if (!career?.length) {
          setCareerData(null)
          setLogsStatus("error")
          return
        }
        setCareerData(career)
        setLogsStatus("ready")
        return
      }

      setCareerData(null)
      setRawLogs([])
      setSeasonStats(null)
      setLogsStatus("loading")
      setStatsStatus("loading")

      // Game logs first — must be real per-game rows (validated in stagingClient).
      const logResponse = await fetchPlayerGameLogsWithMeta(
        nbaId!,
        season,
        "Regular Season",
        500,
        { includeAdvanced: tab === "advanced" },
      )
      if (cancelled || reqId !== requestKey.current) return

      const validatedLogs = filterGameLogRecords(logResponse?.data ?? [])
      if (validatedLogs.length > 0) {
        setRawLogs(validatedLogs)
        setLogsStatus("ready")
      } else {
        setRawLogs([])
        setLogsStatus("error")
      }

      const stats = await fetchPlayerSeasonStats(nbaId!, season)
      if (cancelled || reqId !== requestKey.current) return

      if (stats) {
        setSeasonStats(stats)
        setStatsStatus("ready")
      } else {
        setSeasonStats(null)
        setStatsStatus("error")
      }
    })()

    return () => {
      cancelled = true
    }
  }, [nbaId, season, isCareer, useStaging, seasonsReady, tab])

  const { rows, averages } = useMemo(() => {
    if (isCareer) {
      if (!careerData?.length) return { rows: null as GameLogRow[] | null, averages: null }
      return mapPlayerCareerToRows(careerData, tab)
    }

    if (!rawLogs.length) {
      return {
        rows: [] as GameLogRow[],
        averages:
          statsStatus === "ready" && seasonStats
            ? mapSeasonStatsToAverages(seasonStats, tab)
            : null,
      }
    }

    const mappedGeneral = rawLogs.map((row, i) => mapPlayerGameLogRow(row, i))
    const mappedAdvanced = rawLogs.map((row, i) => mapPlayerGameLogAdvancedRow(row, i))
    const mappedRows = tab === "general" ? mappedGeneral : mappedAdvanced
    return {
      rows: mappedRows,
      averages:
        statsStatus === "ready" && seasonStats
          ? mapSeasonStatsToAverages(seasonStats, tab)
          : averagesFromGameLogRows(mappedRows, tab),
    }
  }, [isCareer, careerData, rawLogs, seasonStats, statsStatus, tab])

  const bubbles = useMemo((): SeasonBubbleSet | null => {
    if (isCareer || statsStatus !== "ready" || !seasonStats) return null
    return mapSeasonStatsToBubbles(seasonStats)
  }, [isCareer, seasonStats, statsStatus])

  const mockTab = tab as GameLogTab
  const mockRows = isCareer ? getCareerLogs(playerId)[mockTab] : getSeasonLogs(season)[mockTab]
  const mockAverages = getSeasonAverages(season, mockTab)
  const mockBubbles = getPlayerSeasonBubbles(season)

  const logsFromApi = logsStatus === "ready" && rawLogs.length > 0
  const statsFromApi = statsStatus === "ready" && seasonStats != null

  return {
    rows: useStaging ? (logsFromApi ? rows : []) : mockRows,
    averages: useStaging
      ? statsFromApi && averages != null
        ? averages
        : null
      : mockAverages,
    bubbles: useStaging ? bubbles : mockBubbles,
    bubblesFromApi: statsFromApi,
    fromApi: logsFromApi,
    logsLoading: useStaging && logsStatus === "loading",
    statsLoading: useStaging && statsStatus === "loading",
    logsError: useStaging && logsStatus === "error",
    nbaId,
  }
}

export function useStagingPlayerGame(
  playerId: string,
  basePlayer: PlayerLive | null,
  nbaGameId: string | null,
) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [snapshot, setSnapshot] = useState<PlayerGameSnapshot | null>(null)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaId || !nbaGameId) {
      setSnapshot(null)
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const row = await fetchPlayerGameLogSingle(nbaId, nbaGameId)
      if (cancelled) return
      if (!row) {
        setSnapshot(null)
        setFromApi(false)
        return
      }
      const name = String(row.PLAYER_NAME ?? row.player_name ?? basePlayer?.name ?? "Player")
      const teamAbbr = String(row.TEAM_ABBREVIATION ?? row.team_abbreviation ?? basePlayer?.teamAbbr ?? "—")
      const base =
        basePlayer ?? stubPlayerForStaging(nbaId, name, teamAbbr)
      setSnapshot(mapPlayerGameLogToSnapshot(base, row))
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, nbaGameId, basePlayer])

  return { snapshot, fromApi }
}

export { CAREER_LOG_VALUE }
