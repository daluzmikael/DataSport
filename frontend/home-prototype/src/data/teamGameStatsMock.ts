import { TAB_CONFIG, type GameLogTab } from "./playerGameLogMock"
import { OTHER_LIVE_GAME_STATS } from "./otherLiveGamesMock"

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

export const MIA_GAME_STATS: Record<GameLogTab, Record<string, string | number>> = {
  general: {
    pts: 82,
    min: 240,
    fgm: 30,
    fga: 71,
    fg_pct: ".423",
    fg3m: 11,
    fg3a: 32,
    fg3_pct: ".344",
    ftm: 11,
    fta: 16,
    ft_pct: ".688",
    oreb: 9,
    dreb: 27,
    reb: 36,
    ast: 19,
    stl: 6,
    blk: 3,
    tov: 12,
    pf: 14,
    plus_minus: "-5",
  },
  advanced: {
    off_rtg: 108.4,
    def_rtg: 112.8,
    net_rtg: "-4.4",
    ts_pct: ".518",
    efg_pct: ".500",
    usg_pct: "—",
    pie: "—",
    pace: 97.8,
    ast_pct: "52.4",
    ast_to: "1.58",
    ast_ratio: 16.2,
    oreb_pct: 22.1,
    dreb_pct: 68.4,
    reb_pct: 44.2,
    tov_pct: 14.2,
  },
  per36: {
    pts: 123.0,
    fgm: 45.0,
    fga: 106.5,
    fg3m: 16.5,
    fg3a: 48.0,
    ftm: 16.5,
    fta: 24.0,
    oreb: 13.5,
    dreb: 40.5,
    reb: 54.0,
    ast: 28.5,
    stl: 9.0,
    blk: 4.5,
    tov: 18.0,
    pf: 21.0,
  },
  per100: {
    pts: 112.8,
    fgm: 41.2,
    fga: 97.6,
    fg3m: 15.1,
    fg3a: 44.0,
    ftm: 15.1,
    fta: 22.0,
    oreb: 12.4,
    dreb: 37.1,
    reb: 49.5,
    ast: 26.1,
    stl: 8.2,
    blk: 4.1,
    tov: 16.5,
    pf: 19.2,
  },
}

export const BOS_GAME_STATS: Record<GameLogTab, Record<string, string | number>> = {
  general: {
    pts: 87,
    min: 240,
    fgm: 32,
    fga: 68,
    fg_pct: ".471",
    fg3m: 9,
    fg3a: 26,
    fg3_pct: ".346",
    ftm: 14,
    fta: 17,
    ft_pct: ".824",
    oreb: 11,
    dreb: 30,
    reb: 41,
    ast: 25,
    stl: 8,
    blk: 5,
    tov: 9,
    pf: 11,
    plus_minus: "+5",
  },
  advanced: {
    off_rtg: 114.2,
    def_rtg: 108.6,
    net_rtg: "+5.6",
    ts_pct: ".568",
    efg_pct: ".537",
    usg_pct: "—",
    pie: "—",
    pace: 98.2,
    ast_pct: "58.2",
    ast_to: "2.78",
    ast_ratio: 18.4,
    oreb_pct: 26.8,
    dreb_pct: 72.1,
    reb_pct: 49.4,
    tov_pct: 11.8,
  },
  per36: {
    pts: 130.5,
    fgm: 48.0,
    fga: 102.0,
    fg3m: 13.5,
    fg3a: 39.0,
    ftm: 21.0,
    fta: 25.5,
    oreb: 16.5,
    dreb: 45.0,
    reb: 61.5,
    ast: 37.5,
    stl: 12.0,
    blk: 7.5,
    tov: 13.5,
    pf: 16.5,
  },
  per100: {
    pts: 118.4,
    fgm: 43.6,
    fga: 92.6,
    fg3m: 12.2,
    fg3a: 35.4,
    ftm: 19.0,
    fta: 23.1,
    oreb: 15.0,
    dreb: 40.8,
    reb: 55.8,
    ast: 34.0,
    stl: 10.9,
    blk: 6.8,
    tov: 12.2,
    pf: 15.0,
  },
}

export function getTeamGameStatsByTab(
  abbr: string,
  tab: GameLogTab,
): Record<string, string | number> {
  const core =
    abbr === "BOS" ? BOS_GAME_STATS : abbr === "MIA" ? MIA_GAME_STATS : null
  if (core) return core[tab] ?? {}
  return OTHER_LIVE_GAME_STATS[abbr]?.[tab] ?? {}
}
