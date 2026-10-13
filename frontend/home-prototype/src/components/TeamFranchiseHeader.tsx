import { useState, type ReactNode } from "react"
import { resolveNbaTeamId, teamAbbrFromProfileId } from "../api/nbaIds"
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

/** Team logo (public/team-logos, copied from the NBA CDN); falls back to the abbreviation if the id is unknown or the image fails. */
function TeamLogo({ profile }: { profile: TeamProfile }) {
  const nbaId = resolveNbaTeamId(teamAbbrFromProfileId(profile.id))
  const [failed, setFailed] = useState(false)
  const box =
    "flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-ds-border bg-ds-raised/40 sm:h-14 sm:w-14"
  if (!nbaId || failed) {
    return (
      <div className={box} aria-hidden>
        <span className="font-mono text-sm font-bold text-ds-muted">{profile.abbr}</span>
      </div>
    )
  }
  return (
    <div className={box}>
      <img
        src={`/team-logos/${nbaId}.svg`}
        alt={`${profile.city} ${profile.name} logo`}
        className="h-10 w-10 object-contain sm:h-12 sm:w-12"
        onError={() => setFailed(true)}
      />
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
            <TeamLogo profile={profile} />
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
            <StatCell label="Championships" value={accolades?.championships ?? "—"} accent />
            <StatCell label="Conference titles" value={accolades?.conferenceTitles ?? "—"} />
            <StatCell label="Last championship" value={accolades?.lastChampionship ?? "—"} />
            <StatCell label="Last playoffs" value={accolades?.lastPlayoffs ?? "—"} />
            <StatCell label="In association">
              <p className="mt-0.5 font-mono text-base font-bold leading-tight tabular-nums text-ds-text sm:text-lg">
                Since {accolades?.founded ?? "—"}
              </p>
              <p className="text-[11px] text-ds-muted">{accolades?.yearsInAssociation ?? "—"} seasons</p>
            </StatCell>
          </div>
        </div>
      </div>
    </div>
  )
}
