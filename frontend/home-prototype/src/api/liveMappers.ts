import type { TeamBoxRow } from "../data/schema/teamBox"
import type {
  CompactGame,
  GameDetailView,
  LeaderLine,
  LineScore,
  PlayerLive,
  TeamGameLive,
  TeamGameStatsLine,
} from "../types"
import { stagingGameOverlayId } from "../utils/stagingGameId"
import { mapBoxScorePlayerRow, mapTeamGameTotals } from "./gameMappers"
import type {
  LiveBoxLeader,
  LiveBoxScore,
  LiveBoxTeam,
  LiveGame,
  LiveNextGame,
  LivePlayerLine,
  LiveTrackedPlayer,
} from "./liveClient"
import { stubPlayerForStaging } from "./mappers"

export function liveOverlayId(gameId: string): string {
  return stagingGameOverlayId(gameId)
}

function lineScore(periods: number[]): LineScore {
  const [q1 = 0, q2 = 0, q3 = 0, q4, ...ot] = periods
  const out: LineScore = { q1, q2, q3 }
  if (q4 != null) out.q4 = q4 + ot.reduce((a, b) => a + b, 0)
  return out
}

/** Period label shown on cards: "Final", "Q3", or the tip time for scheduled games. */
function periodFor(game: LiveGame): string {
  if (game.state === "final") return game.periodText || "Final"
  if (game.state === "live") return game.periodText || "Live"
  return game.statusText || "Scheduled"
}

function pct(made: number, att: number): string {
  if (!att) return "—"
  const v = made / att
  return v >= 1 ? "1.000" : `.${Math.round(v * 1000).toString().padStart(3, "0")}`
}

function teamStatsLine(t: LiveBoxTeam): TeamGameStatsLine {
  const s = t.statistics
  const n = (k: string) => Number(s[k] ?? 0)
  return {
    fg: `${n("fgm")}/${n("fga")}`,
    fg3: `${n("fg3m")}/${n("fg3a")}`,
    ft: `${n("ftm")}/${n("fta")}`,
    reb: n("reb"),
    ast: n("ast"),
    tov: n("tov"),
    pf: n("pf"),
  }
}

function leaderLines(rows: LiveBoxLeader[]): LeaderLine[] {
  return rows.map((r) => ({ name: r.familyName || r.name, value: r.value }))
}

export function boxToGameDetail(box: LiveBoxScore, followed: boolean): GameDetailView {
  const { game, teams, leaders } = box
  const base = {
    id: liveOverlayId(game.gameId),
    home: { abbr: teams.home.tricode, name: teams.home.name, score: teams.home.score, line: lineScore(teams.home.periods) },
    away: { abbr: teams.away.tricode, name: teams.away.name, score: teams.away.score, line: lineScore(teams.away.periods) },
    period: periodFor(game),
    clock: game.clock,
    isLive: game.state === "live",
    possession: "home" as const,
    homeTimeouts: teams.home.timeoutsRemaining ?? 0,
    awayTimeouts: teams.away.timeoutsRemaining ?? 0,
    homeTeamFouls: Number(teams.home.statistics.teamFouls ?? 0),
    awayTeamFouls: Number(teams.away.statistics.teamFouls ?? 0),
    homeGameStats: teamStatsLine(teams.home),
    awayGameStats: teamStatsLine(teams.away),
    topScorers: leaderLines(leaders.points),
    topAssists: leaderLines(leaders.assists),
    topRebounds: leaderLines(leaders.rebounds),
  }
  return followed
    ? ({ ...base, kind: "followed-team" } satisfies TeamGameLive)
    : { ...base, kind: "other-live" }
}

/** Minimal detail from a scoreboard/schedule row (no box score available). */
export function gameToDetail(game: LiveGame, followed: boolean): GameDetailView {
  const top = (side: "home" | "away") => game.leaders[side]
  const pts: LeaderLine[] = []
  const reb: LeaderLine[] = []
  const ast: LeaderLine[] = []
  for (const side of ["away", "home"] as const) {
    const l = top(side)
    if (!l) continue
    const name = l.name.split(" ").slice(-1)[0] || l.name
    if (l.points != null) pts.push({ name, value: l.points })
    if (l.rebounds != null) reb.push({ name, value: l.rebounds })
    if (l.assists != null) ast.push({ name, value: l.assists })
  }
  if (!pts.length && game.pointsLeader) {
    pts.push({ name: game.pointsLeader.name.split(" ").slice(-1)[0], value: game.pointsLeader.points })
  }
  const empty: TeamGameStatsLine = { fg: "—", fg3: "—", ft: "—", reb: 0, ast: 0, tov: 0, pf: 0 }
  const base = {
    id: liveOverlayId(game.gameId),
    home: { abbr: game.home.tricode, name: game.home.name, score: game.home.score, line: lineScore(game.home.periods) },
    away: { abbr: game.away.tricode, name: game.away.name, score: game.away.score, line: lineScore(game.away.periods) },
    period: periodFor(game),
    clock: game.clock,
    isLive: game.state === "live",
    possession: "home" as const,
    homeTimeouts: game.home.timeoutsRemaining ?? 0,
    awayTimeouts: game.away.timeoutsRemaining ?? 0,
    homeTeamFouls: 0,
    awayTeamFouls: 0,
    homeGameStats: empty,
    awayGameStats: empty,
    topScorers: pts.sort((a, b) => b.value - a.value),
    topAssists: ast.sort((a, b) => b.value - a.value),
    topRebounds: reb.sort((a, b) => b.value - a.value),
  }
  return followed ? { ...base, kind: "followed-team" } : { ...base, kind: "other-live" }
}

export function gameToCompact(game: LiveGame, followed: boolean): CompactGame {
  return {
    id: liveOverlayId(game.gameId),
    kind: "other-live",
    awayAbbr: game.away.tricode,
    homeAbbr: game.home.tricode,
    awayScore: game.away.score,
    homeScore: game.home.score,
    period: periodFor(game),
    clock: game.clock,
    state: game.state,
    followed,
  }
}

function boxRecord(p: LivePlayerLine): Record<string, unknown> {
  return {
    PLAYER_ID: p.personId,
    PLAYER_NAME: p.name,
    TEAM_ABBREVIATION: p.teamTricode,
    MIN: p.minutes,
    PTS: p.pts,
    FGM: p.fgm,
    FGA: p.fga,
    FG3M: p.fg3m,
    FG3A: p.fg3a,
    FTM: p.ftm,
    FTA: p.fta,
    OREB: p.oreb,
    DREB: p.dreb,
    REB: p.reb,
    AST: p.ast,
    STL: p.stl,
    BLK: p.blk,
    TOV: p.tov,
    PF: p.pf,
    PLUS_MINUS: p.plusMinus,
  }
}

function dnpRow(p: LivePlayerLine): TeamBoxRow {
  return { id: `nba-${p.personId}`, player: p.name, isDnp: true, values: { min: "DNP" } }
}

/** Box rows per team tricode in the shape TeamBoxScoreTable renders. */
export function boxToRows(
  box: LiveBoxScore,
): Record<string, { general: TeamBoxRow[]; advanced: TeamBoxRow[] }> {
  const out: Record<string, { general: TeamBoxRow[]; advanced: TeamBoxRow[] }> = {}
  for (const side of ["home", "away"] as const) {
    const t = box.teams[side]
    const played = t.players.filter((p) => p.played)
    const sat = t.players.filter((p) => !p.played)
    out[t.tricode] = {
      general: [
        ...played.map((p, i) => mapBoxScorePlayerRow(boxRecord(p), i, "general")),
        ...sat.map(dnpRow),
      ],
      advanced: [
        ...played.map((p, i) => mapBoxScorePlayerRow(boxRecord(p), i, "advanced")),
        ...sat.map(dnpRow),
      ],
    }
  }
  return out
}

function gameScore(p: LivePlayerLine): number {
  const gs =
    p.pts +
    0.4 * p.fgm -
    0.7 * p.fga -
    0.4 * (p.fta - p.ftm) +
    0.7 * p.oreb +
    0.3 * p.dreb +
    p.stl +
    0.7 * p.ast +
    0.7 * p.blk -
    0.4 * p.pf -
    p.tov
  return Math.round(gs * 10) / 10
}

/** Live/final box line for a followed player → PlayerLive card row. */
export function trackedToPlayerLive(
  favoriteId: string,
  tracked: LiveTrackedPlayer,
  seasonAvgGameScore?: number,
): PlayerLive | null {
  const l = tracked.line
  if (!l) return null
  const base = stubPlayerForStaging(String(l.personId), l.name, l.teamTricode)
  const tsa = l.fga + 0.44 * l.fta
  return {
    ...base,
    id: favoriteId,
    gameId: liveOverlayId(l.gameId),
    teamAbbr: l.teamTricode,
    opponentAbbr: l.opponentTricode,
    minutes: l.minutes,
    status: l.oncourt ? "on court" : "bench",
    period: l.state === "final" ? "Final" : l.periodText,
    clock: l.state === "final" ? shortDate(l.date) : l.clock,
    pts: l.pts,
    fg: `${l.fgm}/${l.fga}`,
    fgPct: pct(l.fgm, l.fga),
    fg3: `${l.fg3m}/${l.fg3a}`,
    fg3Pct: pct(l.fg3m, l.fg3a),
    ft: `${l.ftm}/${l.fta}`,
    ftPct: pct(l.ftm, l.fta),
    oreb: l.oreb,
    dreb: l.dreb,
    reb: l.reb,
    ast: l.ast,
    tov: l.tov,
    stl: l.stl,
    blk: l.blk,
    pf: l.pf,
    plusMinus: l.plusMinus > 0 ? `+${l.plusMinus}` : String(l.plusMinus),
    gameScore: gameScore(l),
    seasonAvgGameScore: seasonAvgGameScore ?? 0,
    tsPct: tsa ? pct(l.pts, 2 * tsa) : "—",
    efgPct: l.fga ? pct(l.fgm + 0.5 * l.fg3m, l.fga) : "—",
    astToTov: l.tov ? (l.ast / l.tov).toFixed(2) : "—",
  }
}

const WEEKDAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
const MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

function parseIsoDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number)
  return new Date(Date.UTC(y, m - 1, d))
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return ""
  const d = parseIsoDate(iso)
  return `${MONTH[d.getUTCMonth()]} ${d.getUTCDate()}`
}

/** "Yesterday", "Sun, Oct 11", … relative to the NBA "today" date. */
export function dayLabel(iso: string, todayIso: string): string {
  const diff = Math.round((parseIsoDate(todayIso).getTime() - parseIsoDate(iso).getTime()) / 86_400_000)
  if (diff === 0) return "Today"
  if (diff === 1) return "Yesterday"
  if (diff === -1) return "Tomorrow"
  const d = parseIsoDate(iso)
  return `${WEEKDAY[d.getUTCDay()]}, ${shortDate(iso)}`
}

export function nextGameLabel(next: LiveNextGame, todayIso: string): { label: string; when: string } {
  const day = dayLabel(next.date, todayIso)
  const time = next.statusText.replace(/\bpm\b/i, "PM").replace(/\bam\b/i, "AM")
  return {
    label: `${next.isHome ? "vs" : "@"} ${next.opponent}`,
    when: `${day === "Today" ? "Tonight" : day} · ${time}`,
  }
}

/** Team totals per tricode, mapped like vault team game rows (general/advanced tabs). */
export function boxToTeamTotals(
  box: LiveBoxScore,
): Record<string, Record<string, Record<string, unknown>>> {
  const out: Record<string, Record<string, Record<string, unknown>>> = {}
  for (const [side, other] of [["home", "away"], ["away", "home"]] as const) {
    const t = box.teams[side]
    const s = t.statistics
    const record: Record<string, unknown> = {
      TEAM_ABBREVIATION: t.tricode,
      WL: box.game.state === "final" ? (t.score > box.teams[other].score ? "W" : "L") : "—",
      MIN: 240,
      PTS: t.score,
      FGM: s.fgm,
      FGA: s.fga,
      FG3M: s.fg3m,
      FG3A: s.fg3a,
      FTM: s.ftm,
      FTA: s.fta,
      OREB: s.oreb,
      DREB: s.dreb,
      REB: s.reb,
      AST: s.ast,
      STL: s.stl,
      BLK: s.blk,
      TOV: s.tov,
      PF: s.pf,
      PLUS_MINUS: t.score - box.teams[other].score,
    }
    out[t.tricode] = {
      general: mapTeamGameTotals(record, "general"),
      advanced: mapTeamGameTotals(record, "advanced"),
    }
  }
  return out
}
