import type { ReactNode } from "react"
import { useStagingTeamFranchiseAccolades } from "../hooks/useStagingTeam"
import type { TeamProfile } from "../types"
import { ReferencedLabel } from "./AskReferenceButton"

interface TeamFranchiseHeaderProps {
  profile: TeamProfile
  onReference: (label: string) => void
}

function StatCell({
  label,
  value,
  accent,
  children,
}: {
  label: string
  value?: string | number
  accent?: boolean
  children?: ReactNode
}) {
  return (
    <div className="min-w-0">
      <p className="text-[9px] font-semibold uppercase tracking-wide text-ds-muted">{label}</p>
      {children ?? (
        <p
          className={`mt-0.5 font-mono text-base font-bold leading-tight tabular-nums sm:text-lg ${
            accent ? "text-ds-accent" : "text-ds-text"
          }`}
        >
          {value}
        </p>
      )}
    </div>
  )
}

export function TeamFranchiseHeader({ profile, onReference }: TeamFranchiseHeaderProps) {
  const { accolades } = useStagingTeamFranchiseAccolades(profile)

  return (
    <div className="rounded-xl border border-ds-border bg-ds-panel px-4 py-3">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        <div className="flex min-w-0 flex-1 flex-col lg:max-w-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
            Franchise
          </p>
          <div className="mt-1 flex items-center gap-3">
            <div
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-dashed border-ds-border bg-ds-raised/40 sm:h-14 sm:w-14"
              aria-hidden
            >
              <span className="text-[9px] font-medium uppercase tracking-wide text-ds-muted">
                [logo]
              </span>
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-bold tracking-tight sm:text-2xl">
                <ReferencedLabel
                  label={`${profile.city} ${profile.name}`}
                  onReference={onReference}
                />
              </h2>
              <p className="mt-0.5 inline-flex items-center gap-0.5 font-mono text-sm text-ds-accent">
                <ReferencedLabel label={profile.abbr} onReference={onReference} />
              </p>
            </div>
          </div>
        </div>

        <div className="hidden w-px shrink-0 bg-ds-border lg:block" aria-hidden />

        <div className="min-w-0 flex-1">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
            Accolades
          </p>
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
            <StatCell label="Championships" value={accolades.championships} accent />
            <StatCell label="Conference titles" value={accolades.conferenceTitles} />
            <StatCell label="Last championship" value={accolades.lastChampionship} />
            <StatCell label="Last playoffs" value={accolades.lastPlayoffs} />
            <StatCell label="In association">
              <p className="mt-0.5 font-mono text-base font-bold leading-tight tabular-nums text-ds-text sm:text-lg">
                Since {accolades.founded}
              </p>
              <p className="text-[11px] text-ds-muted">{accolades.yearsInAssociation} seasons</p>
            </StatCell>
          </div>
        </div>
      </div>
    </div>
  )
}
