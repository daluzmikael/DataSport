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
import { CAREER_LOG_VALUE } from "../data/schema/gameLog"

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

/* Two fixture tables used to sit here: hand-typed PTS/AST/REB/STL/BLK for three
 * players, plus a generic { PTS: 22, AST: 5, REB: 6, STL: 1, BLK: 0.5 } for everyone
 * else. The radar was drawn from those whenever the API had not answered, so a chart
 * labelled with a player's name showed a shape that belonged to no one. */

export function useStagingPlayerSkillProfile(
  playerId: string,
  _playerName: string,
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

  const solo: SkillRadarCategory[] = useMemo(
    () => (fromApi && seasonRow ? buildSoloSkillRadar(seasonRow) : []),
    [fromApi, seasonRow],
  )

  const career: SkillRadarCategory[] = useMemo(
    () => (fromApi && careerRow ? buildSoloSkillRadar(careerRow) : []),
    [fromApi, careerRow],
  )

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
