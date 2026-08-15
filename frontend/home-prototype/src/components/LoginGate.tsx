import { useState } from "react"
import type { FormEvent } from "react"
import { useAuth } from "../contexts/AuthContext"

interface LoginGateProps {
  onEnter: () => void
}

export function LoginGate({ onEnter }: LoginGateProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isSignup, setIsSignup] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const { login, signup } = useAuth()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      const result = isSignup
        ? await signup(email, password)
        : await login(email, password)

      if (result.success) {
        onEnter()
      } else {
        setError(result.error || "Authentication failed")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-ds-bg px-6">
      <div className="w-full max-w-md rounded-2xl border border-ds-border bg-ds-panel p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ds-accent">
            NBA · Prototype
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">DataSport</h1>
          <p className="mt-2 text-sm text-ds-muted">
            Live scores, your follows, and an AI analyzer in one place.
          </p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          <label className="block text-sm text-ds-muted">
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="mt-1.5 w-full rounded-lg border border-ds-border bg-ds-raised px-3 py-2.5 text-ds-text outline-none ring-ds-accent/40 focus:ring-2"
              disabled={submitting}
            />
          </label>
          <label className="block text-sm text-ds-muted">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1.5 w-full rounded-lg border border-ds-border bg-ds-raised px-3 py-2.5 text-ds-text outline-none ring-ds-accent/40 focus:ring-2"
              disabled={submitting}
            />
          </label>
          <button
            type="submit"
            disabled={submitting || !email || !password}
            className="w-full rounded-lg border border-ds-accent-vivid py-2.5 font-heading font-semibold text-ds-accent-vivid transition hover:bg-ds-accent-vivid/12 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Loading..." : isSignup ? "Sign up" : "Log in"}
          </button>
        </form>
        <button
          type="button"
          onClick={() => setIsSignup(!isSignup)}
          className="mt-3 w-full text-center text-sm text-ds-muted hover:text-ds-text"
          disabled={submitting}
        >
          {isSignup ? "Already have an account? Log in" : "Don't have an account? Sign up"}
        </button>
        <button
          type="button"
          onClick={onEnter}
          className="mt-4 w-full text-center text-sm text-ds-muted underline-offset-2 hover:text-ds-text hover:underline"
          disabled={submitting}
        >
          Continue as demo user
        </button>
      </div>
    </div>
  )
}
