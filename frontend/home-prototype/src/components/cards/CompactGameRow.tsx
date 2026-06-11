import type { CompactGame } from "../../types"

interface CompactGameRowProps {
  game: CompactGame
  onOpen: () => void
}

export function CompactGameRow({ game, onOpen }: CompactGameRowProps) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center justify-between rounded-lg border border-ds-border/80 bg-ds-panel px-3 py-2 text-left text-sm transition hover:border-ds-border hover:bg-ds-raised"
    >
      <div className="flex items-center gap-2 font-mono tabular-nums">
        <span className="w-8 text-xs text-ds-muted">{game.awayAbbr}</span>
        <span className="font-bold">
          {game.awayScore} – {game.homeScore}
        </span>
        <span className="w-8 text-xs text-ds-muted">{game.homeAbbr}</span>
      </div>
      <span className="text-[10px] text-ds-muted">
        {game.period === "Final" ? "Final" : `${game.period} ${game.clock}`.trim()}
      </span>
    </button>
  )
}
