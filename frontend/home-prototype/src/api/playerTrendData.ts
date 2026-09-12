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

/* `mockTrendPoints()` generated a career arc from a hash of the player id: a base
 * value, a fixed slope, and seeded jitter across eight seasons. It produced a
 * plausible-looking improvement curve for anyone, including players who never played
 * those seasons. Trends come from `/api/staging/players/{id}/season-trends`. */

