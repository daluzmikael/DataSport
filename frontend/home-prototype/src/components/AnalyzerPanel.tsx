import { History, Send, Sparkles } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import type { ChatMessage } from "../types"

interface AnalyzerPanelProps {
  messages: ChatMessage[]
  onSend: (text: string) => void
  contextHint?: string | null
  draft?: string
  onDraftChange?: (draft: string) => void
  /** Increment to focus the input (e.g. after referencing an entity) */
  focusKey?: number
  onToggleChats?: () => void
}

const STARTERS = [
  "In the current Celtics game, who is shooting worst from three on both teams?",
  "Which season was Michael Jordan's best 3-point shooting year?",
  "Compare Tatum's game score tonight to his season average.",
]

export function AnalyzerPanel({
  messages,
  onSend,
  contextHint,
  draft: controlledDraft,
  onDraftChange,
  focusKey = 0,
  onToggleChats,
}: AnalyzerPanelProps) {
  const [internalDraft, setInternalDraft] = useState("")
  const draft = controlledDraft ?? internalDraft
  const setDraft = onDraftChange ?? setInternalDraft
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (focusKey > 0) {
      inputRef.current?.focus()
    }
  }, [focusKey])

  const submit = () => {
    const text = draft.trim()
    if (!text) return
    onSend(text)
    setDraft("")
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
  }

  return (
    <section className="flex h-full min-w-0 flex-col bg-ds-bg">
      <header className="shrink-0 border-b border-ds-border px-5 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-ds-accent-vivid" />
            <p className="text-[11px] uppercase tracking-[0.1em] text-ds-accent-vivid">
              DataSport · Analyst mode
            </p>
          </div>
          {onToggleChats && (
            <button
              type="button"
              onClick={onToggleChats}
              title="Chat history"
              className="flex h-7 w-7 items-center justify-center rounded-md text-ds-muted transition hover:bg-ds-raised hover:text-ds-text"
            >
              <History className="h-4 w-4" />
            </button>
          )}
        </div>
        {contextHint && (
          <p className="mt-1.5 rounded-md border border-ds-accent-vivid/40 bg-ds-accent-100 px-2 py-1 text-[11px] text-ds-accent">
            Context: {contextHint}
          </p>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="mx-auto max-w-2xl space-y-4">
          {messages.length <= 1 && (
            <div className="mb-6 rounded-lg border border-ds-border bg-ds-bg p-4 shadow-sm">
              <p className="text-[10px] uppercase tracking-[0.1em] text-ds-accent-vivid">
                Assistant
              </p>
              <p className="mt-1 text-sm leading-relaxed text-ds-text">
                Welcome to DataSport. Ask about any NBA stat — historical seasons, live
                games, or players you follow. Try referencing the Celtics game on the
                right, or ask something unrelated like Jordan's best three-point season.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {STARTERS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => {
                      setDraft(q)
                    }}
                    className="rounded border border-ds-accent-vivid px-2.5 py-1 text-left text-[11px] text-ds-accent-vivid transition hover:bg-ds-accent-vivid/10"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-ds-accent/20 text-ds-text"
                    : m.pending
                      ? "border border-ds-border bg-ds-panel text-ds-muted italic"
                      : "border border-ds-border bg-ds-panel text-ds-text"
                }`}
              >
                {m.content.split("\n").map((line, i) => (
                  <p key={i} className={i > 0 ? "mt-2" : ""}>
                    {line.split("**").map((part, j) =>
                      j % 2 === 1 ? (
                        <strong key={j}>{part}</strong>
                      ) : (
                        <span key={j}>{part}</span>
                      ),
                    )}
                  </p>
                ))}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <footer className="shrink-0 px-5 pb-8 pt-4">
        <form
          className="mx-auto flex max-w-2xl gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask DataSport about stats, live games, or history…"
            className="flex-1 rounded-xl border border-ds-border bg-ds-raised px-4 py-3 text-sm shadow-sm outline-none ring-ds-accent/30 focus:ring-2"
          />
          <button
            type="submit"
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-ds-accent-vivid text-ds-accent-vivid transition hover:bg-ds-accent-vivid/12 disabled:opacity-45"
            disabled={!draft.trim()}
          >
            <Send className="h-5 w-5" />
          </button>
        </form>
      </footer>
    </section>
  )
}
