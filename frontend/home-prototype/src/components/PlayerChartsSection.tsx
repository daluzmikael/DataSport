import { useState } from "react"
import { CAREER_LOG_VALUE } from "../data/playerGameLogMock"
import {
  DEFAULT_LEADERBOARD_SEASON,
  LEADERBOARD_STAT_LABELS,
} from "../api/playerLeaderboardData"
import { DEFAULT_SCATTER_SEASON } from "../api/playerScatterData"
import { TREND_STAT_LABELS } from "../api/playerTrendData"
import { resolveNbaPlayerId } from "../api/nbaIds"
import { useStagingLeagueLeaderboard } from "../hooks/useStagingLeagueLeaderboard"
import { useStagingPlayerSkillProfile } from "../hooks/useStagingPlayerSkillProfile"
import { useStagingPlayerSeasonTrends } from "../hooks/useStagingPlayerTrends"
import {
  usePlayerShotChartSeasons,
  useStagingPlayerShotCharts,
} from "../hooks/useStagingPlayerShotCharts"
import { ChartDashboardSearch } from "./ChartDashboardSearch"
import {
  PlayerSkillRadarCompare,
  PlayerSkillRadarSolo,
} from "./charts/PlayerSkillRadar"
import { useStagingLeagueScatter } from "../hooks/useStagingLeagueScatter"
import { PlayerLeaderboardChart } from "./charts/PlayerLeaderboardChart"
import { PlayerTrendChart } from "./charts/PlayerTrendChart"
import ScatterChart from "./recharts/Scatter"
import { ShotChartCourt } from "./ShotChartCourt"
import { StagingBadge } from "./StagingBadge"

type ChartTab = "profile" | "shots" | "trends" | "leaderboards" | "scatter"

const CHART_TABS: { id: ChartTab; label: string; enabled: boolean }[] = [
  { id: "profile", label: "Stat profile", enabled: true },
  { id: "shots", label: "Shot charts", enabled: true },
  { id: "trends", label: "Trends", enabled: true },
  { id: "leaderboards", label: "Leaderboards", enabled: true },
  { id: "scatter", label: "Scatter", enabled: true },
]

interface PlayerChartsSectionProps {
  playerId: string
  playerName: string
}

function playerShortName(fullName: string): string {
  const parts = fullName.trim().split(/\s+/)
  return parts[parts.length - 1] ?? fullName
}

export function PlayerChartsSection({
  playerId,
  playerName,
}: PlayerChartsSectionProps) {
  const [tab, setTab] = useState<ChartTab>("profile")
  const { seasons, season, setSeason, loading: seasonsLoading, isCareer } =
    usePlayerShotChartSeasons(playerId)
  const { shots, fromApi: shotsFromApi, loading: shotsLoading } = useStagingPlayerShotCharts(
    playerId,
    season,
  )
  const {
    solo,
    compare,
    fromApi: profileFromApi,
    loading: profileLoading,
    compareLabel,
    compareFooter,
    isCareerSeason,
  } = useStagingPlayerSkillProfile(playerId, playerName, season)
  const {
    pts: ptsTrend,
    ast: astTrend,
    fromApi: trendsFromApi,
    loading: trendsLoading,
  } = useStagingPlayerSeasonTrends(playerId)
  const {
    entries: scoringLeaders,
    fromApi: leadersFromApi,
    loading: leadersLoading,
  } = useStagingLeagueLeaderboard(playerId)
  const {
    ptsMin: ptsMinScatter,
    astTov: astTovScatter,
    fromApi: scatterFromApi,
    loading: scatterLoading,
  } = useStagingLeagueScatter()
  const highlightNbaId = resolveNbaPlayerId(playerId)

  const seasonLabel = isCareer ? "Career" : `${season} season`
  const compareSeasonKey = isCareerSeason ? "Career" : season
  const fromApi =
    tab === "profile"
      ? profileFromApi
      : tab === "shots"
        ? shotsFromApi
        : tab === "trends"
          ? trendsFromApi
          : tab === "leaderboards"
            ? leadersFromApi
            : tab === "scatter"
              ? scatterFromApi
              : false
  const highlightSeason = isCareer ? undefined : season
  const shortName = playerShortName(playerName)
  const soloProfilePlaceholder = `Ask AI more, e.g. Compare ${shortName}'s profile this year to LeBron's in 2018`
  const compareProfilePlaceholder = `Ask AI more, e.g. Compare ${shortName}'s rookie year to his latest vs Jaylen Brown's rookie year to his latest`
  const heatmapPlaceholder = `Ask AI more, e.g. show me ${shortName}'s heatmap from 3`
  const zonesPlaceholder = `Ask AI more, e.g. show me ${shortName}'s best shooting zones from within the arc`
  const ptsTrendPlaceholder = `Ask AI more, e.g. ${shortName} PPG trend from 2017 to 2025`
  const astTrendPlaceholder = `Ask AI more, e.g. ${shortName} assists trend vs Jaylen Brown 2017-2025`
  const leaderboardPlaceholder = `Ask AI more, e.g. Show me the top 10 scorers in 2023`
  const ptsMinScatterPlaceholder = `Ask AI more, e.g. Scatterplot of points per game vs minutes for ${DEFAULT_SCATTER_SEASON}`
  const astTovScatterPlaceholder = `Ask AI more, e.g. Plot assists per game vs turnovers per game in ${DEFAULT_SCATTER_SEASON}`
  const scatterTimeFrame = `${DEFAULT_SCATTER_SEASON} regular season · min 20 GP`

  return (
    <section className="rounded-xl border border-ds-border bg-ds-panel p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold">Player charts</h2>
          <StagingBadge show={fromApi} />
          {(profileLoading ||
            shotsLoading ||
            trendsLoading ||
            leadersLoading ||
            scatterLoading) && (
            <span className="text-[10px] text-ds-muted">Loading vault…</span>
          )}
        </div>
        <label className="flex items-center gap-2 text-xs text-ds-muted">
          <span className="font-medium">Season</span>
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            disabled={seasonsLoading}
            className={`rounded-md border border-ds-border bg-ds-raised px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ds-accent/40 disabled:cursor-wait disabled:opacity-60 ${
              isCareer ? "font-semibold text-ds-gold" : "text-ds-text"
            }`}
          >
            {seasonsLoading ? (
              <option value={season}>Loading seasons…</option>
            ) : (
              <>
                {seasons.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
                <option value={CAREER_LOG_VALUE} className="font-semibold text-ds-gold">
                  Career
                </option>
              </>
            )}
          </select>
        </label>
      </div>

      <div className="mb-4 flex flex-wrap gap-1 border-b border-ds-border/60 pb-2">
        {CHART_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            disabled={!t.enabled}
            onClick={() => t.enabled && setTab(t.id)}
            className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition ${
              tab === t.id
                ? "bg-ds-accent/20 text-ds-accent"
                : t.enabled
                  ? "text-ds-muted hover:bg-ds-raised hover:text-ds-text"
                  : "cursor-not-allowed text-ds-muted/40"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="space-y-4">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-2">
              <ChartDashboardSearch
                playerName={playerName}
                placeholder={soloProfilePlaceholder}
              />
              <div className="rounded-lg border border-ds-border/60 bg-ds-raised/30 p-3">
                <PlayerSkillRadarSolo
                  data={solo}
                  playerName={playerName}
                  title={`${seasonLabel} · solo profile`}
                />
              </div>
            </div>
            <div className="space-y-2">
              <ChartDashboardSearch
                playerName={playerName}
                placeholder={compareProfilePlaceholder}
              />
              <div className="rounded-lg border border-ds-border/60 bg-ds-raised/30 p-3">
                {isCareerSeason ? (
                  <p className="py-16 text-center text-sm text-ds-muted">
                    Pick a specific season to see how it stacks up against career averages.
                  </p>
                ) : (
                  <PlayerSkillRadarCompare
                    rows={compare}
                    seasonLabel={compareSeasonKey}
                    compareLabel={compareLabel}
                    title={`${seasonLabel} · vs career`}
                  />
                )}
              </div>
            </div>
          </div>
          {!isCareerSeason && (
            <p className="text-center text-[10px] text-ds-muted">{compareFooter}</p>
          )}
        </div>
      )}

      {tab === "shots" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            <ChartDashboardSearch
              playerName={playerName}
              placeholder={heatmapPlaceholder}
            />
            <ShotChartCourt
              shots={shots}
              playerName={playerName}
              subtitle={seasonLabel}
              chartKind="heatmap"
              legendId="playerHeatLegend"
            />
          </div>
          <div className="space-y-2">
            <ChartDashboardSearch
              playerName={playerName}
              placeholder={zonesPlaceholder}
            />
            <ShotChartCourt
              shots={shots}
              playerName={playerName}
              subtitle={seasonLabel}
              chartKind="zones"
              legendId="playerZonesLegend"
            />
          </div>
        </div>
      )}

      {tab === "trends" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            <ChartDashboardSearch
              playerName={playerName}
              placeholder={ptsTrendPlaceholder}
            />
            <div className="rounded-lg border border-ds-border/60 bg-ds-raised/30 p-3">
              <PlayerTrendChart
                data={ptsTrend}
                playerName={playerName}
                statLabel={TREND_STAT_LABELS.PTS}
                highlightSeason={highlightSeason}
              />
            </div>
          </div>
          <div className="space-y-2">
            <ChartDashboardSearch
              playerName={playerName}
              placeholder={astTrendPlaceholder}
            />
            <div className="rounded-lg border border-ds-border/60 bg-ds-raised/30 p-3">
              <PlayerTrendChart
                data={astTrend}
                playerName={playerName}
                statLabel={TREND_STAT_LABELS.AST}
                highlightSeason={highlightSeason}
              />
            </div>
          </div>
        </div>
      )}
      {tab === "leaderboards" && (
        <div className="space-y-2">
          <ChartDashboardSearch
            playerName={playerName}
            placeholder={leaderboardPlaceholder}
          />
          <div className="rounded-lg border border-ds-border/60 bg-ds-raised/30 p-3">
            <PlayerLeaderboardChart
              entries={scoringLeaders}
              title={`League leaders: ${LEADERBOARD_STAT_LABELS.PTS}`}
              subtitle={`${DEFAULT_LEADERBOARD_SEASON} regular season · min 20 GP`}
              statLabel={LEADERBOARD_STAT_LABELS.PTS}
              highlightPlayerId={highlightNbaId ?? undefined}
            />
          </div>
        </div>
      )}
      {/* PLAYER-CHARTS-AI-TODO: scatter tab — staging defaults only; see playerChartsAiTodo.ts */}
      {tab === "scatter" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            <ChartDashboardSearch
              playerName={playerName}
              placeholder={ptsMinScatterPlaceholder}
            />
            <ScatterChart
              data={ptsMinScatter}
              config={{
                statDisplayName: "Points per game vs minutes",
                xAxisLabel: "Minutes per game",
                yAxisLabel: "Points per game",
                timeFrame: scatterTimeFrame,
              }}
            />
          </div>
          <div className="space-y-2">
            <ChartDashboardSearch
              playerName={playerName}
              placeholder={astTovScatterPlaceholder}
            />
            <ScatterChart
              data={astTovScatter}
              config={{
                statDisplayName: "Assists per game vs turnovers",
                xAxisLabel: "Turnovers per game",
                yAxisLabel: "Assists per game",
                timeFrame: scatterTimeFrame,
              }}
            />
          </div>
        </div>
      )}
    </section>
  )
}
