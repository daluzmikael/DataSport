import { Radio } from "lucide-react"
import { useVaultGameBoard } from "../hooks/useVaultGameBoard"
import type { LiveBoardSection } from "../hooks/useLiveBoard"
import type { DetailTarget } from "../types"
import { LiveDashboardFeedList } from "./LiveDashboardFeedList"

interface LiveDashboardProps {
  /** Real `/api/live` sections; null → the live API is unreachable, show the vault board. */
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

export function LiveDashboard({ sections, updatedAt, onOpenDetail }: LiveDashboardProps) {
  const isLive = sections != null
  const { days, loading } = useVaultGameBoard()

  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-col border-l border-ds-border bg-ds-panel">
      <header className="shrink-0 border-b border-ds-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-ds-live" />
          <h2 className="text-sm font-semibold">Your live board</h2>
          <span
            className={`ml-auto rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
              isLive ? "bg-ds-accent/15 text-ds-accent" : "bg-ds-raised text-ds-muted"
            }`}
            title={
              isLive
                ? `NBA live feed${updatedAt ? ` · updated ${updatedAt.toLocaleTimeString()}` : ""}`
                : "Live API unreachable — showing recent games from the vault"
            }
          >
            {isLive ? "NBA live" : "Vault"}
          </span>
        </div>
        <p className="mt-1 text-[11px] leading-snug text-ds-muted">
          Teams &amp; players you follow first, then other NBA games. Scroll for recent
          nights — tap any card for full stats.
        </p>
      </header>
      <div className="ds-scroll-y flex-1 min-h-0 space-y-4 p-3 pr-2">
        {isLive ? (
          sections.map((section, i) => (
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
          ))
        ) : (
          <>
            <section className="space-y-2">
              <p className="sticky top-0 z-10 -mx-1 bg-ds-panel px-1 py-1 text-[10px] font-bold uppercase tracking-wider text-ds-live">
                Live now
              </p>
              <p className="rounded-lg border border-dashed border-ds-border/70 px-3 py-2 text-[11px] leading-snug text-ds-muted">
                The live feed isn&apos;t reachable right now — the results below are real
                games from the vault.
              </p>
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
          </>
        )}
      </div>
    </aside>
  )
}
