import type { TeamLeaderStatId, TeamSeasonLeaderEntry } from "../data/teamSeasonLeadersMock"

/** API `stat` query param for `/teams/{id}/leaders`. */
export const TEAM_LEADER_API_STATS: Record<TeamLeaderStatId, string | null> = {
  pts: "PTS",
  reb: "REB",
  ast: "AST",
  stl: "STL",
  blk: "BLK",
  fg3m: "FG3M",
  tov: "TOV",
  min: "MIN",
  fg_pct: "FG_PCT",
  fg3_pct: "FG3_PCT",
  ts_pct: "TS_PCT",
  usg_pct: null,
}

export function leaderApiStat(statId: TeamLeaderStatId): string | null {
  return TEAM_LEADER_API_STATS[statId]
}

function formatPct(value: number): string {
  if (value > 0 && value <= 1) {
    return `.${Math.round(value * 1000)
      .toString()
      .padStart(3, "0")}`
  }
  if (value > 1 && value <= 100) {
    return `.${Math.round(value * 10)
      .toString()
      .padStart(3, "0")}`
  }
  return String(value)
}

export function formatLeaderValue(statId: TeamLeaderStatId, raw: unknown): string | number {
  if (raw == null || raw === "") return "—"
  const n = typeof raw === "number" ? raw : parseFloat(String(raw))
  if (Number.isNaN(n)) return String(raw)
  if (statId === "fg_pct" || statId === "fg3_pct" || statId === "ts_pct") {
    return formatPct(n)
  }
  if (statId === "min") return n.toFixed(1)
  if (statId === "tov" || statId === "stl" || statId === "blk" || statId === "fg3m") {
    return n.toFixed(1)
  }
  return Math.round(n * 10) / 10
}

export function mapLeaderRow(
  statId: TeamLeaderStatId,
  row: Record<string, unknown> | undefined,
): TeamSeasonLeaderEntry {
  if (!row) return { player: "—", value: "—" }
  return {
    player: String(row.PLAYER_NAME ?? row.player_name ?? "—"),
    value: formatLeaderValue(statId, row.value),
  }
}

export function mapLeaderRows(
  statId: TeamLeaderStatId,
  rows: Record<string, unknown>[] | null | undefined,
  limit: number,
): TeamSeasonLeaderEntry[] {
  const mapped = (rows ?? []).slice(0, limit).map((row) => mapLeaderRow(statId, row))
  while (mapped.length < limit) {
    mapped.push({ player: "—", value: "—" })
  }
  return mapped
}
