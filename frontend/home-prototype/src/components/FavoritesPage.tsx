import { Plus, Search, Star, Trash2, Users } from "lucide-react"
import { useMemo, useState } from "react"
import {
  INITIAL_FOLLOWED_PLAYERS,
  INITIAL_FOLLOWED_TEAMS,
  SEARCHABLE_PLAYERS,
  SEARCHABLE_TEAMS,
} from "../data/favoritesMock"
import type { FavoritePlayer, FavoriteTeam } from "../types"

interface FavoritesPageProps {
  onOpenPlayer: (id: string) => void
  onOpenTeam: (id: string) => void
}

function matchesQuery(text: string, q: string) {
  return text.toLowerCase().includes(q.trim().toLowerCase())
}

export function FavoritesPage({ onOpenPlayer, onOpenTeam }: FavoritesPageProps) {
  const [teams, setTeams] = useState(INITIAL_FOLLOWED_TEAMS)
  const [players, setPlayers] = useState(INITIAL_FOLLOWED_PLAYERS)
  const [query, setQuery] = useState("")

  const followedTeamIds = useMemo(() => new Set(teams.map((t) => t.id)), [teams])
  const followedPlayerIds = useMemo(() => new Set(players.map((p) => p.id)), [players])

  const searchResults = useMemo(() => {
    const q = query.trim()
    if (q.length < 2) return { teams: [] as FavoriteTeam[], players: [] as FavoritePlayer[] }
    const teamHits = SEARCHABLE_TEAMS.filter(
      (t) =>
        !followedTeamIds.has(t.id) &&
        (matchesQuery(t.name, q) ||
          matchesQuery(t.city, q) ||
          matchesQuery(t.abbr, q)),
    ).slice(0, 6)
    const playerHits = SEARCHABLE_PLAYERS.filter(
      (p) =>
        !followedPlayerIds.has(p.id) &&
        (matchesQuery(p.name, q) || matchesQuery(p.teamAbbr, q)),
    ).slice(0, 8)
    return { teams: teamHits, players: playerHits }
  }, [query, followedTeamIds, followedPlayerIds])

  const addTeam = (team: FavoriteTeam) => {
    setTeams((prev) => [...prev, team])
    setQuery("")
  }

  const addPlayer = (player: FavoritePlayer) => {
    setPlayers((prev) => [...prev, player])
    setQuery("")
  }

  const removeTeam = (id: string) => setTeams((prev) => prev.filter((t) => t.id !== id))
  const removePlayer = (id: string) => setPlayers((prev) => prev.filter((p) => p.id !== id))

  const showSearch = query.trim().length >= 2

  return (
    <main className="flex h-full min-w-0 flex-col overflow-hidden bg-ds-bg">
      <header className="shrink-0 border-b border-ds-border px-6 py-4">
        <div className="flex items-center gap-2">
          <Star className="h-5 w-5 text-ds-accent" />
          <h1 className="text-lg font-semibold">Following</h1>
        </div>
        <p className="mt-1 text-sm text-ds-muted">
          Teams and players you follow — including those not on tonight&apos;s live board. Search
          to add more.
        </p>
        <div className="relative mt-4 max-w-xl">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ds-muted" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search teams or players to follow…"
            className="w-full rounded-xl border border-ds-border bg-ds-raised py-2.5 pl-10 pr-4 text-sm outline-none ring-ds-accent/30 focus:ring-2"
          />
          {showSearch && (
            <div className="absolute left-0 right-0 top-full z-20 mt-2 max-h-64 overflow-y-auto rounded-xl border border-ds-border bg-ds-panel shadow-xl">
              {searchResults.teams.length === 0 && searchResults.players.length === 0 ? (
                <p className="px-4 py-3 text-sm text-ds-muted">No matches — try another name</p>
              ) : (
                <>
                  {searchResults.teams.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => addTeam(t)}
                      className="flex w-full items-center justify-between gap-2 border-b border-ds-border/50 px-4 py-2.5 text-left text-sm hover:bg-ds-raised"
                    >
                      <span>
                        <span className="font-semibold">{t.abbr}</span>
                        <span className="ml-2 text-ds-muted">
                          {t.city} {t.name}
                        </span>
                      </span>
                      <Plus className="h-4 w-4 shrink-0 text-ds-accent" />
                    </button>
                  ))}
                  {searchResults.players.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => addPlayer(p)}
                      className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left text-sm hover:bg-ds-raised"
                    >
                      <span>
                        {p.name}
                        <span className="ml-2 text-ds-muted">{p.teamAbbr}</span>
                      </span>
                      <Plus className="h-4 w-4 shrink-0 text-ds-accent" />
                    </button>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <section className="mb-8">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-ds-muted">
            Teams ({teams.length})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {teams.map((team) => (
              <div
                key={team.id}
                className="flex items-center justify-between rounded-xl border border-ds-border bg-ds-panel px-4 py-3"
              >
                <button
                  type="button"
                  onClick={() => onOpenTeam(team.id)}
                  className="min-w-0 flex-1 text-left transition hover:opacity-90"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-lg font-bold">{team.abbr}</span>
                    {team.isLive && (
                      <span className="rounded bg-ds-live/20 px-1.5 py-0.5 text-[10px] font-bold uppercase text-ds-live">
                        Live
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-ds-muted">
                    {team.city} {team.name}
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => removeTeam(team.id)}
                  className="rounded p-1.5 text-ds-muted hover:bg-ds-raised hover:text-ds-live"
                  title="Unfollow team"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-ds-muted">
            <Users className="h-3.5 w-3.5" />
            Players ({players.length})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {players.map((player) => (
              <div
                key={player.id}
                className="flex items-center justify-between rounded-xl border border-ds-border bg-ds-panel px-4 py-3"
              >
                <button
                  type="button"
                  onClick={() => onOpenPlayer(player.id)}
                  className="min-w-0 flex-1 text-left transition hover:opacity-90"
                >
                  <div className="flex items-center gap-2">
                    <span className="truncate font-semibold">{player.name}</span>
                    {player.isLive && (
                      <span className="shrink-0 rounded bg-ds-live/20 px-1.5 py-0.5 text-[10px] font-bold uppercase text-ds-live">
                        Live
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-ds-muted">
                    {player.teamAbbr}
                    {player.position ? ` · ${player.position}` : ""}
                    {player.seasonAvgGameScore != null && (
                      <span className="ml-2 font-mono text-ds-accent">
                        GS {player.seasonAvgGameScore.toFixed(1)}
                      </span>
                    )}
                  </p>
                  {!player.isLive && (
                    <p className="mt-0.5 text-[11px] text-ds-muted">Not on live board — tap for profile</p>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => removePlayer(player.id)}
                  className="ml-2 shrink-0 rounded p-1.5 text-ds-muted hover:bg-ds-raised hover:text-ds-live"
                  title="Unfollow player"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
