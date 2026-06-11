import { useEffect, useMemo, useRef, useState } from "react"

import {

  fetchPlayerCareer,

  fetchPlayerGameLogSeasons,

  fetchPlayerGameLogSingle,

  fetchPlayerGameLogsOutcome,

  fetchPlayerSeasonStats,

} from "../api/stagingClient"

import {

  averagesFromGameLogRows,

  mapPlayerCareerToRows,

  mapPlayerGameLogAdvancedRow,

  mapPlayerGameLogRow,

  mapPlayerGameLogToSnapshot,

  mapSeasonStatsToAverages,

  mapCareerTotalsForAccolades,

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

const RETRY_BASE_MS = 350
const RETRY_MAX_MS = 2500

function sleep(ms: number, signal?: AbortSignal): Promise<boolean> {
  if (signal?.aborted) return Promise.resolve(false)
  return new Promise((resolve) => {
    const timer = window.setTimeout(() => resolve(!signal?.aborted), ms)
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer)
        resolve(false)
      },
      { once: true },
    )
  })
}



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

    seasonsReady: !nbaId || !USE_STAGING_API || status === "ready",

    fromApi: useApi,

    defaultSeason: resolvedSeasons[0] ?? mockSeasons[0],

  }

}



export function useStagingPlayerGameLog(

  playerId: string,

  season: string,

  tab: PlayerGameLogTab,

  isCareer: boolean,

  fetchEnabled: boolean,

) {

  const nbaId = resolveNbaPlayerId(playerId)

  const useStaging = Boolean(nbaId && USE_STAGING_API)



  const [rawLogs, setRawLogs] = useState<Record<string, unknown>[]>([])

  const [careerData, setCareerData] = useState<Record<string, unknown>[] | null>(null)

  const [seasonStats, setSeasonStats] = useState<Record<string, unknown> | null>(null)

  const [logsStatus, setLogsStatus] = useState<LoadStatus>("idle")

  const [statsStatus, setStatsStatus] = useState<LoadStatus>("idle")



  const requestKey = useRef(0)

  const fetchTarget = useRef("")



  useEffect(() => {

    if (!useStaging || !fetchEnabled) {

      setRawLogs([])

      setCareerData(null)

      setSeasonStats(null)

      setLogsStatus("idle")

      setStatsStatus("idle")

      fetchTarget.current = ""

      return

    }



    const targetKey = `${nbaId}|${season}|${isCareer ? "career" : "season"}`

    const reqId = ++requestKey.current

    const ac = new AbortController()

    let cancelled = false

    const targetChanged = fetchTarget.current !== targetKey

    if (targetChanged) {

      fetchTarget.current = targetKey

      setRawLogs([])

      setCareerData(null)

      setSeasonStats(null)

      setLogsStatus("loading")

      setStatsStatus(isCareer ? "idle" : "loading")

    }



    const isStale = () => cancelled || reqId !== requestKey.current



    ;(async () => {



      if (isCareer) {

        setLogsStatus("loading")

        setStatsStatus("idle")



        let careerDelay = RETRY_BASE_MS

        while (true) {

          if (isStale() || ac.signal.aborted) return

          setLogsStatus("loading")

          const career = await fetchPlayerCareer(nbaId!)

          if (isStale()) return

          if (career?.length) {

            setCareerData(career)

            setLogsStatus("ready")

            return

          }

          const cont = await sleep(careerDelay, ac.signal)

          if (!cont || isStale()) return

          careerDelay = Math.min(careerDelay + 300, RETRY_MAX_MS)

        }

      }



      // Keep retrying until logs load — tab switches only remap client-side.

      let logsDelay = RETRY_BASE_MS

      while (true) {

        if (isStale() || ac.signal.aborted) return

        setLogsStatus("loading")



        const outcome = await fetchPlayerGameLogsOutcome(

          nbaId!,

          season,

          "Regular Season",

          500,

          { includeAdvanced: true },

        )



        if (isStale()) return



        if (outcome.kind === "ok") {

          setRawLogs(outcome.data)

          setLogsStatus("ready")

          break

        }



        if (outcome.kind === "empty") {

          setRawLogs([])

          setLogsStatus("ready")

          break

        }



        const cont = await sleep(logsDelay, ac.signal)

        if (!cont || isStale()) return

        logsDelay = Math.min(logsDelay + 300, RETRY_MAX_MS)

      }



      let statsDelay = RETRY_BASE_MS

      while (true) {

        if (isStale() || ac.signal.aborted) return

        setStatsStatus("loading")

        const stats = await fetchPlayerSeasonStats(nbaId!, season)

        if (isStale()) return

        if (stats) {

          setSeasonStats(stats)

          setStatsStatus("ready")

          break

        }

        const cont = await sleep(statsDelay, ac.signal)

        if (!cont || isStale()) return

        statsDelay = Math.min(statsDelay + 300, RETRY_MAX_MS)

      }

    })()



    return () => {

      cancelled = true

      ac.abort()

    }

  }, [nbaId, season, isCareer, useStaging, fetchEnabled])



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



  const statsFromApi = statsStatus === "ready" && seasonStats != null

  const tableRowsReady =
    logsStatus === "ready" &&
    (isCareer ? Boolean(rows && rows.length > 0) : rawLogs.length > 0)



  return {

    rows: useStaging ? (tableRowsReady ? (rows ?? []) : []) : mockRows,

    averages: useStaging

      ? statsFromApi && averages != null

        ? averages

        : null

      : mockAverages,

    bubbles: useStaging ? bubbles : mockBubbles,

    bubblesFromApi: statsFromApi,

    fromApi: tableRowsReady,

    logsLoading: useStaging && logsStatus === "loading",

    statsLoading: useStaging && statsStatus === "loading",

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



export function useStagingPlayerCareerTotals(playerId: string) {

  const nbaId = resolveNbaPlayerId(playerId)

  const [careerTotals, setCareerTotals] = useState<Record<string, number> | undefined>(

    undefined,

  )

  const [loading, setLoading] = useState(false)



  useEffect(() => {

    if (!nbaId || !USE_STAGING_API) {

      setCareerTotals(undefined)

      setLoading(false)

      return

    }



    let cancelled = false

    setLoading(true)



    ;(async () => {

      const career = await fetchPlayerCareer(nbaId)

      if (cancelled) return

      setCareerTotals(

        career?.length ? mapCareerTotalsForAccolades(career) : undefined,

      )

      setLoading(false)

    })()



    return () => {

      cancelled = true

    }

  }, [nbaId])



  return { careerTotals, loading }

}



/**
 * Standard entry point for PlayerGameLogTable + PlayerStatBubbles.
 * Pass any resolvable player id (`1628369`, `nba-1628369`, or mock alias).
 */
export function usePlayerGameLogTableState(playerId: string) {
  const [tab, setTab] = useState<PlayerGameLogTab>("general")
  const {
    seasons,
    defaultSeason,
    fromApi: seasonsFromApi,
    seasonsLoading,
    seasonsReady,
  } = usePlayerGameLogSeasons(playerId)

  const [season, setSeason] = useState<string>(defaultSeason)
  const activePlayer = useRef(playerId)

  useEffect(() => {
    if (!seasonsReady) return
    if (activePlayer.current !== playerId) {
      activePlayer.current = playerId
      setSeason(seasons[0] ?? defaultSeason)
    }
  }, [playerId, seasonsReady, seasons, defaultSeason])

  useEffect(() => {
    if (!seasonsReady) return
    if (!seasons.includes(season) && season !== CAREER_LOG_VALUE) {
      setSeason(seasons[0] ?? defaultSeason)
    }
  }, [seasons, season, defaultSeason, seasonsReady])

  const isCareer = season === CAREER_LOG_VALUE
  const fetchEnabled = seasonsReady && (isCareer || seasons.includes(season))
  const nbaId = resolveNbaPlayerId(playerId)
  const usesStaging = Boolean(nbaId && USE_STAGING_API)

  const gameLog = useStagingPlayerGameLog(
    playerId,
    season,
    tab,
    isCareer,
    fetchEnabled,
  )

  return {
    tab,
    setTab,
    season,
    setSeason,
    seasons,
    seasonsLoading,
    seasonsReady,
    seasonsFromApi,
    isCareer,
    usesStaging,
    nbaId,
    latestSeason: seasons[0],
    ...gameLog,
  }
}

export { CAREER_LOG_VALUE }


