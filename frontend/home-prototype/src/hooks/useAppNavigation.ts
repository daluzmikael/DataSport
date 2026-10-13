/**
 * App-level navigation on the browser History API: the nav page and the detail
 * overlay live in the URL, and every page switch or overlay drill-in is its own
 * history entry, so browser Back/Forward (and mouse / trackpad back gestures) walk
 * the same path the user took.
 *
 * URL scheme (page omitted for the analyzer):
 *   ?page=players
 *   ?page=players&detail=player:nba-203999[&season=2024-25]
 *   ?page=players&detail=team:<teamId>
 *   ?page=players&detail=game:<gameId>
 *   ?page=players&detail=player-game:<playerId>&game=<gameId>
 *
 * Overlays drilled into from one page stack up as entries above that page's entry.
 * Each entry records its `depth` in that stack, so overlay Back is `history.back()`
 * and Close is `history.go(-depth)`. Closing goes back rather than pushing, so
 * Forward reopens what was just closed.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import type { DetailTarget, NavPage } from "../types"

const NAV_PAGES: readonly NavPage[] = ["analyzer", "dashboard", "social", "favorites", "players"]
const DEFAULT_PAGE: NavPage = "analyzer"
/** Query keys this hook owns; anything else in the URL is left alone. */
const NAV_PARAMS = ["page", "detail", "season", "game"] as const

export interface NavEntry {
  page: NavPage
  detail: DetailTarget
  /**
   * Overlay entries stacked on this page, counting this one (0 = the bare page).
   * 0 with a detail means the overlay has no entries of ours below it (e.g. a hash
   * change), so Close replaces the entry instead of going back.
   */
  depth: number
  /** Unique per history entry; lets the overlay restore its own scroll position. */
  key: string
}

interface HistoryState {
  dsNav: NavEntry
}

let keySeq = 0
function newKey(): string {
  keySeq += 1
  return `${Date.now().toString(36)}-${keySeq}`
}

function readState(state: unknown): NavEntry | null {
  const entry = (state as Partial<HistoryState> | null)?.dsNav
  if (!entry || !NAV_PAGES.includes(entry.page)) return null
  return entry
}

function parseDetail(params: URLSearchParams): DetailTarget {
  const raw = params.get("detail")
  if (!raw) return null
  const sep = raw.indexOf(":")
  if (sep <= 0) return null
  const type = raw.slice(0, sep)
  const id = raw.slice(sep + 1)
  if (!id) return null
  switch (type) {
    case "player": {
      const season = params.get("season")
      return season ? { type: "player", id, season } : { type: "player", id }
    }
    case "team":
      return { type: "team", id }
    case "game":
      return { type: "game", id }
    case "player-game": {
      const gameId = params.get("game")
      return gameId ? { type: "player-game", playerId: id, gameId } : null
    }
    default:
      return null
  }
}

function parseUrl(normalize: (t: DetailTarget) => DetailTarget): Pick<NavEntry, "page" | "detail"> {
  const params = new URLSearchParams(window.location.search)
  const page = params.get("page") as NavPage | null
  return {
    page: page && NAV_PAGES.includes(page) ? page : DEFAULT_PAGE,
    detail: normalize(parseDetail(params)),
  }
}

/** `:` stays literal so links read as `detail=player:nba-203999`. */
function encodeParam(value: string): string {
  return encodeURIComponent(value).replace(/%3A/gi, ":")
}

function urlFor(entry: Pick<NavEntry, "page" | "detail">): string {
  const ours: [string, string][] = []
  if (entry.page !== DEFAULT_PAGE) ours.push(["page", entry.page])
  const d = entry.detail
  if (d?.type === "player") {
    ours.push(["detail", `player:${d.id}`])
    if (d.season) ours.push(["season", d.season])
  } else if (d?.type === "team" || d?.type === "game") {
    ours.push(["detail", `${d.type}:${d.id}`])
  } else if (d?.type === "player-game") {
    ours.push(["detail", `player-game:${d.playerId}`], ["game", d.gameId])
  }
  const rest = new URLSearchParams(window.location.search)
  for (const k of NAV_PARAMS) rest.delete(k)
  const query = [
    ...ours.map(([k, v]) => `${k}=${encodeParam(v)}`),
    ...(rest.toString() ? [rest.toString()] : []),
  ].join("&")
  return `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`
}

function writeEntry(mode: "push" | "replace", entry: NavEntry) {
  const state: HistoryState = { dsNav: entry }
  if (mode === "push") window.history.pushState(state, "", urlFor(entry))
  else window.history.replaceState(state, "", urlFor(entry))
}

function sameDetail(a: DetailTarget, b: DetailTarget): boolean {
  if (!a || !b) return a === b
  return JSON.stringify(a) === JSON.stringify(b)
}

/**
 * Entry for the current history slot. A refresh keeps `history.state`, so the
 * stack below is still ours. A fresh deep link to an overlay is split into the
 * bare page plus the overlay on top, so Back / Close land on the page instead of
 * leaving the app. Idempotent (StrictMode runs state initializers twice).
 */
function bootstrapEntry(normalize: (t: DetailTarget) => DetailTarget): NavEntry {
  const existing = readState(window.history.state)
  if (existing) return existing
  const { page, detail } = parseUrl(normalize)
  const base: NavEntry = { page, detail: null, depth: 0, key: newKey() }
  writeEntry("replace", base)
  if (!detail) return base
  const top: NavEntry = { page, detail, depth: 1, key: newKey() }
  writeEntry("push", top)
  return top
}

/** `normalizeDetail` should be a stable (module-level) function. */
export function useAppNavigation(normalizeDetail: (t: DetailTarget) => DetailTarget) {
  const [entry, setEntryState] = useState<NavEntry>(() => bootstrapEntry(normalizeDetail))
  // Actions read the latest entry synchronously (two calls in one handler must chain).
  const entryRef = useRef(entry)
  const setEntry = useCallback((next: NavEntry) => {
    entryRef.current = next
    setEntryState(next)
  }, [])

  // `history.go()` is async. Actions issued before its popstate lands would push on
  // top of the entry we're leaving, so hold the latest one until the traversal ends.
  const traversingRef = useRef(false)
  const queuedRef = useRef<(() => void) | null>(null)
  const traverse = useCallback((delta: number) => {
    traversingRef.current = true
    window.history.go(delta)
    // Safety valve if the traversal never fires popstate.
    window.setTimeout(() => {
      if (!traversingRef.current) return
      traversingRef.current = false
      const queued = queuedRef.current
      queuedRef.current = null
      queued?.()
    }, 600)
  }, [])
  const whenSettled = useCallback((action: () => void) => {
    if (traversingRef.current) queuedRef.current = action
    else action()
  }, [])

  useEffect(() => {
    const onPopState = (e: PopStateEvent) => {
      let next = readState(e.state)
      if (!next) {
        // An entry we didn't write (e.g. a hash change): adopt it as a bare slot.
        const { page, detail } = parseUrl(normalizeDetail)
        next = { page, detail, depth: 0, key: newKey() }
        writeEntry("replace", next)
      }
      setEntry(next)
      if (traversingRef.current) {
        traversingRef.current = false
        const queued = queuedRef.current
        queuedRef.current = null
        queued?.()
      }
    }
    window.addEventListener("popstate", onPopState)
    return () => window.removeEventListener("popstate", onPopState)
  }, [normalizeDetail, setEntry])

  const push = useCallback(
    (next: Omit<NavEntry, "key">) => {
      const full = { ...next, key: newKey() }
      writeEntry("push", full)
      setEntry(full)
    },
    [setEntry],
  )

  /** Close the overlay and return to the page underneath it. */
  const closeDetail = useCallback(() => {
    whenSettled(() => {
      const cur = entryRef.current
      if (!cur.detail) return
      if (cur.depth > 0) {
        traverse(-cur.depth)
      } else {
        const bare: NavEntry = { page: cur.page, detail: null, depth: 0, key: newKey() }
        writeEntry("replace", bare)
        setEntry(bare)
      }
    })
  }, [setEntry, traverse, whenSettled])

  /** Previous overlay in the stack, or close when this is the first one. */
  const backDetail = useCallback(() => {
    whenSettled(() => {
      if (entryRef.current.depth > 1) traverse(-1)
      else closeDetail()
    })
  }, [closeDetail, traverse, whenSettled])

  /** Drill into a player / team / game; each target is its own history entry. */
  const openDetail = useCallback(
    (target: DetailTarget) => {
      whenSettled(() => {
        const next = normalizeDetail(target)
        if (!next) {
          closeDetail()
          return
        }
        const cur = entryRef.current
        if (sameDetail(next, cur.detail)) return
        push({ page: cur.page, detail: next, depth: cur.detail ? cur.depth + 1 : 1 })
      })
    },
    [closeDetail, normalizeDetail, push, whenSettled],
  )

  /** Switch nav page. Re-selecting the current page just closes an open overlay. */
  const navigatePage = useCallback(
    (page: NavPage) => {
      whenSettled(() => {
        const cur = entryRef.current
        if (page === cur.page) {
          if (cur.detail) closeDetail()
          return
        }
        push({ page, detail: null, depth: 0 })
      })
    },
    [closeDetail, push, whenSettled],
  )

  return { entry, page: entry.page, detail: entry.detail, navigatePage, openDetail, backDetail, closeDetail }
}
