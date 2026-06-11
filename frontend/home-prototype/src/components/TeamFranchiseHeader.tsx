import type { ReactNode } from "react"
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
  const { accolades, currentSeason } = profile

  return (
    <div className="rounded-xl border border-ds-border bg-ds-panel px-4 py-3">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        <div className="flex min-w-0 shrink-0 flex-col lg:w-[11.5rem]">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
            Franchise
          </p>
          <h2 className="text-2xl font-bold tracking-tight">
            <ReferencedLabel
              label={`${profile.city} ${profile.name}`}
              onReference={onReference}
            />
          </h2>
          <p className="mt-0.5 inline-flex items-center gap-0.5 font-mono text-sm text-ds-accent">
            <ReferencedLabel label={profile.abbr} onReference={onReference} />
          </p>
          <div
            className="mt-3 flex flex-1 min-h-[4.5rem] items-center justify-center rounded-lg border border-dashed border-ds-border bg-ds-raised/40 px-3 py-4"
            aria-hidden
          >
            <span className="text-xs font-medium uppercase tracking-wide text-ds-muted">[logo]</span>
          </div>
        </div>

        <div className="hidden w-px shrink-0 bg-ds-border lg:block" aria-hidden />

        <div className="shrink-0 lg:w-[10.5rem]">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
            {profile.seasonLabel}
          </p>
          <div className="grid grid-cols-3 gap-x-4 gap-y-3 lg:grid-cols-1 lg:gap-y-2.5">
            <StatCell label="Standing" value={currentSeason.standing} />
            <StatCell label="Record" value={currentSeason.record} />
            <StatCell label="Best player (GS)">
              <p className="mt-0.5 text-sm font-bold leading-tight">
                <ReferencedLabel
                  label={currentSeason.bestPlayer.name}
                  onReference={onReference}
                />
              </p>
              <p className="font-mono text-base font-bold tabular-nums text-ds-accent sm:text-lg">
                {currentSeason.bestPlayer.avgGameScore.toFixed(1)}
              </p>
            </StatCell>
          </div>
        </div>

        <div className="hidden w-px shrink-0 bg-ds-border lg:block" aria-hidden />

        <div className="min-w-0 flex-1">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-ds-muted">
            Accolades
          </p>
          <div className="grid grid-cols-3 gap-x-6 gap-y-3">
            <StatCell label="All-time" value={accolades.allTimeRecord} />
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
