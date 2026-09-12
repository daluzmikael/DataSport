/** The stat cells shown in the team totals strip of a game view.
 *
 * Columns only. The `MIA_GAME_STATS` / `BOS_GAME_STATS` constants that used to sit
 * beside them were one hard-coded imaginary game, reused for every matchup.
 */
import { TAB_CONFIG, type GameLogTab } from "./gameLog"

export interface TeamStatCell {
  id: string
  label: string
  value: string | number
  minWidth?: number
}

export function teamGameStatCells(tab: GameLogTab): Omit<TeamStatCell, "value">[] {
  return TAB_CONFIG[tab].columns
    .filter((c) => c.id !== "game" && c.id !== "wl" && c.id !== "player")
    .map((c) => ({ id: c.id, label: c.label, minWidth: c.minWidth }))
}
