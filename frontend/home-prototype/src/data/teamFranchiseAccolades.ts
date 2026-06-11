import { BOS_FRANCHISE_HISTORY } from "./bosFranchiseHistory"
import type { TeamFranchiseAccolades, TeamHistorySeason } from "../types"

export function sumHistoryRecord(history: TeamHistorySeason[]): { wins: number; losses: number } {
  return history.reduce(
    (acc, row) => {
      const [w, l] = row.wl.split("-").map(Number)
      return { wins: acc.wins + w, losses: acc.losses + l }
    },
    { wins: 0, losses: 0 },
  )
}

export function formatAllTimeRecord(wins: number, losses: number): string {
  return `${wins.toLocaleString("en-US")}-${losses.toLocaleString("en-US")}`
}

function recordFromHistory(history: TeamHistorySeason[]): string {
  const { wins, losses } = sumHistoryRecord(history)
  return formatAllTimeRecord(wins, losses)
}

/** Real franchise milestones · regular-season record derived from season history mock */
export const BOS_FRANCHISE_ACCOLADES: TeamFranchiseAccolades = {
  allTimeRecord: recordFromHistory(BOS_FRANCHISE_HISTORY),
  championships: 18,
  conferenceTitles: 23,
  lastChampionship: "2023-24",
  lastPlayoffs: "2024-25",
  founded: "1946",
  yearsInAssociation: BOS_FRANCHISE_HISTORY.length,
}

export function accoladesFromHistory(
  history: TeamHistorySeason[],
  overrides?: Partial<TeamFranchiseAccolades>,
): TeamFranchiseAccolades {
  const { wins, losses } = sumHistoryRecord(history)
  const winPct = wins / (wins + losses)
  return {
    allTimeRecord: formatAllTimeRecord(wins, losses),
    championships: overrides?.championships ?? Math.max(0, Math.round(winPct * 6)),
    conferenceTitles: overrides?.conferenceTitles ?? Math.max(0, Math.round(winPct * 10)),
    lastChampionship: overrides?.lastChampionship ?? history.at(-2)?.season ?? "—",
    lastPlayoffs: overrides?.lastPlayoffs ?? history.at(-1)?.season ?? "—",
    founded: overrides?.founded ?? "1946",
    yearsInAssociation: overrides?.yearsInAssociation ?? history.length,
  }
}
