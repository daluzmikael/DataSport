import { Radio } from "lucide-react"
import { PAST_DASHBOARD_DAYS } from "../data/pastDashboardMock"
import type { DetailTarget, LiveFeedItem } from "../types"
import { LiveDashboardFeedList } from "./LiveDashboardFeedList"

interface LiveDashboardProps {
  liveItems: LiveFeedItem[]
  onOpenDetail: (target: DetailTarget) => void
}

export function LiveDashboard({ liveItems, onOpenDetail }: LiveDashboardProps) {
  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-col border-l border-ds-border bg-ds-panel">
      <header className="shrink-0 border-b border-ds-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-ds-live" />
          <h2 className="text-sm font-semibold">Your live board</h2>
        </div>
        <p className="mt-1 text-[11px] leading-snug text-ds-muted">
          Teams & players you follow first, then other NBA games. Scroll for recent
          nights — tap any card for full stats.
        </p>
      </header>
      <div className="ds-scroll-y flex-1 min-h-0 space-y-4 p-3 pr-2">
        <section className="space-y-2">
          <p className="sticky top-0 z-10 -mx-1 bg-ds-panel px-1 py-1 text-[10px] font-bold uppercase tracking-wider text-ds-live">
            Live now
          </p>
          <LiveDashboardFeedList items={liveItems} onOpenDetail={onOpenDetail} />
        </section>

        {PAST_DASHBOARD_DAYS.map((day) => (
          <section key={day.label} className="space-y-2 border-t border-ds-border/60 pt-3">
            <p className="sticky top-0 z-10 -mx-1 bg-ds-panel px-1 py-1 text-[10px] font-bold uppercase tracking-wider text-ds-muted">
              {day.label}
            </p>
            <LiveDashboardFeedList items={day.items} onOpenDetail={onOpenDetail} />
          </section>
        ))}
      </div>
    </aside>
  )
}
