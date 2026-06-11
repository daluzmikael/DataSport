import { ChevronRight } from "lucide-react"
import type { TeamGameLive } from "../../types"

interface TeamGameCardProps {
  game: TeamGameLive
  onOpen: () => void
}

function LeaderCol({ label, lines }: { label: string; lines: { name: string; value: number }[] }) {
  return (
    <div className="min-w-0 flex-1">
      <p className="text-[9px] font-semibold uppercase tracking-wide text-ds-muted">{label}</p>
      <ul className="mt-0.5 space-y-0.5">
        {lines.map((l) => (
          <li key={l.name} className="flex justify-between gap-1 text-[11px]">
            <span className="truncate text-ds-muted">{l.name}</span>
            <span className="font-mono font-medium tabular-nums">{l.value}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function quarterLine(line: TeamGameLive["away"]["line"]): QuarterKey[] {
  const keys: QuarterKey[] = ["q1", "q2", "q3"]
  if (line.q4 != null) keys.push("q4")
  return keys
}

type QuarterKey = "q1" | "q2" | "q3" | "q4"

function formatQuarterTotals(abbr: string, line: TeamGameLive["away"]["line"]): string {
  const parts = quarterLine(line).map((k) => line[k] as number)
  return `${abbr} ${parts.join("-")}`
}

export function TeamGameCard({ game, onOpen }: TeamGameCardProps) {
  const { home, away, period, clock } = game
  const isLive = game.isLive

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group w-full rounded-xl border border-ds-border bg-ds-raised p-3 text-left transition hover:border-ds-accent/40 hover:bg-ds-raised/90"
    >
      <div className="mb-2 flex items-center justify-between">
        {isLive ? (
          <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-ds-live">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ds-live" />
            Live · Following
          </span>
        ) : (
          <span className="text-[10px] font-bold uppercase tracking-wide text-ds-muted">
            Final · Following
          </span>
        )}
        <ChevronRight className="h-4 w-4 text-ds-muted opacity-0 transition group-hover:opacity-100" />
      </div>

      {/* Score bug */}
      <div className="rounded-lg bg-ds-bg/80 px-2.5 py-2 font-mono">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] text-ds-muted">{away.name}</p>
            <p className="text-sm font-bold">{away.abbr}</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold tabular-nums">
              {away.score}
              <span className="mx-1 text-ds-muted">–</span>
              {home.score}
            </p>
            <p className="text-[10px] text-ds-muted">
              {isLive && clock ? `${period} · ${clock}` : period}
            </p>
          </div>
          <div className="min-w-0 flex-1 text-right">
            <p className="text-[10px] text-ds-muted">{home.name}</p>
            <p className="text-sm font-bold text-ds-accent">{home.abbr}</p>
          </div>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-x-3 border-t border-ds-border/60 pt-2 text-[10px] tabular-nums text-ds-muted">
          <div>
            <span className="text-ds-muted/70">By quarter </span>
            {formatQuarterTotals(away.abbr, away.line)}
          </div>
          <div className="text-right">{formatQuarterTotals(home.abbr, home.line)}</div>
        </div>
      </div>

      <div className="mt-2.5 flex gap-2">
        <LeaderCol label="PTS" lines={game.topScorers} />
        <LeaderCol label="AST" lines={game.topAssists} />
        <LeaderCol label="REB" lines={game.topRebounds} />
      </div>
    </button>
  )
}
