/** The chart contract, mirrored from backend/Visualizer/chart_spec.py.
 *
 * Selected server-side from the router plan and the frame it produced, so the picture
 * and the sentence beside it are built from the same rows and cannot disagree.
 */

export type ChartKind =
  | "leaderboard"
  | "trend"
  | "compare_trend"
  | "radar"
  | "compare_radar"
  | "scatter"
  | "shot_chart"
  | "table"

/** How a value should be read, not how it is stored — the vault keeps percentages as
 *  fractions (FG_PCT 0.523), so the renderer has to be told it is looking at one. */
export type ChartUnit = "pct" | "per_game" | "count" | "rating"

export interface FieldSpec {
  column: string
  label: string
  unit?: ChartUnit | null
  precision?: number
}

export interface ChartSpec {
  kind: ChartKind
  title: string
  subtitle?: string | null
  x?: FieldSpec | null
  y?: FieldSpec[]
  series?: string | null
  /** shot_chart only: which view to open with. The renderer offers the rest. */
  mode?: string | null
  /** shot_chart only: individual attempts, present when the scope is small enough to
   *  draw them. Hex bins need volume to mean anything, so a single game is shown as
   *  makes and misses instead. Empty for a large-scope (binned) chart. */
  points?: Array<Record<string, unknown>>
  rows: Array<Record<string, unknown>>
  citation?: string
  /** Applied floors, name corrections, row caps. Rendered in the footer: a reader who
   *  only looks at the picture must not be misled by it. */
  notes?: string[]
}

/* -------------------------------------------------------------------------- */
/* Row shapes, one per kind — these mirror shaping.py exactly.                 */
/* -------------------------------------------------------------------------- */

export interface LeaderboardRow {
  rank: number
  name: string
  teamAbbr: string
  value: number
}

export interface TrendRow {
  season: string
  value: number
}

/** `{ season, "<entity>": number, ... }` */
export type CompareTrendRow = { season: string } & Record<string, string | number>

export interface RadarRow {
  category: string
  normalized: number
  raw: number
}

/** `{ category, "<entity>": number, ... }` */
export type CompareRadarRow = { category: string } & Record<string, string | number>

export interface ScatterRow {
  name: string
  teamAbbr: string
  x: number
  y: number
}

/** One hex cell, aggregated server-side. `x`/`y` are already in the court SVG space the
 *  renderer draws in, so no transform is needed here. */
export interface ShotChartRow {
  x: number
  y: number
  made: number
  total: number
}

/** One attempt, in the vault's own court coordinates. Matches the TS ShotPoint. */
export interface ShotPointRow {
  loc_x: number
  loc_y: number
  shot_made_flag: 0 | 1
}

/* -------------------------------------------------------------------------- */
/* Shared presentation                                                         */
/* -------------------------------------------------------------------------- */

/** House palette. First entry matches the accent green every existing chart uses. */
export const SERIES_COLORS = [
  "#3ecf8e",
  "#f5c542",
  "#5b9dff",
  "#e0685a",
  "#b98bff",
] as const

export function seriesColor(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length] ?? SERIES_COLORS[0]
}

/** Format a raw vault value for display.
 *
 * Percentages are stored as fractions, so 0.523 has to render as 52.3% — but a few
 * columns (USG_PCT on some tables) already arrive scaled, hence the <= 1 guard rather
 * than an unconditional multiply.
 */
export function formatValue(
  value: number | null | undefined,
  field?: FieldSpec | null,
): string {
  if (value == null || !Number.isFinite(value)) return "—"
  const precision = field?.precision ?? 1
  if (field?.unit === "pct") {
    const pct = Math.abs(value) <= 1 ? value * 100 : value
    return `${pct.toFixed(precision)}%`
  }
  return value.toFixed(precision)
}

/** Season labels are "2023-24" in the vault. Render them compactly without assuming
 *  the older 9-character "2023-2024" form. */
export function shortSeason(season: string): string {
  const match = /^(\d{4})-(\d{2,4})$/.exec(season?.trim() ?? "")
  if (!match) return season ?? ""
  const start = match[1]!.slice(2)
  const end = match[2]!.slice(-2)
  return `${start}–${end}`
}

/** Series keys in a pivoted row — every key except the axis one. */
export function seriesKeys(
  rows: Array<Record<string, unknown>>,
  axisKey: string,
): string[] {
  const keys = new Set<string>()
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (key !== axisKey) keys.add(key)
    }
  }
  return [...keys]
}
