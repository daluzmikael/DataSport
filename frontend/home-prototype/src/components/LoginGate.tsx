interface LoginGateProps {
  onEnter: () => void
}

export function LoginGate({ onEnter }: LoginGateProps) {
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
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            onEnter()
          }}
        >
          <label className="block text-sm text-ds-muted">
            Email
            <input
              type="email"
              placeholder="you@example.com"
              className="mt-1.5 w-full rounded-lg border border-ds-border bg-ds-raised px-3 py-2.5 text-ds-text outline-none ring-ds-accent/40 focus:ring-2"
            />
          </label>
          <label className="block text-sm text-ds-muted">
            Password
            <input
              type="password"
              placeholder="••••••••"
              className="mt-1.5 w-full rounded-lg border border-ds-border bg-ds-raised px-3 py-2.5 text-ds-text outline-none ring-ds-accent/40 focus:ring-2"
            />
          </label>
          <button
            type="submit"
            className="w-full rounded-lg bg-ds-accent py-2.5 font-semibold text-ds-bg transition hover:bg-ds-accent-dim"
          >
            Log in
          </button>
        </form>
        <button
          type="button"
          onClick={onEnter}
          className="mt-4 w-full text-center text-sm text-ds-muted underline-offset-2 hover:text-ds-text hover:underline"
        >
          Continue as demo user
        </button>
      </div>
    </div>
  )
}
