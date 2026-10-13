import { useEffect, useState } from "react"
import { USE_STAGING_API } from "../api/config"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { fetchPlayerGameLogSeasons, fetchPlayerSeasonStats } from "../api/stagingClient"

function n(row: Record<string, unknown>, key: string): number | null {
  const v = Number(row[key])
  return Number.isFinite(v) ? v : null
}

function pctText(v: number | null): string | null {
  return v == null ? null : `${(v * 100).toFixed(1)}%`
}

function ordinal(rank: number): string {
  const mod100 = rank % 100
  if (mod100 >= 11 && mod100 <= 13) return `${rank}th`
  return `${rank}${["th", "st", "nd", "rd"][rank % 10] ?? "th"}`
}

/** Plain-language season summary built only from the staged per-game row. */
export function seasonSummaryText(row: Record<string, unknown>, season: string): string {
  const name = String(row.PLAYER_NAME ?? "He")
  const team = row.TEAM_ABBREVIATION ? ` for ${row.TEAM_ABBREVIATION}` : ""
  const gp = n(row, "GP")
  const pts = n(row, "PTS")
  const reb = n(row, "REB")
  const ast = n(row, "AST")
  const lines: string[] = []

  lines.push(
    `In ${season}, ${name} averaged ${pts?.toFixed(1) ?? "—"} points, ${reb?.toFixed(1) ?? "—"} rebounds and ${ast?.toFixed(1) ?? "—"} assists` +
      `${gp ? ` across ${gp} games` : ""}${team}.`,
  )

  const fg = pctText(n(row, "FG_PCT"))
  const fg3 = pctText(n(row, "FG3_PCT"))
  const fg3a = n(row, "FG3A")
  if (fg) {
    lines.push(
      `He shot ${fg} from the field` +
        (fg3 && fg3a && fg3a >= 1 ? ` and ${fg3} from three on ${fg3a.toFixed(1)} attempts a night.` : "."),
    )
  }

  const ranks: string[] = []
  for (const [key, label] of [
    ["PTS_RANK", "scoring"],
    ["REB_RANK", "rebounding"],
    ["AST_RANK", "assists"],
  ] as const) {
    const r = n(row, key)
    if (r != null && r > 0 && r <= 10) ranks.push(`${ordinal(r)} in ${label}`)
  }
  if (ranks.length) lines.push(`League rank: ${ranks.join(", ")}.`)

  const td = n(row, "TD3")
  const dd = n(row, "DD2")
  if (td && td >= 3) lines.push(`${td} triple-doubles and ${dd ?? 0} double-doubles.`)
  else if (dd && dd >= 10) lines.push(`${dd} double-doubles.`)

  const pm = n(row, "PLUS_MINUS")
  const w = n(row, "W")
  const l = n(row, "L")
  if (w != null && l != null) {
    lines.push(
      `Team went ${w}-${l} in his games` +
        (pm != null ? ` with a ${pm >= 0 ? "+" : ""}${pm.toFixed(1)} plus-minus.` : "."),
    )
  }

  return lines.join(" ")
}

/** Latest staged season's summary for the player overview; null until loaded. */
export function useStagingPlayerSeasonSummary(playerId: string) {
  const nbaId = resolveNbaPlayerId(playerId)
  const [summary, setSummary] = useState<string | null>(null)
  const [season, setSeason] = useState<string | null>(null)

  useEffect(() => {
    setSummary(null)
    setSeason(null)
    if (!USE_STAGING_API || !nbaId) return
    let cancelled = false
    ;(async () => {
      const seasons = (await fetchPlayerGameLogSeasons(nbaId)) ?? []
      for (const s of seasons.slice(0, 2)) {
        const row = await fetchPlayerSeasonStats(nbaId, s)
        if (cancelled) return
        if (row && Number(row.GP) > 0) {
          setSummary(seasonSummaryText(row, s))
          setSeason(s)
          return
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [nbaId])

  return { summary, season }
}
