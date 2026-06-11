import type { NavPage } from "../types"

const copy: Record<Exclude<NavPage, "analyzer" | "favorites">, { title: string; body: string }> = {
  dashboard: {
    title: "Dashboard",
    body: "Chart-first view: leaderboards, trends, shot charts. This tab switches the main canvas away from chat (not built in prototype).",
  },
  social: {
    title: "Social",
    body: "See what others are asking and discussing. Placeholder for community feed.",
  },
}

export function PlaceholderPage({
  page,
}: {
  page: Exclude<NavPage, "analyzer" | "favorites">
}) {
  const { title, body } = copy[page]
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="max-w-md rounded-2xl border border-ds-border bg-ds-panel p-8 text-center">
        <h2 className="text-xl font-bold">{title}</h2>
        <p className="mt-3 text-sm text-ds-muted">{body}</p>
        <p className="mt-4 text-xs text-ds-muted">
          Use the analyzer icon in the left nav to return to the home layout.
        </p>
      </div>
    </div>
  )
}
