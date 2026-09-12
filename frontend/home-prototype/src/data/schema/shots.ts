/** A single shot attempt, in NBA court coordinates.
 *
 * Replaces `mockShots.ts`. Two things used to fill shot charts, and neither was real:
 *
 *  - `generateMockShots()` — a seeded random spray keyed off the player id. It looked
 *    convincing and changed when you switched players, which made it feel like data.
 *  - `shotsFromShotZoneRow()` — real per-zone totals, then random placement of the
 *    individual dots inside each zone. The zone percentages were true; every dot's
 *    position was invented.
 *
 * `player_shot_chart` now carries all 6.3M real attempts back to 1996-97, so the field
 * names here are the vault's own: `LOC_X` / `LOC_Y` in tenths of a foot, origin at the
 * centre of the basket, x increasing to the shooter's right, y increasing away from the
 * baseline. The half court runs roughly x ∈ [-250, 250], y ∈ [-50, 420].
 */
export interface ShotPoint {
  loc_x: number
  loc_y: number
  shot_made_flag: 0 | 1
  /** "Jump Shot", "Driving Layup Shot" — the real ACTION_TYPE. */
  action_type?: string
  /** "2PT Field Goal" | "3PT Field Goal" */
  shot_type?: string
  zone?: string
  distance_ft?: number
  period?: number
  game_id?: string
  game_date?: string
}

/** Map one `/api/staging/players/{id}/shot-chart` row to a chart point. */
export function shotFromVaultRow(row: Record<string, unknown>): ShotPoint | null {
  const x = Number(row.LOC_X)
  const y = Number(row.LOC_Y)
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null
  return {
    loc_x: x,
    loc_y: y,
    shot_made_flag: Number(row.SHOT_MADE_FLAG) === 1 ? 1 : 0,
    action_type: row.ACTION_TYPE ? String(row.ACTION_TYPE) : undefined,
    shot_type: row.SHOT_TYPE ? String(row.SHOT_TYPE) : undefined,
    zone: row.SHOT_ZONE_BASIC ? String(row.SHOT_ZONE_BASIC) : undefined,
    distance_ft: Number.isFinite(Number(row.SHOT_DISTANCE))
      ? Number(row.SHOT_DISTANCE)
      : undefined,
    period: Number.isFinite(Number(row.PERIOD)) ? Number(row.PERIOD) : undefined,
    game_id: row.GAME_ID ? String(row.GAME_ID) : undefined,
    game_date: row.GAME_DATE ? String(row.GAME_DATE) : undefined,
  }
}

export function shotChartTotals(shots: ShotPoint[]): {
  attempts: number
  made: number
  pct: number | null
} {
  const attempts = shots.length
  const made = shots.filter((s) => s.shot_made_flag === 1).length
  return { attempts, made, pct: attempts ? made / attempts : null }
}
