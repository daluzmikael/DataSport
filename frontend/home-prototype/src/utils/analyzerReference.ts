/** Token inserted into the analyzer draft when referencing a player or team */
export function formatAnalyzerReference(label: string): string {
  return `[${label}]`
}

export function appendAnalyzerReference(draft: string, label: string): string {
  const token = formatAnalyzerReference(label)
  const trimmed = draft.trimEnd()
  if (!trimmed) return `${token} `
  if (trimmed.endsWith(token)) return `${trimmed} `
  return `${trimmed} ${token} `
}

/** Opponent abbreviations from game log labels like "11/28 vs ORL" or "LIVE vs MIA" */
export function teamAbbrsFromGameLabel(game: string): string[] {
  const found: string[] = []
  for (const match of game.matchAll(/(?:vs|@)\s+([A-Z]{2,3})\b/g)) {
    found.push(match[1])
  }
  return found
}
