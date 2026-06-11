import { getPlayerLiveGameInsight } from "../data/playerAnalyzerMock"

import { generateMockShots } from "../data/mockShots"

import type { PlayerGameSnapshot } from "../api/mappers"

import type { PlayerLive } from "../types"

import {

  cityMatchup,

  playerStatusClass,

  resolveHistoricalGamePageStatus,

  resolvePlayerGamePageStatus,

  trackedGameTitle,

} from "../utils/gameLabels"

import { parseStagingGameId } from "../utils/stagingGameId"

import { getGameDetail, LIVE_FEED } from "../data/mock"

import { AnalyzerInsightBlock } from "./AnalyzerInsightBlock"

import { PlayerStatBubbles } from "./PlayerStatBubbles"

import { ShotChartCourt } from "./ShotChartCourt"

import { StagingBadge } from "./StagingBadge"



interface PlayerGameDetailProps {

  player: PlayerLive

  gameId: string

  gameSnapshot?: PlayerGameSnapshot | null

  fromApi?: boolean

  onOpenGame: (gameId: string) => void

  onAsk?: () => void

}



export function PlayerGameDetail({

  player,

  gameId,

  gameSnapshot = null,

  fromApi = false,

  onOpenGame,

  onAsk,

}: PlayerGameDetailProps) {

  const isHistorical = parseStagingGameId(gameId) != null

  const viewPlayer = gameSnapshot?.player ?? player

  const game = getGameDetail(gameId)

  const status =

    isHistorical && gameSnapshot

      ? resolveHistoricalGamePageStatus(

          viewPlayer.minutes,

          gameSnapshot.gameDateLabel,

          gameSnapshot.wl,

        )

      : resolvePlayerGamePageStatus(viewPlayer, gameId)



  const title =

    isHistorical && gameSnapshot

      ? gameSnapshot.matchup.replace(/\s+vs\.?\s+/i, " vs ").replace(/\s+@\s+/i, " @ ")

      : trackedGameTitle(LIVE_FEED, game ?? null, viewPlayer)



  const mockShots = generateMockShots(player.id)

  const insight = getPlayerLiveGameInsight(player.id, gameId)



  return (

    <div className="mx-auto max-w-4xl space-y-4">

      <section className="rounded-xl border border-ds-border bg-ds-panel p-4">

        <div className="mb-2 flex items-center gap-1">

          <StagingBadge show={fromApi} />

          {isHistorical && gameSnapshot && (

            <span className="text-[10px] text-ds-muted">

              {gameSnapshot.gameDateLabel} · {gameSnapshot.matchup}

              {gameSnapshot.wl === "W" || gameSnapshot.wl === "L" ? ` · ${gameSnapshot.wl}` : ""}

            </span>

          )}

        </div>

        <div className="flex flex-wrap items-end gap-4">

          <div>

            <p className="text-[10px] font-semibold uppercase tracking-wide text-ds-muted">

              Game score

            </p>

            <p className="font-mono text-3xl font-bold tabular-nums text-ds-accent">

              {viewPlayer.gameScore.toFixed(1)}

            </p>

          </div>

          <div className="mb-1 h-10 w-px bg-ds-border" aria-hidden />

          <div className="mb-0.5">

            <p className="text-[10px] font-semibold uppercase tracking-wide text-ds-muted">

              Status

            </p>

            <p className={`text-sm font-semibold ${playerStatusClass(status.statusTone)}`}>

              {status.statusLabel}

            </p>

            <p className="text-[11px] text-ds-muted">

              {status.metaLine}

              {isHistorical ? (

                <>

                  {" "}

                  ·{" "}

                  <button

                    type="button"

                    onClick={() => onOpenGame(gameId)}

                    className="text-ds-accent underline-offset-2 hover:underline"

                  >

                    View full game

                  </button>

                </>

              ) : game && "home" in game ? (

                <>

                  {" "}

                  ·{" "}

                  <button

                    type="button"

                    onClick={() => onOpenGame(gameId)}

                    className="text-ds-accent underline-offset-2 hover:underline"

                  >

                    {cityMatchup(game.away.abbr, game.home.abbr)}

                  </button>

                </>

              ) : null}

            </p>

          </div>

        </div>



        <div className="mt-3">

          <PlayerStatBubbles mode="game" player={viewPlayer} sectionLabel="This game" />

        </div>

      </section>



      <AnalyzerInsightBlock

        title={isHistorical ? "Game read" : "Live game read"}

        badge={isHistorical ? "Example · AI game summary" : "Example · AI live summary"}

        onAsk={onAsk}

      >

        {insight}

      </AnalyzerInsightBlock>



      <section className="rounded-xl border border-ds-border bg-ds-panel p-4">

        <ShotChartCourt

          shots={mockShots}

          playerName={viewPlayer.name}

          subtitle={`${title} · ${status.metaLine} · Shot frequency`}

        />

      </section>



      <section className="rounded-xl border border-ds-border bg-ds-panel p-4">

        <h3 className="text-sm font-semibold">On/off & lineup (placeholder)</h3>

        <p className="mt-2 text-sm text-ds-muted">

          Plus/minus and stint table for {title} when API is ready.

        </p>

      </section>

    </div>

  )

}

