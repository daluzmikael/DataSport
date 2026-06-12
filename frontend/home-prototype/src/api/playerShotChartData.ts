import type { MockShot } from "../data/mockShots"

/** NBA court zones mapped to shot-chart coordinate ranges (1/10 ft, basket at origin). */
const ZONE_BOUNDS: Record<string, { x: [number, number]; y: [number, number] }> = {
  restricted_area: { x: [-42, 42], y: [8, 72] },
  in_the_paint_nonra: { x: [-76, 76], y: [72, 138] },
  midrange: { x: [-210, 210], y: [120, 270] },
  left_corner_3: { x: [-228, -198], y: [18, 88] },
  right_corner_3: { x: [198, 228], y: [18, 88] },
  above_the_break_3: { x: [-210, 210], y: [265, 405] },
  backcourt: { x: [-120, 120], y: [385, 415] },
}

export const SHOT_ZONE_KEYS = [
  "restricted_area",
  "in_the_paint_nonra",
  "midrange",
  "left_corner_3",
  "right_corner_3",
  "above_the_break_3",
  "corner_3",
  "backcourt",
] as const

const ZONE_ORDER = [
  "restricted_area",
  "in_the_paint_nonra",
  "midrange",
  "left_corner_3",
  "right_corner_3",
  "above_the_break_3",
  "backcourt",
] as const

/** Sum per-zone makes/attempts across seasons for career shot charts. */
export function mergeShotZoneRows(
  rows: Record<string, unknown>[],
): Record<string, unknown> {
  const totals: Record<string, number> = {}
  for (const row of rows) {
    for (const key of SHOT_ZONE_KEYS) {
      for (const suffix of ["_fgm", "_fga"] as const) {
        const col = `${key}${suffix}`
        const val = Number(row[col] ?? 0)
        if (!Number.isNaN(val) && val > 0) {
          totals[col] = (totals[col] ?? 0) + val
        }
      }
    }
  }
  const merged: Record<string, unknown> = { ...totals }
  for (const key of SHOT_ZONE_KEYS) {
    const fgm = totals[`${key}_fgm`] ?? 0
    const fga = totals[`${key}_fga`] ?? 0
    if (fga > 0) merged[`${key}_fg_pct`] = fgm / fga
  }
  return merged
}

function hashSeed(seed: string): number {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0
  return Math.abs(h)
}

function mulberry32(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function normalizeFgPct(raw: unknown): number {
  const n = typeof raw === "number" ? raw : parseFloat(String(raw ?? ""))
  if (Number.isNaN(n)) return 0.45
  if (n > 1 && n <= 100) return n / 100
  return Math.min(1, Math.max(0, n))
}

/**
 * Build hex-chart shot points from `player_shot_zones` totals row.
 * Uses deterministic placement within each zone so charts are stable per player/season.
 */
export function shotsFromShotZoneRow(
  row: Record<string, unknown>,
  seed: string,
): MockShot[] {
  const rand = mulberry32(hashSeed(seed))
  const shots: MockShot[] = []
  const hasCornerSplit =
    Number(row.left_corner_3_fga ?? 0) > 0 || Number(row.right_corner_3_fga ?? 0) > 0

  for (const zone of ZONE_ORDER) {
    if (zone === "backcourt" && Number(row.backcourt_fga ?? 0) <= 0) continue
    if (!hasCornerSplit && zone === "left_corner_3") {
      const combined = Number(row.corner_3_fga ?? 0)
      if (combined > 0) {
        const bounds = ZONE_BOUNDS.left_corner_3
        const fgPct = normalizeFgPct(row.corner_3_fg_pct)
        const count = Math.max(1, Math.round(combined / 2))
        for (let i = 0; i < count; i++) {
          if (!bounds) break
          const loc_x = bounds.x[0] + rand() * (bounds.x[1] - bounds.x[0])
          const loc_y = bounds.y[0] + rand() * (bounds.y[1] - bounds.y[0])
          shots.push({
            loc_x,
            loc_y,
            shot_made_flag: (rand() < fgPct ? 1 : 0) as 0 | 1,
          })
        }
        const rightBounds = ZONE_BOUNDS.right_corner_3
        for (let i = 0; i < count; i++) {
          if (!rightBounds) break
          const loc_x = rightBounds.x[0] + rand() * (rightBounds.x[1] - rightBounds.x[0])
          const loc_y = rightBounds.y[0] + rand() * (rightBounds.y[1] - rightBounds.y[0])
          shots.push({
            loc_x,
            loc_y,
            shot_made_flag: (rand() < fgPct ? 1 : 0) as 0 | 1,
          })
        }
      }
      continue
    }
    if (!hasCornerSplit && zone === "right_corner_3") continue

    const fga = Number(row[`${zone}_fga`] ?? 0)
    const fgPct = normalizeFgPct(row[`${zone}_fg_pct`])
    const bounds = ZONE_BOUNDS[zone]
    if (!bounds || fga <= 0) continue

    const count = Math.max(1, Math.round(fga))
    for (let i = 0; i < count; i++) {
      const loc_x = bounds.x[0] + rand() * (bounds.x[1] - bounds.x[0])
      const loc_y = bounds.y[0] + rand() * (bounds.y[1] - bounds.y[0])
      if (loc_y > 418 || loc_y < 4) continue
      shots.push({
        loc_x,
        loc_y,
        shot_made_flag: (rand() < fgPct ? 1 : 0) as 0 | 1,
      })
    }
  }

  return shots
}
