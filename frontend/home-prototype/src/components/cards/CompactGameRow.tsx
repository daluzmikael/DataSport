import type { CompactGame } from "../../types"

interface CompactGameRowProps {
  game: CompactGame
  onOpen: () => void
}

export function CompactGameRow({ game, onOpen }: CompactGameRowProps) {
  const scheduled = game.state === "scheduled"
  const isFinal = game.state === "final" || game.period.startsWith("Final")
  const isLive = game.state === "live"
  return (
    <button
      type="button"
      onClick={onOpen}
      disabled={scheduled}
      className={`flex w-full items-center justify-between rounded-lg border bg-ds-panel px-3 py-2 text-left text-sm transition ${
        game.followed ? "border-ds-accent/40" : "border-ds-border/80"
      } ${scheduled ? "cursor-default" : "hover:border-ds-border hover:bg-ds-raised"}`}
    >
      <div className="flex items-center gap-2 font-mono tabular-nums">
        <span className={`w-8 text-xs ${game.followed ? "text-ds-text" : "text-ds-muted"}`}>
          {game.awayAbbr}
        </span>
        {scheduled ? (
          <span className="text-xs text-ds-muted">@</span>
        ) : (
          <span className="font-bold">
            {game.awayScore} – {game.homeScore}
          </span>
        )}
        <span className={`w-8 text-xs ${game.followed ? "text-ds-text" : "text-ds-muted"}`}>
          {game.homeAbbr}
        </span>
      </div>
      <span className="flex items-center gap-1.5 text-[10px] text-ds-muted">
        {game.followed && (
          <span className="font-bold uppercase tracking-wide text-ds-accent">Following</span>
        )}
        {isLive && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ds-live" />}
        <span className={isLive ? "text-ds-live" : undefined}>
          {isFinal ? game.period : `${game.period} ${game.clock}`.trim()}
        </span>
      </span>
    </button>
  )
}
