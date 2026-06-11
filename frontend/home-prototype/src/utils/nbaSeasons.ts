/** Matches backend ingestion.config START_SEASON / END_SEASON. */
export const NBA_START_SEASON = "1996-97"
export const NBA_END_SEASON = "2025-26"

/** Build NBA season labels newest-first, e.g. 2025 → "2025-26", 1996 → "1996-97". */
export function buildNbaSeasonList(startYear = 1996, endYear = 2025): string[] {
  const seasons: string[] = []
  for (let year = endYear; year >= startYear; year--) {
    const suffix = String((year + 1) % 100).padStart(2, "0")
    seasons.push(`${year}-${suffix}`)
  }
  return seasons
}

/** Full supported range when vault season list is unavailable. */
export const FALLBACK_NBA_SEASONS = buildNbaSeasonList(1996, 2025)
