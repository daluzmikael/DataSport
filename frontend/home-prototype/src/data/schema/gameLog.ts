/** Game-log table SHAPE: column sets and tab labels.
 *
 * Split out of the old `playerGameLogMock`, which mixed these column definitions with
 * several hundred lines of invented box scores. The columns are real configuration —
 * which stats a tab shows and how wide each one renders — and every VALUE that fills
 * them now comes from the vault.
 */
export type GameLogTab = "general" | "advanced" | "per36" | "per100"

export interface GameLogColumn {
  id: string
  label: string
  minWidth?: number
}

export interface GameLogRow {
  id: string
  isLive: boolean
  game: string
  values: Record<string, string | number>
}

export interface SeasonGameLog {
  season: string
  label: string
  rows: GameLogRow[]
}

export const CAREER_LOG_VALUE = "career"

const generalCols: GameLogColumn[] = [
  { id: "game", label: "Game", minWidth: 100 },
  { id: "wl", label: "W/L", minWidth: 40 },
  { id: "min", label: "MIN", minWidth: 44 },
  { id: "pts", label: "PTS", minWidth: 44 },
  { id: "fgm", label: "FGM", minWidth: 44 },
  { id: "fga", label: "FGA", minWidth: 44 },
  { id: "fg_pct", label: "FG%", minWidth: 48 },
  { id: "fg3m", label: "3PM", minWidth: 44 },
  { id: "fg3a", label: "3PA", minWidth: 44 },
  { id: "fg3_pct", label: "3P%", minWidth: 48 },
  { id: "ftm", label: "FTM", minWidth: 44 },
  { id: "fta", label: "FTA", minWidth: 44 },
  { id: "ft_pct", label: "FT%", minWidth: 48 },
  { id: "oreb", label: "OREB", minWidth: 48 },
  { id: "dreb", label: "DREB", minWidth: 48 },
  { id: "reb", label: "REB", minWidth: 44 },
  { id: "ast", label: "AST", minWidth: 44 },
  { id: "stl", label: "STL", minWidth: 44 },
  { id: "blk", label: "BLK", minWidth: 44 },
  { id: "tov", label: "TOV", minWidth: 44 },
  { id: "pf", label: "PF", minWidth: 40 },
  { id: "plus_minus", label: "+/-", minWidth: 44 },
]

const advancedCols: GameLogColumn[] = [
  { id: "game", label: "Game", minWidth: 100 },
  { id: "off_rtg", label: "OFF RTG", minWidth: 56 },
  { id: "def_rtg", label: "DEF RTG", minWidth: 56 },
  { id: "net_rtg", label: "NET RTG", minWidth: 56 },
  { id: "ts_pct", label: "TS%", minWidth: 48 },
  { id: "efg_pct", label: "eFG%", minWidth: 52 },
  { id: "usg_pct", label: "USG%", minWidth: 52 },
  { id: "pie", label: "PIE", minWidth: 44 },
  { id: "pace", label: "PACE", minWidth: 48 },
  { id: "ast_pct", label: "AST%", minWidth: 52 },
  { id: "ast_to", label: "AST/TO", minWidth: 52 },
  { id: "ast_ratio", label: "AST RATIO", minWidth: 64 },
  { id: "oreb_pct", label: "OREB%", minWidth: 56 },
  { id: "dreb_pct", label: "DREB%", minWidth: 56 },
  { id: "reb_pct", label: "REB%", minWidth: 52 },
  { id: "tov_pct", label: "TOV%", minWidth: 52 },
]

const per36Cols: GameLogColumn[] = [
  { id: "game", label: "Game", minWidth: 100 },
  { id: "pts", label: "PTS", minWidth: 44 },
  { id: "fgm", label: "FGM", minWidth: 44 },
  { id: "fga", label: "FGA", minWidth: 44 },
  { id: "fg3m", label: "3PM", minWidth: 44 },
  { id: "fg3a", label: "3PA", minWidth: 44 },
  { id: "ftm", label: "FTM", minWidth: 44 },
  { id: "fta", label: "FTA", minWidth: 44 },
  { id: "oreb", label: "OREB", minWidth: 48 },
  { id: "dreb", label: "DREB", minWidth: 48 },
  { id: "reb", label: "REB", minWidth: 44 },
  { id: "ast", label: "AST", minWidth: 44 },
  { id: "stl", label: "STL", minWidth: 44 },
  { id: "blk", label: "BLK", minWidth: 44 },
  { id: "tov", label: "TOV", minWidth: 44 },
  { id: "pf", label: "PF", minWidth: 40 },
]

const per100Cols: GameLogColumn[] = [
  { id: "game", label: "Game", minWidth: 100 },
  { id: "pts", label: "PTS", minWidth: 44 },
  { id: "fgm", label: "FGM", minWidth: 44 },
  { id: "fga", label: "FGA", minWidth: 44 },
  { id: "fg3m", label: "3PM", minWidth: 44 },
  { id: "fg3a", label: "3PA", minWidth: 44 },
  { id: "ftm", label: "FTM", minWidth: 44 },
  { id: "fta", label: "FTA", minWidth: 44 },
  { id: "oreb", label: "OREB", minWidth: 48 },
  { id: "dreb", label: "DREB", minWidth: 48 },
  { id: "reb", label: "REB", minWidth: 44 },
  { id: "ast", label: "AST", minWidth: 44 },
  { id: "stl", label: "STL", minWidth: 44 },
  { id: "blk", label: "BLK", minWidth: 44 },
  { id: "tov", label: "TOV", minWidth: 44 },
  { id: "pf", label: "PF", minWidth: 40 },
]

export const TAB_CONFIG: Record<
  GameLogTab,
  { label: string; columns: GameLogColumn[] }
> = {
  general: { label: "General", columns: generalCols },
  advanced: { label: "Advanced", columns: advancedCols },
  per36: { label: "Per 36 min", columns: per36Cols },
  per100: { label: "Per 100 poss", columns: per100Cols },
}

/** Overlay game id from a game-log row id.
 *
 * Rows built from the vault carry the real 10-digit NBA game id (`gl-0022300123`),
 * so this is a pure format change. The old version had a hard-coded fall-through to
 * `"game-celtics"` — a fixture that no longer exists — which meant any row it could
 * not parse opened a made-up game instead of failing visibly.
 */
export function gameLogRowToGameId(rowId: string): string | null {
  const match = /^gl-(\d{1,10})$/.exec(rowId)
  if (!match) return null
  return `game-${match[1].padStart(10, "0")}`
}
