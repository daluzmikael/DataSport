import { Radio } from "lucide-react"
import { PAST_DASHBOARD_DAYS } from "../data/pastDashboardMock"
import type { LiveBoardSection } from "../hooks/useLiveBoard"
import type { DetailTarget, LiveFeedItem } from "../types"
import { LiveDashboardFeedList } from "./LiveDashboardFeedList"

interface LiveDashboardProps {
  /** Mock live items — used only when `sections` is null (API unreachable). */
  liveItems: LiveFeedItem[]
  /** Real `/api/live` sections; null → fall back to mock data. */
  sections?: LiveBoardSection[] | null
  updatedAt?: Date | null
  onOpenDetail: (target: DetailTarget) => void
}

const TONE_CLASS: Record<LiveBoardSection["tone"], string> = {
  live: "text-ds-live",
  today: "text-ds-accent",
  upcoming: "text-ds-accent",
  past: "text-ds-muted",
}

function mockSections(liveItems: LiveFeedItem[]): LiveBoardSection[] {
  return [
    { key: "mock-live", label: "Live now", tone: "live", items: liveItems },
    ...PAST_DASHBOARD_DAYS.map((day) => ({
      key: `mock-${day.label}`,
      label: day.label,
      tone: "past" as const,
      items: day.items,
    })),
  ]
}

export function LiveDashboard({ liveItems, sections, updatedAt, onOpenDetail }: LiveDashboardProps) {
  const isReal = sections != null
  const shown = sections ?? mockSections(liveItems)

  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-col border-l border-ds-border bg-ds-panel">
      <header className="shrink-0 border-b border-ds-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-ds-live" />
          <h2 className="text-sm font-semibold">Your live board</h2>
          <span
            className={`ml-auto rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
              isReal ? "bg-ds-accent/15 text-ds-accent" : "bg-ds-raised text-ds-muted"
            }`}
            title={
              isReal
                ? `NBA live feed${updatedAt ? ` · updated ${updatedAt.toLocaleTimeString()}` : ""}`
                : "Live API unreachable — showing demo data"
            }
          >
            {isReal ? "NBA live" : "Demo"}
          </span>
        </div>
        <p className="mt-1 text-[11px] leading-snug text-ds-muted">
          Teams & players you follow first, then other NBA games. Scroll for recent
          nights — tap any card for full stats.
        </p>
      </header>
      <div className="ds-scroll-y flex-1 min-h-0 space-y-4 p-3 pr-2">
        {shown.map((section, i) => (
          <section
            key={section.key}
            className={`space-y-2 ${i > 0 ? "border-t border-ds-border/60 pt-3" : ""}`}
          >
            <p
              className={`sticky top-0 z-10 -mx-1 bg-ds-panel px-1 py-1 text-[10px] font-bold uppercase tracking-wider ${TONE_CLASS[section.tone]}`}
            >
              {section.label}
            </p>
            {section.items.length === 0 && section.emptyText ? (
              <p className="px-1 text-[11px] text-ds-muted">{section.emptyText}</p>
            ) : (
              <LiveDashboardFeedList items={section.items} onOpenDetail={onOpenDetail} />
            )}
          </section>
        ))}
      </div>
    </aside>
  )
}
