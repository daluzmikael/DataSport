import { Send, Sparkles } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import type { ChatMessage } from "../types"
import { MOCK_REPLIES } from "../data/mock"

interface AnalyzerPanelProps {
  messages: ChatMessage[]
  onSend: (text: string) => void
  contextHint?: string | null
  draft?: string
  onDraftChange?: (draft: string) => void
  /** Increment to focus the input (e.g. after referencing an entity) */
  focusKey?: number
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
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-ds-accent" />
          <h2 className="text-sm font-semibold">Analyzer</h2>
          <span className="rounded bg-ds-nba/20 px-1.5 py-0.5 text-[10px] font-bold text-ds-nba">
            NBA
          </span>
        </div>
        {contextHint && (
          <p className="mt-1.5 rounded-md border border-ds-accent/30 bg-ds-accent/10 px-2 py-1 text-[11px] text-ds-accent">
            Context: {contextHint}
          </p>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="mx-auto max-w-2xl space-y-4">
          {messages.length <= 1 && (
            <div className="mb-6 rounded-xl border border-ds-border bg-ds-panel/60 p-4">
              <p className="text-sm leading-relaxed text-ds-muted">
                <span className="font-medium text-ds-text">Ask anything about the NBA.</span>{" "}
                Reference live games from your board on the right — or ask historical
                questions with no game context. Follow-up questions work like a normal chat.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {STARTERS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => {
                      setDraft(q)
                    }}
                    className="rounded-full border border-ds-border px-3 py-1 text-left text-[11px] text-ds-muted transition hover:border-ds-accent/50 hover:text-ds-text"
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

      <footer className="shrink-0 border-t border-ds-border bg-ds-panel/50 px-5 py-4">
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
            className="flex-1 rounded-xl border border-ds-border bg-ds-raised px-4 py-3 text-sm outline-none ring-ds-accent/30 focus:ring-2"
          />
          <button
            type="submit"
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-ds-accent text-ds-bg transition hover:bg-ds-accent-dim disabled:opacity-40"
            disabled={!draft.trim()}
          >
            <Send className="h-5 w-5" />
          </button>
        </form>
      </footer>
    </section>
  )
}

export function pickMockReply(text: string): string {
  const lower = text.toLowerCase()
  if (lower.includes("jordan") && (lower.includes("3") || lower.includes("three"))) {
    return MOCK_REPLIES.jordan
  }
  if (lower.includes("celtics") || lower.includes("three") || lower.includes("3pt")) {
    return MOCK_REPLIES.default
  }
  return (
    "I'll pull from the vault once the live pipeline is connected. For this prototype, try a Celtics live question or ask about Jordan's three-point seasons."
  )
}
