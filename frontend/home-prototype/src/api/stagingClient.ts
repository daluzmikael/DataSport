import { API_URL, USE_STAGING_API } from "./config"

function isGameLogRecord(row: unknown): row is Record<string, unknown> {
  if (!row || typeof row !== "object") return false
  const r = row as Record<string, unknown>
  const gameId = r.GAME_ID ?? r.game_id
  const matchup = r.MATCHUP ?? r.matchup
  const hasGameId = gameId != null && String(gameId).trim().length > 0
  const hasMatchup = typeof matchup === "string" && matchup.trim().length > 0
  return hasGameId || hasMatchup
}

function filterGameLogRecords(data: unknown): Record<string, unknown>[] {
  if (!Array.isArray(data)) return []
  return data.filter(isGameLogRecord)
}

export type StagingResponse<T> = {
  success: boolean
  data: T
  meta?: Record<string, unknown>
}

const SEASON_LABEL_RE = /^\d{4}-\d{2}$/

function isSeasonList(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((item) => typeof item === "string" && SEASON_LABEL_RE.test(item))
  )
}

function stagingUrl(path: string, params?: Record<string, string | number>): string {
  const base =
    API_URL && API_URL.length > 0
      ? API_URL
      : typeof window !== "undefined"
        ? window.location.origin
        : "http://localhost:8000"
  const url = new URL(`${base}${path}`)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, String(v))
    }
  }
  return url.toString()
}

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  )
}

const inflightGets = new Map<string, Promise<StagingResponse<unknown> | null>>()

async function stagingGetFull<T>(
  path: string,
  params?: Record<string, string | number>,
  options?: { signal?: AbortSignal; retries?: number },
): Promise<StagingResponse<T> | null> {
  if (!USE_STAGING_API) return null
  const retries = options?.retries ?? 0
  const url = stagingUrl(path, params)

  const run = async (): Promise<StagingResponse<T> | null> => {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url, { signal: options?.signal })
        if (!res.ok) {
          if (attempt < retries) {
            await new Promise((r) => setTimeout(r, 500 * (attempt + 1)))
            continue
          }
          return null
        }
        return (await res.json()) as StagingResponse<T>
      } catch (err) {
        if (options?.signal?.aborted || isAbortError(err)) return null
        if (attempt < retries) {
          await new Promise((r) => setTimeout(r, 500 * (attempt + 1)))
          continue
        }
        return null
      }
    }
    return null
  }

  // React Strict Mode double-mounts share one in-flight request per URL.
  if (!options?.signal) {
    const existing = inflightGets.get(url)
    if (existing) return existing as Promise<StagingResponse<T> | null>
    const promise = run().finally(() => {
      inflightGets.delete(url)
    })
    inflightGets.set(url, promise as Promise<StagingResponse<unknown> | null>)
    return promise
  }

  return run()
}

async function stagingGet<T>(path: string, params?: Record<string, string | number>): Promise<T | null> {
  const json = await stagingGetFull<T>(path, params)
  return json?.data ?? null
}

export async function fetchStagingHealth(): Promise<{ tables: string[] } | null> {
  if (!USE_STAGING_API) return null
  try {
    const res = await fetch(stagingUrl("/api/staging/health"))
    if (!res.ok) return null
    const json = await res.json()
    return { tables: json.tables ?? [] }
  } catch {
    return null
  }
}

export type StagingPlayerSearchHit = {
  nbaId: string
  id: string
  name: string
  teamAbbr: string
  teamId?: string
  firstSeason?: string
  lastSeason?: string
  seasonCount?: number
}

function mapPlayerSearchRow(row: Record<string, unknown>): StagingPlayerSearchHit | null {
  const rawId = row.PLAYER_ID ?? row.player_id
  const nbaId = rawId != null ? String(rawId).trim() : ""
  if (!nbaId) return null
  const name = String(row.PLAYER_NAME ?? row.player_name ?? "Unknown")
  const teamAbbr = String(row.TEAM_ABBREVIATION ?? row.team_abbreviation ?? "—")
  const teamRaw = row.TEAM_ID ?? row.team_id
  const firstSeason = row.first_season ?? row.firstSeason
  const lastSeason = row.last_season ?? row.lastSeason
  const seasonCountRaw = row.season_count ?? row.seasonCount
  const seasonCount =
    seasonCountRaw != null && !Number.isNaN(Number(seasonCountRaw))
      ? Number(seasonCountRaw)
      : undefined
  return {
    nbaId,
    id: `nba-${nbaId}`,
    name,
    teamAbbr,
    teamId: teamRaw != null ? String(teamRaw) : undefined,
    firstSeason: firstSeason != null ? String(firstSeason) : undefined,
    lastSeason: lastSeason != null ? String(lastSeason) : undefined,
    seasonCount,
  }
}

/** Search the full vault by player name (all seasons, one row per player). */
export async function fetchPlayerSearch(
  q: string,
  limit = 50,
): Promise<StagingPlayerSearchHit[] | null> {
  const term = q.trim()
  if (term.length < 2) return []
  const json = await stagingGetFull<Record<string, unknown>[]>(
    "/api/staging/players/search",
    { q: term, limit },
    { retries: 2 },
  )
  if (!json?.data) return null
  return json.data
    .map((row) => mapPlayerSearchRow(row))
    .filter((h): h is StagingPlayerSearchHit => h != null)
}

export type StagingImpactProfile = {
  label: string
  tier: number
  headline_metric: string
  headline_score: number | null
  net_rating?: number | null
  usg_pct?: number | null
  pie?: number | null
  e_net_rating?: number | null
  player_name?: string
  team_abbr?: string
}

export async function fetchPlayerImpactProfile(
  playerId: string,
  season: string,
  seasonType = "Regular Season",
): Promise<StagingImpactProfile | null> {
  const json = await stagingGetFull<StagingImpactProfile>(
    `/api/staging/players/${playerId}/impact-profile`,
    { season, season_type: seasonType },
    { retries: 1 },
  )
  return json?.data ?? null
}

export async function fetchPlayerSeasonStats(
  playerId: string,
  season: string,
  seasonType = "Regular Season",
  perMode = "PerGame",
) {
  const json = await stagingGetFull<Record<string, unknown>>(
    `/api/staging/players/${playerId}/season-stats`,
    {
      season,
      season_type: seasonType,
      per_mode: perMode,
    },
    { retries: 2 },
  )
  return json?.data ?? null
}

export async function fetchPlayerGameLogSeasons(
  playerId: string,
  seasonType = "Regular Season",
): Promise<string[] | null> {
  const direct = await stagingGetFull<string[]>(
    `/api/staging/players/${playerId}/game-log-seasons`,
    { season_type: seasonType },
    { retries: 2 },
  )
  if (isSeasonList(direct?.data)) return direct!.data

  // Back-compat: older backends only expose seasons on game-logs meta.
  const probe = await stagingGetFull<Record<string, unknown>[]>(
    `/api/staging/players/${playerId}/game-logs`,
    { season: "2024-25", season_type: seasonType, limit: 1 },
    { retries: 1 },
  )
  const fromMeta = probe?.meta?.available_seasons
  if (isSeasonList(fromMeta)) return fromMeta

  return null
}

export async function fetchPlayerGameLogs(
  playerId: string,
  season: string,
  seasonType = "Regular Season",
  limit = 500,
) {
  return stagingGet<Record<string, unknown>[]>(`/api/staging/players/${playerId}/game-logs`, {
    season,
    season_type: seasonType,
    limit,
  })
}

export async function fetchPlayerGameLogSingle(playerId: string, nbaGameId: string) {
  const gid = nbaGameId.replace(/\D/g, "").padStart(10, "0")
  return stagingGet<Record<string, unknown>>(`/api/staging/players/${playerId}/game-log/${gid}`)
}

export async function fetchGameSummary(nbaGameId: string) {
  const gid = nbaGameId.replace(/\D/g, "").padStart(10, "0")
  return stagingGet<Record<string, unknown>>(`/api/staging/games/${gid}/summary`)
}

export async function fetchGameBoxScore(nbaGameId: string) {
  const gid = nbaGameId.replace(/\D/g, "").padStart(10, "0")
  return stagingGet<{
    players: Record<string, unknown>[]
    team_totals: Record<string, Record<string, unknown>>
  }>(`/api/staging/games/${gid}/box-score`)
}

export type GameLogsFetchOutcome =
  | { kind: "ok"; data: Record<string, unknown>[] }
  | { kind: "empty" }
  | { kind: "failed" }

export async function fetchPlayerGameLogsOutcome(
  playerId: string,
  season: string,
  seasonType = "Regular Season",
  limit = 500,
  options?: { includeAdvanced?: boolean },
): Promise<GameLogsFetchOutcome> {
  const json = await stagingGetFull<Record<string, unknown>[]>(
    `/api/staging/players/${playerId}/game-logs`,
    {
      season,
      season_type: seasonType,
      limit,
      include_advanced: options?.includeAdvanced ? "true" : "false",
    },
    { retries: 2 },
  )
  if (!json) return { kind: "failed" }
  const rows = filterGameLogRecords(json.data)
  if (!rows.length) return { kind: "empty" }
  return { kind: "ok", data: rows }
}

export async function fetchPlayerGameLogsWithMeta(
  playerId: string,
  season: string,
  seasonType = "Regular Season",
  limit = 500,
  options?: { signal?: AbortSignal; includeAdvanced?: boolean },
) {
  const outcome = await fetchPlayerGameLogsOutcome(playerId, season, seasonType, limit, {
    includeAdvanced: options?.includeAdvanced,
  })
  if (outcome.kind !== "ok") return null
  return {
    success: true,
    data: outcome.data,
    meta: { season, season_type: seasonType, count: outcome.data.length },
  }
}

export async function fetchStagingSeasons() {
  return stagingGet<string[]>("/api/staging/seasons")
}

export async function fetchPlayerSeasonTrends(
  playerId: string,
  seasonType = "Regular Season",
) {
  return stagingGet<Record<string, unknown>[]>(
    `/api/staging/players/${playerId}/season-trends`,
    { season_type: seasonType },
  )
}

export async function fetchLeagueScatter(
  season: string,
  xStat: string,
  yStat: string,
  options?: { minGp?: number; limit?: number },
) {
  return stagingGet<Record<string, unknown>[]>(
    "/api/staging/league/scatter",
    {
      season,
      x_stat: xStat,
      y_stat: yStat,
      min_gp: options?.minGp ?? 20,
      limit: options?.limit ?? 500,
    },
  )
}

export async function fetchLeagueLeaders(
  season: string,
  stat = "PTS",
  options?: { minGp?: number; limit?: number; highlightPlayerId?: string },
) {
  const params: Record<string, string | number> = {
    season,
    stat,
    min_gp: options?.minGp ?? 20,
    limit: options?.limit ?? 10,
  }
  if (options?.highlightPlayerId) {
    params.highlight_player_id = options.highlightPlayerId
  }
  return stagingGet<Record<string, unknown>[]>(
    "/api/staging/league/leaders",
    params,
  )
}

export async function fetchPlayerCareer(playerId: string) {
  const json = await stagingGetFull<Record<string, unknown>[]>(
    `/api/staging/players/${playerId}/career`,
    undefined,
    { retries: 2 },
  )
  return json?.data ?? null
}

export async function fetchPlayerShotZones(
  playerId: string,
  season: string,
  seasonType = "Regular Season",
  perMode: "PerGame" | "Totals" = "PerGame",
) {
  return stagingGet<Record<string, unknown>>(`/api/staging/players/${playerId}/shot-zones`, {
    season,
    season_type: seasonType,
    per_mode: perMode,
  })
}

export async function fetchTeamSeasonStats(
  teamId: string,
  season: string,
  seasonType = "Regular Season",
  measureType: "Base" | "Advanced" = "Base",
) {
  return stagingGet<Record<string, unknown>>(`/api/staging/teams/${teamId}/season-stats`, {
    season,
    season_type: seasonType,
    per_mode: "PerGame",
    measure_type: measureType,
  })
}

export async function fetchTeamGameLogSeasons(
  teamId: string,
  seasonType = "Regular Season",
): Promise<string[] | null> {
  return fetchTeamSeasons(teamId, seasonType)
}

export async function fetchTeamSeasons(
  teamId: string,
  seasonType = "Regular Season",
): Promise<string[] | null> {
  const json = await stagingGetFull<string[]>(
    `/api/staging/teams/${teamId}/seasons`,
    { season_type: seasonType },
    { retries: 2 },
  )
  if (isSeasonList(json?.data)) return json!.data
  const legacy = await stagingGetFull<string[]>(
    `/api/staging/teams/${teamId}/game-log-seasons`,
    { season_type: seasonType },
    { retries: 1 },
  )
  if (isSeasonList(legacy?.data)) return legacy!.data
  return null
}

export async function fetchTeamSeasonHistory(teamId: string, seasonType = "Regular Season") {
  return stagingGet<Record<string, unknown>[]>(`/api/staging/teams/${teamId}/season-history`, {
    season_type: seasonType,
    per_mode: "PerGame",
  })
}

export async function fetchTeamRoster(
  teamId: string,
  season: string,
  seasonType = "Regular Season",
) {
  return stagingGet<Record<string, unknown>[]>(`/api/staging/teams/${teamId}/roster`, {
    season,
    season_type: seasonType,
  })
}

export async function fetchTeamShotZones(
  teamId: string,
  season: string,
  seasonType = "Regular Season",
) {
  return stagingGet<Record<string, unknown>>(`/api/staging/teams/${teamId}/shot-zones`, {
    season,
    season_type: seasonType,
    per_mode: "PerGame",
  })
}

export async function fetchTeamGameLogs(
  teamId: string,
  season: string,
  seasonType = "Regular Season",
  options?: { includeAdvanced?: boolean },
) {
  return stagingGet<Record<string, unknown>[]>(`/api/staging/teams/${teamId}/game-logs`, {
    season,
    season_type: seasonType,
    limit: 82,
    include_advanced: options?.includeAdvanced ? "true" : "false",
  })
}

export async function fetchTeamStandings(
  teamId: string,
  season: string,
  seasonType = "Regular Season",
) {
  return stagingGet<Record<string, unknown>>(`/api/staging/teams/${teamId}/standings`, {
    season,
    season_type: seasonType,
  })
}

export async function fetchTeamAllTimeRecord(teamId: string, seasonType = "Regular Season") {
  return stagingGet<{
    total_wins?: number
    total_losses?: number
    seasons_count?: number
  }>(`/api/staging/teams/${teamId}/all-time-record`, { season_type: seasonType })
}

export async function fetchTeamBestPlayer(
  teamId: string,
  season: string,
  seasonType = "Regular Season",
  minGp = 10,
) {
  return stagingGet<{
    PLAYER_ID?: number | string
    PLAYER_NAME?: string
    game_score?: number
    GP?: number
  }>(`/api/staging/teams/${teamId}/best-player`, {
    season,
    season_type: seasonType,
    min_gp: minGp,
  })
}

export async function fetchTeamLeaders(
  teamId: string,
  season: string,
  stat: string,
  minGp = 10,
) {
  return stagingGet<Record<string, unknown>[]>(`/api/staging/teams/${teamId}/leaders`, {
    season,
    season_type: "Regular Season",
    stat,
    min_gp: minGp,
  })
}
