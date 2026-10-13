import { useCallback, useEffect, useRef, useState } from "react"
import { LIVE_FEED } from "./data/liveState"
import { useLiveBoard } from "./hooks/useLiveBoard"
import { useAppNavigation, type NavEntry } from "./hooks/useAppNavigation"
import { postAnalysis } from "./api/analysisClient"
import { MOCK_PLAYER_NBA_IDS } from "./api/nbaIds"
import { AuthProvider, useAuth } from "./contexts/AuthContext"
import { ConversationProvider, useConversation } from "./contexts/ConversationContext"
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
import type { ChatMessage, DetailTarget } from "./types"

/**
 * Prototype aliases (`player-jokic`) only carry demo data. Unless the player is on
 * tonight's live feed (real live line), open the real vault profile instead.
 */
function normalizeDetailTarget(target: DetailTarget): DetailTarget {
  if (target?.type !== "player") return target
  const nbaId = MOCK_PLAYER_NBA_IDS[target.id]
  if (!nbaId) return target
  const onLiveFeed = LIVE_FEED.some((i) => i.kind === "followed-player" && i.id === target.id)
  return onLiveFeed ? target : { ...target, id: `nba-${nbaId}` }
}

// "Continue as demo user" lasts for the tab, so a refresh (or a deep link opened
// in the same tab) doesn't bounce back to the login screen.
const ENTERED_KEY = "ds_entered"

function readEntered(): boolean {
  try {
    return window.sessionStorage.getItem(ENTERED_KEY) === "1"
  } catch {
    return false
  }
}

function rememberEntered() {
  try {
    window.sessionStorage.setItem(ENTERED_KEY, "1")
  } catch {
    // Storage blocked: the gate just shows again on refresh.
  }
}

function AppShell() {
  const { user } = useAuth()
  const [entered, setEntered] = useState(readEntered)
  const loggedIn = entered || !!user
  // Page + overlay live in the URL / browser history (see useAppNavigation).
  const {
    entry: navEntry,
    page: nav,
    detail,
    navigatePage,
    openDetail: setDetail,
    backDetail,
    closeDetail,
  } = useAppNavigation(normalizeDetailTarget)
  const [activeThread, setActiveThread] = useState<string | null>(null)
  const [chatsOpen, setChatsOpen] = useState(false)
  // The chat opens empty. `SAMPLE_MESSAGES` seeded it with a scripted exchange that
  // read as a real answer the user had never asked for.
  const [messages, setMessages] = useState<ChatMessage[]>([])
  // The overlay entry on screen. It outlives `detail` by the slide-out animation,
  // whether the close came from the X, Escape or the browser's Back button.
  const [shownDetail, setShownDetail] = useState<NavEntry | null>(detail ? navEntry : null)
  if (detail && shownDetail?.key !== navEntry.key) setShownDetail(navEntry)
  const closingDetail = !detail && shownDetail != null
  useEffect(() => {
    if (!closingDetail) return
    const t = window.setTimeout(() => setShownDetail(null), 420)
    return () => window.clearTimeout(t)
  }, [closingDetail])
  const [contextHint, setContextHint] = useState<string | null>(null)
  const [askDraft, setAskDraft] = useState("")
  const [referenceFocusKey, setReferenceFocusKey] = useState(0)
  const { createConversation, saveMessage } = useConversation()
  // Compact conversation state from the last /api/analysis reply (entities,
  // seasons, stat focus). Sent back each turn so follow-ups resolve cheaply.
  const convStateRef = useRef<unknown>(undefined)
  const liveBoard = useLiveBoard()

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
      let convId = activeThread
      if (!convId) {
        convId = createConversation()
        setActiveThread(convId)
      }

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

      // Save user message to backend
      await saveMessage(userMsg)

      try {
        const result = await postAnalysis(text, history, convStateRef.current)
        if (result.conversationState) convStateRef.current = result.conversationState
        const assistantMsg: ChatMessage = {
          id: pendingId,
          role: "assistant",
          content: result.analysis,
          charts: result.charts,
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? assistantMsg
              : m,
          ),
        )
        // Save assistant response
        await saveMessage(assistantMsg)
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err)
        const errMsg: ChatMessage = {
          id: pendingId,
          role: "assistant",
          content: `Couldn't reach the analyzer API. Is the backend running on :8000?\n\n${detail}`,
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? errMsg
              : m,
          ),
        )
      }
    },
    [messages, activeThread, createConversation, saveMessage],
  )

  const handleAskFromDetail = useCallback(
    (prefill: string) => {
      setContextHint(prefill.slice(0, 80) + (prefill.length > 80 ? "…" : ""))
      handleSend(prefill)
      // The answer lands in the analyzer; Back returns to the overlay it was asked from.
      navigatePage("analyzer")
    },
    [handleSend, navigatePage],
  )

  if (!loggedIn) {
    return (
      <LoginGate
        onEnter={() => {
          rememberEntered()
          setEntered(true)
        }}
      />
    )
  }

  return (
    <>
      <StagingConnectionBar />
      <div className="relative flex h-full w-full overflow-hidden">
        <div className="h-full w-16 shrink-0">
          <NavRail active={nav} onNavigate={navigatePage} />
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
          <LiveDashboard
            sections={liveBoard.sections}
            updatedAt={liveBoard.updatedAt}
            onOpenDetail={setDetail}
          />
        </div>

        <ChatSidebar
          threads={[]}
          folders={[]}
          activeId={activeThread}
          onSelect={(id) => {
            convStateRef.current = undefined
            setActiveThread(id)
            setChatsOpen(false)
          }}
          open={chatsOpen}
          onClose={() => setChatsOpen(false)}
        />
      </div>
      <DetailOverlay
        target={shownDetail?.detail ?? null}
        historyKey={shownDetail?.key}
        closing={closingDetail}
        onClose={closeDetail}
        onBack={!closingDetail && shownDetail && shownDetail.depth > 1 ? backDetail : undefined}
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

export default function App() {
  return (
    <AuthProvider>
      <ConversationProvider>
        <AppShell />
      </ConversationProvider>
    </AuthProvider>
  )
}
