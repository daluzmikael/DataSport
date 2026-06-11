import { getPlayerSeasonInsight } from "../data/playerAnalyzerMock"
import { getPlayerAccolades } from "../data/playerAccoladesMock"
import { useStagingPlayerCareerTotals } from "../hooks/useStagingPlayer"
import { generateMockShots } from "../data/mockShots"
import { LIVE_FEED } from "../data/mock"
import type { PlayerLive } from "../types"
import { isPlayerInLiveGame, resolvePlayerGameId } from "../utils/gameLabels"
import { AnalyzerInsightBlock } from "./AnalyzerInsightBlock"
import { PlayerGameLogTable } from "./PlayerGameLogTable"
import { ReferencedLabel } from "./AskReferenceButton"
import { ShotChartCourt } from "./ShotChartCourt"

interface PlayerProfileDetailProps {
  player: PlayerLive
  initialSeason?: string
  onOpenPlayerGame: (playerId: string, gameId: string) => void
  onReference: (label: string) => void
  onAsk?: () => void
}

function PlayerAccoladesRow({ playerId }: { playerId: string }) {
  const { careerTotals } = useStagingPlayerCareerTotals(playerId)
  const stats = getPlayerAccolades(playerId, careerTotals)

  return (
    <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-8">
      {stats.map((item, index) => (
        <div
          key={`${item.label}-${index}`}
          className="min-w-0 rounded-lg border border-ds-border/80 bg-ds-bg/50 px-1 py-1.5 text-center"
        >
          {item.label ? (
            <p className="truncate text-[8px] font-semibold uppercase tracking-wide text-ds-muted">
              {item.label}
            </p>
          ) : (
            <p className="text-[8px] text-transparent" aria-hidden>
              —
            </p>
          )}
          <p className="mt-0.5 truncate font-mono text-sm font-bold leading-tight tabular-nums text-ds-text sm:text-base">
            {item.value}
          </p>
          {item.subline && (
            <p className="mt-0.5 truncate text-[9px] leading-tight text-ds-muted">
              {item.subline}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

export function PlayerProfileDetail({
  player,
  initialSeason,
  onOpenPlayerGame,
  onReference,
  onAsk,
}: PlayerProfileDetailProps) {
  const seasonInsight = getPlayerSeasonInsight(player.id)
  const mockShots = generateMockShots(player.id)
  const liveGameId = isPlayerInLiveGame(player, LIVE_FEED)
    ? resolvePlayerGameId(player, LIVE_FEED)
    : undefined

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <AnalyzerInsightBlock
        title="Season overview"
        badge="Example · AI season summary"
        onAsk={onAsk}
      >
        {seasonInsight}
      </AnalyzerInsightBlock>

      <section className="rounded-xl border border-ds-border bg-ds-panel p-4">
        <PlayerAccoladesRow playerId={player.id} />
      </section>

      <PlayerGameLogTable
        key={`${player.id}-${initialSeason ?? ""}`}
        playerId={player.id}
        initialSeason={initialSeason}
        showSeasonBubbles
        showLiveRow={Boolean(liveGameId)}
        liveGameId={liveGameId}
        onOpenPlayerGame={onOpenPlayerGame}
        onReference={onReference}
      />

      <section className="rounded-xl border border-ds-border bg-ds-panel p-4">
        <ShotChartCourt
          shots={mockShots}
          playerName={player.name}
          subtitle="2024-25 season · Shot frequency"
        />
        <p className="mt-3 text-xs leading-relaxed text-ds-muted">
          Interested in a previous year&apos;s shot map? Ask the chat for a heat map of last
          year compared to this year for a better look — e.g.{" "}
          <ReferencedLabel label={player.name} onReference={onReference} /> 2023-24 vs
          2024-25.
        </p>
      </section>
    </div>
  )
}
