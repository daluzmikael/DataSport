import { useEffect, useMemo, useState } from "react"
import { USE_STAGING_API } from "../api/config"
import {
  buildSeasonVsCareerCompare,
  buildSoloSkillRadar,
  CAREER_COMPARE_LABEL,
  careerCompareFooterText,
  type SkillCompareRow,
  type SkillRadarCategory,
} from "../api/playerSkillProfile"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { fetchPlayerCareer, fetchPlayerSeasonStats } from "../api/stagingClient"
import { CAREER_LOG_VALUE } from "../data/playerGameLogMock"

const CAREER_REG_TOTALS_DS = "1"

function findCareerTotals(
  career: Record<string, unknown>[],
): Record<string, unknown> | null {
  const wanted = new Set([CAREER_REG_TOTALS_DS, "CareerTotalsRegularSeason"])
  const row = career.find((r) => wanted.has(String(r.dataset ?? "")))
  return row ?? null
}

function careerAverageRow(totals: Record<string, unknown>): Record<string, unknown> {
  const gp = Number(totals.GP ?? totals.gp ?? 0)
  if (!gp || gp <= 0) return totals
  const out: Record<string, unknown> = { ...totals }
  for (const key of ["PTS", "REB", "AST", "STL", "BLK", "MIN"]) {
    const val = Number(totals[key] ?? totals[key.toLowerCase()] ?? 0)
    if (!Number.isNaN(val)) out[key] = val / gp
  }
  return out
}

async function fetchCareerAverages(nbaId: string): Promise<Record<string, unknown> | null> {
  const career = await fetchPlayerCareer(nbaId)
  const totals = career ? findCareerTotals(career) : null
  return totals ? careerAverageRow(totals) : null
}

function mockStatsForPlayer(playerId: string): Record<string, unknown> {
  const mocks: Record<string, Record<string, unknown>> = {
    "player-tatum": { PTS: 26.8, AST: 6.0, REB: 8.7, STL: 1.1, BLK: 0.5 },
    "player-curry": { PTS: 24.5, AST: 6.1, REB: 4.4, STL: 0.9, BLK: 0.4 },
    "player-lebron": { PTS: 25.0, AST: 7.5, REB: 7.5, STL: 1.2, BLK: 0.6 },
  }
  return mocks[playerId] ?? { PTS: 22, AST: 5, REB: 6, STL: 1, BLK: 0.5 }
}

function mockCareerForPlayer(playerId: string): Record<string, unknown> {
  const mocks: Record<string, Record<string, unknown>> = {
    "player-tatum": { PTS: 22.5, AST: 5.3, REB: 7.2, STL: 1.0, BLK: 0.6 },
    "player-curry": { PTS: 24.7, AST: 6.4, REB: 4.6, STL: 1.5, BLK: 0.2 },
    "player-lebron": { PTS: 27.0, AST: 7.4, REB: 7.5, STL: 1.5, BLK: 0.7 },
  }
  return mocks[playerId] ?? { PTS: 20, AST: 4.5, REB: 5.5, STL: 0.9, BLK: 0.4 }
}

export function useStagingPlayerSkillProfile(
  playerId: string,
  playerName: string,
  season: string,
) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [seasonRow, setSeasonRow] = useState<Record<string, unknown> | null>(null)
  const [careerRow, setCareerRow] = useState<Record<string, unknown> | null>(null)
  const [fromApi, setFromApi] = useState(false)
  const [loading, setLoading] = useState(false)
  const isCareerSeason = season === CAREER_LOG_VALUE

  useEffect(() => {
    if (!nbaId || !USE_STAGING_API || !season) {
      setSeasonRow(null)
      setCareerRow(null)
      setFromApi(false)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setSeasonRow(null)
    setCareerRow(null)
    setFromApi(false)
    ;(async () => {
      const careerAvg = await fetchCareerAverages(nbaId)
      let seasonStats: Record<string, unknown> | null = null
      if (isCareerSeason) {
        seasonStats = careerAvg
      } else {
        seasonStats = await fetchPlayerSeasonStats(nbaId, season, "Regular Season", "PerGame")
      }
      if (cancelled) return
      setSeasonRow(seasonStats)
      setCareerRow(careerAvg)
      setFromApi(Boolean(seasonStats || careerAvg))
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId, season, isCareerSeason])

  const solo: SkillRadarCategory[] = useMemo(() => {
    const row =
      fromApi && seasonRow ? seasonRow : mockStatsForPlayer(playerId)
    return buildSoloSkillRadar(row)
  }, [fromApi, seasonRow, playerId])

  const career: SkillRadarCategory[] = useMemo(() => {
    const row =
      fromApi && careerRow ? careerRow : mockCareerForPlayer(playerId)
    return buildSoloSkillRadar(row)
  }, [fromApi, careerRow, playerId])

  const compare: SkillCompareRow[] = useMemo(
    () =>
      buildSeasonVsCareerCompare(
        solo,
        career,
        isCareerSeason ? "Career" : season,
        CAREER_COMPARE_LABEL,
      ),
    [solo, career, season, isCareerSeason],
  )

  const compareFooter = useMemo(() => careerCompareFooterText(career), [career])

  return {
    solo,
    career,
    compare,
    fromApi,
    loading,
    compareLabel: CAREER_COMPARE_LABEL,
    compareFooter,
    isCareerSeason,
  }
}
