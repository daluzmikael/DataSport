import { OTHER_LIVE_BOX_SCORES } from "./otherLiveGamesMock"
import {
  TAB_CONFIG,
  type GameLogColumn,
  type GameLogTab,
} from "./playerGameLogMock"

export type { GameLogTab }

export interface TeamBoxRow {
  id: string
  player: string
  isSeasonAvg?: boolean
  isDnp?: boolean
  values: Record<string, string | number>
}

function dnpRow(id: string, player: string): TeamBoxRow {
  const dash = "—"
  const values: Record<string, string | number> = {
    wl: dash,
    min: "DNP",
    pts: dash,
    fgm: dash,
    fga: dash,
    fg_pct: dash,
    fg3m: dash,
    fg3a: dash,
    fg3_pct: dash,
    ftm: dash,
    fta: dash,
    ft_pct: dash,
    oreb: dash,
    dreb: dash,
    reb: dash,
    ast: dash,
    stl: dash,
    blk: dash,
    tov: dash,
    pf: dash,
    plus_minus: dash,
  }
  return { id, player, isDnp: true, values }
}

function benchRow(
  id: string,
  player: string,
  min: number,
  pts: number,
  plus_minus: string,
): TeamBoxRow {
  return {
    id,
    player,
    values: {
      wl: "—",
      min,
      pts,
      fgm: Math.floor(pts * 0.38),
      fga: Math.floor(pts * 0.82),
      fg_pct: ".450",
      fg3m: Math.floor(pts * 0.12),
      fg3a: Math.floor(pts * 0.35),
      fg3_pct: ".340",
      ftm: 1,
      fta: 2,
      ft_pct: ".500",
      oreb: 0,
      dreb: 2,
      reb: 2,
      ast: 2,
      stl: 0,
      blk: 0,
      tov: 1,
      pf: 1,
      plus_minus,
    },
  }
}

export interface TeamBoxScoreData {
  teamAbbr: string
  seasonLabel: string
  byTab: Record<GameLogTab, { seasonAvg: TeamBoxRow; players: TeamBoxRow[] }>
}

export function teamBoxColumns(tab: GameLogTab): GameLogColumn[] {
  return TAB_CONFIG[tab].columns.map((c) =>
    c.id === "game" ? { id: "player", label: "Player", minWidth: 108 } : c,
  )
}

const BOS_GENERAL_PLAYERS: TeamBoxRow[] = [
  {
    id: "bos-tatum",
    player: "Tatum",
    values: {
      wl: "—",
      min: 22,
      pts: 24,
      fgm: 9,
      fga: 18,
      fg_pct: ".500",
      fg3m: 2,
      fg3a: 6,
      fg3_pct: ".333",
      ftm: 4,
      fta: 5,
      ft_pct: ".800",
      oreb: 1,
      dreb: 6,
      reb: 7,
      ast: 7,
      stl: 1,
      blk: 0,
      tov: 2,
      pf: 2,
      plus_minus: "+6",
    },
  },
  {
    id: "bos-brown",
    player: "Brown",
    values: {
      wl: "—",
      min: 35,
      pts: 19,
      fgm: 7,
      fga: 15,
      fg_pct: ".467",
      fg3m: 2,
      fg3a: 5,
      fg3_pct: ".400",
      ftm: 3,
      fta: 4,
      ft_pct: ".750",
      oreb: 1,
      dreb: 4,
      reb: 5,
      ast: 4,
      stl: 2,
      blk: 0,
      tov: 1,
      pf: 3,
      plus_minus: "+5",
    },
  },
  {
    id: "bos-white",
    player: "White",
    values: {
      wl: "—",
      min: 28,
      pts: 11,
      fgm: 4,
      fga: 9,
      fg_pct: ".444",
      fg3m: 2,
      fg3a: 5,
      fg3_pct: ".400",
      ftm: 1,
      fta: 1,
      ft_pct: "1.000",
      oreb: 0,
      dreb: 2,
      reb: 2,
      ast: 6,
      stl: 1,
      blk: 1,
      tov: 0,
      pf: 2,
      plus_minus: "+4",
    },
  },
  {
    id: "bos-holiday",
    player: "Holiday",
    values: {
      wl: "—",
      min: 26,
      pts: 8,
      fgm: 3,
      fga: 7,
      fg_pct: ".429",
      fg3m: 1,
      fg3a: 4,
      fg3_pct: ".250",
      ftm: 1,
      fta: 2,
      ft_pct: ".500",
      oreb: 0,
      dreb: 3,
      reb: 3,
      ast: 5,
      stl: 2,
      blk: 0,
      tov: 1,
      pf: 2,
      plus_minus: "+3",
    },
  },
  {
    id: "bos-horford",
    player: "Horford",
    values: {
      wl: "—",
      min: 20,
      pts: 6,
      fgm: 2,
      fga: 5,
      fg_pct: ".400",
      fg3m: 1,
      fg3a: 3,
      fg3_pct: ".333",
      ftm: 1,
      fta: 1,
      ft_pct: "1.000",
      oreb: 2,
      dreb: 6,
      reb: 8,
      ast: 2,
      stl: 0,
      blk: 1,
      tov: 0,
      pf: 1,
      plus_minus: "+2",
    },
  },
  {
    id: "bos-porzingis",
    player: "Porzingis",
    values: {
      wl: "—",
      min: 24,
      pts: 14,
      fgm: 5,
      fga: 10,
      fg_pct: ".500",
      fg3m: 2,
      fg3a: 4,
      fg3_pct: ".500",
      ftm: 2,
      fta: 2,
      ft_pct: "1.000",
      oreb: 1,
      dreb: 4,
      reb: 5,
      ast: 1,
      stl: 0,
      blk: 2,
      tov: 1,
      pf: 3,
      plus_minus: "+4",
    },
  },
  {
    id: "bos-hauser",
    player: "Hauser",
    values: {
      wl: "—",
      min: 14,
      pts: 5,
      fgm: 2,
      fga: 4,
      fg_pct: ".500",
      fg3m: 1,
      fg3a: 3,
      fg3_pct: ".333",
      ftm: 0,
      fta: 0,
      ft_pct: "—",
      oreb: 0,
      dreb: 1,
      reb: 1,
      ast: 0,
      stl: 0,
      blk: 0,
      tov: 0,
      pf: 1,
      plus_minus: "+1",
    },
  },
  benchRow("bos-pritchard", "Pritchard", 16, 7, "+2"),
  benchRow("bos-kornet", "Kornet", 12, 4, "0"),
  benchRow("bos-tillman", "Tillman", 10, 3, "+1"),
  benchRow("bos-brissett", "Brissett", 8, 2, "-1"),
  dnpRow("bos-scheierman", "Scheierman"),
  dnpRow("bos-walsh", "Walsh"),
  dnpRow("bos-queta", "Queta"),
]

const MIA_GENERAL_PLAYERS: TeamBoxRow[] = [
  {
    id: "mia-herro",
    player: "Herro",
    values: {
      wl: "—",
      min: 32,
      pts: 18,
      fgm: 7,
      fga: 16,
      fg_pct: ".438",
      fg3m: 3,
      fg3a: 8,
      fg3_pct: ".375",
      ftm: 1,
      fta: 2,
      ft_pct: ".500",
      oreb: 0,
      dreb: 3,
      reb: 3,
      ast: 4,
      stl: 1,
      blk: 0,
      tov: 2,
      pf: 2,
      plus_minus: "-4",
    },
  },
  {
    id: "mia-adebayo",
    player: "Adebayo",
    values: {
      wl: "—",
      min: 30,
      pts: 16,
      fgm: 7,
      fga: 12,
      fg_pct: ".583",
      fg3m: 0,
      fg3a: 1,
      fg3_pct: ".000",
      ftm: 2,
      fta: 4,
      ft_pct: ".500",
      oreb: 2,
      dreb: 5,
      reb: 7,
      ast: 4,
      stl: 0,
      blk: 1,
      tov: 2,
      pf: 3,
      plus_minus: "-3",
    },
  },
  {
    id: "mia-rozier",
    player: "Rozier",
    values: {
      wl: "—",
      min: 28,
      pts: 12,
      fgm: 5,
      fga: 12,
      fg_pct: ".417",
      fg3m: 1,
      fg3a: 4,
      fg3_pct: ".250",
      ftm: 1,
      fta: 1,
      ft_pct: "1.000",
      oreb: 0,
      dreb: 2,
      reb: 2,
      ast: 3,
      stl: 1,
      blk: 0,
      tov: 1,
      pf: 2,
      plus_minus: "-5",
    },
  },
  {
    id: "mia-robinson",
    player: "Robinson",
    values: {
      wl: "—",
      min: 22,
      pts: 4,
      fgm: 2,
      fga: 3,
      fg_pct: ".667",
      fg3m: 0,
      fg3a: 0,
      fg3_pct: "—",
      ftm: 0,
      fta: 0,
      ft_pct: "—",
      oreb: 3,
      dreb: 4,
      reb: 7,
      ast: 1,
      stl: 0,
      blk: 0,
      tov: 0,
      pf: 4,
      plus_minus: "-2",
    },
  },
  {
    id: "mia-jaquez",
    player: "Jaquez Jr.",
    values: {
      wl: "—",
      min: 24,
      pts: 10,
      fgm: 4,
      fga: 8,
      fg_pct: ".500",
      fg3m: 0,
      fg3a: 2,
      fg3_pct: ".000",
      ftm: 2,
      fta: 2,
      ft_pct: "1.000",
      oreb: 1,
      dreb: 2,
      reb: 3,
      ast: 2,
      stl: 1,
      blk: 0,
      tov: 1,
      pf: 2,
      plus_minus: "-1",
    },
  },
  {
    id: "mia-highsmith",
    player: "Highsmith",
    values: {
      wl: "—",
      min: 18,
      pts: 8,
      fgm: 3,
      fga: 6,
      fg_pct: ".500",
      fg3m: 2,
      fg3a: 4,
      fg3_pct: ".500",
      ftm: 0,
      fta: 0,
      ft_pct: "—",
      oreb: 0,
      dreb: 2,
      reb: 2,
      ast: 1,
      stl: 0,
      blk: 0,
      tov: 0,
      pf: 1,
      plus_minus: "-2",
    },
  },
  {
    id: "mia-jovic",
    player: "Jovic",
    values: {
      wl: "—",
      min: 12,
      pts: 6,
      fgm: 2,
      fga: 5,
      fg_pct: ".400",
      fg3m: 1,
      fg3a: 3,
      fg3_pct: ".333",
      ftm: 1,
      fta: 1,
      ft_pct: "1.000",
      oreb: 0,
      dreb: 2,
      reb: 2,
      ast: 1,
      stl: 0,
      blk: 0,
      tov: 1,
      pf: 1,
      plus_minus: "-1",
    },
  },
  {
    id: "mia-larsson",
    player: "Larsson",
    values: {
      wl: "—",
      min: 8,
      pts: 8,
      fgm: 3,
      fga: 4,
      fg_pct: ".750",
      fg3m: 2,
      fg3a: 2,
      fg3_pct: "1.000",
      ftm: 0,
      fta: 0,
      ft_pct: "—",
      oreb: 0,
      dreb: 1,
      reb: 1,
      ast: 0,
      stl: 0,
      blk: 0,
      tov: 0,
      pf: 0,
      plus_minus: "+2",
    },
  },
  benchRow("mia-love", "Love", 14, 5, "-1"),
  benchRow("mia-ware", "Ware", 11, 4, "0"),
  benchRow("mia-burks", "Burks", 9, 3, "-2"),
  benchRow("mia-anderson", "Anderson", 7, 2, "0"),
  dnpRow("mia-mitchell", "Mitchell"),
  dnpRow("mia-bryant", "Bryant"),
  dnpRow("mia-cain", "Cain"),
]

const BOS_PLAYERS = BOS_GENERAL_PLAYERS
const MIA_PLAYERS = MIA_GENERAL_PLAYERS

function at<T>(arr: T[], i: number, fallback: T): T {
  return arr[i] ?? fallback
}

function seasonAvgRow(
  teamAbbr: string,
  values: Record<string, string | number>,
): TeamBoxRow {
  return {
    id: `${teamAbbr}-season`,
    player: "Season avg",
    isSeasonAvg: true,
    values,
  }
}

const BOS_BY_TAB: TeamBoxScoreData["byTab"] = {
  general: {
    seasonAvg: seasonAvgRow("BOS", {
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
    }),
    players: BOS_PLAYERS,
  },
  advanced: {
    seasonAvg: seasonAvgRow("BOS", {
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
    }),
    players: BOS_PLAYERS.map((p, i) => ({
      ...p,
      values: p.isDnp
        ? { off_rtg: "—", def_rtg: "—", net_rtg: "—", ts_pct: "—", efg_pct: "—", usg_pct: "—", pie: "—", pace: "—", ast_pct: "—", ast_to: "—", ast_ratio: "—", oreb_pct: "—", dreb_pct: "—", reb_pct: "—", tov_pct: "—" }
        : {
        off_rtg: at([118, 112, 116, 108, 114, 120, 105, 106, 104, 102, 100], i, 100),
        def_rtg: at([108, 110, 109, 111, 107, 106, 112, 110, 109, 111, 110], i, 110),
        net_rtg: at(["+10", "+2", "+7", "-3", "+7", "+14", "-7", "-4", "-5", "-9", "-10"], i, "—"),
        ts_pct: at([".582", ".521", ".598", ".445", ".512", ".612", ".556", ".498", ".482", ".468", "—"], i, "—"),
        efg_pct: at([".548", ".500", ".578", ".429", ".500", ".600", ".542", ".480", ".462", ".440", "—"], i, "—"),
        usg_pct: at(["28.1", "24.2", "18.4", "16.2", "14.8", "22.4", "12.1", "14.2", "12.8", "11.4", "—"], i, "—"),
        pie: at([".168", ".142", ".118", ".102", ".098", ".152", ".084", ".092", ".086", ".078", "—"], i, "—"),
        pace: 98.6,
        ast_pct: at(["32.4", "18.2", "28.4", "22.1", "12.4", "8.2", "6.4", "14.2", "10.8", "8.4", "—"], i, "—"),
        ast_to: at(["3.50", "4.00", "—", "5.00", "—", "1.00", "—", "2.50", "—", "—", "—"], i, "—"),
        ast_ratio: at([24.2, 18.4, 22.1, 20.8, 14.2, 12.4, 8.2, 16.4, 14.8, 12.2, 0], i, "—"),
        oreb_pct: at(["4.2", "3.1", "2.1", "1.8", "8.4", "4.8", "2.2", "2.4", "3.2", "2.8", "—"], i, "—"),
        dreb_pct: at(["18.6", "12.4", "8.2", "10.4", "22.4", "14.2", "6.8", "8.4", "9.2", "7.6", "—"], i, "—"),
        reb_pct: at(["11.4", "8.2", "5.4", "6.2", "15.4", "9.6", "4.5", "5.4", "6.2", "5.2", "—"], i, "—"),
        tov_pct: at(["9.2", "6.8", "4.2", "8.4", "5.2", "7.8", "4.1", "6.2", "5.8", "5.4", "—"], i, "—"),
      },
    })),
  },
  per36: {
    seasonAvg: seasonAvgRow("BOS", {
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
    }),
    players: BOS_PLAYERS.map((p) => {
      if (p.isDnp) return { ...p, values: { pts: "—", fgm: "—", fga: "—", fg3m: "—", fg3a: "—", ftm: "—", fta: "—", oreb: "—", dreb: "—", reb: "—", ast: "—", stl: "—", blk: "—", tov: "—", pf: "—" } }
      const min = p.values.min as number
      const s = 36 / min
      const n = (k: string) =>
        typeof p.values[k] === "number"
          ? ((p.values[k] as number) * s).toFixed(1)
          : p.values[k]
      return {
        ...p,
        values: {
          pts: n("pts"),
          fgm: n("fgm"),
          fga: n("fga"),
          fg3m: n("fg3m"),
          fg3a: n("fg3a"),
          ftm: n("ftm"),
          fta: n("fta"),
          oreb: n("oreb"),
          dreb: n("dreb"),
          reb: n("reb"),
          ast: n("ast"),
          stl: n("stl"),
          blk: n("blk"),
          tov: n("tov"),
          pf: n("pf"),
        },
      }
    }),
  },
  per100: {
    seasonAvg: seasonAvgRow("BOS", {
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
    }),
    players: BOS_PLAYERS.map((p, i) => ({
      ...p,
      values: p.isDnp
        ? { pts: "—", fgm: "—", fga: "—", fg3m: "—", fg3a: "—", ftm: "—", fta: "—", oreb: "—", dreb: "—", reb: "—", ast: "—", stl: "—", blk: "—", tov: "—", pf: "—" }
        : {
        pts: at([39.2, 31.1, 18.0, 13.1, 9.8, 22.9, 8.2, 14.4, 9.6, 6.4, 4.8], i, "—"),
        fgm: at([14.7, 11.5, 6.6, 4.9, 3.3, 8.2, 3.3, 5.4, 3.6, 2.4, 1.8], i, "—"),
        fga: at([29.4, 24.6, 14.7, 11.5, 8.2, 16.4, 6.6, 11.2, 8.4, 5.6, 4.2], i, "—"),
        fg3m: at([3.3, 3.3, 3.3, 1.6, 1.6, 3.3, 1.6, 1.6, 0.8, 0.8, 0], i, "—"),
        fg3a: at([9.8, 8.2, 8.2, 6.6, 4.9, 6.6, 4.9, 4.9, 3.2, 2.4, 0], i, "—"),
        ftm: at([6.6, 4.9, 1.6, 1.6, 1.6, 3.3, 0, 1.6, 1.6, 0.8, 0.8], i, "—"),
        fta: at([8.2, 6.6, 1.6, 3.3, 1.6, 3.3, 0, 3.2, 3.2, 1.6, 1.6], i, "—"),
        oreb: at([1.6, 1.6, 0, 0, 3.3, 1.6, 0, 0, 0.8, 0, 0], i, "—"),
        dreb: at([9.8, 6.6, 3.3, 4.9, 9.8, 6.6, 1.6, 3.2, 2.4, 1.6, 0.8], i, "—"),
        reb: at([11.5, 8.2, 3.3, 4.9, 13.1, 8.2, 1.6, 3.2, 3.2, 1.6, 0.8], i, "—"),
        ast: at([11.5, 6.6, 9.8, 8.2, 3.3, 1.6, 0, 4.8, 2.4, 1.6, 0.8], i, "—"),
        stl: at([1.6, 3.3, 1.6, 3.3, 0, 0, 0, 0, 0, 0, 0], i, "—"),
        blk: at([0, 0, 1.6, 0, 1.6, 3.3, 0, 0, 0.8, 0, 0], i, "—"),
        tov: at([3.3, 1.6, 0, 1.6, 0, 1.6, 0, 0.8, 0.8, 0.8, 0], i, "—"),
        pf: at([3.3, 4.9, 3.3, 3.3, 1.6, 4.9, 1.6, 1.6, 1.6, 0.8, 0.8], i, "—"),
      },
    })),
  },
}

const MIA_BY_TAB: TeamBoxScoreData["byTab"] = {
  general: {
    seasonAvg: seasonAvgRow("MIA", {
      wl: "32-26",
      min: "—",
      pts: 110.2,
      fgm: 40.4,
      fga: 86.8,
      fg_pct: ".465",
      fg3m: 12.8,
      fg3a: 36.2,
      fg3_pct: ".354",
      ftm: 16.6,
      fta: 21.2,
      ft_pct: ".783",
      oreb: 9.8,
      dreb: 33.4,
      reb: 43.2,
      ast: 24.8,
      stl: 7.2,
      blk: 4.2,
      tov: 13.4,
      pf: 19.6,
      plus_minus: "-1.2",
    }),
    players: MIA_PLAYERS,
  },
  advanced: {
    seasonAvg: seasonAvgRow("MIA", {
      off_rtg: 112.4,
      def_rtg: 111.8,
      net_rtg: "+0.6",
      ts_pct: ".562",
      efg_pct: ".528",
      usg_pct: "—",
      pie: "—",
      pace: 97.2,
      ast_pct: "—",
      ast_to: "—",
      ast_ratio: 18.4,
      oreb_pct: 22.4,
      dreb_pct: 71.2,
      reb_pct: 46.8,
      tov_pct: 13.2,
    }),
    players: MIA_PLAYERS.map((p, i) => ({
      ...p,
      values: p.isDnp
        ? { off_rtg: "—", def_rtg: "—", net_rtg: "—", ts_pct: "—", efg_pct: "—", usg_pct: "—", pie: "—", pace: "—", ast_pct: "—", ast_to: "—", ast_ratio: "—", oreb_pct: "—", dreb_pct: "—", reb_pct: "—", tov_pct: "—" }
        : {
        off_rtg: at([108, 114, 106, 102, 110, 104, 112, 106, 104, 102, 100, 98], i, 100),
        def_rtg: at([112, 110, 114, 108, 111, 113, 109, 111, 110, 112, 110, 111], i, 110),
        net_rtg: at(["-4", "+4", "-8", "-6", "-1", "-9", "+3", "-5", "-6", "-10", "-12", "—"], i, "—"),
        ts_pct: at([".498", ".598", ".445", ".612", ".512", ".556", ".712", ".482", ".468", ".452", ".440", "—"], i, "—"),
        efg_pct: at([".468", ".583", ".417", ".667", ".500", ".500", ".750", ".460", ".445", ".430", ".420", "—"], i, "—"),
        usg_pct: at(["26.2", "22.8", "20.4", "14.2", "18.6", "16.4", "14.8", "15.2", "14.4", "13.8", "12.4", "—"], i, "—"),
        pie: at([".122", ".148", ".102", ".084", ".098", ".088", ".112", ".086", ".082", ".078", ".074", "—"], i, "—"),
        pace: 97.2,
        ast_pct: at(["22.4", "18.2", "16.8", "8.4", "12.4", "10.2", "6.4", "8.2", "7.4", "6.8", "6.2", "—"], i, "—"),
        ast_to: at(["2.00", "2.00", "3.00", "—", "2.00", "—", "—", "—", "—", "—", "—", "—"], i, "—"),
        ast_ratio: at([18.2, 16.4, 15.2, 12.4, 14.8, 13.2, 10.8, 11.2, 10.4, 9.8, 9.2, 0], i, "—"),
        oreb_pct: at(["2.2", "6.4", "2.1", "12.4", "4.2", "3.8", "2.4", "2.8", "2.4", "2.2", "2.0", "—"], i, "—"),
        dreb_pct: at(["10.2", "14.8", "8.4", "16.2", "9.8", "10.4", "8.2", "8.8", "8.4", "7.6", "7.2", "—"], i, "—"),
        reb_pct: at(["6.2", "10.6", "5.4", "14.4", "7.0", "7.1", "5.3", "5.8", "5.4", "5.0", "4.6", "—"], i, "—"),
        tov_pct: at(["10.2", "11.2", "8.4", "6.2", "9.8", "8.4", "7.2", "7.8", "7.4", "7.0", "6.8", "—"], i, "—"),
      },
    })),
  },
  per36: {
    seasonAvg: seasonAvgRow("MIA", {
      pts: 110.2,
      fgm: 40.4,
      fga: 86.8,
      fg3m: 12.8,
      fg3a: 36.2,
      ftm: 16.6,
      fta: 21.2,
      oreb: 9.8,
      dreb: 33.4,
      reb: 43.2,
      ast: 24.8,
      stl: 7.2,
      blk: 4.2,
      tov: 13.4,
      pf: 19.6,
    }),
    players: MIA_PLAYERS.map((p) => {
      if (p.isDnp) return { ...p, values: { pts: "—", fgm: "—", fga: "—", fg3m: "—", fg3a: "—", ftm: "—", fta: "—", oreb: "—", dreb: "—", reb: "—", ast: "—", stl: "—", blk: "—", tov: "—", pf: "—" } }
      const min = p.values.min as number
      const s = 36 / min
      const n = (k: string) =>
        typeof p.values[k] === "number"
          ? ((p.values[k] as number) * s).toFixed(1)
          : p.values[k]
      return {
        ...p,
        values: {
          pts: n("pts"),
          fgm: n("fgm"),
          fga: n("fga"),
          fg3m: n("fg3m"),
          fg3a: n("fg3a"),
          ftm: n("ftm"),
          fta: n("fta"),
          oreb: n("oreb"),
          dreb: n("dreb"),
          reb: n("reb"),
          ast: n("ast"),
          stl: n("stl"),
          blk: n("blk"),
          tov: n("tov"),
          pf: n("pf"),
        },
      }
    }),
  },
  per100: {
    seasonAvg: seasonAvgRow("MIA", {
      pts: 113.6,
      fgm: 41.6,
      fga: 89.4,
      fg3m: 13.2,
      fg3a: 37.3,
      ftm: 17.1,
      fta: 21.8,
      oreb: 10.1,
      dreb: 34.4,
      reb: 44.5,
      ast: 25.6,
      stl: 7.4,
      blk: 4.3,
      tov: 13.8,
      pf: 20.2,
    }),
    players: MIA_PLAYERS.map((p, i) => ({
      ...p,
      values: p.isDnp
        ? { pts: "—", fgm: "—", fga: "—", fg3m: "—", fg3a: "—", ftm: "—", fta: "—", oreb: "—", dreb: "—", reb: "—", ast: "—", stl: "—", blk: "—", tov: "—", pf: "—" }
        : {
        pts: at([28.4, 25.2, 18.8, 6.2, 15.6, 12.4, 36.0, 12.8, 10.2, 7.6, 5.4, 4.2], i, "—"),
        fgm: at([11.0, 11.0, 9.8, 4.9, 6.2, 4.9, 13.5, 4.2, 3.6, 2.8, 2.0, 1.6], i, "—"),
        fga: at([25.2, 18.8, 18.8, 7.4, 12.4, 9.8, 6.8, 9.6, 8.4, 6.4, 4.8, 3.6], i, "—"),
        fg3m: at([4.7, 0, 1.6, 0, 0, 3.1, 9.0, 1.6, 1.2, 0.8, 0.4, 0], i, "—"),
        fg3a: at([12.6, 1.6, 6.2, 0, 0, 6.2, 9.0, 4.8, 3.6, 2.4, 1.6, 0], i, "—"),
        ftm: at([1.6, 3.1, 1.6, 0, 3.1, 0, 0, 1.6, 1.2, 0.8, 0.8, 0.4], i, "—"),
        fta: at([3.1, 6.2, 1.6, 0, 3.1, 0, 0, 3.2, 2.4, 1.6, 1.6, 0.8], i, "—"),
        oreb: at([0, 3.1, 0, 7.4, 1.6, 0, 0, 0, 0.8, 0, 0, 0], i, "—"),
        dreb: at([4.7, 7.8, 3.1, 6.2, 3.1, 3.1, 4.5, 3.2, 2.8, 2.4, 1.6, 0.8], i, "—"),
        reb: at([4.7, 10.9, 3.1, 13.6, 4.7, 3.1, 4.5, 3.2, 3.6, 2.4, 1.6, 0.8], i, "—"),
        ast: at([6.2, 6.2, 4.7, 1.6, 3.1, 1.6, 0, 2.4, 1.6, 1.2, 0.8, 0], i, "—"),
        stl: at([1.6, 0, 1.6, 0, 1.6, 0, 0, 0, 0, 0, 0, 0], i, "—"),
        blk: at([0, 1.6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], i, "—"),
        tov: at([3.1, 3.1, 1.6, 0, 1.6, 1.6, 0, 0.8, 0.8, 0.8, 0, 0], i, "—"),
        pf: at([3.1, 4.7, 3.1, 6.2, 3.1, 1.6, 0, 1.6, 1.6, 1.2, 0.8, 0], i, "—"),
      },
    })),
  },
}

const TEAM_DATA: Record<string, TeamBoxScoreData> = {
  BOS: { teamAbbr: "BOS", seasonLabel: "2024-25", byTab: BOS_BY_TAB },
  MIA: { teamAbbr: "MIA", seasonLabel: "2024-25", byTab: MIA_BY_TAB },
  ...OTHER_LIVE_BOX_SCORES,
}

export function getTeamBoxScore(teamAbbr: string): TeamBoxScoreData | undefined {
  return TEAM_DATA[teamAbbr]
}

export function getTeamSeasonAvg(
  teamAbbr: string,
  tab: GameLogTab,
): Record<string, string | number> {
  const data = TEAM_DATA[teamAbbr]
  if (!data) return {}
  return data.byTab[tab].seasonAvg.values
}

export function getTeamSeasonLabel(teamAbbr: string): string {
  return TEAM_DATA[teamAbbr]?.seasonLabel ?? "2024-25"
}

export interface TeamShotChartPlayer {
  id: string
  name: string
  fga: number
  fgm: number
  isDnp: boolean
}

/** Full roster for shot-chart player picker (includes DNP placeholders). */
export function getTeamShotChartRoster(teamAbbr: string): TeamShotChartPlayer[] {
  const data = TEAM_DATA[teamAbbr]
  if (!data) return []
  return data.byTab.general.players.map((row) => {
    const fga = Number(row.values.fga)
    const fgm = Number(row.values.fgm)
    return {
      id: row.id,
      name: row.player,
      fga: row.isDnp || !Number.isFinite(fga) ? 0 : fga,
      fgm: row.isDnp || !Number.isFinite(fgm) ? 0 : fgm,
      isDnp: Boolean(row.isDnp),
    }
  })
}
