import { useCallback, useMemo, useState } from "react"
import {
  CHAT_FOLDERS,
  CHAT_THREADS,
  LIVE_FEED,
  SAMPLE_MESSAGES,
} from "./data/mock"
import { buildLiveDashboardFeed } from "./data/liveDashboardFeed"
import { postAnalysis } from "./api/analysisClient"
import { AnalyzerPanel } from "./components/AnalyzerPanel"
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
  const [chatsOpen, setChatsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(SAMPLE_MESSAGES)
  const [detail, setDetail] = useState<DetailTarget>(null)
  const [closingDetail, setClosingDetail] = useState(false)
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

  const handleSend = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: text,
      }
      const pendingId = `a-${Date.now()}`
      const pendingMsg: ChatMessage = {
        id: pendingId,
        role: "assistant",
        content: "Thinking…",
        pending: true,
      }
      const history = messages
        .filter((m) => !m.pending)
        .slice(-8)
        .map((m) => ({ role: m.role, content: m.content }))

      setMessages((prev) => [...prev, userMsg, pendingMsg])
      setContextHint(null)
      setAskDraft("")

      try {
        const result = await postAnalysis(text, history)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? { id: pendingId, role: "assistant", content: result.analysis }
              : m,
          ),
        )
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? {
                  id: pendingId,
                  role: "assistant",
                  content: `Couldn't reach the analyzer API. Is the backend running on :8000?\n\n${detail}`,
                }
              : m,
          ),
        )
      }
    },
    [messages],
  )

  const handleAskFromDetail = useCallback(
    (prefill: string) => {
      setContextHint(prefill.slice(0, 80) + (prefill.length > 80 ? "…" : ""))
      handleSend(prefill)
    },
    [handleSend],
  )

  const handleCloseDetail = useCallback(() => {
    setClosingDetail(true)
    window.setTimeout(() => {
      setDetail(null)
      setClosingDetail(false)
    }, 420)
  }, [])

  if (!loggedIn) {
    return <LoginGate onEnter={() => setLoggedIn(true)} />
  }

  return (
    <>
      <StagingConnectionBar />
      <div className="relative flex h-full w-full overflow-hidden">
        <div className="h-full w-16 shrink-0">
          <NavRail active={nav} onNavigate={setNav} />
        </div>

        <div className="min-w-0 flex-1 overflow-hidden">
          {nav === "analyzer" && (
            <AnalyzerPanel
              messages={messages}
              onSend={handleSend}
              contextHint={contextHint}
              draft={askDraft}
              onDraftChange={setAskDraft}
              focusKey={referenceFocusKey}
              onToggleChats={() => setChatsOpen((v) => !v)}
            />
          )}
          {nav === "favorites" && (
            <FavoritesPage
              onOpenPlayer={(id) => setDetail({ type: "player", id })}
              onOpenTeam={(id) => setDetail({ type: "team", id })}
            />
          )}
          {nav === "players" && (
            <PlayerLibraryPage
              onOpenPlayer={(id) => setDetail({ type: "player", id })}
              onOpenTeam={(id) => setDetail({ type: "team", id })}
            />
          )}
          {(nav === "dashboard" || nav === "social") && (
            <PlaceholderPage page={nav} />
          )}
        </div>

        <div className="h-full w-[360px] shrink-0 border-l border-ds-border">
          <LiveDashboard liveItems={liveFeed} onOpenDetail={setDetail} />
        </div>

        <ChatSidebar
          threads={CHAT_THREADS}
          folders={CHAT_FOLDERS}
          activeId={activeThread}
          onSelect={(id) => {
            setActiveThread(id)
            setChatsOpen(false)
          }}
          open={chatsOpen}
          onClose={() => setChatsOpen(false)}
        />
      </div>
      <DetailOverlay
        target={detail}
        closing={closingDetail}
        onClose={handleCloseDetail}
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
