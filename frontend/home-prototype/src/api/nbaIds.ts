/**
 * Resolve any of these to an NBA `player_id` for staging API reads:
 * - `"1628369"` (raw numeric id — works for every player in the vault)
 * - `"nba-1628369"`
 * - `"player-tatum"` (prototype mock aliases below)
 */
export const MOCK_PLAYER_NBA_IDS: Record<string, string> = {
  "player-tatum": "1628369",
  "player-brown": "1627759",
  "player-durant": "201142",
  "player-curry": "201939",
  "player-jokic": "203999",
  "player-embiid": "203954",
  "player-giannis": "203507",
  "player-lebron": "2544",
  "player-luka": "1629029",
  "player-edwards": "1630162",
  "player-booker": "1626164",
  "player-doncic": "1629029",
}

/** Map team abbr → NBA team_id (2024-25). */
export const TEAM_ABBR_TO_NBA_ID: Record<string, string> = {
  ATL: "1610612737",
  BOS: "1610612738",
  BKN: "1610612751",
  CHA: "1610612766",
  CHI: "1610612741",
  CLE: "1610612739",
  DAL: "1610612742",
  DEN: "1610612743",
  DET: "1610612765",
  GSW: "1610612744",
  HOU: "1610612745",
  IND: "1610612754",
  LAC: "1610612746",
  LAL: "1610612747",
  MEM: "1610612763",
  MIA: "1610612748",
  MIL: "1610612749",
  MIN: "1610612750",
  NOP: "1610612740",
  NYK: "1610612752",
  OKC: "1610612760",
  ORL: "1610612753",
  PHI: "1610612755",
  PHX: "1610612756",
  POR: "1610612757",
  SAC: "1610612758",
  SAS: "1610612759",
  TOR: "1610612761",
  UTA: "1610612762",
  WAS: "1610612764",
}

export function resolveNbaPlayerId(id: string): string | null {
  if (/^\d+$/.test(id)) return id
  const nbaPrefixed = /^nba-(\d+)$/.exec(id)
  if (nbaPrefixed) return nbaPrefixed[1]
  return MOCK_PLAYER_NBA_IDS[id] ?? null
}

/** True when game-log table + stat bubbles can load from the staging vault. */
export function hasStagingPlayerId(id: string): boolean {
  return resolveNbaPlayerId(id) != null
}

export function mockPlayerIdFromNba(nbaId: string): string {
  for (const [mockId, id] of Object.entries(MOCK_PLAYER_NBA_IDS)) {
    if (id === nbaId) return mockId
  }
  return `nba-${nbaId}`
}

/** Normalize nba-* / numeric ids to prototype mock ids when mapped. */
export function canonicalMockPlayerId(playerId: string): string {
  const nbaId = resolveNbaPlayerId(playerId)
  return nbaId ? mockPlayerIdFromNba(nbaId) : playerId
}

export function resolveNbaTeamId(teamIdOrAbbr: string): string | null {
  if (/^\d+$/.test(teamIdOrAbbr)) return teamIdOrAbbr
  const abbr = teamIdOrAbbr.replace(/^team-/, "").toUpperCase()
  return TEAM_ABBR_TO_NBA_ID[abbr] ?? null
}

export function teamAbbrFromProfileId(teamId: string): string {
  return teamId.replace(/^team-/, "").toUpperCase()
}
