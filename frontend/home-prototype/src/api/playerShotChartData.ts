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

/* `shotsFromShotZoneRow()` used to live here. It took real per-zone FGA and FG% and
 * scattered individual dots inside each zone with a seeded RNG, so the zone
 * percentages were true and every dot position was invented. `player_shot_chart` has
 * the real coordinates now, so the synthesis is gone rather than kept as a fallback —
 * a fallback that looks identical to real data is the thing worth removing. */

