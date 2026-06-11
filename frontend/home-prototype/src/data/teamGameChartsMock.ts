import { getTeamBoxScore } from "./teamBoxScoreMock"
import { getTeamGameStatsByTab } from "./teamGameStatsMock"

export interface ScatterPoint {
  playerName: string
  teamAbbr: string
  paintPts: number
  fta: number
}

const TEAM_COLORS: Record<string, string> = {
  MIA: "#f97316",
  BOS: "#22c55e",
  LAL: "#eab308",
  DEN: "#3b82f6",
  NYK: "#f97316",
  CLE: "#a855f7",
}

export function teamChartColor(abbr: string): string {
  return TEAM_COLORS[abbr] ?? "#94a3b8"
}

/** Tonight's box scores → paint points (x) vs FTA (y) per player */
export function buildPaintFtScatter(awayAbbr: string, homeAbbr: string): ScatterPoint[] {
  const points: ScatterPoint[] = []

  for (const abbr of [awayAbbr, homeAbbr]) {
    const box = getTeamBoxScore(abbr)
    const players = box?.byTab.general.players ?? []
    for (const row of players) {
      if (row.isDnp) continue
      const pts = Number(row.values.pts)
      const fgm = Number(row.values.fgm)
      const fg3m = Number(row.values.fg3m)
      const oreb = Number(row.values.oreb)
      const fta = Number(row.values.fta)
      if (!Number.isFinite(pts) || !Number.isFinite(fta)) continue

      const twos = Math.max(0, fgm - fg3m)
      const paintPts = Math.round(twos * 1.85 + oreb * 1.5 + Math.max(0, pts - twos * 2 - fg3m * 3) * 0.35)

      points.push({
        playerName: row.player,
        teamAbbr: abbr,
        paintPts: Math.min(28, Math.max(0, paintPts)),
        fta: Math.max(0, fta),
      })
    }
  }

  return points
}

export interface RadarCategory {
  category: string
  [teamAbbr: string]: string | number
}

const PROFILE_BENCHMARKS: Record<string, number> = {
  PTS: 120,
  AST: 32,
  REB: 52,
  STL: 12,
  BLK: 8,
}

function normStat(value: number, bench: number): number {
  return Math.min(100, Math.round((value / bench) * 100))
}

/** Team skill profile from live game totals (same axes as dashboard radar) */
export function buildTeamCompareRadar(
  awayAbbr: string,
  homeAbbr: string,
): RadarCategory[] {
  const away = getTeamGameStatsByTab(awayAbbr, "general")
  const home = getTeamGameStatsByTab(homeAbbr, "general")

  const keys = ["PTS", "AST", "REB", "STL", "BLK"] as const
  const statKey: Record<(typeof keys)[number], string> = {
    PTS: "pts",
    AST: "ast",
    REB: "reb",
    STL: "stl",
    BLK: "blk",
  }

  return keys.map((cat) => {
    const k = statKey[cat]
    const aVal = Number(away[k]) || 0
    const hVal = Number(home[k]) || 0
    return {
      category: cat,
      [awayAbbr]: normStat(aVal, PROFILE_BENCHMARKS[cat]),
      [homeAbbr]: normStat(hVal, PROFILE_BENCHMARKS[cat]),
    }
  })
}
