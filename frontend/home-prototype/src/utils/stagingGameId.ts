/** Overlay id from game log row → 10-digit NBA game_id, or null for mock games. */
export function parseStagingGameId(overlayGameId: string): string | null {
  const match = /^game-(\d{10})$/.exec(overlayGameId)
  return match ? match[1] : null
}

export function stagingGameOverlayId(nbaGameId: string): string {
  const digits = nbaGameId.replace(/\D/g, "").padStart(10, "0")
  return `game-${digits}`
}

/** Season label encoded in an NBA game id.
 *
 * `0022300123` decomposes as `00` + season-type digit + two-digit season start year +
 * a five-digit game number, so `23` means the 2023-24 season. This is how a game view
 * knows which season slice to read without threading it through every prop.
 */
export function seasonFromGameId(gameId: string): string | null {
  const digits = gameId.replace(/\D/g, "").padStart(10, "0")
  if (digits.length !== 10) return null
  const yy = Number(digits.slice(3, 5))
  if (!Number.isFinite(yy)) return null
  // Season ids run 96..99 for the 1990s and 00..~50 for 2000 onward.
  const startYear = yy >= 90 ? 1900 + yy : 2000 + yy
  const endYY = String((startYear + 1) % 100).padStart(2, "0")
  return `${startYear}-${endYY}`
}
