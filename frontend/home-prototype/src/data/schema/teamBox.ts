/** Box-score table SHAPE, shared by the game box score and the team roster views.
 *
 * The old `teamBoxScoreMock` also carried ~900 lines of invented player lines,
 * including a `benchRow()` helper that derived fake makes and attempts from a points
 * figure — 9 makes on 18 attempts because the player "scored 24". Those rows are gone;
 * what remains here is the column configuration they were poured into.
 */
import { TAB_CONFIG, type GameLogColumn, type GameLogTab } from "./gameLog"

export type { GameLogTab }

export interface TeamBoxRow {
  id: string
  player: string
  isSeasonAvg?: boolean
  isDnp?: boolean
  values: Record<string, string | number>
}

export interface TeamBoxScoreData {
  teamAbbr: string
  seasonLabel: string
  byTab: Record<GameLogTab, { seasonAvg: TeamBoxRow; players: TeamBoxRow[] }>
}

/** The game-log columns with the leading `game` column swapped for `player`. */
export function teamBoxColumns(tab: GameLogTab): GameLogColumn[] {
  return TAB_CONFIG[tab].columns.map((c) =>
    c.id === "game" ? { id: "player", label: "Player", minWidth: 108 } : c,
  )
}

/** A player entry on a team shot chart, sized by attempts. */
export interface TeamShotChartPlayer {
  id: string
  name: string
  fga: number
}

const DASH = "—"

/** The row shown for a player who did not play — every stat blank, never zero. */
export function dnpRow(id: string, player: string): TeamBoxRow {
  const values: Record<string, string | number> = { min: "DNP" }
  for (const col of TAB_CONFIG.general.columns) {
    if (col.id !== "game" && col.id !== "min") values[col.id] = DASH
  }
  return { id, player, isDnp: true, values }
}
