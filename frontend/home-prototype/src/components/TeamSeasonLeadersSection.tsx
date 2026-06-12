import { useState } from "react"
import {
  leaderStatLabel,
  TEAM_LEADER_STAT_OPTIONS,
  type TeamLeaderStatId,
  type TeamSeasonLeaderEntry,
} from "../data/teamSeasonLeadersMock"
import {
  useStagingTeamLeaders,
  useStagingTeamSeasonSnapshot,
  useTeamVaultSeason,
} from "../hooks/useStagingTeam"
import type { TeamProfile } from "../types"
import { ReferencedLabel } from "./AskReferenceButton"
import { StagingBadge } from "./StagingBadge"

interface TeamSeasonLeadersSectionProps {
  profile: TeamProfile
  onReference: (label: string) => void
}

function SeasonStatCell({
  label,
  value,
  children,
}: {
  label: string
  value?: string | number
  children?: React.ReactNode
}) {
  return (
    <div className="min-w-0 rounded-lg border border-ds-border/60 bg-ds-raised/50 px-3 py-2.5">
      <p className="text-[9px] font-semibold uppercase tracking-wide text-ds-muted">{label}</p>
      {children ?? (
        <p className="mt-0.5 font-mono text-base font-bold leading-tight tabular-nums text-ds-text sm:text-lg">
          {value}
        </p>
      )}
    </div>
  )
}

const RANK_LABELS = ["1st", "2nd", "3rd"]

function LeaderCard({
  rank,
  leader,
  statId,
  onReference,
}: {
  rank: number
  leader: TeamSeasonLeaderEntry
  statId: TeamLeaderStatId
  onReference: (label: string) => void
}) {
  return (
    <div className="min-w-0 rounded-lg border border-ds-border/60 bg-ds-raised/50 px-3 py-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
        {RANK_LABELS[rank] ?? `${rank + 1}th`} · {leaderStatLabel(statId)}
      </p>
      <p className="mt-1 text-sm font-bold leading-tight">
        <ReferencedLabel label={leader.player} onReference={onReference} />
      </p>
      <p className="mt-0.5 font-mono text-2xl font-bold tabular-nums text-ds-accent">
        {leader.value}
      </p>
    </div>
  )
}

export function TeamSeasonLeadersSection({
  profile,
  onReference,
}: TeamSeasonLeadersSectionProps) {
  const { season, setSeason, seasons: seasonOptions } = useTeamVaultSeason(profile)
  const [selectedStat, setSelectedStat] = useState<TeamLeaderStatId>("pts")
  const { leaders, fromApi: leadersFromApi } = useStagingTeamLeaders(
    profile,
    season,
    selectedStat,
  )
  const { snapshot, fromApi: snapshotFromApi } = useStagingTeamSeasonSnapshot(profile, season)
  const fromApi = leadersFromApi || snapshotFromApi

  return (
    <section className="rounded-xl border border-ds-border bg-ds-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ds-border px-3 py-2">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <label className="flex items-center gap-2">
            <select
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              className="rounded-md border border-ds-border bg-ds-raised px-2 py-1 text-sm font-semibold text-ds-text outline-none focus:ring-2 focus:ring-ds-accent/40"
              aria-label="Season"
            >
              {seasonOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <span className="text-sm font-semibold">season</span>
            <StagingBadge show={fromApi} />
          </label>
        </div>
        <p className="text-[10px] text-ds-muted">
          Standing, record, top GS · per-game leaders
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3 border-b border-ds-border px-3 py-3">
        <SeasonStatCell label="Standing" value={snapshot.standing} />
        <SeasonStatCell label="Record" value={snapshot.record} />
        <SeasonStatCell label="Best player (GS)">
          <p className="mt-0.5 text-sm font-bold leading-tight">
            <ReferencedLabel
              label={snapshot.bestPlayer.name}
              onReference={onReference}
            />
          </p>
          <p className="font-mono text-base font-bold tabular-nums text-ds-accent sm:text-lg">
            {snapshot.bestPlayer.avgGameScore.toFixed(1)}
          </p>
        </SeasonStatCell>
      </div>

      <div className="p-3">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
          Season leaders
        </p>
        <div className="mb-3 flex flex-wrap gap-1">
          {TEAM_LEADER_STAT_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => setSelectedStat(opt.id)}
              className={`rounded px-1.5 py-0.5 text-[10px] font-medium transition ${
                selectedStat === opt.id
                  ? "bg-ds-accent/20 text-ds-accent"
                  : "text-ds-muted hover:bg-ds-raised hover:text-ds-text"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {leaders.map((leader, index) => (
            <LeaderCard
              key={index}
              rank={index}
              leader={leader}
              statId={selectedStat}
              onReference={onReference}
            />
          ))}
        </div>
        <p className="mt-2 text-[10px] text-ds-muted">Per game · {season}</p>
      </div>
    </section>
  )
}
