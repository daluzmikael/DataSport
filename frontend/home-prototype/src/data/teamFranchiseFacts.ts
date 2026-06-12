import type { TeamFranchiseAccolades } from "../types"

/** Franchise founding year (NBA / BAA) — general reference, not from vault. */
export const TEAM_FRANCHISE_FOUNDED: Record<string, number> = {
  ATL: 1949,
  BOS: 1946,
  BKN: 1967,
  CHA: 1988,
  CHI: 1966,
  CLE: 1970,
  DAL: 1980,
  DEN: 1967,
  DET: 1948,
  GSW: 1946,
  HOU: 1967,
  IND: 1967,
  LAC: 1970,
  LAL: 1947,
  MEM: 1995,
  MIA: 1988,
  MIL: 1968,
  MIN: 1989,
  NOP: 2002,
  NYK: 1946,
  OKC: 1967,
  ORL: 1989,
  PHI: 1949,
  PHX: 1968,
  POR: 1970,
  SAC: 1945,
  SAS: 1967,
  TOR: 1995,
  UTA: 1974,
  WAS: 1961,
}

/** Static franchise milestones (not in vault). Last playoffs/championship on hold for vault ClinchedPlayoffBirth. */
const TEAM_ACCOLADES: Record<
  string,
  Pick<
    TeamFranchiseAccolades,
    "championships" | "conferenceTitles" | "lastChampionship" | "lastPlayoffs"
  >
> = {
  ATL: { championships: 1, conferenceTitles: 1, lastChampionship: "1957-58", lastPlayoffs: "2024-25" },
  BOS: { championships: 18, conferenceTitles: 23, lastChampionship: "2023-24", lastPlayoffs: "2024-25" },
  BKN: { championships: 0, conferenceTitles: 2, lastChampionship: "—", lastPlayoffs: "2024-25" },
  CHA: { championships: 0, conferenceTitles: 0, lastChampionship: "—", lastPlayoffs: "2023-24" },
  CHI: { championships: 6, conferenceTitles: 6, lastChampionship: "1997-98", lastPlayoffs: "2023-24" },
  CLE: { championships: 1, conferenceTitles: 5, lastChampionship: "2015-16", lastPlayoffs: "2024-25" },
  DAL: { championships: 1, conferenceTitles: 2, lastChampionship: "2010-11", lastPlayoffs: "2024-25" },
  DEN: { championships: 1, conferenceTitles: 1, lastChampionship: "2022-23", lastPlayoffs: "2024-25" },
  DET: { championships: 3, conferenceTitles: 7, lastChampionship: "2003-04", lastPlayoffs: "2023-24" },
  GSW: { championships: 7, conferenceTitles: 11, lastChampionship: "2021-22", lastPlayoffs: "2024-25" },
  HOU: { championships: 2, conferenceTitles: 4, lastChampionship: "1994-95", lastPlayoffs: "2023-24" },
  IND: { championships: 0, conferenceTitles: 1, lastChampionship: "—", lastPlayoffs: "2024-25" },
  LAC: { championships: 0, conferenceTitles: 0, lastChampionship: "—", lastPlayoffs: "2024-25" },
  LAL: { championships: 17, conferenceTitles: 19, lastChampionship: "2019-20", lastPlayoffs: "2024-25" },
  MEM: { championships: 0, conferenceTitles: 0, lastChampionship: "—", lastPlayoffs: "2024-25" },
  MIA: { championships: 3, conferenceTitles: 7, lastChampionship: "2012-13", lastPlayoffs: "2024-25" },
  MIL: { championships: 2, conferenceTitles: 3, lastChampionship: "2020-21", lastPlayoffs: "2024-25" },
  MIN: { championships: 0, conferenceTitles: 0, lastChampionship: "—", lastPlayoffs: "2024-25" },
  NOP: { championships: 0, conferenceTitles: 0, lastChampionship: "—", lastPlayoffs: "2024-25" },
  NYK: { championships: 2, conferenceTitles: 4, lastChampionship: "1972-73", lastPlayoffs: "2023-24" },
  OKC: { championships: 1, conferenceTitles: 4, lastChampionship: "1978-79", lastPlayoffs: "2024-25" },
  ORL: { championships: 0, conferenceTitles: 2, lastChampionship: "—", lastPlayoffs: "2023-24" },
  PHI: { championships: 3, conferenceTitles: 5, lastChampionship: "1982-83", lastPlayoffs: "2024-25" },
  PHX: { championships: 0, conferenceTitles: 3, lastChampionship: "—", lastPlayoffs: "2024-25" },
  POR: { championships: 1, conferenceTitles: 3, lastChampionship: "1976-77", lastPlayoffs: "2023-24" },
  SAC: { championships: 1, conferenceTitles: 0, lastChampionship: "1950-51", lastPlayoffs: "2023-24" },
  SAS: { championships: 5, conferenceTitles: 6, lastChampionship: "2013-14", lastPlayoffs: "2023-24" },
  TOR: { championships: 1, conferenceTitles: 1, lastChampionship: "2018-19", lastPlayoffs: "2023-24" },
  UTA: { championships: 0, conferenceTitles: 2, lastChampionship: "—", lastPlayoffs: "2023-24" },
  WAS: { championships: 1, conferenceTitles: 4, lastChampionship: "1977-78", lastPlayoffs: "2023-24" },
}

const DEFAULT_ACCOLADES = {
  championships: 0,
  conferenceTitles: 0,
  lastChampionship: "—" as const,
  lastPlayoffs: "—" as const,
}

/** Seasons in the league through the 2024-25 campaign. */
export function franchiseSeasonsPlayed(abbr: string): number {
  const founded = TEAM_FRANCHISE_FOUNDED[abbr.toUpperCase()]
  if (!founded) return 0
  return 2025 - founded
}

export function franchiseFoundedYear(abbr: string): string {
  const y = TEAM_FRANCHISE_FOUNDED[abbr.toUpperCase()]
  return y != null ? String(y) : "—"
}

export function getTeamFranchiseAccolades(abbr: string): TeamFranchiseAccolades {
  const code = abbr.toUpperCase()
  const staticAccolades = TEAM_ACCOLADES[code] ?? DEFAULT_ACCOLADES
  const founded = franchiseFoundedYear(code)
  const years = franchiseSeasonsPlayed(code)
  return {
    allTimeRecord: "—",
    ...staticAccolades,
    founded: founded !== "—" ? founded : "1946",
    yearsInAssociation: years > 0 ? years : 0,
  }
}
