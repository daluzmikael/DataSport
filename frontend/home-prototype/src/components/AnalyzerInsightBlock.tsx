import { Sparkles } from "lucide-react"
import { useCallback, useState } from "react"

import { postAnalysis } from "../api/analysisClient"

/** An AI summary panel backed by the real analyst.
 *
 * This used to render a canned paragraph from `playerAnalyzerMock` — the same two
 * sentences for every player, with a badge reading "Example · AI season summary". It
 * looked like generated analysis and was a fixture.
 *
 * It now calls `POST /api/analysis`, the same router → SQL → analyst pipeline the ask
 * bar uses, so the text is real. It runs ON DEMAND rather than on mount: opening a
 * profile should not spend a model call the reader never asked for.
 */
interface AnalyzerInsightBlockProps {
  title: string
  /** The question to put to the analyst when the reader asks for a summary. */
  question: string
  /** Inline green "Ask" after the summary — focuses the overlay ask bar. */
  onAsk?: () => void
}

export function AnalyzerInsightBlock({ title, question, onAsk }: AnalyzerInsightBlockProps) {
  const [text, setText] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await postAnalysis(question)
      setText(result.analysis.trim())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the analyst")
    } finally {
      setLoading(false)
    }
  }, [question])

  return (
    <section className="rounded-xl border border-ds-border bg-ds-panel p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Sparkles className="h-4 w-4 text-ds-accent" aria-hidden />
        <h3 className="text-sm font-semibold">{title}</h3>
        {text && (
          <span className="rounded-md border border-ds-accent/30 bg-ds-accent/10 px-2 py-0.5 text-[10px] font-medium text-ds-accent">
            Vault · AI
          </span>
        )}
      </div>

      {!text && !loading && (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={generate}
            className="rounded-lg border border-ds-accent/40 bg-ds-accent/10 px-3 py-1.5 text-xs font-semibold text-ds-accent transition hover:bg-ds-accent/20"
          >
            Generate summary
          </button>
          <p className="text-[11px] text-ds-muted">
            Runs a real query against the vault.
          </p>
        </div>
      )}

      {loading && (
        <p className="text-sm text-ds-muted">Reading the vault…</p>
      )}

      {error && (
        <p className="text-sm text-ds-live">
          {error}{" "}
          <button
            type="button"
            onClick={generate}
            className="font-semibold underline-offset-2 hover:underline"
          >
            Retry
          </button>
        </p>
      )}

      {text && (
        <p className="whitespace-pre-line text-sm leading-relaxed text-ds-text/90">
          {text}
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
      )}
    </section>
  )
}
