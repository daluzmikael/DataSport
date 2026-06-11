import type { GameLogTab } from "../data/playerGameLogMock"
import type { TeamBoxRow } from "../data/teamBoxScoreMock"
import type { GameDetailView, LineScore } from "../types"
import { stagingGameOverlayId } from "../utils/stagingGameId"
import {
  advancedValuesFromRow,
  formatShortGameDate,
  generalValuesFromRow,
  mapPlayerGameLogAdvancedRow,
  mapPlayerGameLogRow,
} from "./mappers"

export interface StagingGameSummary {
  gameId: string
  gameDateLabel: string
  status: string
  away: { abbr: string; score: number; wl: string; line: LineScore }
  home: { abbr: string; score: number; wl: string; line: LineScore }
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

function lineFromApi(line: Record<string, unknown> | undefined): LineScore {
  if (!line) return { q1: 0, q2: 0, q3: 0 }
  const out: LineScore = {
    q1: Number(line.q1 ?? 0),
    q2: Number(line.q2 ?? 0),
    q3: Number(line.q3 ?? 0),
  }
  if (line.q4 != null) out.q4 = Number(line.q4)
  return out
}

export function mapStagingGameSummary(row: Record<string, unknown>): StagingGameSummary {
  const away = (row.away ?? {}) as Record<string, unknown>
  const home = (row.home ?? {}) as Record<string, unknown>
  return {
    gameId: String(row.game_id ?? ""),
    gameDateLabel: formatShortGameDate(row.game_date),
    status: String(row.status ?? "Final"),
    away: {
      abbr: String(away.abbr ?? ""),
      score: Number(away.score ?? 0),
      wl: String(away.wl ?? "—"),
      line: lineFromApi(away.line as Record<string, unknown>),
    },
    home: {
      abbr: String(home.abbr ?? ""),
      score: Number(home.score ?? 0),
      wl: String(home.wl ?? "—"),
      line: lineFromApi(home.line as Record<string, unknown>),
    },
  }
}

export function mapBoxScorePlayerRow(
  row: Record<string, unknown>,
  index: number,
  tab: GameLogTab,
): TeamBoxRow {
  const playerId = String(pick(row, "PLAYER_ID", "player_id") ?? index)
  const mapped =
    tab === "advanced" ? mapPlayerGameLogAdvancedRow(row, index) : mapPlayerGameLogRow(row, index)
  const name = String(pick(row, "PLAYER_NAME", "player_name") ?? "—")
  const values =
    tab === "advanced"
      ? { ...mapped.values }
      : { wl: "—", ...mapped.values }

  return {
    id: `nba-${playerId}`,
    player: name,
    values,
  }
}

export function mapTeamGameTotals(
  row: Record<string, unknown>,
  tab: GameLogTab,
): Record<string, string | number> {
  if (tab === "advanced") {
    return advancedValuesFromRow(row)
  }
  const g = generalValuesFromRow(row)
  return { wl: String(pick(row, "WL", "wl") ?? "—"), ...g }
}

export function resolveBoxScorePlayerId(rowId: string): string | null {
  const match = /^nba-(\d+)$/.exec(rowId)
  return match ? match[1] : null
}

export function stagingSummaryToGameDetail(
  summary: StagingGameSummary,
): GameDetailView {
  return {
    id: stagingGameOverlayId(summary.gameId),
    kind: "other-live",
    away: {
      abbr: summary.away.abbr,
      name: summary.away.abbr,
      score: summary.away.score,
      line: summary.away.line,
    },
    home: {
      abbr: summary.home.abbr,
      name: summary.home.abbr,
      score: summary.home.score,
      line: summary.home.line,
    },
    period: summary.status,
    clock: "",
    isLive: false,
    possession: "away",
    homeTimeouts: 0,
    awayTimeouts: 0,
    homeTeamFouls: 0,
    awayTeamFouls: 0,
    homeGameStats: { fg: "—", fg3: "—", ft: "—", reb: 0, ast: 0, tov: 0, pf: 0 },
    awayGameStats: { fg: "—", fg3: "—", ft: "—", reb: 0, ast: 0, tov: 0, pf: 0 },
    topScorers: [],
    topAssists: [],
    topRebounds: [],
  }
}
