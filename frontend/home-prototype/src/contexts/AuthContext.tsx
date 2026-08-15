import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react"

interface AuthUser {
  uid: string
  email: string
  token: string
}

interface AuthContextType {
  user: AuthUser | null
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  signup: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  loading: boolean
  getFreshToken: () => Promise<string | null>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

  useEffect(() => {
    const stored = localStorage.getItem("auth_user")
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (parsed.uid && parsed.token) {
          setUser(parsed)
        } else {
          localStorage.removeItem("auth_user")
        }
      } catch {
        localStorage.removeItem("auth_user")
      }
    }
    setLoading(false)
  }, [])

  const persistUser = (u: AuthUser) => {
    setUser(u)
    localStorage.setItem("auth_user", JSON.stringify(u))
  }

  const getFreshToken = useCallback(async (): Promise<string | null> => {
    return user?.token ?? null
  }, [user])

  const login = async (email: string, password: string) => {
    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Login failed")

      const authUser: AuthUser = {
        uid: data.uid,
        email,
        token: data.token,
      }
      persistUser(authUser)
      return { success: true }
    } catch (e) {
      return { success: false, error: e instanceof Error ? e.message : "Login failed" }
    }
  }

  const signup = async (email: string, password: string) => {
    try {
      const res = await fetch(`${API_URL}/api/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Signup failed")

      const authUser: AuthUser = {
        uid: data.uid,
        email,
        token: data.token,
      }
      persistUser(authUser)
      return { success: true }
    } catch (e) {
      return { success: false, error: e instanceof Error ? e.message : "Signup failed" }
    }
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem("auth_user")
  }

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, loading, getFreshToken }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
