import { useState } from "react"
import {
  DEFAULT_LEADER_COLUMN_STATS,
  leaderStatLabel,
  TEAM_LEADER_STAT_OPTIONS,
  type TeamLeaderStatId,
  type TeamSeasonLeaderEntry,
} from "../data/teamSeasonLeadersMock"
import { useStagingTeamLeaders } from "../hooks/useStagingTeam"
import { getTeamSeasonOptions } from "../data/teamSeasonGameLogBuilder"
import type { TeamProfile } from "../types"
import { ReferencedLabel } from "./AskReferenceButton"
import { StagingBadge } from "./StagingBadge"

interface TeamSeasonLeadersSectionProps {
  profile: TeamProfile
  onReference: (label: string) => void
}

function LeaderColumn({
  columnIndex,
  statId,
  onStatChange,
  season,
  leaders,
  onReference,
}: {
  columnIndex: number
  statId: TeamLeaderStatId
  onStatChange: (index: number, stat: TeamLeaderStatId) => void
  season: string
  leaders: Record<TeamLeaderStatId, TeamSeasonLeaderEntry>
  onReference: (label: string) => void
}) {
  const leader = leaders[statId]
  const defaultLabels = ["Top scorer", "Top rebounder", "Top assister"]

  return (
    <div className="flex min-w-0 flex-1 flex-col border-t border-ds-border pt-4 lg:border-t-0 lg:border-l lg:pl-4 lg:pt-0 [&:first-child]:border-t-0 [&:first-child]:lg:border-l-0 [&:first-child]:lg:pl-0">
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
        {defaultLabels[columnIndex] ?? "Team leader"}
      </p>
      <div className="mb-2 flex flex-wrap gap-1">
        {TEAM_LEADER_STAT_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => onStatChange(columnIndex, opt.id)}
            className={`rounded px-1.5 py-0.5 text-[10px] font-medium transition ${
              statId === opt.id
                ? "bg-ds-accent/20 text-ds-accent"
                : "text-ds-muted hover:bg-ds-raised hover:text-ds-text"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <div className="mt-auto rounded-lg border border-ds-border/60 bg-ds-raised/50 px-3 py-2.5">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
          {leaderStatLabel(statId)}
        </p>
        <p className="mt-1 text-sm font-bold leading-tight">
          <ReferencedLabel label={leader.player} onReference={onReference} />
        </p>
        <p className="mt-0.5 font-mono text-2xl font-bold tabular-nums text-ds-accent">
          {leader.value}
        </p>
        <p className="text-[10px] text-ds-muted">Per game · {season}</p>
      </div>
    </div>
  )
}

export function TeamSeasonLeadersSection({
  profile,
  onReference,
}: TeamSeasonLeadersSectionProps) {
  const seasonOptions = getTeamSeasonOptions(profile)
  const [season, setSeason] = useState(profile.seasonLabel)
  const [columnStats, setColumnStats] = useState<TeamLeaderStatId[]>([
    ...DEFAULT_LEADER_COLUMN_STATS,
  ])
  const { leaders, fromApi } = useStagingTeamLeaders(profile, season)

  const setColumnStat = (index: number, stat: TeamLeaderStatId) => {
    setColumnStats((prev) => prev.map((s, i) => (i === index ? stat : s)))
  }

  return (
    <section className="rounded-xl border border-ds-border bg-ds-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ds-border px-3 py-2">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <label className="flex items-center gap-2">
            <select
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              className="rounded-md border border-ds-border bg-ds-raised px-2 py-1 text-sm font-semibold text-ds-text outline-none focus:ring-2 focus:ring-ds-accent/40"
              aria-label="Leaders season"
            >
              {seasonOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <span className="text-sm font-semibold">team leaders</span>
            <StagingBadge show={fromApi} />
          </label>
        </div>
        <p className="text-[10px] text-ds-muted">Season per-game leaders · switch stat per column</p>
      </div>

      <div className="flex flex-col gap-4 p-3 lg:flex-row lg:gap-0">
        {columnStats.map((statId, index) => (
          <LeaderColumn
            key={index}
            columnIndex={index}
            statId={statId}
            onStatChange={setColumnStat}
            season={season}
            leaders={leaders}
            onReference={onReference}
          />
        ))}
      </div>
    </section>
  )
}
