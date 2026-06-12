import { Library, Search } from "lucide-react"
import { useMemo, useState } from "react"
import { USE_STAGING_API } from "../api/config"
import type { StagingPlayerSearchHit } from "../api/stagingClient"
import { SEARCHABLE_TEAMS } from "../data/favoritesMock"
import { usePlayerVaultSearch } from "../hooks/usePlayerVaultSearch"
import { useStagingSeasonList } from "../hooks/useStagingSeasonList"
import type { FavoriteTeam } from "../types"
import { StagingBadge } from "./StagingBadge"

type SearchMode = "players" | "teams"

function matchesQuery(text: string, q: string) {
  return text.toLowerCase().includes(q.trim().toLowerCase())
}

function teamLabelForHit(hit: StagingPlayerSearchHit, latestVaultSeason: string): string {
  if (hit.lastSeason && hit.lastSeason !== latestVaultSeason) return "ret"
  return hit.teamAbbr
}

function formatSeasonSpan(
  first?: string,
  last?: string,
  count?: number,
): string | null {
  if (!first && !last) return null
  if (first && last && first !== last) {
    const seasons =
      count != null && count > 0
        ? ` · ${count} season${count === 1 ? "" : "s"} in vault`
        : ""
    return `${first} – ${last}${seasons}`
  }
  const single = last ?? first
  if (!single) return null
  return count != null && count > 1 ? `${single} · ${count} seasons` : single
}

interface PlayerLibraryPageProps {
  onOpenPlayer: (id: string) => void
  onOpenTeam: (id: string) => void
}

export function PlayerLibraryPage({ onOpenPlayer, onOpenTeam }: PlayerLibraryPageProps) {
  const [mode, setMode] = useState<SearchMode>("players")
  const [query, setQuery] = useState("")
  const { defaultSeason: latestVaultSeason } = useStagingSeasonList()
  const { results: playerResults, loading, fromApi } = usePlayerVaultSearch(
    mode === "players" ? query : "",
  )

  const teamResults = useMemo(() => {
    const q = query.trim()
    if (mode !== "teams" || q.length < 2) return [] as FavoriteTeam[]
    return SEARCHABLE_TEAMS.filter(
      (t) =>
        matchesQuery(t.name, q) || matchesQuery(t.city, q) || matchesQuery(t.abbr, q),
    )
  }, [mode, query])

  const showResults = query.trim().length >= 2
  const isPlayers = mode === "players"

  return (
    <main className="flex h-full min-w-0 flex-col overflow-hidden bg-ds-bg">
      <header className="shrink-0 border-b border-ds-border px-6 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Library className="h-5 w-5 text-ds-accent" />
            <h1 className="text-lg font-semibold">
              {isPlayers ? "Player library" : "Team library"}
            </h1>
          </div>
          <div
            className="inline-flex rounded-lg border border-ds-border bg-ds-raised p-0.5"
            role="tablist"
            aria-label="Search mode"
          >
            {(["players", "teams"] as const).map((option) => (
              <button
                key={option}
                type="button"
                role="tab"
                aria-selected={mode === option}
                onClick={() => setMode(option)}
                className={`rounded-md px-3 py-1 text-xs font-semibold transition ${
                  mode === option
                    ? "bg-ds-accent/20 text-ds-accent"
                    : "text-ds-muted hover:text-ds-text"
                }`}
              >
                {option === "players" ? "Players" : "Teams"}
              </button>
            ))}
          </div>
          <StagingBadge show={isPlayers && fromApi} />
        </div>
        <p className="mt-1 max-w-2xl text-sm text-ds-muted">
          {isPlayers
            ? "Search the full staging vault by name. Each result is one player with every season they have on file — open a profile to browse game logs, bubbles, and career data."
            : "Search all 30 NBA franchises by name, city, or abbreviation — open a team profile for standings, rosters, game logs, and season leaders."}
        </p>

        <div className="relative mt-4 max-w-xl">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ds-muted" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              isPlayers
                ? "Search players (e.g. Jordan, Durant, Curry)…"
                : "Search teams (e.g. Lakers, Boston, GSW)…"
            }
            className="w-full rounded-xl border border-ds-border bg-ds-raised py-2.5 pl-10 pr-4 text-sm outline-none ring-ds-accent/30 focus:ring-2"
            autoFocus
          />
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isPlayers && !USE_STAGING_API && (
          <p className="rounded-lg border border-ds-border bg-ds-panel px-4 py-3 text-sm text-ds-muted">
            Staging API is disabled. Set{" "}
            <code className="font-mono text-ds-text">VITE_USE_STAGING_API=true</code> and run the
            backend to search the vault.
          </p>
        )}

        {!showResults && (
          <p className="text-sm text-ds-muted">
            {isPlayers
              ? "Type at least 2 characters to search all players across every staged season."
              : "Type at least 2 characters to search all 30 NBA teams."}
          </p>
        )}

        {isPlayers && showResults && loading && (
          <p className="text-sm text-ds-muted">Searching vault…</p>
        )}

        {isPlayers && showResults && !loading && playerResults.length === 0 && (
          <p className="text-sm text-ds-muted">
            No players matched &ldquo;{query.trim()}&rdquo; in the vault.
          </p>
        )}

        {!isPlayers && showResults && teamResults.length === 0 && (
          <p className="text-sm text-ds-muted">
            No teams matched &ldquo;{query.trim()}&rdquo;.
          </p>
        )}

        {isPlayers && showResults && playerResults.length > 0 && (
          <>
            <p className="mb-3 text-xs font-medium uppercase tracking-wider text-ds-muted">
              {playerResults.length} player{playerResults.length === 1 ? "" : "s"}
            </p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {playerResults.map((hit) => {
                const span = formatSeasonSpan(
                  hit.firstSeason,
                  hit.lastSeason,
                  hit.seasonCount,
                )
                return (
                  <button
                    key={hit.nbaId}
                    type="button"
                    onClick={() => onOpenPlayer(hit.id)}
                    className="flex items-center justify-between gap-3 rounded-xl border border-ds-border bg-ds-panel px-4 py-3 text-left transition hover:border-ds-accent/40 hover:bg-ds-raised"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-ds-text">{hit.name}</p>
                      <p className="mt-0.5 text-sm text-ds-muted">
                        <span className="font-mono">
                          {teamLabelForHit(hit, latestVaultSeason)}
                        </span>
                        <span className="mx-1.5 text-ds-border">·</span>
                        <span className="font-mono text-[11px] text-ds-muted/80">
                          {hit.nbaId}
                        </span>
                      </p>
                      {span && (
                        <p className="mt-1 truncate text-[11px] text-ds-muted">{span}</p>
                      )}
                    </div>
                    <span className="shrink-0 text-xs font-semibold text-ds-accent">Open</span>
                  </button>
                )
              })}
            </div>
          </>
        )}

        {!isPlayers && showResults && teamResults.length > 0 && (
          <>
            <p className="mb-3 text-xs font-medium uppercase tracking-wider text-ds-muted">
              {teamResults.length} team{teamResults.length === 1 ? "" : "s"}
            </p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {teamResults.map((team) => (
                <button
                  key={team.id}
                  type="button"
                  onClick={() => onOpenTeam(team.id)}
                  className="flex items-center justify-between gap-3 rounded-xl border border-ds-border bg-ds-panel px-4 py-3 text-left transition hover:border-ds-accent/40 hover:bg-ds-raised"
                >
                  <div className="min-w-0">
                    <p className="font-mono text-lg font-bold text-ds-text">{team.abbr}</p>
                    <p className="truncate text-sm text-ds-muted">
                      {team.city} {team.name}
                    </p>
                  </div>
                  <span className="shrink-0 text-xs font-semibold text-ds-accent">Open</span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  )
}
