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
      className="flex h-full min-w-0 flex-col items-center bg-ds-nav-bg py-5"
      aria-label="Main navigation"
    >
      <div className="mb-6 flex h-8 w-8 items-center justify-center rounded-md border border-ds-nav-icon-active font-heading text-sm font-semibold text-ds-nav-icon-active">
        DS
      </div>
      <div className="flex flex-1 flex-col gap-1.5">
        {pages.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            type="button"
            title={label}
            onClick={() => onNavigate(id)}
            className={`flex h-10 w-10 items-center justify-center rounded-md transition ${
              active === id
                ? "bg-ds-nav-icon-active-bg text-ds-nav-icon-active"
                : "text-ds-nav-icon hover:text-ds-nav-icon-active"
            }`}
          >
            <Icon className="h-[19px] w-[19px]" strokeWidth={1.75} />
          </button>
        ))}
        <button
          type="button"
          title="Charts (coming soon)"
          className="flex h-10 w-10 cursor-not-allowed items-center justify-center rounded-md text-ds-nav-icon-muted"
          disabled
        >
          <BarChart3 className="h-[19px] w-[19px]" strokeWidth={1.75} />
        </button>
      </div>
      <div className="mt-auto flex flex-col gap-1.5 border-t border-ds-nav-border pt-3">
        <button
          type="button"
          title="Account (coming soon)"
          className="flex h-10 w-10 cursor-not-allowed items-center justify-center rounded-md text-ds-nav-icon-muted"
          disabled
        >
          <User className="h-[19px] w-[19px]" strokeWidth={1.75} />
        </button>
        <button
          type="button"
          title="Settings (coming soon)"
          className="flex h-10 w-10 cursor-not-allowed items-center justify-center rounded-md text-ds-nav-icon-muted"
          disabled
        >
          <Settings className="h-[19px] w-[19px]" strokeWidth={1.75} />
        </button>
      </div>
    </nav>
  )
}
