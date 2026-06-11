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
    per36Pts: "—",
    per36Reb: "—",
    per36Ast: "—",
    per36Stl: "—",
    per36Blk: "—",
    per36Tov: "—",
    per100Pts: "—",
    per100Reb: "—",
    per100Ast: "—",
    per100Stl: "—",
    per100Blk: "—",
    per100Tov: "—",
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
