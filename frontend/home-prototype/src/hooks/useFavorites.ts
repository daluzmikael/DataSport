/** Followed teams and players — the user's own list, kept in localStorage.
 *
 * `favoritesMock` shipped four teams and six players as everyone's starting follows,
 * plus a hand-written `SEARCHABLE_TEAMS` of 30 entries that had to be kept in sync
 * with the vault by hand. Follows are user state, so they persist per browser and
 * start empty; the searchable team list now comes from `/api/staging/teams`.
 */
import { useCallback, useEffect, useState } from "react"

import type { FavoritePlayer, FavoriteTeam } from "../types"

const TEAMS_KEY = "datasport.followed.teams.v1"
const PLAYERS_KEY = "datasport.followed.players.v1"

function read<T>(key: string): T[] {
  if (typeof window === "undefined") return []
  try {
    const raw = window.localStorage.getItem(key)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? (parsed as T[]) : []
  } catch {
    return []
  }
}

function write<T>(key: string, value: T[]): void {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // A full or disabled localStorage is not worth breaking the page over.
  }
}

export function useFollowedTeams() {
  const [teams, setTeams] = useState<FavoriteTeam[]>(() => read<FavoriteTeam>(TEAMS_KEY))

  useEffect(() => {
    write(TEAMS_KEY, teams)
  }, [teams])

  const add = useCallback((team: FavoriteTeam) => {
    setTeams((prev) => (prev.some((t) => t.id === team.id) ? prev : [...prev, team]))
  }, [])

  const remove = useCallback((id: string) => {
    setTeams((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return { teams, add, remove, setTeams }
}

export function useFollowedPlayers() {
  const [players, setPlayers] = useState<FavoritePlayer[]>(() =>
    read<FavoritePlayer>(PLAYERS_KEY),
  )

  useEffect(() => {
    write(PLAYERS_KEY, players)
  }, [players])

  const add = useCallback((player: FavoritePlayer) => {
    setPlayers((prev) => (prev.some((p) => p.id === player.id) ? prev : [...prev, player]))
  }, [])

  const remove = useCallback((id: string) => {
    setPlayers((prev) => prev.filter((p) => p.id !== id))
  }, [])

  return { players, add, remove, setPlayers }
}
