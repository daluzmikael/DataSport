import { resolveBoxScorePlayerId } from "../api/gameMappers"
import { mockPlayerIdFromNba } from "../api/nbaIds"
import { getBoxScoreProfileId } from "../data/gamePlayerProfiles"
import {
  getTeamBoxScore,
  teamBoxColumns,
  type GameLogTab,
  type TeamBoxRow,
} from "../data/teamBoxScoreMock"
import { AskReferenceButton, ReferencedLabel } from "./AskReferenceButton"

/** ~6 player rows visible; header sticks inside the scroll region */
const BOX_SCORE_BODY_MAX_H = "max-h-[12.75rem]"

interface TeamBoxScoreTableProps {
  teamAbbr: string
  tab: GameLogTab
  rows?: TeamBoxRow[]
  subtitle?: string
  onOpenPlayer?: (playerId: string) => void
  onReference?: (label: string) => void
}

function resolveBoxScoreOpenId(rowId: string): string | undefined {
  const mockId = getBoxScoreProfileId(rowId)
  if (mockId) return mockId
  const nbaId = resolveBoxScorePlayerId(rowId)
  if (nbaId) return mockPlayerIdFromNba(nbaId)
  return undefined
}

export function TeamBoxScoreTable({
  teamAbbr,
  tab,
  rows,
  subtitle,
  onOpenPlayer,
  onReference,
}: TeamBoxScoreTableProps) {
  const data = getTeamBoxScore(teamAbbr)
  const columns = teamBoxColumns(tab)
  const players = rows ?? data?.byTab[tab].players

  if (!players?.length) {
    return (
      <div className="rounded-xl border border-ds-border bg-ds-panel p-3 text-sm text-ds-muted">
        No box score for {teamAbbr}
      </div>
    )
  }

  return (
    <section className="flex flex-col overflow-hidden rounded-xl border border-ds-border bg-ds-panel">
      <div className="shrink-0 border-b border-ds-border px-3 py-2">
        <h3 className="text-sm font-semibold">
          <ReferencedLabel label={teamAbbr} onReference={onReference} /> box score
        </h3>
        <p className="text-[10px] text-ds-muted">
          {subtitle ?? `Tonight · use tabs above for ${data?.seasonLabel ?? "season"} team averages`}
        </p>
      </div>

      <div className={`${BOX_SCORE_BODY_MAX_H} overflow-auto`}>
        <table className="w-max min-w-full border-collapse text-left text-[11px]">
          <thead className="sticky top-0 z-10 bg-ds-raised">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.id}
                  className="whitespace-nowrap border-b border-ds-border px-2 py-1.5 font-semibold uppercase tracking-wide text-ds-muted"
                  style={{ minWidth: col.minWidth }}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono tabular-nums">
            {players.map((row) => (
              <tr
                key={row.id}
                className={`border-b border-ds-border/40 hover:bg-ds-raised/40 ${
                  row.isDnp ? "text-ds-muted/80" : ""
                }`}
              >
                {columns.map((col) => {
                  const isPlayer = col.id === "player"
                  const display = isPlayer ? row.player : (row.values[col.id] ?? "—")
                  const profileId = isPlayer ? resolveBoxScoreOpenId(row.id) : undefined

                  return (
                    <td
                      key={col.id}
                      className={`whitespace-nowrap px-2 py-1.5 ${
                        isPlayer
                          ? `font-sans font-medium ${row.isDnp ? "italic text-ds-muted" : "text-ds-text"}`
                          : ""
                      }`}
                      style={{ minWidth: col.minWidth }}
                    >
                      {isPlayer && profileId && onOpenPlayer ? (
                        <span className="inline-flex items-center gap-0.5">
                          <button
                            type="button"
                            onClick={() => onOpenPlayer(profileId)}
                            className="text-left font-medium text-ds-accent underline-offset-2 hover:underline"
                          >
                            {display}
                          </button>
                          {onReference && (
                            <AskReferenceButton
                              label={String(display)}
                              onReference={onReference}
                            />
                          )}
                        </span>
                      ) : isPlayer && onReference ? (
                        <ReferencedLabel label={String(display)} onReference={onReference} />
                      ) : (
                        display
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="shrink-0 px-3 py-1.5 text-[10px] text-ds-muted">
        Scroll ↕ for full roster · ↔ for more stats
      </p>
    </section>
  )
}
