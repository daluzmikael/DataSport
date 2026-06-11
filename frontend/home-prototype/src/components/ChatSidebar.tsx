import { ChevronDown, ChevronRight, Folder, Plus, Search } from "lucide-react"
import { useState } from "react"
import type { ChatFolder, ChatThread } from "../types"

interface ChatSidebarProps {
  threads: ChatThread[]
  folders: ChatFolder[]
  activeId: string | null
  onSelect: (id: string) => void
}

export function ChatSidebar({ threads, folders, activeId, onSelect }: ChatSidebarProps) {
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({
    live: true,
    projects: true,
  })

  const unfiled = threads.filter((t) => !t.folder)

  const toggle = (id: string) =>
    setOpenFolders((prev) => ({ ...prev, [id]: !prev[id] }))

  return (
    <aside className="flex h-full min-w-0 flex-col border-r border-ds-border bg-ds-panel/80">
      <div className="flex items-center justify-between border-b border-ds-border px-3 py-2.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-ds-muted">
          Chats
        </span>
        <button
          type="button"
          className="rounded p-1 text-ds-muted hover:bg-ds-raised hover:text-ds-text"
          title="New chat"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      <div className="px-2 py-2">
        <div className="flex items-center gap-2 rounded-lg border border-ds-border bg-ds-raised px-2 py-1.5">
          <Search className="h-3.5 w-3.5 shrink-0 text-ds-muted" />
          <input
            type="search"
            placeholder="Search…"
            className="w-full bg-transparent text-xs outline-none placeholder:text-ds-muted"
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-1 pb-2 text-sm">
        {folders.map((folder) => {
          const items = threads.filter((t) => t.folder === folder.id)
          const open = openFolders[folder.id] ?? true
          return (
            <div key={folder.id} className="mb-1">
              <button
                type="button"
                onClick={() => toggle(folder.id)}
                className="flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-ds-muted hover:bg-ds-raised hover:text-ds-text"
              >
                {open ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" />
                )}
                <Folder className="h-3.5 w-3.5" />
                <span className="truncate font-medium">{folder.name}</span>
              </button>
              {open &&
                items.map((t) => (
                  <ThreadButton
                    key={t.id}
                    thread={t}
                    active={activeId === t.id}
                    onSelect={onSelect}
                    indent
                  />
                ))}
            </div>
          )
        })}
        {unfiled.length > 0 && (
          <div className="mt-2">
            <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-ds-muted">
              Recent
            </p>
            {unfiled.map((t) => (
              <ThreadButton
                key={t.id}
                thread={t}
                active={activeId === t.id}
                onSelect={onSelect}
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}

function ThreadButton({
  thread,
  active,
  onSelect,
  indent,
}: {
  thread: ChatThread
  active: boolean
  onSelect: (id: string) => void
  indent?: boolean
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(thread.id)}
      className={`mb-0.5 w-full rounded-md px-2 py-2 text-left transition ${
        indent ? "ml-5 mr-1 w-[calc(100%-1.25rem)]" : "mx-1 w-[calc(100%-0.5rem)]"
      } ${
        active
          ? "bg-ds-accent/15 text-ds-text"
          : "text-ds-muted hover:bg-ds-raised hover:text-ds-text"
      }`}
    >
      <p className="truncate text-xs font-medium">{thread.title}</p>
      <p className="text-[10px] text-ds-muted">{thread.updatedAt}</p>
    </button>
  )
}
