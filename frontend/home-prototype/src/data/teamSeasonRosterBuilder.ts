import type { TeamProfile, TeamRosterPlayer } from "../types"
import { getTeamSeasonOptions } from "./teamSeasonGameLogBuilder"

export { getTeamSeasonOptions }

const POSITIONS = ["G", "G-F", "F", "F-C", "C"] as const

function rosterPlayer(
  id: string,
  name: string,
  position: string,
  number: string,
  height: string,
): TeamRosterPlayer {
  return { id, name, position, number, height }
}

/** Hand-crafted rosters for landmark Celtics seasons */
const BOS_ROSTERS_BY_SEASON: Record<string, TeamRosterPlayer[]> = {
  "2023-24": [
    rosterPlayer("r23-tatum", "Jayson Tatum", "F", "0", "6-8"),
    rosterPlayer("r23-brown", "Jaylen Brown", "G-F", "7", "6-6"),
    rosterPlayer("r23-white", "Derrick White", "G", "9", "6-4"),
    rosterPlayer("r23-holiday", "Jrue Holiday", "G", "4", "6-3"),
    rosterPlayer("r23-horford", "Al Horford", "C-F", "42", "6-9"),
    rosterPlayer("r23-porzingis", "Kristaps Porzingis", "C-F", "8", "7-2"),
    rosterPlayer("r23-hauser", "Sam Hauser", "F", "30", "6-7"),
    rosterPlayer("r23-pritchard", "Payton Pritchard", "G", "11", "6-1"),
    rosterPlayer("r23-kornet", "Luke Kornet", "C-F", "40", "7-1"),
    rosterPlayer("r23-tillman", "Xavier Tillman", "F", "26", "6-8"),
    rosterPlayer("r23-walsh", "Jordan Walsh", "F", "27", "6-6"),
    rosterPlayer("r23-queta", "Neemias Queta", "C", "88", "7-0"),
  ],
  "2007-08": [
    rosterPlayer("r08-pierce", "Paul Pierce", "F", "34", "6-7"),
    rosterPlayer("r08-garnett", "Kevin Garnett", "F", "5", "6-11"),
    rosterPlayer("r08-allen", "Ray Allen", "G", "20", "6-5"),
    rosterPlayer("r08-rondo", "Rajon Rondo", "G", "9", "6-1"),
    rosterPlayer("r08-perkins", "Kendrick Perkins", "C", "43", "6-10"),
    rosterPlayer("r08-house", "Eddie House", "G", "50", "6-1"),
    rosterPlayer("r08-posey", "James Posey", "F", "41", "6-8"),
    rosterPlayer("r08-bigbaby", "Glen Davis", "F", "11", "6-9"),
    rosterPlayer("r08-powe", "Leon Powe", "F", "0", "6-8"),
    rosterPlayer("r08-cassell", "Sam Cassell", "G", "28", "6-3"),
    rosterPlayer("r08-brown", "Tony Allen", "G", "42", "6-4"),
    rosterPlayer("r08-scal", "Brian Scalabrine", "F", "24", "6-9"),
  ],
  "1985-86": [
    rosterPlayer("r86-bird", "Larry Bird", "F", "33", "6-9"),
    rosterPlayer("r86-mchale", "Kevin McHale", "F", "32", "6-10"),
    rosterPlayer("r86-parish", "Robert Parish", "C", "00", "7-0"),
    rosterPlayer("r86-ainge", "Danny Ainge", "G", "30", "6-5"),
    rosterPlayer("r86-johnson", "Dennis Johnson", "G", "3", "6-4"),
    rosterPlayer("r86-lewis", "Reggie Lewis", "F", "35", "6-7"),
    rosterPlayer("r86-wedman", "Scott Wedman", "F", "4", "6-7"),
    rosterPlayer("r86-sichting", "Jerry Sichting", "G", "42", "6-1"),
    rosterPlayer("r86-williams", "Bill Walton", "C", "5", "6-11"),
    rosterPlayer("r86-kite", "Greg Kite", "C", "50", "7-0"),
    rosterPlayer("r86-clark", "Carlos Clark", "G", "15", "6-4"),
    rosterPlayer("r86-roberts", "Fred Roberts", "F", "35", "6-10"),
  ],
  "1965-66": [
    rosterPlayer("r66-russell", "Bill Russell", "C", "6", "6-10"),
    rosterPlayer("r66-havlicek", "John Havlicek", "F-G", "17", "6-5"),
    rosterPlayer("r66-jones-s", "Sam Jones", "G", "24", "6-4"),
    rosterPlayer("r66-cousy", "Bob Cousy", "G", "14", "6-1"),
    rosterPlayer("r66-heinsohn", "Tom Heinsohn", "F", "15", "6-7"),
    rosterPlayer("r66-sanders", "Tom Sanders", "F", "16", "6-6"),
    rosterPlayer("r66-nelson", "Don Nelson", "F", "19", "6-6"),
    rosterPlayer("r66-watts", "Ron Watts", "F", "23", "6-6"),
    rosterPlayer("r66-greer", "Willie Naulls", "F", "12", "6-6"),
    rosterPlayer("r66-melle", "Larry Siegfried", "G", "20", "6-3"),
    rosterPlayer("r66-walton", "Mel Counts", "C", "44", "7-0"),
    rosterPlayer("r66-barnes", "Jim Barnes", "F-C", "30", "6-8"),
  ],
}

type EraPool = { maxYear: number; players: TeamRosterPlayer[] }

const BOS_ERA_POOLS: EraPool[] = [
  {
    maxYear: 1955,
    players: [
      rosterPlayer("e-bob", "Bob Cousy", "G", "14", "6-1"),
      rosterPlayer("e-mac", "Ed Macauley", "C-F", "22", "6-8"),
      rosterPlayer("e-sharman", "Bill Sharman", "G", "21", "6-1"),
      rosterPlayer("e-lovellette", "Clyde Lovellette", "C", "12", "6-9"),
      rosterPlayer("e-heinsohn", "Tom Heinsohn", "F", "15", "6-7"),
    ],
  },
  {
    maxYear: 1970,
    players: [
      rosterPlayer("e-russell", "Bill Russell", "C", "6", "6-10"),
      rosterPlayer("e-havlicek", "John Havlicek", "F-G", "17", "6-5"),
      rosterPlayer("e-jones", "Sam Jones", "G", "24", "6-4"),
      rosterPlayer("e-sanders", "Tom Sanders", "F", "16", "6-6"),
      rosterPlayer("e-nelson", "Don Nelson", "F", "19", "6-6"),
      rosterPlayer("e-siegfried", "Larry Siegfried", "G", "20", "6-3"),
    ],
  },
  {
    maxYear: 1985,
    players: [
      rosterPlayer("e-bird", "Larry Bird", "F", "33", "6-9"),
      rosterPlayer("e-mchale", "Kevin McHale", "F", "32", "6-10"),
      rosterPlayer("e-parish", "Robert Parish", "C", "00", "7-0"),
      rosterPlayer("e-ainge", "Danny Ainge", "G", "30", "6-5"),
      rosterPlayer("e-dj", "Dennis Johnson", "G", "3", "6-4"),
      rosterPlayer("e-max", "Cedric Maxwell", "F", "31", "6-8"),
    ],
  },
  {
    maxYear: 2000,
    players: [
      rosterPlayer("e-pierce", "Paul Pierce", "F", "34", "6-7"),
      rosterPlayer("e-walker", "Antoine Walker", "F", "8", "6-9"),
      rosterPlayer("e-anderson", "Kenny Anderson", "G", "7", "6-1"),
      rosterPlayer("e-fox", "Rick Fox", "F", "44", "6-7"),
      rosterPlayer("e-delk", "Tony Delk", "G", "00", "6-2"),
      rosterPlayer("e-williams", "Derek Anderson", "G", "1", "6-5"),
    ],
  },
  {
    maxYear: 2015,
    players: [
      rosterPlayer("e-pierce2", "Paul Pierce", "F", "34", "6-7"),
      rosterPlayer("e-garnett", "Kevin Garnett", "F", "5", "6-11"),
      rosterPlayer("e-allen", "Ray Allen", "G", "20", "6-5"),
      rosterPlayer("e-rondo", "Rajon Rondo", "G", "9", "6-1"),
      rosterPlayer("e-bradley", "Avery Bradley", "G", "0", "6-2"),
      rosterPlayer("e-iso", "Isaiah Thomas", "G", "4", "5-9"),
    ],
  },
  {
    maxYear: 2099,
    players: [
      rosterPlayer("e-tatum", "Jayson Tatum", "F", "0", "6-8"),
      rosterPlayer("e-brown", "Jaylen Brown", "G-F", "7", "6-6"),
      rosterPlayer("e-white", "Derrick White", "G", "9", "6-4"),
      rosterPlayer("e-horford", "Al Horford", "C-F", "42", "6-9"),
      rosterPlayer("e-smart", "Marcus Smart", "G", "36", "6-3"),
      rosterPlayer("e-timelord", "Robert Williams III", "C-F", "44", "6-9"),
    ],
  },
]

const GENERIC_NAMES = [
  "Alex Johnson", "Marcus Reed", "Tyler Brooks", "Jordan Hayes", "Chris Palmer",
  "Devin Shaw", "Ryan Coleman", "Eric Foster", "Nate Griffin", "Luke Pierce",
  "Sam Ortiz", "Mike Dalton", "Jake Morrison", "Ben Carter", "Drew Lawson",
]

function seededRandom(seed: string): () => number {
  let h = 0
  for (let i = 0; i < seed.length; i++) {
    h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0
  }
  return () => {
    h = (Math.imul(1103515245, h) + 12345) | 0
    return (h >>> 0) / 4294967296
  }
}

function eraPoolForYear(year: number): EraPool["players"] {
  const pool = BOS_ERA_POOLS.find((p) => year <= p.maxYear) ?? BOS_ERA_POOLS.at(-1)!
  return pool.players
}

function generateBosRoster(season: string): TeamRosterPlayer[] {
  const hardcoded = BOS_ROSTERS_BY_SEASON[season]
  if (hardcoded) return hardcoded

  const year = Number.parseInt(season.slice(0, 4), 10)
  const rng = seededRandom(`bos-roster-${season}`)
  const eraStars = eraPoolForYear(year)
  const roster: TeamRosterPlayer[] = []
  const used = new Set<string>()

  for (const star of eraStars) {
    roster.push({
      ...star,
      id: `${star.id}-${season}`,
    })
    used.add(star.name)
  }

  const targetSize = 12 + Math.floor(rng() * 3)
  let i = 0
  while (roster.length < targetSize) {
    const name = GENERIC_NAMES[Math.floor(rng() * GENERIC_NAMES.length)]
    if (used.has(name)) continue
    used.add(name)
    const pos = POSITIONS[Math.floor(rng() * POSITIONS.length)]
    const num = String(Math.floor(rng() * 99))
    const ft = 6
    const inch = 1 + Math.floor(rng() * 10)
    roster.push(
      rosterPlayer(
        `gen-${season}-${i}`,
        name,
        pos,
        num,
        `${ft}-${inch}`,
      ),
    )
    i++
  }

  return roster.sort((a, b) => Number(a.number) - Number(b.number))
}

function generateStubRoster(teamKey: string, season: string): TeamRosterPlayer[] {
  const rng = seededRandom(`${teamKey}-roster-${season}`)
  return Array.from({ length: 12 }, (_, i) => {
    const name = GENERIC_NAMES[(i + season.charCodeAt(0)) % GENERIC_NAMES.length]
    const pos = POSITIONS[i % POSITIONS.length]
    const ft = 6 + (i % 2)
    const inch = 2 + (i % 8)
    return rosterPlayer(
      `${teamKey}-${season}-r${i}`,
      i < 3 ? `${name} ${i + 1}` : name,
      pos,
      String(1 + Math.floor(rng() * 55)),
      `${ft}-${inch}`,
    )
  })
}

const rosterCache = new Map<string, TeamRosterPlayer[]>()

export function getTeamSeasonRoster(
  profile: TeamProfile,
  season: string,
): TeamRosterPlayer[] {
  const cacheKey = `${profile.id}:${season}`
  const cached = rosterCache.get(cacheKey)
  if (cached) return cached

  if (season === profile.seasonLabel) {
    rosterCache.set(cacheKey, profile.roster)
    return profile.roster
  }

  let roster: TeamRosterPlayer[]
  if (profile.id === "team-bos") {
    roster = generateBosRoster(season)
  } else {
    roster = generateStubRoster(profile.abbr.toLowerCase(), season)
  }

  rosterCache.set(cacheKey, roster)
  return roster
}
