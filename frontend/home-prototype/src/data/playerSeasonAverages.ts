import { getSeasonAverages, type GameLogTab } from "./playerGameLogMock"

export interface SeasonBubbleSet {
  pts: string
  fg: string
  fgPct: string
  fg3: string
  fg3Pct: string
  ft: string
  ftPct: string
  reb: string
  oreb: string
  dreb: string
  ast: string
  tov: string
  pf: string
  stl: string
  blk: string
  plusMinus: string
  tsPct: string
  efgPct: string
  usgPct: string
  astPct: string
  astToTov: string
  orebPct: string
  drebPct: string
  pie: string
  per36Pts: string
  per36Reb: string
  per36Ast: string
  per36Stl: string
  per36Blk: string
  per36Tov: string
  per100Pts: string
  per100Reb: string
  per100Ast: string
  per100Stl: string
  per100Blk: string
  per100Tov: string
  contestedShots: string
  contestedShots2pt: string
  contestedShots3pt: string
  deflections: string
  screenAssists: string
  screenAssistPoints: string
  boxOuts: string
  offensiveBoxOuts: string
  defensiveBoxOuts: string
  looseBallsRecoveredTotal: string
  looseBallsRecoveredOffensive: string
  looseBallsRecoveredDefensive: string
  chargesDrawn: string
  boxOutPlayerTeamRebounds: string
  boxOutPlayerRebounds: string
  minutes: string
}

function fmt(n: string | number, decimals = 1): string {
  const v = typeof n === "number" ? n : parseFloat(String(n))
  if (Number.isNaN(v)) return String(n)
  return v.toFixed(decimals)
}

export function getPlayerSeasonBubbles(season = "2024-25"): SeasonBubbleSet {
  const g = getSeasonAverages(season, "general")
  const a = getSeasonAverages(season, "advanced")
  const p36 = getSeasonAverages(season, "per36")
  const p100 = getSeasonAverages(season, "per100")

  return {
    pts: fmt(g.pts),
    fg: `${fmt(g.fgm, 1)}/${fmt(g.fga, 1)}`,
    fgPct: String(g.fg_pct),
    fg3: `${fmt(g.fg3m, 1)}/${fmt(g.fg3a, 1)}`,
    fg3Pct: String(g.fg3_pct),
    ft: `${fmt(g.ftm, 1)}/${fmt(g.fta, 1)}`,
    ftPct: String(g.ft_pct),
    reb: fmt(g.reb),
    oreb: fmt(g.oreb, 1),
    dreb: fmt(g.dreb, 1),
    ast: fmt(g.ast),
    tov: fmt(g.tov, 1),
    pf: fmt(g.pf, 1),
    stl: fmt(g.stl, 1),
    blk: fmt(g.blk, 1),
    plusMinus: String(g.plus_minus),
    tsPct: String(a.ts_pct),
    efgPct: String(a.efg_pct),
    usgPct: String(a.usg_pct),
    astPct: String(a.ast_pct),
    astToTov: String(a.ast_to),
    orebPct: String(a.oreb_pct),
    drebPct: String(a.dreb_pct),
    pie: String(a.pie),
    per36Pts: fmt(p36.pts),
    per36Reb: fmt(p36.reb),
    per36Ast: fmt(p36.ast),
    per36Stl: fmt(p36.stl, 1),
    per36Blk: fmt(p36.blk, 1),
    per36Tov: fmt(p36.tov, 1),
    per100Pts: fmt(p100.pts),
    per100Reb: fmt(p100.reb),
    per100Ast: fmt(p100.ast),
    per100Stl: fmt(p100.stl, 1),
    per100Blk: fmt(p100.blk, 1),
    per100Tov: fmt(p100.tov, 1),
    contestedShots: "7.8",
    contestedShots2pt: "5.1",
    contestedShots3pt: "2.7",
    deflections: "2.9",
    screenAssists: "2.4",
    screenAssistPoints: "5.6",
    boxOuts: "3.2",
    offensiveBoxOuts: "1.1",
    defensiveBoxOuts: "2.1",
    looseBallsRecoveredTotal: "1.4",
    looseBallsRecoveredOffensive: "0.5",
    looseBallsRecoveredDefensive: "0.9",
    chargesDrawn: "0.3",
    boxOutPlayerTeamRebounds: "1.8",
    boxOutPlayerRebounds: "1.2",
    minutes: fmt(g.min),
  }
}

export function seasonBubbleTabLabels(): Record<GameLogTab, string> {
  return {
    general: "Season averages",
    advanced: "Season averages",
    per36: "Per 36 min",
    per100: "Per 100 poss",
  }
}
