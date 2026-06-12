import { useStagingTeamHistory } from "../hooks/useStagingTeam"
import type { TeamProfile } from "../types"
import { ReferencedLabel } from "./AskReferenceButton"
import { TeamFranchiseHeader } from "./TeamFranchiseHeader"
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

export function TeamDetail({ profile, liveGameId, onOpenGame, onReference }: TeamDetailProps) {
  const { history, fromApi: historyFromApi } = useStagingTeamHistory(profile)
  const displayProfile: TeamProfile = profile

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
    <div className="mx-auto max-w-5xl space-y-4">
      <TeamFranchiseHeader profile={profile} onReference={onReference} />

      <TeamSeasonLeadersSection profile={displayProfile} onReference={onReference} />

      <TeamSeasonGameLogTable
        profile={displayProfile}
        liveGameId={liveGameId}
        onOpenGame={onOpenGame}
        onReference={onReference}
      />

      <section className="rounded-xl border border-ds-border bg-ds-panel">
        <div className="border-b border-ds-border px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">Season history</h3>
            <StagingBadge show={historyFromApi} />
          </div>
          <p className="text-[10px] text-ds-muted">Franchise averages · chronological</p>
        </div>
        <div className="max-h-[min(320px,40vh)] overflow-auto">
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
                    row.season === profile.seasonLabel ? "bg-ds-accent/10" : ""
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
        <p className="px-3 py-1.5 text-[10px] text-ds-muted">
          {history.length} seasons · scroll ↕
        </p>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <TeamRosterSection profile={profile} onReference={onReference} />

        <section className="rounded-xl border border-ds-border bg-ds-panel">
          <div className="border-b border-ds-border px-3 py-2">
            <h3 className="text-sm font-semibold">Top game scores</h3>
            <p className="text-[10px] text-ds-muted">Single-game GS · 1996–present (mock)</p>
          </div>
          <div className="max-h-[min(360px,42vh)] overflow-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead className="sticky top-0 z-10 bg-ds-raised">
                <tr className="text-[10px] uppercase tracking-wide text-ds-muted">
                  <th className="px-3 py-2 font-semibold">#</th>
                  <th className="px-3 py-2 font-semibold">Player</th>
                  <th className="px-3 py-2 font-semibold">Season</th>
                  <th className="px-3 py-2 font-semibold">Opp</th>
                  <th className="px-3 py-2 font-semibold text-right">GS</th>
                </tr>
              </thead>
              <tbody className="font-mono tabular-nums">
                {profile.gameScoreLeaders.map((row) => (
                  <tr
                    key={`${row.rank}-${row.player}`}
                    className="border-b border-ds-border/40 hover:bg-ds-raised/40"
                  >
                    <td className="px-3 py-2 text-ds-muted">{row.rank}</td>
                    <td className="px-3 py-2 font-sans font-medium">
                      <ReferencedLabel label={row.player} onReference={onReference} />
                    </td>
                    <td className="px-3 py-2">{row.season}</td>
                    <td className="px-3 py-2">
                      <ReferencedLabel label={row.opponent} onReference={onReference} />
                    </td>
                    <td className="px-3 py-2 text-right font-semibold text-ds-accent">
                      {row.gameScore.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}
