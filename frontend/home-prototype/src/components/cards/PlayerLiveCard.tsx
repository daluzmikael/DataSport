import { ChevronRight } from "lucide-react"
import type { PlayerLive } from "../../types"

interface PlayerLiveCardProps {
  player: PlayerLive
  onOpen: () => void
}

import { LIVE_FEED } from "../../data/mock"
import { isPlayerInLiveGame, playerStatusClass, resolvePlayerCardStatus } from "../../utils/gameLabels"

export function PlayerLiveCard({ player, onOpen }: PlayerLiveCardProps) {
  const view = resolvePlayerCardStatus(player, LIVE_FEED)
  const isFinal = player.period === "Final"

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group w-full rounded-xl border border-ds-border bg-ds-raised/70 p-2.5 text-left transition hover:border-ds-accent/40"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{player.name}</p>
          <p className="text-[10px] text-ds-muted">
            {player.teamAbbr} vs {player.opponentAbbr}
            {isFinal ? " · Final" : ` · ${player.period} ${player.clock}`.trim()}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="font-mono text-xs font-bold text-ds-accent">
            GS {player.gameScore.toFixed(1)}
          </p>
          <ChevronRight className="ml-auto h-3.5 w-3.5 text-ds-muted opacity-0 group-hover:opacity-100" />
        </div>
      </div>
      <p className="mt-1.5 text-[11px] text-ds-muted">
        {player.minutes} min
        {(isPlayerInLiveGame(player, LIVE_FEED) || isFinal) && (
          <>
            {" · "}
            <span className={playerStatusClass(view.statusTone)}>
              {view.statusLabel}
            </span>
          </>
        )}
      </p>
      <div className="mt-2 grid grid-cols-5 gap-1 rounded-md bg-ds-bg/60 px-2 py-1.5 text-center text-[10px]">
        <Stat label="FG" value={player.fg} />
        <Stat label="3P" value={player.fg3} />
        <Stat label="REB" value={String(player.reb)} />
        <Stat label="AST" value={String(player.ast)} />
        <Stat label="TOV" value={String(player.tov)} />
      </div>
    </button>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[9px] uppercase text-ds-muted">{label}</p>
      <p className="font-mono font-semibold tabular-nums">{value}</p>
    </div>
  )
}
