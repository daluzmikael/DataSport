import { TEAM_LEADER_STAT_OPTIONS } from "../data/teamSeasonLeadersMock"
import { useStagingTeamAllLeaders, useTeamVaultSeason } from "../hooks/useStagingTeam"
import type { TeamProfile } from "../types"
import { ReferencedLabel } from "./AskReferenceButton"
import { StagingBadge } from "./StagingBadge"

interface TeamSeasonLeadersSectionProps {
  profile: TeamProfile
  onReference: (label: string) => void
}

export function TeamSeasonLeadersSection({
  profile,
  onReference,
}: TeamSeasonLeadersSectionProps) {
  const { season, setSeason, seasons: seasonOptions } = useTeamVaultSeason(profile)
  const { leaders, fromApi } = useStagingTeamAllLeaders(profile, season)

  return (
    <div className="pt-6">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <label className="flex items-center gap-2">
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="rounded-md border border-ds-border bg-ds-raised px-2 py-1 text-sm font-semibold text-ds-text outline-none focus:ring-2 focus:ring-ds-accent-vivid/40"
            aria-label="Season"
          >
            {seasonOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          <span className="text-sm font-semibold">leaders</span>
          <StagingBadge show={fromApi} />
        </label>
        <p className="text-[11px] text-ds-muted">Season per-game leaders · {season}</p>
      </div>
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-wide text-ds-muted">
            <th className="border-b border-ds-border py-2 pr-2 font-semibold">Stat</th>
            <th className="border-b border-ds-border py-2 pr-2 font-semibold">Leader</th>
            <th className="border-b border-ds-border py-2 font-semibold">Value</th>
          </tr>
        </thead>
        <tbody>
          {TEAM_LEADER_STAT_OPTIONS.map(({ id, label }) => {
            const leader = leaders[id]
            return (
              <tr key={id} className="hover:bg-ds-raised/60">
                <td className="border-b border-ds-border/60 py-2 pr-2 font-heading font-semibold">
                  {label}
                </td>
                <td className="border-b border-ds-border/60 py-2 pr-2">
                  <ReferencedLabel label={leader.player} onReference={onReference} />
                </td>
                <td className="border-b border-ds-border/60 py-2 font-mono tabular-nums">
                  {leader.value}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
