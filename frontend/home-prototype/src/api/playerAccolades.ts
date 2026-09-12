/** Build the eight accolade tiles on a player profile from real award rows.
 *
 * The module this replaces held exactly two profiles — Tatum and Durant — and gave
 * every other player in the league `DEFAULT_PROFILE = { draft: "undrafted" }`. LeBron
 * James rendered as **UDFA**. Counts now come from `player_awards` (one row per award
 * instance) and the draft slot from `player_bio`.
 */
import type { AwardSummaryEntry, PlayerBio } from "./stagingClient"

export interface PlayerAccoladeStat {
  label: string
  value: string
  subline?: string
}

export const ACCOLADE_SLOT_COUNT = 8

/** Career totals worth showing when a player has fewer than eight honours. */
const CAREER_FILLER_META: Record<string, { label: string; subline: string }> = {
  pts: { label: "Career PTS", subline: "regular season" },
  reb: { label: "Career REB", subline: "regular season" },
  ast: { label: "Career AST", subline: "regular season" },
  fg3m: { label: "Career 3PM", subline: "regular season" },
  min: { label: "Career MIN", subline: "regular season" },
  fgm: { label: "Career FGM", subline: "regular season" },
  stl: { label: "Career STL", subline: "regular season" },
  blk: { label: "Career BLK", subline: "regular season" },
}

function formatCount(n: number): string {
  return n.toLocaleString("en-US")
}

function ordinal(pick: number): string {
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

/** Compress a season list into the year the award was won: "2023-24" -> "2024". */
function awardYears(seasons: string[], max = 4): string | undefined {
  const years = seasons
    .map((s) => {
      const m = /^(\d{4})-(\d{2})$/.exec(s.trim())
      if (m) return String(Number(m[1]) + 1)
      return /^\d{4}$/.test(s.trim()) ? s.trim() : null
    })
    .filter((y): y is string => Boolean(y))
    .sort()
  if (!years.length) return undefined
  if (years.length <= max) return years.join(", ")
  return `${years.slice(0, max).join(", ")} +${years.length - max}`
}

function find(summary: AwardSummaryEntry[], exact: string): AwardSummaryEntry | undefined {
  return summary.find((e) => e.description.toLowerCase() === exact.toLowerCase())
}

/** Count All-NBA / All-Defensive selections split by team number. */
function teamSplit(
  rows: Array<Record<string, unknown>>,
  description: string,
): { total: number; first: number; second: number; third: number } {
  const matching = rows.filter(
    (r) => String(r.DESCRIPTION ?? "").toLowerCase() === description.toLowerCase(),
  )
  const count = (n: string) =>
    matching.filter((r) => String(r.ALL_NBA_TEAM_NUMBER ?? "").trim() === n).length
  return {
    total: matching.length,
    first: count("1"),
    second: count("2"),
    third: count("3"),
  }
}

function draftSlot(bio: PlayerBio | null | undefined): PlayerAccoladeStat {
  const rawNumber = String(bio?.DRAFT_NUMBER ?? "").trim()
  const year = String(bio?.DRAFT_YEAR ?? "").trim()

  if (!bio || !rawNumber) {
    // No bio row at all. An empty tile is honest; "UDFA" is a claim.
    return { label: "Draft", value: "—" }
  }
  if (/^undrafted$/i.test(rawNumber)) {
    return { label: "Draft", value: "UDFA", subline: year && !/^undrafted$/i.test(year) ? year : "undrafted" }
  }
  const pick = Number(rawNumber)
  if (!Number.isFinite(pick)) return { label: "Draft", value: "—" }
  return {
    label: "Draft",
    value: ordinal(pick),
    subline: year && !/^undrafted$/i.test(year) ? year : undefined,
  }
}

export function buildPlayerAccolades(
  summary: AwardSummaryEntry[],
  awardRows: Array<Record<string, unknown>>,
  bio: PlayerBio | null | undefined,
  careerTotals?: Record<string, number>,
): PlayerAccoladeStat[] {
  const slots: PlayerAccoladeStat[] = []
  const used = new Set<string>()

  const push = (stat: PlayerAccoladeStat | null) => {
    if (!stat || slots.length >= ACCOLADE_SLOT_COUNT || used.has(stat.label)) return
    used.add(stat.label)
    slots.push(stat)
  }

  const simple = (
    description: string,
    label: string,
    singular: string,
    plural: string,
  ): PlayerAccoladeStat | null => {
    const entry = find(summary, description)
    if (!entry?.count) return null
    return {
      label,
      value: String(entry.count),
      subline: awardYears(entry.seasons) ?? (entry.count === 1 ? singular : plural),
    }
  }

  push(simple("NBA Champion", "Championships", "title", "titles"))
  push(simple("NBA Finals Most Valuable Player", "Finals MVP", "award", "awards"))
  push(simple("NBA Most Valuable Player", "MVP", "award", "awards"))

  const allNba = teamSplit(awardRows, "All-NBA")
  if (allNba.total) {
    push({
      label: "All-NBA",
      value: String(allNba.total),
      subline:
        allNba.first || allNba.second || allNba.third
          ? `${allNba.first} 1st · ${allNba.second} 2nd · ${allNba.third} 3rd`
          : "selections",
    })
  }

  push(simple("NBA All-Star", "All-Star", "selection", "selections"))
  push(simple("NBA Defensive Player of the Year", "DPOY", "award", "awards"))

  const allDef = teamSplit(awardRows, "All-Defensive Team")
  if (allDef.total) {
    push({
      label: "All-Def",
      value: String(allDef.total),
      subline:
        allDef.first || allDef.second
          ? `${allDef.first} 1st · ${allDef.second} 2nd`
          : "selections",
    })
  }

  push(simple("NBA Rookie of the Year", "ROY", "award", "awards"))
  push(simple("NBA Sixth Man of the Year", "6MOY", "award", "awards"))
  push(simple("NBA Most Improved Player", "MIP", "award", "awards"))
  push(draftSlot(bio))

  if (careerTotals) {
    const ranked = Object.keys(CAREER_FILLER_META)
      .filter((key) => typeof careerTotals[key] === "number")
      .map((key) => ({ key, amount: careerTotals[key] }))
      .sort((a, b) => b.amount - a.amount)
    for (const { key, amount } of ranked) {
      if (slots.length >= ACCOLADE_SLOT_COUNT) break
      const meta = CAREER_FILLER_META[key]
      push({ label: meta.label, value: formatCount(amount), subline: meta.subline })
    }
  }

  // Pad to a full row. Blank tiles keep the grid stable and claim nothing.
  while (slots.length < ACCOLADE_SLOT_COUNT) {
    slots.push({ label: "", value: "—" })
  }
  return slots.slice(0, ACCOLADE_SLOT_COUNT)
}
