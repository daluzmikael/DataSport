/** The stat set the player season-average bubbles render.
 *
 * Every field is a preformatted string because the bubbles display them verbatim.
 * The values are mapped from `player_season_stats` in `api/mappers.ts`; the old
 * module in this slot filled them from a hand-written 2024-25 line.
 */
import type { GameLogTab } from "./gameLog"

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


export function seasonBubbleTabLabels(): Record<GameLogTab, string> {
  return {
    general: "Season averages",
    advanced: "Season averages",
    per36: "Per 36 min",
    per100: "Per 100 poss",
  }
}
