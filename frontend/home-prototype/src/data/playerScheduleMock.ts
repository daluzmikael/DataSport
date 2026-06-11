export interface PlayerNextGame {
  label: string
  when: string
}

const SCHEDULE: Record<string, PlayerNextGame> = {
  "player-tatum": { label: "vs PHI", when: "Fri · 7:30 PM ET" },
  "player-jokic": { label: "@ MIN", when: "Thu · 9:00 PM ET" },
  "player-embiid": { label: "vs TOR", when: "Sat · 7:00 PM ET" },
}

export function getPlayerNextGame(playerId: string): PlayerNextGame | null {
  return SCHEDULE[playerId] ?? null
}
