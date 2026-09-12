import { Radio } from "lucide-react"
import { useVaultGameBoard } from "../hooks/useVaultGameBoard"
import type { DetailTarget, LiveFeedItem } from "../types"
import { LiveDashboardFeedList } from "./LiveDashboardFeedList"

interface LiveDashboardProps {
  liveItems: LiveFeedItem[]
  onOpenDetail: (target: DetailTarget) => void
}

export function LiveDashboard({ liveItems, onOpenDetail }: LiveDashboardProps) {
  const { days, loading } = useVaultGameBoard()

  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-col border-l border-ds-border bg-ds-panel">
      <header className="shrink-0 border-b border-ds-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-ds-live" />
          <h2 className="text-sm font-semibold">Your live board</h2>
        </div>
        <p className="mt-1 text-[11px] leading-snug text-ds-muted">
          Teams &amp; players you follow first, then other NBA games. Scroll for recent
          nights — tap any card for full stats.
        </p>
      </header>
      <div className="ds-scroll-y flex-1 min-h-0 space-y-4 p-3 pr-2">
        <section className="space-y-2">
          <p className="sticky top-0 z-10 -mx-1 bg-ds-panel px-1 py-1 text-[10px] font-bold uppercase tracking-wider text-ds-live">
            Live now
          </p>
          {liveItems.length > 0 ? (
            <LiveDashboardFeedList items={liveItems} onOpenDetail={onOpenDetail} />
          ) : (
            <p className="rounded-lg border border-dashed border-ds-border/70 px-3 py-2 text-[11px] leading-snug text-ds-muted">
              No games in progress. Live scores need the live API, which isn&apos;t wired
              up yet — the results below are real games from the vault.
            </p>
          )}
        </section>

        {loading && !days && (
          <p className="px-1 py-2 text-[11px] text-ds-muted">Loading recent games…</p>
        )}

        {days?.map((day) => (
          <section key={day.date} className="space-y-2 border-t border-ds-border/60 pt-3">
            <p className="sticky top-0 z-10 -mx-1 bg-ds-panel px-1 py-1 text-[10px] font-bold uppercase tracking-wider text-ds-muted">
              {day.label}
            </p>
            <LiveDashboardFeedList items={day.items} onOpenDetail={onOpenDetail} />
          </section>
        ))}

        {days?.length === 0 && !loading && (
          <p className="px-1 py-2 text-[11px] text-ds-muted">
            No games found in the vault.
          </p>
        )}
      </div>
    </aside>
  )
}
