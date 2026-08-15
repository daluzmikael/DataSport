import {
  useStagingTeamGameLog,
  useStagingTeamLeaders,
  useStagingTeamSeasonSnapshot,
  useTeamVaultSeason,
} from "../hooks/useStagingTeam"
import type { TeamLeaderStatId, TeamSeasonLeaderEntry } from "../data/teamSeasonLeadersMock"
import type { TeamProfile } from "../types"
import { ReferencedLabel } from "./AskReferenceButton"
import { StagingBadge } from "./StagingBadge"

interface TeamOverviewSectionProps {
  profile: TeamProfile
  onReference: (label: string) => void
}

const TOP_STATS: { id: TeamLeaderStatId; label: string }[] = [
  { id: "pts", label: "PTS" },
  { id: "reb", label: "REB" },
  { id: "ast", label: "AST" },
]

function KeyStat({ label, value }: { label: string; value?: string | number }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-ds-muted">{label}</p>
      <p className="mt-0.5 font-heading text-xl font-semibold tabular-nums text-ds-text sm:text-2xl">
        {value ?? "—"}
      </p>
    </div>
  )
}

function TopLeaderCard({
  label,
  season,
  leader,
  onReference,
}: {
  label: string
  season: string
  leader: TeamSeasonLeaderEntry
  onReference: (label: string) => void
}) {
  return (
    <div className="min-w-0 rounded-lg border border-ds-border bg-ds-panel px-3 py-3 shadow-sm">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-ds-accent-vivid">
        {label}
      </p>
      <p className="mt-1 font-heading text-lg font-semibold leading-tight">
        <ReferencedLabel label={leader.player} onReference={onReference} />
      </p>
      <p className="mt-0.5 font-heading text-3xl font-semibold tabular-nums text-ds-accent">
        {leader.value}
      </p>
      <p className="mt-0.5 text-[11px] text-ds-muted">Per game · {season}</p>
    </div>
  )
}

export function TeamOverviewSection({ profile, onReference }: TeamOverviewSectionProps) {
  const { season, setSeason, seasons: seasonOptions } = useTeamVaultSeason(profile)
  const { snapshot, fromApi: snapshotFromApi } = useStagingTeamSeasonSnapshot(profile, season)
  const { averages, fromApi: avgFromApi } = useStagingTeamGameLog(profile, season, "general")

  const pts = useStagingTeamLeaders(profile, season, "pts", 1)
  const reb = useStagingTeamLeaders(profile, season, "reb", 1)
  const ast = useStagingTeamLeaders(profile, season, "ast", 1)
  const leaderById: Record<string, { leaders: TeamSeasonLeaderEntry[]; fromApi: boolean }> = {
    pts,
    reb,
    ast,
  }
  const fromApi = snapshotFromApi || avgFromApi || pts.fromApi || reb.fromApi || ast.fromApi

  return (
    <div className="space-y-6 pt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2">
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="rounded-md border border-ds-border bg-ds-raised px-2 py-1 text-sm font-semibold text-ds-text outline-none focus:ring-2 focus:ring-ds-accent-vivid/40"
            aria-label="Overview season"
          >
            {seasonOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          <span className="text-sm font-semibold">overview</span>
          <StagingBadge show={fromApi} />
        </label>
        <div className="flex gap-6">
          <KeyStat label="Standing" value={snapshot.standing} />
          <KeyStat label="Record" value={snapshot.record} />
        </div>
      </div>

      <div>
        <h3 className="mb-2 font-heading text-lg font-semibold">Season leaders</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          {TOP_STATS.map(({ id, label }) => (
            <TopLeaderCard
              key={id}
              label={label}
              season={season}
              leader={leaderById[id]?.leaders[0] ?? { player: "—", value: "—" }}
              onReference={onReference}
            />
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-2 font-heading text-lg font-semibold">Key stats</h3>
        <div className="mb-4 h-px w-full bg-ds-border" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <KeyStat label="Record" value={snapshot.record} />
          <KeyStat label="PPG" value={averages.pts} />
          <KeyStat label="RPG" value={averages.reb} />
          <KeyStat label="APG" value={averages.ast} />
          <KeyStat label="FG%" value={averages.fg_pct} />
          <KeyStat label="3P%" value={averages.fg3_pct} />
        </div>
      </div>
    </div>
  )
}
