import { useState } from "react"
import { useStagingTeamHistory } from "../hooks/useStagingTeam"
import type { TeamProfile } from "../types"
import { TeamFranchiseHeader } from "./TeamFranchiseHeader"
import { TeamOverviewSection } from "./TeamOverviewSection"
import { TeamRosterSection } from "./TeamRosterSection"
import { TeamSeasonLeadersSection } from "./TeamSeasonLeadersSection"
import { TeamSeasonGameLogTable } from "./TeamSeasonGameLogTable"
import { StagingBadge } from "./StagingBadge"

interface TeamDetailProps {
  profile: TeamProfile
  liveGameId?: string
  onOpenGame?: (gameId: string) => void
  onReference: (label: string) => void
}

type TeamTab = "overview" | "leaders" | "gamelog" | "roster"

const TABS: { id: TeamTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "leaders", label: "Season Leaders" },
  { id: "gamelog", label: "Game Log" },
  { id: "roster", label: "Roster" },
]

export function TeamDetail({ profile, liveGameId, onOpenGame, onReference }: TeamDetailProps) {
  const [tab, setTab] = useState<TeamTab>("overview")
  const { history, fromApi: historyFromApi } = useStagingTeamHistory(profile)

  const histCols = [
    { id: "season", label: "Season" },
    { id: "wl", label: "W-L" },
    { id: "pts", label: "PTS" },
    { id: "reb", label: "REB" },
    { id: "ast", label: "AST" },
    { id: "fg_pct", label: "FG%" },
    { id: "fg3_pct", label: "3P%" },
  ]

  return (
    <div className="mx-auto max-w-5xl space-y-0">
      <TeamFranchiseHeader profile={profile} onReference={onReference} />

      <div className="mt-6 flex flex-wrap border-b border-ds-border">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`mr-5 border-b-2 pb-2.5 pt-2 font-heading text-[15px] font-semibold transition ${
              tab === id
                ? "border-ds-accent-vivid text-ds-text"
                : "border-transparent text-ds-muted hover:text-ds-text"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="space-y-6">
          <TeamOverviewSection profile={profile} onReference={onReference} />

          <section>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <h3 className="font-heading text-lg font-semibold">Franchise history</h3>
              <StagingBadge show={historyFromApi} />
            </div>
            <p className="mb-2 text-[11px] text-ds-muted">Franchise averages · chronological</p>
            <div className="max-h-[min(320px,40vh)] overflow-auto rounded-lg border border-ds-border">
              <table className="w-full min-w-[520px] border-collapse text-left text-xs">
                <thead className="sticky top-0 z-10 bg-ds-raised">
                  <tr>
                    {histCols.map((col) => (
                      <th
                        key={col.id}
                        className="whitespace-nowrap border-b border-ds-border px-3 py-2 font-semibold uppercase tracking-wide text-ds-muted"
                      >
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-mono tabular-nums">
                  {history.map((row) => (
                    <tr
                      key={row.season}
                      className={`border-b border-ds-border/40 hover:bg-ds-raised/40 ${
                        row.season === profile.seasonLabel ? "bg-ds-accent-100" : ""
                      }`}
                    >
                      <td className="px-3 py-2 font-sans font-medium">{row.season}</td>
                      <td className="px-3 py-2">{row.wl}</td>
                      <td className="px-3 py-2">{row.values.pts}</td>
                      <td className="px-3 py-2">{row.values.reb}</td>
                      <td className="px-3 py-2">{row.values.ast}</td>
                      <td className="px-3 py-2">{row.values.fg_pct}</td>
                      <td className="px-3 py-2">{row.values.fg3_pct}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-1 text-[10px] text-ds-muted">{history.length} seasons · scroll ↕</p>
          </section>
        </div>
      )}

      {tab === "leaders" && (
        <TeamSeasonLeadersSection profile={profile} onReference={onReference} />
      )}

      {tab === "gamelog" && (
        <div className="pt-6">
          <TeamSeasonGameLogTable
            profile={profile}
            liveGameId={liveGameId}
            onOpenGame={onOpenGame}
            onReference={onReference}
          />
        </div>
      )}

      {tab === "roster" && (
        <div className="space-y-6 pt-6">
          <TeamRosterSection profile={profile} onReference={onReference} />

        </div>
      )}
    </div>
  )
}
