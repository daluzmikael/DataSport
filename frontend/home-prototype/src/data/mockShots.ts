export interface MockShot {
  loc_x: number
  loc_y: number
  shot_made_flag: 0 | 1
}

/** Seeded PRNG for stable charts per player. */
function mulberry32(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function hashId(id: string): number {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return Math.abs(h)
}

/** ~90 shots with realistic half-court spread (NBA shot chart coords). */
export function generateMockShots(playerId: string, count = 92): MockShot[] {
  const rand = mulberry32(hashId(playerId))
  const shots: MockShot[] = []

  const zones: { x: [number, number]; y: [number, number]; makeRate: number; weight: number }[] =
    [
      { x: [-40, 40], y: [0, 80], makeRate: 0.62, weight: 0.22 },
      { x: [-120, 120], y: [80, 180], makeRate: 0.48, weight: 0.18 },
      { x: [-180, -60], y: [180, 300], makeRate: 0.38, weight: 0.14 },
      { x: [60, 180], y: [180, 300], makeRate: 0.41, weight: 0.14 },
      { x: [-220, -140], y: [60, 260], makeRate: 0.36, weight: 0.12 },
      { x: [140, 220], y: [60, 260], makeRate: 0.39, weight: 0.12 },
      { x: [-80, 80], y: [260, 380], makeRate: 0.34, weight: 0.08 },
    ]

  while (shots.length < count) {
    const roll = rand()
    let acc = 0
    let zone = zones[0]
    for (const z of zones) {
      acc += z.weight
      if (roll <= acc) {
        zone = z
        break
      }
    }
    const loc_x = zone.x[0] + rand() * (zone.x[1] - zone.x[0])
    const loc_y = zone.y[0] + rand() * (zone.y[1] - zone.y[0])
    if (loc_y > 418 || loc_y < 4) continue

    const made = rand() < zone.makeRate ? 1 : 0
    shots.push({ loc_x, loc_y, shot_made_flag: made as 0 | 1 })
  }

  return shots
}

/** Team tonight shot chart — count aligned with live game FGA where possible */
export function generateTeamGameShots(teamAbbr: string): MockShot[] {
  const fgaByTeam: Record<string, number> = {
    MIA: 71,
    BOS: 68,
    LAL: 58,
    DEN: 54,
    NYK: 48,
    CLE: 46,
  }
  const count = fgaByTeam[teamAbbr] ?? 70
  return generateMockShots(`team-game-${teamAbbr}`, count)
}

/** One player's tonight shots — seeded by box score row id, count ≈ FGA */
export function generateBoxScorePlayerShots(boxRowId: string, fga: number): MockShot[] {
  if (fga <= 0) return []
  const count = Math.max(6, Math.min(fga, 40))
  return generateMockShots(`box-shot-${boxRowId}`, count)
}
