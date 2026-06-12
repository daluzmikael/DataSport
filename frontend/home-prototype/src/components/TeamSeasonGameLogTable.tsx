import { useRef, useState } from "react"
import { TAB_CONFIG, type GameLogTab } from "../data/playerGameLogMock"
import { useStagingTeamGameLog, useTeamVaultSeason } from "../hooks/useStagingTeam"
import { teamAbbrsFromGameLabel } from "../utils/analyzerReference"
import type { TeamProfile } from "../types"
import { AskReferenceButton } from "./AskReferenceButton"
import { StagingBadge } from "./StagingBadge"

const TABS: GameLogTab[] = ["general", "advanced", "per36", "per100"]

interface TeamSeasonGameLogTableProps {
  profile: TeamProfile
  liveGameId?: string
  onOpenGame?: (gameId: string) => void
  onReference: (label: string) => void
}

export function TeamSeasonGameLogTable({
  profile,
  liveGameId,
  onOpenGame,
  onReference,
}: TeamSeasonGameLogTableProps) {
  const { season, setSeason, seasons: seasonOptions, latestSeason } = useTeamVaultSeason(profile)
  const [tab, setTab] = useState<GameLogTab>("general")
  const avgScrollRef = useRef<HTMLDivElement>(null)
  const tableScrollRef = useRef<HTMLDivElement>(null)

  const { rows: stagingRows, averages, fromApi } = useStagingTeamGameLog(profile, season, tab)
  const columns = TAB_CONFIG[tab].columns.map((c) =>
    c.id === "game" ? c : c.id === "wl" ? { ...c, label: "W/L" } : c,
  )
  const rows = stagingRows.map((row) =>
    season === latestSeason ? row : { ...row, isLive: false },
  )
  const isCurrentSeason = season === latestSeason

  const syncScroll = (source: "avg" | "table", scrollLeft: number) => {
    const other = source === "avg" ? tableScrollRef.current : avgScrollRef.current
    if (other && other.scrollLeft !== scrollLeft) {
      other.scrollLeft = scrollLeft
    }
  }

  return (
    <section className="rounded-xl border border-ds-border bg-ds-panel">
      <div className="border-b border-ds-border px-3 py-2">
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
            <span className="text-sm font-semibold">game log</span>
            <StagingBadge show={fromApi} />
          </label>
        </div>
        <p className="text-[10px] text-ds-muted">Team box score totals · all games this season</p>
      </div>
      <div className="flex flex-wrap gap-1 border-b border-ds-border px-2 pt-2">
        {TABS.map((id) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`rounded-t-lg px-3 py-2 text-xs font-medium transition ${
              tab === id
                ? "bg-ds-raised text-ds-text"
                : "text-ds-muted hover:bg-ds-raised/50 hover:text-ds-text"
            }`}
          >
            {TAB_CONFIG[id].label}
          </button>
        ))}
      </div>

      <div
        ref={avgScrollRef}
        className="overflow-x-auto border-b border-ds-border bg-ds-raised/70"
        onScroll={(e) => syncScroll("avg", e.currentTarget.scrollLeft)}
      >
        <table className="w-max min-w-full border-collapse text-left text-xs font-mono tabular-nums">
          <tbody>
            <tr className="text-sm font-semibold text-ds-accent">
              {columns.map((col) => (
                <td
                  key={col.id}
                  className={`whitespace-nowrap px-2.5 py-2 ${
                    col.id === "game" ? "font-sans text-xs" : ""
                  }`}
                  style={{ minWidth: col.minWidth }}
                >
                  {col.id === "game" ? "Season avg" : (averages[col.id] ?? "—")}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div
        ref={tableScrollRef}
        className="max-h-[min(360px,42vh)] overflow-auto"
        onScroll={(e) => syncScroll("table", e.currentTarget.scrollLeft)}
      >
        <table className="w-max min-w-full border-collapse text-left text-xs">
          <thead className="sticky top-0 z-10 bg-ds-raised">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.id}
                  className="whitespace-nowrap border-b border-ds-border px-2.5 py-2 font-semibold uppercase tracking-wide text-ds-muted"
                  style={{ minWidth: col.minWidth }}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono tabular-nums">
            {rows.map((row) => {
              const live = isCurrentSeason && row.isLive
              return (
                <tr
                  key={row.id}
                  className={
                    live
                      ? "border-b border-ds-accent/40 bg-ds-accent/10 text-sm"
                      : "border-b border-ds-border/40 text-[11px] hover:bg-ds-raised/40"
                  }
                >
                  {columns.map((col) => {
                    const isGame = col.id === "game"
                    const display = isGame ? row.game : (row.values[col.id] ?? "—")
                    const opponents = isGame ? teamAbbrsFromGameLabel(row.game) : []
                    return (
                      <td
                        key={col.id}
                        className={`whitespace-nowrap px-2.5 ${
                          live ? "py-3" : "py-2"
                        } ${isGame ? "font-sans font-semibold" : ""} ${
                          live && isGame ? "text-ds-accent" : ""
                        }`}
                        style={{ minWidth: col.minWidth }}
                      >
                        {isGame ? (
                          <span className="inline-flex flex-wrap items-center gap-0.5">
                            {live && (
                              <span className="mr-0.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-ds-live align-middle" />
                            )}
                            {live && liveGameId && onOpenGame ? (
                              <button
                                type="button"
                                onClick={() => onOpenGame(liveGameId)}
                                className="text-ds-accent underline-offset-2 hover:underline"
                              >
                                {display}
                              </button>
                            ) : (
                              <span>{display}</span>
                            )}
                            {opponents.map((abbr) => (
                              <AskReferenceButton
                                key={abbr}
                                label={abbr}
                                onReference={onReference}
                              />
                            ))}
                          </span>
                        ) : (
                          display
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="px-3 py-1.5 text-[10px] text-ds-muted">Scroll ↔ columns · ↕ games</p>
    </section>
  )
}
