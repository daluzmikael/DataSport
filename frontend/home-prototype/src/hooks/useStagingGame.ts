import { useEffect, useState } from "react"
import { fetchGameBoxScore, fetchGameSummary } from "../api/stagingClient"
import {
  mapBoxScorePlayerRow,
  mapStagingGameSummary,
  mapTeamGameTotals,
  type StagingGameSummary,
} from "../api/gameMappers"
import type { GameLogTab } from "../data/playerGameLogMock"
import type { TeamBoxRow } from "../data/teamBoxScoreMock"

export function useStagingGame(nbaGameId: string | null) {
  const [summary, setSummary] = useState<StagingGameSummary | null>(null)
  const [players, setPlayers] = useState<Record<string, unknown>[] | null>(null)
  const [teamTotals, setTeamTotals] = useState<Record<string, Record<string, unknown>> | null>(
    null,
  )
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    if (!nbaGameId) {
      setSummary(null)
      setPlayers(null)
      setTeamTotals(null)
      setFromApi(false)
      return
    }
    let cancelled = false
    ;(async () => {
      const [sum, box] = await Promise.all([
        fetchGameSummary(nbaGameId),
        fetchGameBoxScore(nbaGameId),
      ])
      if (cancelled) return
      if (!sum && !box?.players?.length) {
        setFromApi(false)
        return
      }
      setSummary(sum ? mapStagingGameSummary(sum) : null)
      setPlayers(box?.players ?? [])
      setTeamTotals(box?.team_totals ?? {})
      setFromApi(true)
    })()
    return () => {
      cancelled = true
    }
  }, [nbaGameId])

  const boxForTeam = (abbr: string, tab: GameLogTab): TeamBoxRow[] => {
    if (!players?.length) return []
    return players
      .filter((p) => String(p.TEAM_ABBREVIATION ?? p.team_abbreviation ?? "").toUpperCase() === abbr.toUpperCase())
      .map((p, i) => mapBoxScorePlayerRow(p, i, tab))
  }

  const teamStats = (abbr: string, tab: GameLogTab): Record<string, string | number> => {
    const row = teamTotals?.[abbr.toUpperCase()]
    if (!row) return {}
    return mapTeamGameTotals(row, tab)
  }

  return { summary, players, teamTotals, boxForTeam, teamStats, fromApi }
}
