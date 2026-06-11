import { useState } from "react"
import {
  getTeamSeasonOptions,
  getTeamSeasonRoster,
} from "../data/teamSeasonRosterBuilder"
import { ReferencedLabel } from "./AskReferenceButton"
import type { TeamProfile } from "../types"

interface TeamRosterSectionProps {
  profile: TeamProfile
  onReference: (label: string) => void
}

export function TeamRosterSection({ profile, onReference }: TeamRosterSectionProps) {
  const seasonOptions = getTeamSeasonOptions(profile)
  const [season, setSeason] = useState(profile.seasonLabel)
  const roster = getTeamSeasonRoster(profile, season)
  const isCurrent = season === profile.seasonLabel

  return (
    <section className="rounded-xl border border-ds-border bg-ds-panel">
      <div className="border-b border-ds-border px-3 py-2">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <label className="flex items-center gap-2">
            <select
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              className="rounded-md border border-ds-border bg-ds-raised px-2 py-1 text-sm font-semibold text-ds-text outline-none focus:ring-2 focus:ring-ds-accent/40"
              aria-label="Roster season"
            >
              {seasonOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <span className="text-sm font-semibold">roster</span>
          </label>
        </div>
        <p className="text-[10px] text-ds-muted">
          {isCurrent ? "Current season" : "Historical roster"} · {roster.length} players
        </p>
      </div>
      <ul className="max-h-[min(360px,42vh)] divide-y divide-ds-border/50 overflow-auto">
        {roster.map((p) => (
          <li
            key={p.id}
            className="flex items-center justify-between px-3 py-2 text-sm hover:bg-ds-raised/40"
          >
            <span>
              <span className="mr-2 font-mono text-xs text-ds-muted">#{p.number}</span>
              <span className="font-medium">
                <ReferencedLabel label={p.name} onReference={onReference} />
              </span>
            </span>
            <span className="text-xs text-ds-muted">
              {p.position} · {p.height}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
