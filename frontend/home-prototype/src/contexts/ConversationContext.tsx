import { createContext, useContext, useState, useCallback, ReactNode } from "react"
import { useAuth } from "./AuthContext"
import type { ChatMessage } from "../types"

interface ConversationContextType {
  conversationId: string | null
  createConversation: () => string
  saveMessage: (message: ChatMessage) => Promise<boolean>
  loadMessages: (id: string) => Promise<ChatMessage[]>
}

const ConversationContext = createContext<ConversationContextType | null>(null)

function generateConversationId(): string {
  return `conv-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const { user, getFreshToken } = useAuth()

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

  const createConversation = useCallback((): string => {
    const id = generateConversationId()
    setConversationId(id)
    return id
  }, [])

  const saveMessage = useCallback(
    async (message: ChatMessage): Promise<boolean> => {
      if (!user || !conversationId) return false

      try {
        const token = await getFreshToken()
        if (!token) return false

        const res = await fetch(`${API_URL}/api/history/message`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            conversationId,
            role: message.role,
            content: message.content,
          }),
        })

        return res.ok
      } catch (e) {
        console.error("Failed to save message:", e)
        return false
      }
    },
    [user, conversationId, getFreshToken, API_URL],
  )

  const loadMessages = useCallback(
    async (id: string): Promise<ChatMessage[]> => {
      if (!user) return []

      try {
        const token = await getFreshToken()
        if (!token) return []

        const res = await fetch(`${API_URL}/api/history/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        })

        if (!res.ok) return []

        const data = await res.json()
        return (data.messages || []).map((msg: any) => ({
          id: msg.id || `${Date.now()}-${Math.random()}`,
          role: msg.role,
          content: msg.content,
        }))
      } catch (e) {
        console.error("Failed to load messages:", e)
        return []
      }
    },
    [user, getFreshToken, API_URL],
  )

  return (
    <ConversationContext.Provider value={{ conversationId, createConversation, saveMessage, loadMessages }}>
      {children}
    </ConversationContext.Provider>
  )
}

export function useConversation() {
  const ctx = useContext(ConversationContext)
  if (!ctx) throw new Error("useConversation must be used within ConversationProvider")
  return ctx
}
