export const DEFAULT_SCATTER_SEASON = "2023-24"

export interface ScatterPointRow {
  player_name: string
  x_value: number
  y_value: number
  /** Recharts reads rows generically, so the shape has to stay index-accessible. */
  [key: string]: unknown
}

function parseNum(raw: unknown): number {
  const n = typeof raw === "number" ? raw : parseFloat(String(raw ?? ""))
  return Number.isNaN(n) ? 0 : n
}

export function scatterRowsFromApi(
  rows: Record<string, unknown>[] | null | undefined,
): ScatterPointRow[] {
  if (!rows?.length) return []
  return rows
    .map((row) => ({
      player_name: String(row.player_name ?? row.PLAYER_NAME ?? row.full_name ?? ""),
      x_value: parseNum(row.x_value),
      y_value: parseNum(row.y_value),
    }))
    .filter((row) => row.player_name && Number.isFinite(row.x_value) && Number.isFinite(row.y_value))
}

/* `mockScatterPtsMin()` and `mockScatterAstTov()` used to live here: two 12-point
 * fixture clouds of real player names against made-up coordinates, returned whenever
 * `/api/staging/league/scatter` had not answered. A scatter plot of invented dots
 * labelled with real players is indistinguishable from the real thing on screen, so
 * the charts now render empty instead. */

