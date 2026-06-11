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

async function stagingGetFull<T>(
  path: string,
  params?: Record<string, string | number>,
  options?: { signal?: AbortSignal; retries?: number },
): Promise<StagingResponse<T> | null> {
  if (!USE_STAGING_API) return null
  const retries = options?.retries ?? 0
  const url = stagingUrl(path, params)

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, { signal: options?.signal })
      if (!res.ok) {
        if (attempt < retries) {
          await new Promise((r) => setTimeout(r, 400 * (attempt + 1)))
          continue
        }
        return null
      }
      return (await res.json()) as StagingResponse<T>
    } catch (err) {
      if (options?.signal?.aborted) return null
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, 400 * (attempt + 1)))
        continue
      }
      return null
    }
  }
  return null
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

export async function fetchPlayerGameLogsWithMeta(
  playerId: string,
  season: string,
  seasonType = "Regular Season",
  limit = 500,
  options?: { signal?: AbortSignal; includeAdvanced?: boolean },
) {
  const json = await stagingGetFull<Record<string, unknown>[]>(
    `/api/staging/players/${playerId}/game-logs`,
    {
      season,
      season_type: seasonType,
      limit,
      include_advanced: options?.includeAdvanced ? "true" : "false",
    },
    { signal: options?.signal, retries: 3 },
  )
  if (!json) return null
  const rows = filterGameLogRecords(json.data)
  if (!rows.length) return null
  return { ...json, data: rows, meta: { ...json.meta, count: rows.length } }
}

export async function fetchStagingSeasons() {
  return stagingGet<string[]>("/api/staging/seasons")
}

export async function fetchPlayerCareer(playerId: string) {
  return stagingGet<Record<string, unknown>[]>(`/api/staging/players/${playerId}/career`)
}

export async function fetchPlayerShotZones(
  playerId: string,
  season: string,
  seasonType = "Regular Season",
) {
  return stagingGet<Record<string, unknown>>(`/api/staging/players/${playerId}/shot-zones`, {
    season,
    season_type: seasonType,
    per_mode: "PerGame",
  })
}

export async function fetchTeamSeasonStats(
  teamId: string,
  season: string,
  seasonType = "Regular Season",
) {
  return stagingGet<Record<string, unknown>>(`/api/staging/teams/${teamId}/season-stats`, {
    season,
    season_type: seasonType,
    per_mode: "PerGame",
  })
}

export async function fetchTeamGameLogs(
  teamId: string,
  season: string,
  seasonType = "Regular Season",
) {
  return stagingGet<Record<string, unknown>[]>(`/api/staging/teams/${teamId}/game-logs`, {
    season,
    season_type: seasonType,
    limit: 82,
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

export async function fetchTeamLeaders(
  teamId: string,
  season: string,
  stat: "PTS" | "REB" | "AST",
) {
  return stagingGet<{ PLAYER_NAME?: string; value?: number }[]>(
    `/api/staging/teams/${teamId}/leaders`,
    { season, season_type: "Regular Season", stat },
  )
}
