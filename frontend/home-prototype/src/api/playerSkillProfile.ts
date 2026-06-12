export const SKILL_CATEGORIES = ["PTS", "AST", "REB", "STL", "BLK"] as const

/** Elite per-game benchmarks — normalized to 100 on radar (matches dashboard). */
export const SKILL_STAT_BENCHMARKS: Record<(typeof SKILL_CATEGORIES)[number], number> = {
  PTS: 35,
  AST: 11,
  REB: 14,
  STL: 2.5,
  BLK: 2.5,
}

export const CAREER_COMPARE_LABEL = "Career avg"

export interface SkillRadarCategory {
  category: string
  normalized: number
  raw: number
}

export interface SkillCompareRow {
  category: string
  [seriesLabel: string]: string | number
}

function parseStat(row: Record<string, unknown>, key: string): number {
  const val = row[key] ?? row[key.toLowerCase()]
  const n = typeof val === "number" ? val : parseFloat(String(val ?? ""))
  return Number.isNaN(n) ? 0 : n
}

export function normalizeSkillValue(category: string, raw: number): number {
  const max = SKILL_STAT_BENCHMARKS[category as (typeof SKILL_CATEGORIES)[number]] ?? 30
  if (!max) return 0
  return Math.min(100, Math.round((raw / max) * 100))
}

export function buildSoloSkillRadar(
  row: Record<string, unknown>,
): SkillRadarCategory[] {
  return SKILL_CATEGORIES.map((cat) => {
    const raw = parseStat(row, cat)
    return { category: cat, raw, normalized: normalizeSkillValue(cat, raw) }
  })
}

export function buildSeasonVsCareerCompare(
  season: SkillRadarCategory[],
  career: SkillRadarCategory[],
  seasonLabel: string,
  careerLabel: string = CAREER_COMPARE_LABEL,
): SkillCompareRow[] {
  return season.map((point, i) => {
    const careerPoint = career[i]
    return {
      category: point.category,
      [seasonLabel]: point.normalized,
      [careerLabel]: careerPoint?.normalized ?? 0,
      [`${seasonLabel}_raw`]: point.raw,
      [`${careerLabel}_raw`]: careerPoint?.raw ?? 0,
    }
  })
}

export function careerCompareFooterText(career: SkillRadarCategory[]): string {
  const parts = career.map((c) => `${c.category} ${c.raw}`)
  return `Career averages — ${parts.join(" · ")} (per game)`
}
