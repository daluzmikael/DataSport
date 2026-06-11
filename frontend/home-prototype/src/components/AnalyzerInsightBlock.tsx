import { Sparkles } from "lucide-react"

interface AnalyzerInsightBlockProps {
  title: string
  badge?: string
  children: string
  /** Inline green “Ask” after the summary — focuses the overlay ask bar. */
  onAsk?: () => void
}

export function AnalyzerInsightBlock({
  title,
  badge = "Example · AI live summary",
  children,
  onAsk,
}: AnalyzerInsightBlockProps) {
  return (
    <section className="rounded-xl border border-ds-border bg-ds-panel p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Sparkles className="h-4 w-4 text-ds-accent" aria-hidden />
        <h3 className="text-sm font-semibold">{title}</h3>
        <span className="rounded-md border border-ds-accent/30 bg-ds-accent/10 px-2 py-0.5 text-[10px] font-medium text-ds-accent">
          {badge}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-ds-text/90">
        {children}
        {onAsk && (
          <>
            {" "}
            <button
              type="button"
              onClick={onAsk}
              className="font-semibold text-ds-accent underline-offset-2 hover:underline"
            >
              Ask
            </button>
          </>
        )}
      </p>
    </section>
  )
}
