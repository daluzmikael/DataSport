import type { GameDetailView } from "../types"
import type { TeamBoxRow } from "./schema/teamBox"

/**
 * Module-level snapshot of real `/api/live` data, filled by `useLiveBoard`.
 * Kept import-free (types only) so liveState.ts can read it without import cycles.
 * Empty until the API answers.
 */

export interface LiveNextGameLabel {
  label: string
  when: string
}

const gameDetails = new Map<string, GameDetailView>()
const boxRows = new Map<string, Record<string, { general: TeamBoxRow[]; advanced: TeamBoxRow[] }>>()
const teamTotals = new Map<string, Record<string, Record<string, Record<string, unknown>>>>()
const nextGames = new Map<string, LiveNextGameLabel>()
const liveTeams = new Set<string>()
const liveTeamsToday = new Set<string>()
let loaded = false

export function isLiveDataLoaded(): boolean {
  return loaded
}

export function markLiveDataLoaded(): void {
  loaded = true
}

export function registerLiveGameDetail(
  detail: GameDetailView,
  rows?: Record<string, { general: TeamBoxRow[]; advanced: TeamBoxRow[] }>,
  totals?: Record<string, Record<string, Record<string, unknown>>>,
): void {
  gameDetails.set(detail.id, detail)
  if (rows) boxRows.set(detail.id, rows)
  if (totals) teamTotals.set(detail.id, totals)
}

/** Real team totals row (`{general, advanced}` values) for the scoreboard stats strip. */
export function getLiveTeamTotals(
  overlayId: string,
  teamAbbr: string,
  tab: string,
): Record<string, string | number> | undefined {
  const t = teamTotals.get(overlayId)?.[teamAbbr.toUpperCase()]
  if (!t) return undefined
  return (tab === "advanced" ? t.advanced : t.general) as Record<string, string | number>
}

export function getLiveGameDetail(overlayId: string): GameDetailView | undefined {
  return gameDetails.get(overlayId)
}

/** Real box rows for a live/final game (`undefined` → caller uses its mock rows). */
export function getLiveBoxRows(
  overlayId: string,
  teamAbbr: string,
  tab: string,
): TeamBoxRow[] | undefined {
  const team = boxRows.get(overlayId)?.[teamAbbr.toUpperCase()]
  if (!team) return undefined
  return tab === "advanced" ? team.advanced : team.general
}

export function setLivePlayerNextGame(ids: string[], next: LiveNextGameLabel | null): void {
  for (const id of ids) {
    if (next) nextGames.set(id, next)
    else nextGames.delete(id)
  }
}

export function getLivePlayerNextGame(playerId: string): LiveNextGameLabel | undefined {
  return nextGames.get(playerId)
}

export function setLiveTeams(liveNow: string[], playingToday: string[]): void {
  liveTeams.clear()
  liveTeamsToday.clear()
  liveNow.forEach((t) => liveTeams.add(t.toUpperCase()))
  playingToday.forEach((t) => liveTeamsToday.add(t.toUpperCase()))
}

/** `undefined` until real data is loaded. */
export function isTeamLiveNow(abbr: string): boolean | undefined {
  return loaded ? liveTeams.has(abbr.toUpperCase()) : undefined
}

export function isTeamPlayingToday(abbr: string): boolean | undefined {
  return loaded ? liveTeamsToday.has(abbr.toUpperCase()) : undefined
}
