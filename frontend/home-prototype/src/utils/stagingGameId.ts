/** Overlay id from game log row → 10-digit NBA game_id, or null for mock games. */
export function parseStagingGameId(overlayGameId: string): string | null {
  const match = /^game-(\d{10})$/.exec(overlayGameId)
  return match ? match[1] : null
}

export function stagingGameOverlayId(nbaGameId: string): string {
  const digits = nbaGameId.replace(/\D/g, "").padStart(10, "0")
  return `game-${digits}`
}
