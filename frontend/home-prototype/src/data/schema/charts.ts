/** Chart shapes and palette for the team/game chart section.
 *
 * The builders that used to live here (`buildPaintFtScatter`, `buildTeamCompareRadar`)
 * read from invented box scores. They now take real rows as arguments, so the same
 * chart shapes are filled from `/api/staging/games/{id}/box-score`.
 */
export interface ScatterPoint {
  playerName: string
  teamAbbr: string
  paintPts: number
  fta: number
}

export interface RadarCategory {
  category: string
  [teamAbbr: string]: string | number
}

/** Fallback palette, keyed by tricode. Deliberately not exhaustive — any team without
 *  an entry gets the neutral slate, which is better than inventing a brand colour. */
const TEAM_COLORS: Record<string, string> = {
  ATL: "#e03a3e", BOS: "#22c55e", BKN: "#64748b", CHA: "#00788c", CHI: "#ce1141",
  CLE: "#860038", DAL: "#0053bc", DEN: "#0e2240", DET: "#c8102e", GSW: "#1d428a",
  HOU: "#ce1141", IND: "#fdbb30", LAC: "#c8102e", LAL: "#eab308", MEM: "#5d76a9",
  MIA: "#98002e", MIL: "#00471b", MIN: "#0c2340", NOP: "#0c2340", NYK: "#f58426",
  OKC: "#007ac1", ORL: "#0077c0", PHI: "#006bb6", PHX: "#e56020", POR: "#e03a3e",
  SAC: "#5a2d81", SAS: "#8a8d8f", TOR: "#ce1141", UTA: "#002b5c", WAS: "#002b5c",
}

export function teamChartColor(abbr: string): string {
  return TEAM_COLORS[(abbr || "").toUpperCase()] ?? "#94a3b8"
}

/** Ceilings used to put the five radar axes on a shared 0-100 scale. Team-game totals,
 *  so they are the same numbers the old module used — only the inputs changed. */
export const RADAR_BENCHMARKS: Record<string, number> = {
  PTS: 120,
  AST: 32,
  REB: 52,
  STL: 12,
  BLK: 8,
}

export function normalizeToBenchmark(value: number, benchmark: number): number {
  if (!benchmark) return 0
  return Math.min(100, Math.round((value / benchmark) * 100))
}

/** Paint points vs free-throw attempts, one dot per player, from real box-score rows. */
export function buildPaintFtScatter(
  rows: Array<Record<string, unknown>>,
): ScatterPoint[] {
  const num = (v: unknown): number => {
    const n = Number(v)
    return Number.isFinite(n) ? n : 0
  }
  return rows
    .map((row) => ({
      playerName: String(row.PLAYER_NAME ?? row.player_name ?? "—"),
      teamAbbr: String(row.TEAM_ABBREVIATION ?? row.team_abbreviation ?? ""),
      // Player-level paint points are not in the box score; attempts inside the arc
      // are the closest real proxy and are labelled as such in the chart axis.
      paintPts: num(row.FGM) * 2 - num(row.FG3M) * 2,
      fta: num(row.FTA),
    }))
    .filter((p) => p.fta > 0 || p.paintPts > 0)
}

/** Five-axis team comparison from two real team-total rows. */
export function buildTeamCompareRadar(
  away: { abbr: string; totals: Record<string, unknown> },
  home: { abbr: string; totals: Record<string, unknown> },
): RadarCategory[] {
  const keys = ["PTS", "AST", "REB", "STL", "BLK"] as const
  return keys.map((key) => {
    const bench = RADAR_BENCHMARKS[key] ?? 100
    const row: RadarCategory = { category: key }
    for (const side of [away, home]) {
      const raw = Number(side.totals[key] ?? side.totals[key.toLowerCase()] ?? 0)
      row[side.abbr] = normalizeToBenchmark(Number.isFinite(raw) ? raw : 0, bench)
    }
    return row
  })
}
