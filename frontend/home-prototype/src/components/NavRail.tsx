import {
  BarChart3,
  LayoutDashboard,
  Library,
  MessageSquare,
  Settings,
  Star,
  User,
  Users,
} from "lucide-react"
import type { NavPage } from "../types"

interface NavRailProps {
  active: NavPage
  onNavigate: (page: NavPage) => void
}

const pages: { id: NavPage; icon: typeof MessageSquare; label: string }[] = [
  { id: "analyzer", icon: MessageSquare, label: "Analyzer" },
  { id: "players", icon: Library, label: "Players" },
  { id: "favorites", icon: Star, label: "Following" },
  { id: "dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { id: "social", icon: Users, label: "Social" },
]

export function NavRail({ active, onNavigate }: NavRailProps) {
  return (
    <nav
      className="flex h-full min-w-0 flex-col items-center border-r border-ds-border bg-ds-panel py-3"
      aria-label="Main navigation"
    >
      <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-ds-accent/15 text-sm font-bold text-ds-accent">
        DS
      </div>
      <div className="flex flex-1 flex-col gap-1">
        {pages.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            type="button"
            title={label}
            onClick={() => onNavigate(id)}
            className={`flex h-10 w-10 items-center justify-center rounded-lg transition ${
              active === id
                ? "bg-ds-accent/20 text-ds-accent"
                : "text-ds-muted hover:bg-ds-raised hover:text-ds-text"
            }`}
          >
            <Icon className="h-5 w-5" strokeWidth={1.75} />
          </button>
        ))}
        <button
          type="button"
          title="Charts (coming soon)"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-ds-muted/50"
          disabled
        >
          <BarChart3 className="h-5 w-5" strokeWidth={1.75} />
        </button>
      </div>
      <div className="mt-auto flex flex-col gap-1 border-t border-ds-border pt-3">
        <button
          type="button"
          title="Account"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-ds-muted hover:bg-ds-raised hover:text-ds-text"
        >
          <User className="h-5 w-5" strokeWidth={1.75} />
        </button>
        <button
          type="button"
          title="Settings"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-ds-muted hover:bg-ds-raised hover:text-ds-text"
        >
          <Settings className="h-5 w-5" strokeWidth={1.75} />
        </button>
      </div>
    </nav>
  )
}
