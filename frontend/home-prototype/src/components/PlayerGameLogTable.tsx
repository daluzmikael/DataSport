import { useEffect, useRef } from "react"

import {

  gameLogRowToGameId,

  TAB_CONFIG,

} from "../data/playerGameLogMock"

import {

  CAREER_LOG_VALUE,

  usePlayerGameLogTableState,

  type PlayerGameLogTab,

} from "../hooks/useStagingPlayer"

import { teamAbbrsFromGameLabel } from "../utils/analyzerReference"

import { AskReferenceButton } from "./AskReferenceButton"

import { PlayerStatBubbles } from "./PlayerStatBubbles"

import { StagingBadge } from "./StagingBadge"



const TABS: PlayerGameLogTab[] = ["general", "advanced"]



interface PlayerGameLogTableProps {

  playerId?: string

  showLiveRow?: boolean

  liveGameId?: string

  showSeasonBubbles?: boolean

  initialSeason?: string

  onOpenPlayerGame?: (playerId: string, gameId: string) => void

  onReference?: (label: string) => void

  onSeasonChange?: (season: string) => void

}



export function PlayerGameLogTable({

  playerId = "player-tatum",

  showLiveRow = true,

  liveGameId,

  showSeasonBubbles = false,

  initialSeason,

  onOpenPlayerGame,

  onReference,

  onSeasonChange,

}: PlayerGameLogTableProps) {

  const {
    tab,
    setTab,
    season,
    setSeason,
    seasons,
    seasonsLoading,
    seasonsReady,
    seasonsFromApi,
    isCareer,
    latestSeason,
    rows: stagingRows,
    bubbles: seasonBubbles,
    bubblesFromApi,
    fromApi,
    logsLoading,
    statsLoading,
  } = usePlayerGameLogTableState(playerId, initialSeason)

  useEffect(() => {
    onSeasonChange?.(season)
  }, [season, onSeasonChange])

  const tableScrollRef = useRef<HTMLDivElement>(null)

  const { columns } = TAB_CONFIG[tab]

  const rows = (stagingRows ?? []).map((row) =>

    !isCareer && showLiveRow && season === latestSeason ? row : { ...row, isLive: false },

  )





  const seasonSelect = (

    <label className="flex items-center gap-2 text-xs text-ds-muted">

      <span className="font-medium">Season</span>

      <select

        value={season}

        onChange={(e) => setSeason(e.target.value)}

        disabled={seasonsLoading}

        className={`rounded-md border border-ds-border bg-ds-raised px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ds-accent/40 disabled:cursor-wait disabled:opacity-60 ${

          isCareer ? "font-semibold text-ds-gold" : "text-ds-text"

        }`}

      >

        {seasonsLoading ? (

          <option value={season}>Loading seasons…</option>

        ) : (

          <>

            <option value={CAREER_LOG_VALUE} className="bg-ds-raised font-semibold text-ds-gold">

              Career

            </option>

            {seasons.map((opt) => (

              <option key={opt} value={opt} className="bg-ds-raised text-ds-text">

                {opt}

              </option>

            ))}

          </>

        )}

      </select>

    </label>

  )



  const logTabs = (

    <div className="flex items-center gap-1">

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

  )



  const bubbleHeaderLeft = seasonSelect



  const logTabRow = (

    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 border-b border-ds-border px-2 pt-2">

      <div />

      {logTabs}

      <div />

    </div>

  )



  return (

    <section className="rounded-xl border border-ds-border bg-ds-panel">

      {showSeasonBubbles && !isCareer && (

        <div className="border-b border-ds-border/60 px-4 py-3">

          {statsLoading ? (

            <div className="space-y-3">

              {bubbleHeaderLeft}

              <p className="text-xs text-ds-muted">Loading season stats…</p>

            </div>

          ) : seasonBubbles ? (

            <PlayerStatBubbles

              mode="season"

              season={seasonBubbles}

              headerLeft={bubbleHeaderLeft}

              bubblesFromApi={bubblesFromApi}

            />

          ) : (

            <div className="space-y-3">

              {bubbleHeaderLeft}

              <p className="text-xs text-ds-muted">Season stats unavailable for {season}.</p>

            </div>

          )}

        </div>

      )}



      {showSeasonBubbles && !isCareer && logTabRow}



      {(!showSeasonBubbles || isCareer) && (

        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 border-b border-ds-border px-2 pt-2">

          <div className="flex items-center justify-start gap-3">

            {seasonSelect}

          </div>

          {logTabs}

          <div className="flex items-center justify-end">

            <StagingBadge show={fromApi || seasonsFromApi || bubblesFromApi} />

          </div>

        </div>

      )}



      <div

        ref={tableScrollRef}

        className="max-h-[min(300px,42vh)] overflow-auto"

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

                  {col.id === "game" && isCareer ? "Summary" : col.label}

                </th>

              ))}

            </tr>

          </thead>

          <tbody className="font-mono tabular-nums">

            {logsLoading && (

              <tr>

                <td

                  colSpan={columns.length}

                  className="px-2.5 py-8 text-center text-xs text-ds-muted"

                >

                  {isCareer ? "Loading career summaries…" : "Loading game logs…"}

                </td>

              </tr>

            )}

            {seasonsReady && !logsLoading && rows.length === 0 && (

              <tr>

                <td

                  colSpan={columns.length}

                  className="px-2.5 py-8 text-center text-xs text-ds-muted"

                >

                  {isCareer
                    ? "No career summaries found for this player."
                    : `No games found for ${season}.`}

                </td>

              </tr>

            )}

            {!logsLoading && rows.map((row) => {

              const live = row.isLive

              return (

                <tr

                  key={row.id}

                  className={

                    live

                      ? "border-b border-ds-accent/40 bg-ds-accent/10 text-sm"

                      : isCareer

                        ? "border-b border-ds-border/40 text-[11px] hover:bg-ds-raised/40"

                        : "border-b border-ds-border/40 text-[11px] hover:bg-ds-raised/40"

                  }

                >

                  {columns.map((col) => {

                    const gameCol = col.id === "game"

                    const raw = gameCol ? row.game : row.values[col.id]

                    const display = raw ?? "—"

                    const opponents =

                      !isCareer && gameCol ? teamAbbrsFromGameLabel(String(row.game)) : []

                    return (

                      <td

                        key={col.id}

                        className={`whitespace-nowrap px-2.5 ${

                          live ? "py-3" : "py-2"

                        } ${gameCol ? "font-sans font-semibold" : ""} ${

                          live && gameCol ? "text-ds-accent" : ""

                        } ${isCareer && gameCol ? "text-ds-gold" : ""}`}

                        style={{ minWidth: col.minWidth }}

                      >

                        {gameCol && onReference && !isCareer ? (

                          <span className="inline-flex flex-wrap items-center gap-0.5">

                            {live && (

                              <span className="mr-0.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-ds-live align-middle" />

                            )}

                            {onOpenPlayerGame ? (

                              <button

                                type="button"

                                onClick={() =>

                                  onOpenPlayerGame(

                                    playerId,

                                    live && liveGameId

                                      ? liveGameId

                                      : gameLogRowToGameId(row.id),

                                  )

                                }

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

                          <>

                            {live && gameCol && (

                              <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-ds-live align-middle" />

                            )}

                            {gameCol && onOpenPlayerGame && !isCareer ? (

                              <button

                                type="button"

                                onClick={() =>

                                  onOpenPlayerGame(

                                    playerId,

                                    live && liveGameId

                                      ? liveGameId

                                      : gameLogRowToGameId(row.id),

                                  )

                                }

                                className="text-ds-accent underline-offset-2 hover:underline"

                              >

                                {display}

                              </button>

                            ) : (

                              display

                            )}

                          </>

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



      <div className="flex items-center justify-end border-t border-ds-border px-3 py-2">

        <p className="text-[10px] text-ds-muted">

          {isCareer ? "Scroll ↔ columns · career summaries" : "Scroll ↔ columns · ↕ games"}

        </p>

      </div>

    </section>

  )

}

