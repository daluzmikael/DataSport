import { useCallback, useMemo, useState } from "react"
import {
  CHAT_FOLDERS,
  CHAT_THREADS,
  LIVE_FEED,
  SAMPLE_MESSAGES,
} from "./data/mock"
import { buildLiveDashboardFeed } from "./data/liveDashboardFeed"
import { AnalyzerPanel, pickMockReply } from "./components/AnalyzerPanel"
import { ChatSidebar } from "./components/ChatSidebar"
import { DetailOverlay } from "./components/DetailOverlay"
import { LiveDashboard } from "./components/LiveDashboard"
import { LoginGate } from "./components/LoginGate"
import { NavRail } from "./components/NavRail"
import { FavoritesPage } from "./components/FavoritesPage"
import { PlayerLibraryPage } from "./components/PlayerLibraryPage"
import { PlaceholderPage } from "./components/PlaceholderPage"
import { StagingConnectionBar } from "./components/StagingConnectionBar"
import type { ChatMessage, DetailTarget, NavPage } from "./types"

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [nav, setNav] = useState<NavPage>("analyzer")
  const [activeThread, setActiveThread] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>(SAMPLE_MESSAGES)
  const [detail, setDetail] = useState<DetailTarget>(null)
  const [contextHint, setContextHint] = useState<string | null>(null)
  const [askDraft, setAskDraft] = useState("")
  const [referenceFocusKey, setReferenceFocusKey] = useState(0)
  const liveFeed = useMemo(() => buildLiveDashboardFeed(LIVE_FEED), [])

  const handleReference = useCallback((label: string) => {
    setAskDraft((prev) => {
      const token = `[${label}]`
      const trimmed = prev.trimEnd()
      if (!trimmed) return `${token} `
      if (trimmed.endsWith(token)) return `${trimmed} `
      return `${trimmed} ${token} `
    })
    setContextHint(`Referenced: ${label}`)
    setReferenceFocusKey((k) => k + 1)
  }, [])

  const handleSend = useCallback((text: string) => {
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
    }
    const reply: ChatMessage = {
      id: `a-${Date.now()}`,
      role: "assistant",
      content: pickMockReply(text),
    }
    setMessages((prev) => [...prev, userMsg, reply])
    setContextHint(null)
    setAskDraft("")
  }, [])

  const handleAskFromDetail = useCallback(
    (prefill: string) => {
      setContextHint(prefill.slice(0, 80) + (prefill.length > 80 ? "…" : ""))
      handleSend(prefill)
    },
    [handleSend],
  )

  if (!loggedIn) {
    return <LoginGate onEnter={() => setLoggedIn(true)} />
  }

  return (
    <>
      <StagingConnectionBar />
      <div
        className="grid h-full w-full overflow-hidden"
        style={{ gridTemplateColumns: "5fr 10fr 50fr 35fr" }}
      >
        <NavRail active={nav} onNavigate={setNav} />
        {nav !== "favorites" && nav !== "players" && (
          <ChatSidebar
            threads={CHAT_THREADS}
            folders={CHAT_FOLDERS}
            activeId={activeThread}
            onSelect={setActiveThread}
          />
        )}
        {nav === "analyzer" && (
          <AnalyzerPanel
            messages={messages}
            onSend={handleSend}
            contextHint={contextHint}
            draft={askDraft}
            onDraftChange={setAskDraft}
            focusKey={referenceFocusKey}
          />
        )}
        {nav === "favorites" && (
          <div className="col-span-3 min-w-0" style={{ gridColumn: "2 / -1" }}>
            <FavoritesPage
              onOpenPlayer={(id) => setDetail({ type: "player", id })}
              onOpenTeam={(id) => setDetail({ type: "team", id })}
            />
          </div>
        )}
        {nav === "players" && (
          <div className="col-span-3 min-w-0" style={{ gridColumn: "2 / -1" }}>
            <PlayerLibraryPage
              onOpenPlayer={(id) => setDetail({ type: "player", id })}
            />
          </div>
        )}
        {(nav === "dashboard" || nav === "social") && (
          <PlaceholderPage page={nav} />
        )}
        {nav === "analyzer" && (
          <LiveDashboard liveItems={liveFeed} onOpenDetail={setDetail} />
        )}
        {(nav === "dashboard" || nav === "social") && (
          <aside className="flex items-center justify-center border-l border-ds-border bg-ds-panel/50 p-4 text-center text-xs text-ds-muted">
            Live board shows on the analyzer home view
          </aside>
        )}
      </div>
      <DetailOverlay
        target={detail}
        onClose={() => setDetail(null)}
        onAsk={handleAskFromDetail}
        askDraft={askDraft}
        onAskDraftChange={setAskDraft}
        onReference={handleReference}
        referenceFocusKey={referenceFocusKey}
        onOpenPlayer={(id) => setDetail({ type: "player", id })}
        onOpenPlayerGame={(playerId, gameId) =>
          setDetail({ type: "player-game", playerId, gameId })
        }
        onOpenGame={(id) => setDetail({ type: "game", id })}
        onOpenTeam={(id) => setDetail({ type: "team", id })}
      />
    </>
  )
}
