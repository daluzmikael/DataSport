import type { GameLogRow, GameLogTab } from "../data/playerGameLogMock"
import type { SeasonBubbleSet } from "../data/playerSeasonAverages"
import type { PlayerLive, TeamSeasonGameRow } from "../types"

function num(v: unknown, decimals = 1): string {
  if (v == null || v === "") return "—"
  const n = typeof v === "number" ? v : parseFloat(String(v))
  if (Number.isNaN(n)) return String(v)
  return n.toFixed(decimals)
}

function pct(v: unknown): string {
  if (v == null || v === "") return "—"
  const n = typeof v === "number" ? v : parseFloat(String(v))
  if (Number.isNaN(n)) return String(v)
  if (n > 0 && n <= 1) return `.${Math.round(n * 1000).toString().padStart(3, "0")}`
  if (n > 1 && n <= 100) return `.${Math.round(n * 10).toString().padStart(3, "0")}`
  return String(v)
}

function pick(row: Record<string, unknown>, ...keys: string[]): unknown {
  for (const k of keys) {
    if (row[k] != null) return row[k]
    const upper = k.toUpperCase()
    if (row[upper] != null) return row[upper]
    const lower = k.toLowerCase()
    if (row[lower] != null) return row[lower]
  }
  return undefined
}

function parseMinutes(v: unknown): number {
  if (v == null || v === "") return 0
  if (typeof v === "number") return v
  const s = String(v).trim()
  if (s.includes(":")) {
    const [m, sec] = s.split(":").map((x) => parseFloat(x))
    if (Number.isNaN(m)) return 0
    return m + (Number.isNaN(sec) ? 0 : sec) / 60
  }
  const n = parseFloat(s)
  return Number.isNaN(n) ? 0 : n
}

function calcShootingPct(made: unknown, att: unknown): string {
  const m = typeof made === "number" ? made : parseFloat(String(made ?? ""))
  const a = typeof att === "number" ? att : parseFloat(String(att ?? ""))
  if (Number.isNaN(m) || Number.isNaN(a) || a === 0) return "—"
  return `.${Math.round((m / a) * 1000)
    .toString()
    .padStart(3, "0")}`
}

function formatPlusMinus(v: unknown): string {
  if (v == null || v === "") return "—"
  const n = typeof v === "number" ? v : parseFloat(String(v))
  if (Number.isNaN(n)) return String(v)
  return n > 0 ? `+${n}` : String(n)
}

export function formatShortGameDate(raw: unknown): string {
  const s = String(raw ?? "")
  const iso = s.split("T")[0]
  const parts = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (parts) return `${parts[2]}/${parts[3]}`
  return s
}

function opponentFromMatchup(matchup: string, teamAbbr: string): string {
  const team = teamAbbr.toUpperCase()
  const vs = matchup.match(/^([A-Z]{2,3})\s+vs\.?\s+([A-Z]{2,3})/i)
  if (vs) {
    const t1 = vs[1].toUpperCase()
    const t2 = vs[2].toUpperCase()
    return t1 === team ? t2 : t1
  }
  const at = matchup.match(/^([A-Z]{2,3})\s+@\s+([A-Z]{2,3})/i)
  if (at) {
    const t1 = at[1].toUpperCase()
    const t2 = at[2].toUpperCase()
    return t1 === team ? t2 : t1
  }
  return teamAbbr
}

function calcGameScore(row: Record<string, unknown>): number {
  const n = (k: string) => {
    const v = pick(row, k)
    const x = typeof v === "number" ? v : parseFloat(String(v ?? ""))
    return Number.isNaN(x) ? 0 : x
  }
  const pts = n("PTS")
  const fgm = n("FGM")
  const fga = n("FGA")
  const ftm = n("FTM")
  const fta = n("FTA")
  const oreb = n("OREB")
  const dreb = n("DREB")
  const ast = n("AST")
  const stl = n("STL")
  const blk = n("BLK")
  const pf = n("PF")
  const tov = n("TOV")
  const score =
    pts +
    0.4 * fgm -
    0.7 * fga -
    0.4 * (fta - ftm) +
    0.7 * oreb +
    0.3 * dreb +
    stl +
    0.7 * ast +
    0.7 * blk -
    0.4 * pf -
    tov
  return Math.round(score * 10) / 10
}

export interface PlayerGameSnapshot {
  player: PlayerLive
  matchup: string
  gameDateLabel: string
  wl: string
  nbaGameId: string
}

export function stubPlayerForStaging(nbaId: string, name: string, teamAbbr = "—"): PlayerLive {
  return {
    id: `nba-${nbaId}`,
    kind: "followed-player",
    name,
    teamAbbr,
    opponentAbbr: "—",
    minutes: 0,
    status: "bench",
    period: "Final",
    clock: "",
    pts: 0,
    fg: "0/0",
    fgPct: ".000",
    fg3: "0/0",
    fg3Pct: ".000",
    ft: "0/0",
    ftPct: ".000",
    oreb: 0,
    dreb: 0,
    reb: 0,
    ast: 0,
    tov: 0,
    stl: 0,
    blk: 0,
    pf: 0,
    plusMinus: "0",
    gameScore: 0,
    seasonAvgGameScore: 0,
    seasonGameScoreRank: 0,
    tsPct: "—",
    efgPct: "—",
    usgPct: "—",
    astPct: "—",
    astToTov: "—",
    orebPct: "—",
    drebPct: "—",
    pie: "—",
    contestedShots: 0,
    contestedShots2pt: 0,
    contestedShots3pt: 0,
    deflections: 0,
    screenAssists: 0,
    screenAssistPoints: 0,
    boxOuts: 0,
    offensiveBoxOuts: 0,
    defensiveBoxOuts: 0,
    looseBallsRecoveredTotal: 0,
    looseBallsRecoveredOffensive: 0,
    looseBallsRecoveredDefensive: 0,
    chargesDrawn: 0,
    boxOutPlayerTeamRebounds: 0,
    boxOutPlayerRebounds: 0,
  }
}

export function mapPlayerGameLogToSnapshot(
  base: PlayerLive,
  row: Record<string, unknown>,
): PlayerGameSnapshot {
  const matchup = String(pick(row, "MATCHUP", "matchup") ?? "")
  const teamAbbr = String(pick(row, "TEAM_ABBREVIATION", "team_abbreviation") ?? base.teamAbbr)
  const gameDateLabel = formatShortGameDate(pick(row, "GAME_DATE", "game_date"))
  const nbaGameId = String(pick(row, "GAME_ID", "game_id") ?? "").replace(/\D/g, "").padStart(10, "0")
  const g = generalValuesFromRow(row)
  const a = advancedValuesFromRow(row)
  const min = parseMinutes(pick(row, "MIN", "min"))

  const player: PlayerLive = {
    ...base,
    gameId: `game-${nbaGameId}`,
    teamAbbr,
    opponentAbbr: opponentFromMatchup(matchup, teamAbbr),
    minutes: min,
    status: "bench",
    period: "Final",
    clock: gameDateLabel,
    pts: parseInt(String(g.pts), 10) || 0,
    fg: `${g.fgm}/${g.fga}`,
    fgPct: String(g.fg_pct),
    fg3: `${g.fg3m}/${g.fg3a}`,
    fg3Pct: String(g.fg3_pct),
    ft: `${g.ftm}/${g.fta}`,
    ftPct: String(g.ft_pct),
    oreb: parseInt(String(g.oreb), 10) || 0,
    dreb: parseInt(String(g.dreb), 10) || 0,
    reb: parseInt(String(g.reb), 10) || 0,
    ast: parseInt(String(g.ast), 10) || 0,
    tov: parseInt(String(g.tov), 10) || 0,
    stl: parseInt(String(g.stl), 10) || 0,
    blk: parseInt(String(g.blk), 10) || 0,
    pf: parseInt(String(g.pf), 10) || 0,
    plusMinus: String(g.plus_minus),
    gameScore: calcGameScore(row),
    tsPct: String(a.ts_pct),
    efgPct: String(a.efg_pct),
    usgPct: String(a.usg_pct),
    astPct: String(a.ast_pct),
    astToTov: String(a.ast_to),
    orebPct: String(a.oreb_pct),
    drebPct: String(a.dreb_pct),
    pie: String(a.pie),
    contestedShots: parseFloat(String(pick(row, "hustle_contestedShots") ?? "0")) || 0,
    contestedShots2pt: parseFloat(String(pick(row, "hustle_contestedShots2pt") ?? "0")) || 0,
    contestedShots3pt: parseFloat(String(pick(row, "hustle_contestedShots3pt") ?? "0")) || 0,
    deflections: parseFloat(String(pick(row, "hustle_deflections") ?? "0")) || 0,
    screenAssists: parseFloat(String(pick(row, "hustle_screenAssists") ?? "0")) || 0,
    screenAssistPoints: parseFloat(String(pick(row, "hustle_screenAssistPoints") ?? "0")) || 0,
    boxOuts: parseFloat(String(pick(row, "hustle_boxOuts") ?? "0")) || 0,
    offensiveBoxOuts: parseFloat(String(pick(row, "hustle_offensiveBoxOuts") ?? "0")) || 0,
    defensiveBoxOuts: parseFloat(String(pick(row, "hustle_defensiveBoxOuts") ?? "0")) || 0,
    looseBallsRecoveredTotal:
      parseFloat(String(pick(row, "hustle_looseBallsRecoveredTotal") ?? "0")) || 0,
    looseBallsRecoveredOffensive:
      parseFloat(String(pick(row, "hustle_looseBallsRecoveredOffensive") ?? "0")) || 0,
    looseBallsRecoveredDefensive:
      parseFloat(String(pick(row, "hustle_looseBallsRecoveredDefensive") ?? "0")) || 0,
    chargesDrawn: parseFloat(String(pick(row, "hustle_chargesDrawn") ?? "0")) || 0,
    boxOutPlayerTeamRebounds:
      parseFloat(String(pick(row, "hustle_boxOutPlayerTeamRebounds") ?? "0")) || 0,
    boxOutPlayerRebounds: parseFloat(String(pick(row, "hustle_boxOutPlayerRebounds") ?? "0")) || 0,
  }

  return {
    player,
    matchup,
    gameDateLabel,
    wl: String(g.wl),
    nbaGameId,
  }
}

/** True when a staging row is a per-game log (not season/career summary). */
export function isGameLogRecord(row: unknown): row is Record<string, unknown> {
  if (!row || typeof row !== "object") return false
  const r = row as Record<string, unknown>
  const gameId = pick(r, "GAME_ID", "game_id")
  const matchup = pick(r, "MATCHUP", "matchup")
  const hasGameId = gameId != null && String(gameId).trim().length > 0
  const hasMatchup = typeof matchup === "string" && matchup.trim().length > 0
  return hasGameId || hasMatchup
}

export function filterGameLogRecords(data: unknown): Record<string, unknown>[] {
  if (!Array.isArray(data)) return []
  return data.filter(isGameLogRecord)
}

function gameLabelFromRow(row: Record<string, unknown>, index: number): { label: string; gameId: string } {
  const gameDate = pick(row, "GAME_DATE", "game_date")
  const matchup = String(pick(row, "MATCHUP", "matchup") ?? "")
  const gameId = String(pick(row, "GAME_ID", "game_id") ?? index)
  const dateLabel = formatShortGameDate(gameDate)
  const label = dateLabel && matchup ? `${dateLabel} ${matchup}` : matchup
  return { label, gameId }
}

export function generalValuesFromRow(
  row: Record<string, unknown>,
  opts?: { decimalPlaces?: number },
): Record<string, string | number> {
  const dec = opts?.decimalPlaces
  const fgm = pick(row, "FGM", "fgm")
  const fga = pick(row, "FGA", "fga")
  const fg3m = pick(row, "FG3M", "fg3m")
  const fg3a = pick(row, "FG3A", "fg3a")
  const ftm = pick(row, "FTM", "ftm")
  const fta = pick(row, "FTA", "fta")
  const minRaw = pick(row, "MIN", "min")
  const minVal = parseMinutes(minRaw)
  const fmt = (v: unknown) => (dec != null ? num(v, dec) : num(v, 0))
  const fmtMin = () => {
    if (dec != null) return minVal > 0 ? num(minVal, dec) : String(minRaw ?? "—")
    return minVal > 0 ? num(minVal, minVal % 1 === 0 ? 0 : 1) : String(minRaw ?? "—")
  }
  const fmtPct = (field: unknown, made: unknown, att: unknown) => {
    if (dec != null && field != null && field !== "") {
      const n = typeof field === "number" ? field : parseFloat(String(field))
      if (!Number.isNaN(n)) return num(n, dec)
    }
    return pct(field) !== "—" ? pct(field) : calcShootingPct(made, att)
  }

  return {
    wl: String(pick(row, "WL", "wl") ?? "—"),
    min: fmtMin(),
    pts: fmt(pick(row, "PTS", "pts")),
    fgm: fmt(fgm),
    fga: fmt(fga),
    fg_pct: fmtPct(pick(row, "FG_PCT", "fg_pct"), fgm, fga),
    fg3m: fmt(fg3m),
    fg3a: fmt(fg3a),
    fg3_pct: fmtPct(pick(row, "FG3_PCT", "fg3_pct"), fg3m, fg3a),
    ftm: fmt(ftm),
    fta: fmt(fta),
    ft_pct: fmtPct(pick(row, "FT_PCT", "ft_pct"), ftm, fta),
    oreb: fmt(pick(row, "OREB", "oreb")),
    dreb: fmt(pick(row, "DREB", "dreb")),
    reb: fmt(pick(row, "REB", "reb")),
    ast: fmt(pick(row, "AST", "ast")),
    stl: fmt(pick(row, "STL", "stl")),
    blk: fmt(pick(row, "BLK", "blk")),
    tov: fmt(pick(row, "TOV", "tov")),
    pf: fmt(pick(row, "PF", "pf")),
    plus_minus: formatPlusMinus(pick(row, "PLUS_MINUS", "plus_minus")),
  }
}

export function advancedValuesFromRow(row: Record<string, unknown>): Record<string, string | number> {
  const net = pick(row, "netRating", "NET_RATING", "net_rating")
  return {
    off_rtg: num(pick(row, "offensiveRating", "OFF_RATING", "off_rating"), 1),
    def_rtg: num(pick(row, "defensiveRating", "DEF_RATING", "def_rating"), 1),
    net_rtg:
      net != null
        ? formatPlusMinus(net)
        : num(pick(row, "NET_RATING", "net_rating"), 1),
    ts_pct: pct(pick(row, "trueShootingPercentage", "TS_PCT", "ts_pct")),
    efg_pct: pct(pick(row, "effectiveFieldGoalPercentage", "EFG_PCT", "efg_pct")),
    usg_pct: pct(pick(row, "usagePercentage", "USG_PCT", "usg_pct")),
    pie: num(pick(row, "PIE", "pie"), 3),
    pace: num(pick(row, "pacePer40", "estimatedPace", "PACE", "pace"), 1),
    ast_pct: pct(pick(row, "assistPercentage", "AST_PCT", "ast_pct")),
    ast_to: num(pick(row, "assistToTurnover", "AST_TO", "ast_to"), 2),
    ast_ratio: num(pick(row, "assistRatio", "AST_RATIO", "ast_ratio"), 1),
    oreb_pct: pct(pick(row, "offensiveReboundPercentage", "OREB_PCT", "oreb_pct")),
    dreb_pct: pct(pick(row, "defensiveReboundPercentage", "DREB_PCT", "dreb_pct")),
    reb_pct: pct(pick(row, "reboundPercentage", "REB_PCT", "reb_pct")),
    tov_pct: pct(pick(row, "turnoverRatio", "TM_TOV_PCT", "tov_pct")),
  }
}

export function mapPlayerGameLogRow(row: Record<string, unknown>, index: number): GameLogRow {
  const { label, gameId } = gameLabelFromRow(row, index)
  return {
    id: `gl-${gameId}`,
    isLive: false,
    game: label,
    values: generalValuesFromRow(row),
  }
}

export function mapPlayerGameLogAdvancedRow(row: Record<string, unknown>, index: number): GameLogRow {
  const { label, gameId } = gameLabelFromRow(row, index)
  return {
    id: `gl-${gameId}`,
    isLive: false,
    game: label,
    values: advancedValuesFromRow(row),
  }
}

/** NBA playercareerstats dataset keys (see phase-4 staging). */
const CAREER_REG_TOTALS_DS = "1"
const CAREER_PO_TOTALS_DS = "3"

function parseCareerNumber(v: unknown): number | null {
  if (v == null || v === "" || v === "None" || v === "NR" || v === "nan") return null
  const n = typeof v === "number" ? v : parseFloat(String(v))
  return Number.isNaN(n) ? null : n
}

function careerAverageRow(totals: Record<string, unknown>): Record<string, unknown> {
  const gp = parseCareerNumber(pick(totals, "GP"))
  if (!gp || gp <= 0) return { ...totals }
  const out: Record<string, unknown> = { ...totals }
  const min = parseCareerNumber(pick(totals, "MIN"))
  if (min != null) out.MIN = min / gp
  for (const key of [
    "PTS",
    "FGM",
    "FGA",
    "FG3M",
    "FG3A",
    "FTM",
    "FTA",
    "OREB",
    "DREB",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
  ]) {
    const val = parseCareerNumber(pick(totals, key))
    if (val != null) out[key] = val / gp
  }
  return out
}

function mapCareerSummaryRow(
  id: string,
  label: string,
  row: Record<string, unknown>,
  tab: GameLogTab,
): GameLogRow {
  const values =
    tab === "advanced"
      ? advancedValuesFromRow(row)
      : generalValuesFromRow({ ...row, WL: "—" }, { decimalPlaces: 1 })
  return { id, isLive: false, game: label, values }
}

function findCareerDataset(
  career: Record<string, unknown>[],
  ...keys: string[]
): Record<string, unknown> | undefined {
  const wanted = new Set(keys)
  return career.find((r) => wanted.has(String(r.dataset ?? "")))
}

export function mapPlayerCareerToRows(
  career: Record<string, unknown>[],
  tab: GameLogTab,
): { rows: GameLogRow[]; averages: Record<string, string | number> } {
  const regTotals = findCareerDataset(
    career,
    CAREER_REG_TOTALS_DS,
    "CareerTotalsRegularSeason",
  )
  const poTotals = findCareerDataset(
    career,
    CAREER_PO_TOTALS_DS,
    "CareerTotalsPostSeason",
  )

  const rows: GameLogRow[] = []
  if (regTotals) {
    rows.push(
      mapCareerSummaryRow(
        "career-reg-avg",
        "Career averages",
        careerAverageRow(regTotals),
        tab,
      ),
    )
    rows.push(mapCareerSummaryRow("career-reg-tot", "Career totals", regTotals, tab))
  }
  if (poTotals && parseCareerNumber(pick(poTotals, "GP"))) {
    rows.push(
      mapCareerSummaryRow(
        "career-po-avg",
        "Playoff career averages",
        careerAverageRow(poTotals),
        tab,
      ),
    )
    rows.push(mapCareerSummaryRow("career-po-tot", "Playoff career totals", poTotals, tab))
  }

  const regAvgRow = regTotals ? careerAverageRow(regTotals) : null
  const averages = regAvgRow
    ? tab === "advanced"
      ? advancedValuesFromRow(regAvgRow)
      : generalValuesFromRow({ ...regAvgRow, WL: "—" }, { decimalPlaces: 1 })
    : {}

  return { rows, averages }
}

const PER36_KEYS = [
  "pts",
  "fgm",
  "fga",
  "fg3m",
  "fg3a",
  "ftm",
  "fta",
  "oreb",
  "dreb",
  "reb",
  "ast",
  "stl",
  "blk",
  "tov",
  "pf",
] as const

function scaleCountingStats(
  values: Record<string, string | number>,
  scale: number,
): Record<string, string | number> {
  const out: Record<string, string | number> = {}
  for (const key of PER36_KEYS) {
    const raw = values[key]
    const n = typeof raw === "number" ? raw : parseFloat(String(raw))
    out[key] = Number.isNaN(n) ? "—" : (n * scale).toFixed(1)
  }
  return out
}

export function per36ValuesFromGeneral(values: Record<string, string | number>): Record<string, string | number> {
  const min = parseMinutes(values.min)
  if (min <= 0) return scaleCountingStats(values, 0)
  return scaleCountingStats(values, 36 / min)
}

export function per100ValuesFromGeneral(
  values: Record<string, string | number>,
  pace: number,
): Record<string, string | number> {
  const min = parseMinutes(values.min)
  if (min <= 0 || pace <= 0) return scaleCountingStats(values, 0)
  const scale = (48 * 100) / (min * pace)
  return scaleCountingStats(values, scale)
}

function avgNumeric(values: Record<string, string | number>[], key: string, decimals = 1): string {
  const nums = values
    .map((v) => (typeof v[key] === "number" ? v[key] : parseFloat(String(v[key]))))
    .filter((n) => !Number.isNaN(n))
  if (!nums.length) return "—"
  const avg = nums.reduce((a, b) => a + b, 0) / nums.length
  return avg.toFixed(decimals)
}

export function averagesFromGameLogRows(
  rows: GameLogRow[],
  tab: GameLogTab,
): Record<string, string | number> {
  if (!rows.length) return {}
  if (tab === "general") {
    const vals = rows.map((r) => r.values)
    const fgm = avgNumeric(vals, "fgm", 1)
    const fga = avgNumeric(vals, "fga", 1)
    const fg3m = avgNumeric(vals, "fg3m", 1)
    const fg3a = avgNumeric(vals, "fg3a", 1)
    const ftm = avgNumeric(vals, "ftm", 1)
    const fta = avgNumeric(vals, "fta", 1)
    const wins = vals.filter((v) => v.wl === "W").length
    const losses = vals.filter((v) => v.wl === "L").length
    return {
      wl: wins + losses > 0 ? `${wins}-${losses}` : "—",
      min: avgNumeric(vals, "min", 1),
      pts: avgNumeric(vals, "pts", 1),
      fgm,
      fga,
      fg_pct: calcShootingPct(parseFloat(fgm), parseFloat(fga)),
      fg3m,
      fg3a,
      fg3_pct: calcShootingPct(parseFloat(fg3m), parseFloat(fg3a)),
      ftm,
      fta,
      ft_pct: calcShootingPct(parseFloat(ftm), parseFloat(fta)),
      oreb: avgNumeric(vals, "oreb", 1),
      dreb: avgNumeric(vals, "dreb", 1),
      reb: avgNumeric(vals, "reb", 1),
      ast: avgNumeric(vals, "ast", 1),
      stl: avgNumeric(vals, "stl", 1),
      blk: avgNumeric(vals, "blk", 1),
      tov: avgNumeric(vals, "tov", 1),
      pf: avgNumeric(vals, "pf", 1),
      plus_minus: avgNumeric(vals, "plus_minus", 1),
    }
  }
  if (tab === "advanced") {
    const vals = rows.map((r) => r.values)
    return {
      off_rtg: avgNumeric(vals, "off_rtg", 1),
      def_rtg: avgNumeric(vals, "def_rtg", 1),
      net_rtg: avgNumeric(vals, "net_rtg", 1),
      ts_pct: avgNumeric(vals, "ts_pct", 3),
      efg_pct: avgNumeric(vals, "efg_pct", 3),
      usg_pct: avgNumeric(vals, "usg_pct", 3),
      pie: avgNumeric(vals, "pie", 3),
      pace: avgNumeric(vals, "pace", 1),
      ast_pct: avgNumeric(vals, "ast_pct", 3),
      ast_to: avgNumeric(vals, "ast_to", 2),
      ast_ratio: avgNumeric(vals, "ast_ratio", 1),
      oreb_pct: avgNumeric(vals, "oreb_pct", 3),
      dreb_pct: avgNumeric(vals, "dreb_pct", 3),
      reb_pct: avgNumeric(vals, "reb_pct", 3),
      tov_pct: avgNumeric(vals, "tov_pct", 3),
    }
  }
  if (tab === "per36") {
    return per36ValuesFromGeneral(averagesFromGameLogRows(rows, "general"))
  }
  if (tab === "per100") {
    const generalAvgs = averagesFromGameLogRows(rows, "general")
    const advAvgs = averagesFromGameLogRows(rows, "advanced")
    const pace = parseFloat(String(advAvgs.pace ?? "100"))
    return per100ValuesFromGeneral(generalAvgs, pace > 0 ? pace : 100)
  }
  return {}
}

export function mapSeasonStatsToAverages(
  row: Record<string, unknown> | null,
  tab: GameLogTab,
): Record<string, string | number> {
  if (!row) return {}
  if (tab === "general") {
    return generalValuesFromRow(row, { decimalPlaces: 1 })
  }
  if (tab === "advanced") {
    return advancedValuesFromRow(row)
  }
  if (tab === "per36") {
    return per36ValuesFromGeneral(generalValuesFromRow(row))
  }
  if (tab === "per100") {
    const pace = parseFloat(String(pick(row, "PACE", "pace", "pacePer40") ?? "100"))
    return per100ValuesFromGeneral(generalValuesFromRow(row), pace > 0 ? pace : 100)
  }
  return {}
}

export function mapSeasonStatsToBubbles(row: Record<string, unknown> | null): SeasonBubbleSet | null {
  const g = mapSeasonStatsToAverages(row, "general")
  const a = mapSeasonStatsToAverages(row, "advanced")
  const p36 = mapSeasonStatsToAverages(row, "per36")
  const p100 = mapSeasonStatsToAverages(row, "per100")
  if (!row) return null
  return {
    pts: String(g.pts ?? "—"),
    fg: `${g.fgm}/${g.fga}`,
    fgPct: String(g.fg_pct ?? "—"),
    fg3: `${g.fg3m}/${g.fg3a}`,
    fg3Pct: String(g.fg3_pct ?? "—"),
    ft: `${g.ftm}/${g.fta}`,
    ftPct: String(g.ft_pct ?? "—"),
    reb: String(g.reb ?? "—"),
    oreb: String(g.oreb ?? "—"),
    dreb: String(g.dreb ?? "—"),
    ast: String(g.ast ?? "—"),
    tov: String(g.tov ?? "—"),
    pf: String(g.pf ?? "—"),
    stl: String(g.stl ?? "—"),
    blk: String(g.blk ?? "—"),
    plusMinus: String(g.plus_minus ?? "—"),
    tsPct: String(a.ts_pct ?? "—"),
    efgPct: String(a.efg_pct ?? "—"),
    usgPct: String(a.usg_pct ?? "—"),
    astPct: String(a.ast_pct ?? "—"),
    astToTov: String(a.ast_to ?? "—"),
    orebPct: String(a.oreb_pct ?? "—"),
    drebPct: String(a.dreb_pct ?? "—"),
    pie: String(a.pie ?? "—"),
    per36Pts: String(p36.pts ?? "—"),
    per36Reb: String(p36.reb ?? "—"),
    per36Ast: String(p36.ast ?? "—"),
    per36Stl: String(p36.stl ?? "—"),
    per36Blk: String(p36.blk ?? "—"),
    per36Tov: String(p36.tov ?? "—"),
    per100Pts: String(p100.pts ?? "—"),
    per100Reb: String(p100.reb ?? "—"),
    per100Ast: String(p100.ast ?? "—"),
    per100Stl: String(p100.stl ?? "—"),
    per100Blk: String(p100.blk ?? "—"),
    per100Tov: String(p100.tov ?? "—"),
    contestedShots: num(pick(row, "hustle_contestedShots", "HUSTLE_CONTESTEDSHOTS"), 1),
    contestedShots2pt: num(pick(row, "hustle_contestedShots2pt"), 1),
    contestedShots3pt: num(pick(row, "hustle_contestedShots3pt"), 1),
    deflections: num(pick(row, "hustle_deflections"), 1),
    screenAssists: num(pick(row, "hustle_screenAssists"), 1),
    screenAssistPoints: num(pick(row, "hustle_screenAssistPoints"), 1),
    boxOuts: num(pick(row, "hustle_boxOuts"), 1),
    offensiveBoxOuts: num(pick(row, "hustle_offensiveBoxOuts"), 1),
    defensiveBoxOuts: num(pick(row, "hustle_defensiveBoxOuts"), 1),
    looseBallsRecoveredTotal: num(pick(row, "hustle_looseBallsRecoveredTotal"), 1),
    looseBallsRecoveredOffensive: num(pick(row, "hustle_looseBallsRecoveredOffensive"), 1),
    looseBallsRecoveredDefensive: num(pick(row, "hustle_looseBallsRecoveredDefensive"), 1),
    chargesDrawn: num(pick(row, "hustle_chargesDrawn"), 1),
    boxOutPlayerTeamRebounds: num(pick(row, "hustle_boxOutPlayerTeamRebounds"), 1),
    boxOutPlayerRebounds: num(pick(row, "hustle_boxOutPlayerRebounds"), 1),
    minutes: String(g.min ?? "—"),
  }
}

export function mapTeamGameLogRow(row: Record<string, unknown>, index: number): TeamSeasonGameRow {
  const gameDate = String(pick(row, "GAME_DATE") ?? "")
  const matchup = String(pick(row, "MATCHUP") ?? "")
  const gameId = String(pick(row, "GAME_ID") ?? index)
  const values = generalValuesFromRow(row)
  return {
    id: `tgl-${gameId}`,
    game: gameDate ? `${gameDate.slice(5).replace("-", "/")} ${matchup}` : matchup,
    isLive: false,
    values,
  }
}
