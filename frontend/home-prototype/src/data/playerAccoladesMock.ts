import { canonicalMockPlayerId } from "../api/nbaIds"
import { getCareerLogs } from "./playerCareerLogMock"

export interface PlayerAccoladeStat {
  label: string
  value: string
  subline?: string
}

export interface PlayerAccoladeProfile {
  championships?: { count: number; years?: string }
  finalsMvp?: number
  mvp?: number
  allNba?: { total: number; firstTeam: number; secondTeam: number }
  allStar?: number
  dpoy?: number
  allDef?: { total: number; firstTeam: number; secondTeam: number }
  draft?: { pick: number; year: number } | "undrafted"
  allRookie?: "1st" | "2nd"
  roty?: boolean
}

const ACCOLADE_SLOT_COUNT = 8

const CAREER_FILLER_META: Record<
  string,
  { label: string; subline: string }
> = {
  min: { label: "Career MIN", subline: "regular season" },
  pts: { label: "Career PTS", subline: "regular season" },
  reb: { label: "Career REB", subline: "regular season" },
  fgm: { label: "Career FGM", subline: "regular season" },
  ast: { label: "Career AST", subline: "regular season" },
  fg3m: { label: "Career 3PM", subline: "regular season" },
  stl: { label: "Career STL", subline: "regular season" },
  blk: { label: "Career BLK", subline: "regular season" },
}

function formatCount(n: number): string {
  return n.toLocaleString("en-US")
}

function ordinalPick(pick: number): string {
  const mod100 = pick % 100
  if (mod100 >= 11 && mod100 <= 13) return `${pick}th`
  switch (pick % 10) {
    case 1:
      return `${pick}st`
    case 2:
      return `${pick}nd`
    case 3:
      return `${pick}rd`
    default:
      return `${pick}th`
  }
}

function buildDraftSlot(profile: PlayerAccoladeProfile): PlayerAccoladeStat {
  const subParts: string[] = []
  if (profile.draft !== "undrafted" && profile.draft?.year) {
    subParts.push(String(profile.draft.year))
  }
  if (profile.allRookie) {
    subParts.push(`${profile.allRookie === "1st" ? "1st" : "2nd"} All-Rookie`)
  }
  if (profile.roty) {
    subParts.push("RoTY")
  }

  const value =
    profile.draft === "undrafted"
      ? "UDFA"
      : profile.draft
        ? ordinalPick(profile.draft.pick)
        : "—"

  const subline =
    subParts.length > 0
      ? subParts.join(" · ")
      : profile.draft === "undrafted"
        ? "undrafted"
        : undefined

  return {
    label: "Draft",
    value,
    subline,
  }
}

function careerTotalsFromMockLogs(playerId: string): Record<string, number> | undefined {
  const key = canonicalMockPlayerId(playerId)
  if (key !== "player-tatum" && !key.startsWith("player-tatum")) return undefined
  const rows = getCareerLogs(key).general
  const totals = rows.find((r) => r.id === "career-reg-tot")
  if (!totals) return undefined
  const out: Record<string, number> = {}
  for (const [entryKey, val] of Object.entries(totals.values)) {
    if (typeof val === "number") out[entryKey] = val
  }
  return out
}

function buildCareerFillers(
  totals: Record<string, number> | undefined,
  usedLabels: Set<string>,
): PlayerAccoladeStat[] {
  if (!totals) return []

  const ranked = Object.keys(CAREER_FILLER_META)
    .filter((key) => typeof totals[key] === "number")
    .map((key) => ({ key, amount: totals[key] }))
    .sort((a, b) => b.amount - a.amount)

  const fillers: PlayerAccoladeStat[] = []
  for (const { key, amount } of ranked) {
    const meta = CAREER_FILLER_META[key]
    if (usedLabels.has(meta.label)) continue
    fillers.push({
      label: meta.label,
      value: formatCount(amount),
      subline: meta.subline,
    })
  }
  return fillers
}

function buildAccoladeRow(profile: PlayerAccoladeProfile, careerTotals?: Record<string, number>): PlayerAccoladeStat[] {
  const slots: PlayerAccoladeStat[] = []
  const usedLabels = new Set<string>()

  const push = (stat: PlayerAccoladeStat) => {
    if (slots.length >= ACCOLADE_SLOT_COUNT) return
    if (usedLabels.has(stat.label)) return
    usedLabels.add(stat.label)
    slots.push(stat)
  }

  if (profile.championships?.count) {
    push({
      label: "Championships",
      value: String(profile.championships.count),
      subline: profile.championships.years,
    })
  }

  if (profile.finalsMvp) {
    push({
      label: "Finals MVP",
      value: String(profile.finalsMvp),
      subline: profile.finalsMvp === 1 ? "award" : "awards",
    })
  } else if (profile.mvp) {
    push({
      label: "MVP",
      value: String(profile.mvp),
      subline: profile.mvp === 1 ? "award" : "awards",
    })
  }

  if (profile.finalsMvp && profile.mvp) {
    push({
      label: "MVP",
      value: String(profile.mvp),
      subline: profile.mvp === 1 ? "award" : "awards",
    })
  }

  if (profile.allNba?.total) {
    const { total, firstTeam, secondTeam } = profile.allNba
    push({
      label: "All-NBA",
      value: firstTeam || secondTeam ? `${firstTeam}·${secondTeam}` : String(total),
      subline:
        firstTeam || secondTeam
          ? `${firstTeam} 1st · ${secondTeam} 2nd`
          : `${total} selections`,
    })
  }

  if (profile.allStar) {
    push({
      label: "All-Star",
      value: String(profile.allStar),
      subline: "selections",
    })
  }

  if (profile.dpoy) {
    push({
      label: "DPOY",
      value: String(profile.dpoy),
      subline: profile.dpoy === 1 ? "award" : "awards",
    })
  }

  if (profile.allDef?.total) {
    const { total, firstTeam, secondTeam } = profile.allDef
    push({
      label: "All-Def",
      value: firstTeam || secondTeam ? `${firstTeam}·${secondTeam}` : String(total),
      subline:
        firstTeam || secondTeam
          ? `${firstTeam} 1st · ${secondTeam} 2nd`
          : `${total} selections`,
    })
  }

  push(buildDraftSlot(profile))

  const fillers = buildCareerFillers(careerTotals, usedLabels)
  for (const filler of fillers) {
    if (slots.length >= ACCOLADE_SLOT_COUNT) break
    push(filler)
  }

  while (slots.length < ACCOLADE_SLOT_COUNT) {
    slots.push({ label: "", value: "—" })
  }

  return slots.slice(0, ACCOLADE_SLOT_COUNT)
}

const TATUM_PROFILE: PlayerAccoladeProfile = {
  championships: { count: 1, years: "2024" },
  allNba: { total: 5, firstTeam: 4, secondTeam: 1 },
  allStar: 6,
  draft: { pick: 3, year: 2017 },
  allRookie: "1st",
}

const DURANT_PROFILE: PlayerAccoladeProfile = {
  championships: { count: 2, years: "2017, 2018" },
  finalsMvp: 2,
  mvp: 1,
  allNba: { total: 10, firstTeam: 6, secondTeam: 4 },
  allStar: 15,
  draft: { pick: 2, year: 2007 },
  allRookie: "1st",
  roty: true,
}

const DEFAULT_PROFILE: PlayerAccoladeProfile = {
  draft: "undrafted",
}

function resolveAccoladeProfile(playerId: string): PlayerAccoladeProfile {
  const key = canonicalMockPlayerId(playerId)
  if (key === "player-tatum" || key.startsWith("player-tatum")) return TATUM_PROFILE
  if (key === "player-durant" || key.startsWith("player-durant")) return DURANT_PROFILE
  return DEFAULT_PROFILE
}

export function getPlayerAccolades(
  playerId: string,
  careerTotalsOverride?: Record<string, number>,
): PlayerAccoladeStat[] {
  const profile = resolveAccoladeProfile(playerId)
  const careerTotals = careerTotalsOverride ?? careerTotalsFromMockLogs(playerId)
  return buildAccoladeRow(profile, careerTotals)
}
