import { Search } from "lucide-react"

interface ChartDashboardSearchProps {
  playerName: string
  placeholder: string
}

/**
 * Placeholder for per-chart dashboard queries (AI not wired yet).
 * PLAYER-CHARTS-AI-TODO: POST /api/dashboards and render by chartType — see playerChartsAiTodo.ts
 */
export function ChartDashboardSearch({
  playerName,
  placeholder,
}: ChartDashboardSearchProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-ds-border/50 bg-ds-bg/60 px-2.5 py-1.5">
      <Search className="h-3.5 w-3.5 shrink-0 text-ds-accent/80" strokeWidth={2.25} />
      <input
        type="text"
        readOnly
        placeholder={placeholder}
        className="min-w-0 flex-1 cursor-default bg-transparent text-xs text-ds-text outline-none placeholder:text-ds-muted/60"
        aria-label={`Chart question about ${playerName}`}
      />
      <span className="shrink-0 rounded bg-ds-raised px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-ds-muted">
        Soon
      </span>
    </div>
  )
}
