export interface TrendPoint {
  season: string
  value: number
}

export type TrendStatKey = "PTS" | "AST" | "REB" | "STL" | "BLK"

export const TREND_STAT_LABELS: Record<TrendStatKey, string> = {
  PTS: "Points per game",
  AST: "Assists per game",
  REB: "Rebounds per game",
  STL: "Steals per game",
  BLK: "Blocks per game",
}

function parseNum(raw: unknown): number {
  const n = typeof raw === "number" ? raw : parseFloat(String(raw ?? ""))
  return Number.isNaN(n) ? 0 : n
}

export function trendPointsFromRows(
  rows: Record<string, unknown>[] | null | undefined,
  statKey: TrendStatKey,
): TrendPoint[] {
  if (!rows?.length) return []
  const bySeason = new Map<string, { season: string; value: number; gp: number }>()
  for (const row of rows) {
    const season = String(row.season ?? row.SEASON ?? "")
    if (!season) continue
    const gp = parseNum(row.GP ?? row.gp)
    const value = parseNum(row[statKey] ?? row[statKey.toLowerCase()])
    const existing = bySeason.get(season)
    if (!existing || gp >= existing.gp) {
      bySeason.set(season, { season, value, gp })
    }
  }
  return [...bySeason.values()].map(({ season, value }) => ({ season, value }))
    .map(({ season, value }) => ({ season, value }))
    .sort((a, b) => {
      const ya = parseInt(a.season.split("-")[0] ?? "0", 10)
      const yb = parseInt(b.season.split("-")[0] ?? "0", 10)
      return ya - yb
    })
}

/** Seeded mock career arc for demo players without vault. */
export function mockTrendPoints(playerId: string, statKey: TrendStatKey): TrendPoint[] {
  const seasons = [
    "2017-18",
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
  ]
  const bases: Record<TrendStatKey, number> = {
    PTS: 13,
    AST: 2.5,
    REB: 5,
    STL: 0.8,
    BLK: 0.3,
  }
  const slopes: Record<TrendStatKey, number> = {
    PTS: 1.8,
    AST: 0.45,
    REB: 0.5,
    STL: 0.04,
    BLK: 0.02,
  }
  let h = 0
  for (const c of playerId) h = (h * 31 + c.charCodeAt(0)) | 0
  const jitter = (i: number) => ((Math.abs(h + i * 17) % 10) - 5) * 0.15
  return seasons.map((season, i) => ({
    season,
    value: Math.round((bases[statKey] + slopes[statKey] * i + jitter(i)) * 10) / 10,
  }))
}
