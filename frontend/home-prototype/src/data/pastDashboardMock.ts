import type { GameDetailView, LiveFeedItem, PlayerLive, TeamGameLive } from "../types"
import { buildOrderedDashboardFeed } from "./orderedDashboardFeed"

const sharedPlayerExtras = {
  seasonAvgGameScore: 7.0,
  seasonGameScoreRank: 10,
  seasonGameScoreRankTotal: 312,
  tsPct: ".550",
  efgPct: ".520",
  usgPct: "28.0",
  astPct: "25.0",
  astToTov: "2.50",
  orebPct: "4.0",
  drebPct: "15.0",
  pie: ".140",
  contestedShots: 6,
  contestedShots2pt: 4,
  contestedShots3pt: 2,
  deflections: 3,
  screenAssists: 2,
  screenAssistPoints: 4,
  boxOuts: 2,
  offensiveBoxOuts: 1,
  defensiveBoxOuts: 1,
  looseBallsRecoveredTotal: 1,
  looseBallsRecoveredOffensive: 0,
  looseBallsRecoveredDefensive: 1,
  chargesDrawn: 0,
  boxOutPlayerTeamRebounds: 1,
  boxOutPlayerRebounds: 1,
} as const

function finalTeamGame(
  id: string,
  away: { abbr: string; name: string; score: number; line: { q1: number; q2: number; q3: number; q4: number } },
  home: { abbr: string; name: string; score: number; line: { q1: number; q2: number; q3: number; q4: number } },
  leaders?: {
    topScorers: { name: string; value: number }[]
    topAssists: { name: string; value: number }[]
    topRebounds: { name: string; value: number }[]
  },
): TeamGameLive {
  return {
    id,
    kind: "followed-team",
    away,
    home,
    period: "Final",
    clock: "",
    isLive: false,
    possession: "home",
    homeTimeouts: 0,
    awayTimeouts: 0,
    homeTeamFouls: 0,
    awayTeamFouls: 0,
    homeGameStats: { fg: "42/88", fg3: "14/38", ft: "18/22", reb: 44, ast: 26, tov: 11, pf: 18 },
    awayGameStats: { fg: "38/86", fg3: "12/36", ft: "16/20", reb: 40, ast: 22, tov: 13, pf: 20 },
    topScorers: leaders?.topScorers ?? [
      { name: "Tatum", value: 32 },
      { name: "Brown", value: 28 },
      { name: "Herro", value: 22 },
    ],
    topAssists: leaders?.topAssists ?? [
      { name: "White", value: 9 },
      { name: "Holiday", value: 7 },
      { name: "Adebayo", value: 6 },
    ],
    topRebounds: leaders?.topRebounds ?? [
      { name: "Horford", value: 11 },
      { name: "Tatum", value: 9 },
      { name: "Adebayo", value: 8 },
    ],
  }
}

function finalPlayer(
  id: string,
  name: string,
  gameId: string,
  teamAbbr: string,
  opponentAbbr: string,
  stats: {
    minutes: number
    pts: number
    fg: string
    fg3: string
    reb: number
    ast: number
    tov: number
    gameScore: number
    seasonAvgGameScore?: number
    seasonGameScoreRank?: number
  },
): LiveFeedItem {
  return {
    id,
    kind: "followed-player",
    name,
    gameId,
    teamAbbr,
    opponentAbbr,
    minutes: stats.minutes,
    status: "bench",
    period: "Final",
    clock: "",
    pts: stats.pts,
    fg: stats.fg,
    fgPct: ".500",
    fg3: stats.fg3,
    fg3Pct: ".400",
    ft: "4/5",
    ftPct: ".800",
    oreb: 1,
    dreb: stats.reb - 1,
    reb: stats.reb,
    ast: stats.ast,
    tov: stats.tov,
    stl: 1,
    blk: 0,
    pf: 2,
    plusMinus: "+8",
    gameScore: stats.gameScore,
    ...sharedPlayerExtras,
    seasonAvgGameScore: stats.seasonAvgGameScore ?? sharedPlayerExtras.seasonAvgGameScore,
    seasonGameScoreRank: stats.seasonGameScoreRank ?? sharedPlayerExtras.seasonGameScoreRank,
  }
}

function finalCompact(
  id: string,
  awayAbbr: string,
  homeAbbr: string,
  awayScore: number,
  homeScore: number,
): LiveFeedItem {
  return {
    id,
    kind: "other-live",
    awayAbbr,
    homeAbbr,
    awayScore,
    homeScore,
    period: "Final",
    clock: "",
  }
}

const YESTERDAY_RAW: LiveFeedItem[] = [
  finalTeamGame(
    "game-celtics-yesterday",
    {
      abbr: "NYK",
      name: "Knicks",
      score: 108,
      line: { q1: 26, q2: 28, q3: 24, q4: 30 },
    },
    {
      abbr: "BOS",
      name: "Celtics",
      score: 118,
      line: { q1: 28, q2: 30, q3: 32, q4: 28 },
    },
    {
      topScorers: [
        { name: "Tatum", value: 32 },
        { name: "Brown", value: 28 },
        { name: "Brunson", value: 26 },
      ],
      topAssists: [
        { name: "White", value: 9 },
        { name: "Holiday", value: 7 },
        { name: "Brunson", value: 6 },
      ],
      topRebounds: [
        { name: "Horford", value: 11 },
        { name: "Tatum", value: 9 },
        { name: "Hart", value: 8 },
      ],
    },
  ),
  finalPlayer("player-tatum-yesterday", "Jayson Tatum", "game-celtics-yesterday", "BOS", "NYK", {
    minutes: 38,
    pts: 32,
    fg: "12/22",
    fg3: "3/8",
    reb: 9,
    ast: 8,
    tov: 2,
    gameScore: 9.2,
  }),
  finalPlayer("player-durant-yesterday", "Kevin Durant", "game-suns-yesterday", "PHX", "MEM", {
    minutes: 36,
    pts: 28,
    fg: "10/18",
    fg3: "4/7",
    reb: 6,
    ast: 5,
    tov: 1,
    gameScore: 8.1,
    seasonAvgGameScore: 7.6,
    seasonGameScoreRank: 4,
  }),
  finalCompact("game-suns-yesterday", "PHX", "MEM", 112, 105),
  finalCompact("game-lakers-yesterday", "LAL", "DEN", 104, 110),
  finalCompact("game-knicks-yesterday", "NYK", "CLE", 98, 102),
]

const TWO_DAYS_RAW: LiveFeedItem[] = [
  finalTeamGame(
    "game-celtics-2d",
    {
      abbr: "BOS",
      name: "Celtics",
      score: 112,
      line: { q1: 30, q2: 26, q3: 28, q4: 28 },
    },
    {
      abbr: "MIA",
      name: "Heat",
      score: 107,
      line: { q1: 24, q2: 28, q3: 27, q4: 28 },
    },
    {
      topScorers: [
        { name: "Tatum", value: 28 },
        { name: "Brown", value: 24 },
        { name: "Herro", value: 22 },
      ],
      topAssists: [
        { name: "White", value: 8 },
        { name: "Holiday", value: 6 },
        { name: "Adebayo", value: 5 },
      ],
      topRebounds: [
        { name: "Horford", value: 10 },
        { name: "Adebayo", value: 9 },
        { name: "Tatum", value: 8 },
      ],
    },
  ),
  finalPlayer("player-tatum-2d", "Jayson Tatum", "game-celtics-2d", "BOS", "MIA", {
    minutes: 35,
    pts: 28,
    fg: "11/20",
    fg3: "2/7",
    reb: 8,
    ast: 6,
    tov: 3,
    gameScore: 7.8,
  }),
  finalPlayer("player-durant-2d", "Kevin Durant", "game-suns-2d", "PHX", "SAC", {
    minutes: 34,
    pts: 26,
    fg: "9/16",
    fg3: "3/6",
    reb: 7,
    ast: 4,
    tov: 2,
    gameScore: 7.4,
    seasonAvgGameScore: 7.6,
    seasonGameScoreRank: 4,
  }),
  finalCompact("game-suns-2d", "PHX", "SAC", 121, 115),
  finalCompact("game-lakers-2d", "LAL", "DEN", 99, 108),
  finalCompact("game-knicks-2d", "MIA", "ATL", 101, 97),
]

const THREE_DAYS_RAW: LiveFeedItem[] = [
  finalTeamGame(
    "game-celtics-3d",
    {
      abbr: "BOS",
      name: "Celtics",
      score: 124,
      line: { q1: 32, q2: 30, q3: 28, q4: 34 },
    },
    {
      abbr: "ORL",
      name: "Magic",
      score: 98,
      line: { q1: 22, q2: 24, q3: 26, q4: 26 },
    },
  ),
  finalPlayer("player-tatum-3d", "Jayson Tatum", "game-celtics-3d", "BOS", "ORL", {
    minutes: 32,
    pts: 30,
    fg: "11/19",
    fg3: "4/9",
    reb: 7,
    ast: 5,
    tov: 1,
    gameScore: 8.6,
  }),
  finalCompact("game-lakers-3d", "LAL", "DEN", 118, 112),
  finalCompact("game-knicks-3d", "NYK", "CLE", 105, 111),
  finalCompact("game-suns-3d", "PHX", "DAL", 108, 114),
]

export interface PastDashboardDay {
  label: string
  items: LiveFeedItem[]
}

export const PAST_DASHBOARD_DAYS: PastDashboardDay[] = [
  { label: "Yesterday", items: buildOrderedDashboardFeed(YESTERDAY_RAW) },
  { label: "2 days ago", items: buildOrderedDashboardFeed(TWO_DAYS_RAW) },
  { label: "3 days ago", items: buildOrderedDashboardFeed(THREE_DAYS_RAW) },
]

const ALL_PAST_RAW = [...YESTERDAY_RAW, ...TWO_DAYS_RAW, ...THREE_DAYS_RAW]

export const PAST_PLAYER_PROFILES: PlayerLive[] = ALL_PAST_RAW.filter(
  (i): i is PlayerLive => i.kind === "followed-player",
)

export const PAST_GAME_DETAILS: Record<string, GameDetailView> = Object.fromEntries(
  ALL_PAST_RAW.filter((i) => i.kind === "followed-team" || i.kind === "other-live").map((i) => {
    if (i.kind === "other-live" && !("home" in i)) {
      const detail: GameDetailView = {
        id: i.id,
        kind: "other-live",
        home: {
          abbr: i.homeAbbr,
          name: i.homeAbbr,
          score: i.homeScore,
          line: { q1: 24, q2: 26, q3: 28, q4: i.homeScore - 78 },
        },
        away: {
          abbr: i.awayAbbr,
          name: i.awayAbbr,
          score: i.awayScore,
          line: { q1: 22, q2: 24, q3: 26, q4: i.awayScore - 72 },
        },
        period: "Final",
        clock: "",
        isLive: false,
        possession: "home",
        homeTimeouts: 0,
        awayTimeouts: 0,
        homeTeamFouls: 0,
        awayTeamFouls: 0,
        homeGameStats: { fg: "40/84", fg3: "12/34", ft: "14/18", reb: 42, ast: 24, tov: 12, pf: 18 },
        awayGameStats: { fg: "38/82", fg3: "11/32", ft: "12/16", reb: 38, ast: 22, tov: 14, pf: 19 },
        topScorers: [
          { name: "Star", value: 28 },
          { name: "Wing", value: 24 },
          { name: "Guard", value: 20 },
        ],
        topAssists: [
          { name: "PG", value: 8 },
          { name: "SG", value: 6 },
          { name: "F", value: 5 },
        ],
        topRebounds: [
          { name: "C", value: 12 },
          { name: "F", value: 9 },
          { name: "G", value: 7 },
        ],
      }
      return [i.id, detail]
    }
    return [i.id, i as GameDetailView]
  }),
)
