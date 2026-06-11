import { SEARCHABLE_TEAMS } from "./favoritesMock"
import { BOS_FRANCHISE_HISTORY } from "./bosFranchiseHistory"
import { BOS_FRANCHISE_ACCOLADES, accoladesFromHistory } from "./teamFranchiseAccolades"
import { gameRow, tabGamesFromGeneral } from "./teamSeasonGameLogBuilder"
import type { TeamProfile } from "../types"

const BOS_SEASON_AVG_GENERAL: Record<string, string | number> = {
  wl: "41-17",
  min: "—",
  pts: 118.6,
  fgm: 42.8,
  fga: 89.4,
  fg_pct: ".479",
  fg3m: 15.2,
  fg3a: 40.1,
  fg3_pct: ".379",
  ftm: 17.8,
  fta: 22.4,
  ft_pct: ".794",
  oreb: 10.2,
  dreb: 35.8,
  reb: 46.0,
  ast: 26.4,
  stl: 7.8,
  blk: 5.4,
  tov: 12.6,
  pf: 18.2,
  plus_minus: "+6.8",
}

const BOS_GENERAL_GAMES = [
  {
    ...gameRow("bos-g-live", "LIVE vs MIA", "—", 87, {
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
    }),
    isLive: true,
  },
  gameRow("bos-g1", "11/28 vs ORL", "W", 124, { plus_minus: "+14" }),
  gameRow("bos-g2", "11/26 @ DET", "W", 116, { plus_minus: "+9" }),
  gameRow("bos-g3", "11/24 vs IND", "L", 108, { plus_minus: "-4" }),
  gameRow("bos-g4", "11/22 @ MIL", "W", 122, { plus_minus: "+11" }),
  gameRow("bos-g5", "11/20 vs BKN", "W", 129, { plus_minus: "+18" }),
  gameRow("bos-g6", "11/18 @ PHI", "L", 101, { plus_minus: "-7" }),
  gameRow("bos-g7", "11/16 vs NYK", "W", 118, { plus_minus: "+6" }),
  gameRow("bos-g8", "11/14 @ MIA", "W", 112, { plus_minus: "+3" }),
  gameRow("bos-g9", "11/12 vs CHI", "W", 107, { plus_minus: "+5" }),
]

const BOS_HISTORY = BOS_FRANCHISE_HISTORY

const BOS_ROSTER: TeamProfile["roster"] = [
  { id: "r-tatum", name: "Jayson Tatum", position: "F", number: "0", height: "6-8" },
  { id: "r-brown", name: "Jaylen Brown", position: "G-F", number: "7", height: "6-6" },
  { id: "r-white", name: "Derrick White", position: "G", number: "9", height: "6-4" },
  { id: "r-holiday", name: "Jrue Holiday", position: "G", number: "4", height: "6-3" },
  { id: "r-horford", name: "Al Horford", position: "C-F", number: "42", height: "6-9" },
  { id: "r-porzingis", name: "Kristaps Porzingis", position: "C-F", number: "8", height: "7-2" },
  { id: "r-hauser", name: "Sam Hauser", position: "F", number: "30", height: "6-7" },
  { id: "r-pritchard", name: "Payton Pritchard", position: "G", number: "11", height: "6-1" },
  { id: "r-kornet", name: "Luke Kornet", position: "C-F", number: "40", height: "7-1" },
  { id: "r-tillman", name: "Xavier Tillman", position: "F", number: "26", height: "6-8" },
  { id: "r-brissett", name: "Oshae Brissett", position: "F", number: "12", height: "6-7" },
  { id: "r-scheierman", name: "Baylor Scheierman", position: "G", number: "55", height: "6-6" },
  { id: "r-walsh", name: "Jordan Walsh", position: "F", number: "27", height: "6-6" },
  { id: "r-queta", name: "Neemias Queta", position: "C", number: "88", height: "7-0" },
]

const BOS_GS_LEADERS: TeamProfile["gameScoreLeaders"] = [
  { rank: 1, player: "Jayson Tatum", season: "2021-22", opponent: "BKN", gameScore: 14.2 },
  { rank: 2, player: "Paul Pierce", season: "2001-02", opponent: "MIA", gameScore: 13.8 },
  { rank: 3, player: "Jayson Tatum", season: "2023-24", opponent: "IND", gameScore: 13.5 },
  { rank: 4, player: "Jaylen Brown", season: "2022-23", opponent: "CHI", gameScore: 13.1 },
  { rank: 5, player: "Kevin Garnett", season: "2007-08", opponent: "WSB", gameScore: 12.9 },
  { rank: 6, player: "Jayson Tatum", season: "2024-25", opponent: "NYK", gameScore: 12.6 },
  { rank: 7, player: "Paul Pierce", season: "2002-03", opponent: "NJN", gameScore: 12.4 },
  { rank: 8, player: "Isaiah Thomas", season: "2016-17", opponent: "WAS", gameScore: 12.2 },
  { rank: 9, player: "Jaylen Brown", season: "2023-24", opponent: "MIA", gameScore: 12.0 },
  { rank: 10, player: "Ray Allen", season: "2008-09", opponent: "TOR", gameScore: 11.8 },
  { rank: 11, player: "Kevin Garnett", season: "2008-09", opponent: "LAL", gameScore: 11.6 },
  { rank: 12, player: "Jayson Tatum", season: "2020-21", opponent: "MIN", gameScore: 11.4 },
  { rank: 13, player: "Paul Pierce", season: "2005-06", opponent: "CLE", gameScore: 11.2 },
  { rank: 14, player: "Jaylen Brown", season: "2024-25", opponent: "MIL", gameScore: 11.0 },
  { rank: 15, player: "Antoine Walker", season: "2001-02", opponent: "DEN", gameScore: 10.9 },
]

export const TEAM_PROFILES: Record<string, TeamProfile> = {
  "team-bos": {
    id: "team-bos",
    abbr: "BOS",
    city: "Boston",
    name: "Celtics",
    seasonLabel: "2024-25",
    seasonGames: {
      general: BOS_GENERAL_GAMES,
      advanced: BOS_GENERAL_GAMES.map((g) => ({
        ...g,
        values: {
          off_rtg: 114,
          def_rtg: 108,
          net_rtg: "+6",
          ts_pct: ".568",
          efg_pct: ".537",
          usg_pct: "—",
          pie: "—",
          pace: 98.2,
          ast_pct: "58",
          ast_to: "2.78",
          ast_ratio: 18.4,
          oreb_pct: 26.8,
          dreb_pct: 72.1,
          reb_pct: 49.4,
          tov_pct: 11.8,
        },
      })),
      per36: BOS_GENERAL_GAMES.map((g) => ({
        ...g,
        values: {
          pts: 118.6,
          fgm: 42.8,
          fga: 89.4,
          fg3m: 15.2,
          fg3a: 40.1,
          ftm: 17.8,
          fta: 22.4,
          oreb: 10.2,
          dreb: 35.8,
          reb: 46.0,
          ast: 26.4,
          stl: 7.8,
          blk: 5.4,
          tov: 12.6,
          pf: 18.2,
        },
      })),
      per100: BOS_GENERAL_GAMES.map((g) => ({
        ...g,
        values: {
          pts: 120.4,
          fgm: 43.4,
          fga: 90.8,
          fg3m: 15.4,
          fg3a: 40.7,
          ftm: 18.1,
          fta: 22.7,
          oreb: 10.4,
          dreb: 36.4,
          reb: 46.8,
          ast: 26.8,
          stl: 7.9,
          blk: 5.5,
          tov: 12.8,
          pf: 18.5,
        },
      })),
    },
    seasonAverages: {
      general: BOS_SEASON_AVG_GENERAL,
      advanced: {
        off_rtg: 118.2,
        def_rtg: 109.8,
        net_rtg: "+8.4",
        ts_pct: ".584",
        efg_pct: ".552",
        usg_pct: "—",
        pie: "—",
        pace: 98.6,
        ast_pct: "—",
        ast_to: "—",
        ast_ratio: 19.2,
        oreb_pct: 24.8,
        dreb_pct: 72.4,
        reb_pct: 48.6,
        tov_pct: 12.1,
      },
      per36: {
        pts: 118.6,
        fgm: 42.8,
        fga: 89.4,
        fg3m: 15.2,
        fg3a: 40.1,
        ftm: 17.8,
        fta: 22.4,
        oreb: 10.2,
        dreb: 35.8,
        reb: 46.0,
        ast: 26.4,
        stl: 7.8,
        blk: 5.4,
        tov: 12.6,
        pf: 18.2,
      },
      per100: {
        pts: 120.2,
        fgm: 43.4,
        fga: 90.6,
        fg3m: 15.4,
        fg3a: 40.6,
        ftm: 18.0,
        fta: 22.7,
        oreb: 10.3,
        dreb: 36.2,
        reb: 46.5,
        ast: 26.8,
        stl: 7.9,
        blk: 5.5,
        tov: 12.8,
        pf: 18.4,
      },
    },
    history: BOS_HISTORY,
    roster: BOS_ROSTER,
    gameScoreLeaders: BOS_GS_LEADERS,
    accolades: BOS_FRANCHISE_ACCOLADES,
    currentSeason: {
      standing: "1st · East",
      record: "41-17",
      bestPlayer: { name: "Jayson Tatum", avgGameScore: 7.1 },
    },
  },
}

function createStubTeamProfile(meta: {
  id: string
  abbr: string
  city: string
  name: string
}): TeamProfile {
  const general = [
    gameRow(`${meta.abbr.toLowerCase()}-g1`, "11/20 vs OPP", "W", 114),
    gameRow(`${meta.abbr.toLowerCase()}-g2`, "11/18 @ OPP", "L", 102),
    gameRow(`${meta.abbr.toLowerCase()}-g3`, "11/16 vs OPP", "W", 118),
  ]
  return {
    id: meta.id,
    abbr: meta.abbr,
    city: meta.city,
    name: meta.name,
    seasonLabel: "2024-25",
    seasonGames: tabGamesFromGeneral(general),
    seasonAverages: {
      general: {
        wl: "30-25",
        min: "—",
        pts: 111.2,
        fgm: 40.4,
        fga: 86.8,
        fg_pct: ".465",
        fg3m: 12.8,
        fg3a: 35.2,
        fg3_pct: ".364",
        ftm: 17.6,
        fta: 22.0,
        ft_pct: ".800",
        oreb: 9.6,
        dreb: 33.4,
        reb: 43.0,
        ast: 25.2,
        stl: 7.4,
        blk: 4.6,
        tov: 13.0,
        pf: 18.0,
        plus_minus: "+1.5",
      },
      advanced: {
        off_rtg: 114.0,
        def_rtg: 112.0,
        net_rtg: "+2.0",
        ts_pct: ".558",
        efg_pct: ".525",
        usg_pct: "—",
        pie: "—",
        pace: 99.2,
        ast_pct: "—",
        ast_to: "—",
        ast_ratio: 18.0,
        oreb_pct: 24.5,
        dreb_pct: 71.5,
        reb_pct: 48.0,
        tov_pct: 12.8,
      },
      per36: {
        pts: 110.0,
        fgm: 40.0,
        fga: 86.0,
        fg3m: 13.0,
        fg3a: 36.0,
        ftm: 17.0,
        fta: 22.0,
        oreb: 9.5,
        dreb: 33.0,
        reb: 42.5,
        ast: 25.0,
        stl: 7.5,
        blk: 4.5,
        tov: 13.0,
        pf: 18.0,
      },
      per100: {
        pts: 112.0,
        fgm: 41.0,
        fga: 87.0,
        fg3m: 13.5,
        fg3a: 36.5,
        ftm: 17.5,
        fta: 22.5,
        oreb: 9.8,
        dreb: 33.5,
        reb: 43.0,
        ast: 25.5,
        stl: 7.6,
        blk: 4.6,
        tov: 13.2,
        pf: 18.2,
      },
    },
    history: [
      {
        season: "2022-23",
        wl: "44-38",
        values: { pts: 110.2, reb: 42.8, ast: 24.6, fg_pct: ".468", fg3_pct: ".358" },
      },
      {
        season: "2023-24",
        wl: "48-34",
        values: { pts: 112.4, reb: 43.2, ast: 25.0, fg_pct: ".472", fg3_pct: ".362" },
      },
      {
        season: "2024-25",
        wl: "30-25",
        values: { pts: 111.2, reb: 43.0, ast: 25.2, fg_pct: ".465", fg3_pct: ".364" },
      },
    ],
    roster: [
      {
        id: `${meta.id}-r1`,
        name: "Starter One",
        position: "G",
        number: "1",
        height: "6-4",
      },
      {
        id: `${meta.id}-r2`,
        name: "Starter Two",
        position: "F",
        number: "2",
        height: "6-8",
      },
      {
        id: `${meta.id}-r3`,
        name: "Starter Three",
        position: "C",
        number: "3",
        height: "7-0",
      },
    ],
    gameScoreLeaders: [
      { rank: 1, player: "Franchise Star", season: "2023-24", opponent: "OPP", gameScore: 11.2 },
      { rank: 2, player: "Veteran Wing", season: "2018-19", opponent: "OPP", gameScore: 10.8 },
      { rank: 3, player: "All-Star Guard", season: "2021-22", opponent: "OPP", gameScore: 10.4 },
    ],
    accolades: accoladesFromHistory([
      {
        season: "2022-23",
        wl: "44-38",
        values: { pts: 110.2, reb: 42.8, ast: 24.6, fg_pct: ".468", fg3_pct: ".358" },
      },
      {
        season: "2023-24",
        wl: "48-34",
        values: { pts: 112.4, reb: 43.2, ast: 25.0, fg_pct: ".472", fg3_pct: ".362" },
      },
      {
        season: "2024-25",
        wl: "30-25",
        values: { pts: 111.2, reb: 43.0, ast: 25.2, fg_pct: ".465", fg3_pct: ".364" },
      },
    ]),
    currentSeason: {
      standing: "8th · East",
      record: "30-25",
      bestPlayer: { name: "Starter One", avgGameScore: 6.4 },
    },
  }
}

const stubCache = new Map<string, TeamProfile>()

export function getTeamProfile(teamId: string): TeamProfile | undefined {
  if (TEAM_PROFILES[teamId]) return TEAM_PROFILES[teamId]
  if (stubCache.has(teamId)) return stubCache.get(teamId)
  const meta = SEARCHABLE_TEAMS.find((t) => t.id === teamId)
  if (!meta) return undefined
  const stub = createStubTeamProfile(meta)
  stubCache.set(teamId, stub)
  return stub
}

export function getTeamProfileByAbbr(abbr: string): TeamProfile | undefined {
  return getTeamProfile(`team-${abbr.toLowerCase()}`)
}
