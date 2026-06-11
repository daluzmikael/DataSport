import { BOS_FRANCHISE_HISTORY } from "./bosFranchiseHistory"
import type {
  TeamHistorySeason,
  TeamProfile,
  TeamSeasonGameLogBundle,
  TeamSeasonGameRow,
} from "../types"

const OPPONENTS = [
  "MIA", "NYK", "LAL", "PHI", "MIL", "CLE", "ATL", "CHI", "ORL", "DET",
  "BKN", "TOR", "IND", "WAS", "CHA", "MEM", "DAL", "DEN", "PHX", "SAC",
]

function seededRandom(seed: string): () => number {
  let h = 0
  for (let i = 0; i < seed.length; i++) {
    h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0
  }
  return () => {
    h = (Math.imul(1103515245, h) + 12345) | 0
    return (h >>> 0) / 4294967296
  }
}

export function gameRow(
  id: string,
  game: string,
  wl: string,
  pts: number,
  extras?: Partial<Record<string, string | number>>,
): TeamSeasonGameRow {
  return {
    id,
    game,
    values: {
      wl,
      min: 240,
      pts,
      fgm: Math.round(pts * 0.36),
      fga: Math.round(pts * 0.76),
      fg_pct: ".470",
      fg3m: Math.round(pts * 0.13),
      fg3a: Math.round(pts * 0.34),
      fg3_pct: ".370",
      ftm: 16,
      fta: 20,
      ft_pct: ".800",
      oreb: 10,
      dreb: 34,
      reb: 44,
      ast: 26,
      stl: 8,
      blk: 5,
      tov: 12,
      pf: 18,
      plus_minus: wl === "W" ? "+8" : wl === "L" ? "-6" : "—",
      ...extras,
    },
  }
}

export function tabGamesFromGeneral(general: TeamSeasonGameRow[]) {
  return {
    general,
    advanced: general.map((g) => ({
      ...g,
      values: {
        off_rtg: 112,
        def_rtg: 110,
        net_rtg: "+2",
        ts_pct: ".555",
        efg_pct: ".520",
        usg_pct: "—",
        pie: "—",
        pace: 99.0,
        ast_pct: "55",
        ast_to: "2.10",
        ast_ratio: 17.8,
        oreb_pct: 25.0,
        dreb_pct: 71.0,
        reb_pct: 48.0,
        tov_pct: 12.5,
      },
    })),
    per36: general.map((g) => ({
      ...g,
      values: {
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
    })),
    per100: general.map((g) => ({
      ...g,
      values: {
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
    })),
  }
}

function num(v: string | number): number {
  return typeof v === "number" ? v : Number.parseFloat(String(v))
}

function historyToGeneralAvg(
  wl: string,
  values: TeamHistorySeason["values"],
): Record<string, string | number> {
  const pts = num(values.pts)
  const reb = num(values.reb)
  const ast = num(values.ast)
  return {
    wl,
    min: "—",
    pts,
    fgm: +(pts * 0.36).toFixed(1),
    fga: +(pts * 0.76).toFixed(1),
    fg_pct: values.fg_pct,
    fg3m: +(pts * 0.13).toFixed(1),
    fg3a: +(pts * 0.34).toFixed(1),
    fg3_pct: values.fg3_pct,
    ftm: +(pts * 0.15).toFixed(1),
    fta: +(pts * 0.19).toFixed(1),
    ft_pct: ".780",
    oreb: +(reb * 0.22).toFixed(1),
    dreb: +(reb * 0.78).toFixed(1),
    reb,
    ast,
    stl: 7.5,
    blk: 4.8,
    tov: 13.0,
    pf: 18.0,
    plus_minus: "+0.0",
  }
}

function defaultSeasonAverages(
  general: Record<string, string | number>,
): TeamSeasonGameLogBundle["averages"] {
  const pts = num(general.pts)
  return {
    general,
    advanced: {
      off_rtg: +(105 + pts * 0.08).toFixed(1),
      def_rtg: +(108 + (120 - pts) * 0.05).toFixed(1),
      net_rtg: "+2.0",
      ts_pct: ".555",
      efg_pct: ".520",
      usg_pct: "—",
      pie: "—",
      pace: 99.0,
      ast_pct: "—",
      ast_to: "—",
      ast_ratio: 18.0,
      oreb_pct: 25.0,
      dreb_pct: 71.0,
      reb_pct: 48.0,
      tov_pct: 12.5,
    },
    per36: {
      pts,
      fgm: general.fgm,
      fga: general.fga,
      fg3m: general.fg3m,
      fg3a: general.fg3a,
      ftm: general.ftm,
      fta: general.fta,
      oreb: general.oreb,
      dreb: general.dreb,
      reb: general.reb,
      ast: general.ast,
      stl: general.stl,
      blk: general.blk,
      tov: general.tov,
      pf: general.pf,
    },
    per100: {
      pts: +(pts * 1.02).toFixed(1),
      fgm: +(num(general.fgm) * 1.02).toFixed(1),
      fga: +(num(general.fga) * 1.02).toFixed(1),
      fg3m: general.fg3m,
      fg3a: general.fg3a,
      ftm: general.ftm,
      fta: general.fta,
      oreb: general.oreb,
      dreb: general.dreb,
      reb: general.reb,
      ast: general.ast,
      stl: general.stl,
      blk: general.blk,
      tov: general.tov,
      pf: general.pf,
    },
  }
}

function generateGeneralGames(
  teamKey: string,
  season: string,
  wl: string,
  avgPts: number,
): TeamSeasonGameRow[] {
  const [wins, losses] = wl.split("-").map(Number)
  const total = wins + losses
  const count = Math.min(18, total)
  const winProb = wins / total
  const rng = seededRandom(`${teamKey}-${season}`)

  return Array.from({ length: count }, (_, i) => {
    const isWin = rng() < winProb
    const opp = OPPONENTS[Math.floor(rng() * OPPONENTS.length)]
    const home = rng() > 0.5
    const month = 10 + Math.floor((i * 5) / count)
    const day = 1 + ((i * 3) % 27)
    const label = `${month}/${String(day).padStart(2, "0")} ${home ? "vs" : "@"} ${opp}`
    const pts = Math.round(avgPts + (rng() - 0.5) * 22)
    return gameRow(`${teamKey}-${season}-g${i}`, label, isWin ? "W" : "L", pts)
  })
}

function buildFromHistory(
  teamKey: string,
  hist: TeamHistorySeason,
): TeamSeasonGameLogBundle {
  const avgPts = num(hist.values.pts)
  const general = generateGeneralGames(teamKey, hist.season, hist.wl, avgPts)
  const averages = defaultSeasonAverages(historyToGeneralAvg(hist.wl, hist.values))
  return {
    season: hist.season,
    games: tabGamesFromGeneral(general),
    averages,
  }
}

const logCache = new Map<string, TeamSeasonGameLogBundle>()

export function getTeamSeasonOptions(profile: TeamProfile): string[] {
  if (profile.history.length > 0) {
    return [...profile.history].reverse().map((h) => h.season)
  }
  return [profile.seasonLabel]
}

export function getTeamSeasonGameLog(
  profile: TeamProfile,
  season: string,
): TeamSeasonGameLogBundle {
  const cacheKey = `${profile.id}:${season}`
  const cached = logCache.get(cacheKey)
  if (cached) return cached

  if (season === profile.seasonLabel) {
    const bundle: TeamSeasonGameLogBundle = {
      season,
      games: profile.seasonGames,
      averages: profile.seasonAverages,
    }
    logCache.set(cacheKey, bundle)
    return bundle
  }

  const hist = profile.history.find((h) => h.season === season)
  if (hist) {
    const bundle = buildFromHistory(profile.abbr.toLowerCase(), hist)
    logCache.set(cacheKey, bundle)
    return bundle
  }

  if (profile.id === "team-bos") {
    const bosHist = BOS_FRANCHISE_HISTORY.find((h) => h.season === season)
    if (bosHist) {
      const bundle = buildFromHistory("bos", bosHist)
      logCache.set(cacheKey, bundle)
      return bundle
    }
  }

  const fallback = buildFromHistory(profile.abbr.toLowerCase(), {
    season,
    wl: "41-41",
    values: { pts: 110, reb: 44, ast: 25, fg_pct: ".460", fg3_pct: ".360" },
  })
  logCache.set(cacheKey, fallback)
  return fallback
}
