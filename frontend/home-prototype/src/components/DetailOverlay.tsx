import { X } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import type { GameLogTab } from "../data/teamBoxScoreMock"
import { getGameDetail, getPlayerProfile, LIVE_FEED } from "../data/mock"
import { getTeamProfile } from "../data/teamProfileMock"
import { teamProfileIdFromAbbr } from "../data/liveDashboardFeed"
import { PLAY_BY_PLAY } from "../data/otherLiveGamesMock"
import type { DetailTarget, GameDetailView } from "../types"
import { TeamDetail } from "./TeamDetail"
import { TeamGameChartsSection } from "./charts/TeamGameChartsSection"
import { TeamGameShotChart } from "./charts/TeamGameShotChart"
import { GameScoreboard } from "./GameScoreboard"
import { TeamBoxScoreTable } from "./TeamBoxScoreTable"
import { PlayerGameDetail } from "./PlayerGameDetail"
import { PlayerProfileDetail } from "./PlayerProfileDetail"
import {
  trackedGameTitle,
  isPlayerInLiveGame,
  resolvePlayerGameId,
  resolvePlayerProfileStatus,
  playerStatusClass,
} from "../utils/gameLabels"
import { stagingSummaryToGameDetail } from "../api/gameMappers"
import { mockPlayerIdFromNba, resolveNbaPlayerId } from "../api/nbaIds"
import { useStagingGame } from "../hooks/useStagingGame"
import { parseStagingGameId, stagingGameOverlayId } from "../utils/stagingGameId"
import { useStagingPlayerGame } from "../hooks/useStagingPlayer"
import { StagingBadge } from "./StagingBadge"
import { AskReferenceButton, ReferencedLabel } from "./AskReferenceButton"

interface DetailOverlayProps {
  target: DetailTarget
  onClose: () => void
  onAsk: (prefill: string) => void
  askDraft: string
  onAskDraftChange: (draft: string) => void
  onReference: (label: string) => void
  referenceFocusKey?: number
  onOpenPlayer: (playerId: string) => void
  onOpenPlayerGame: (playerId: string, gameId: string) => void
  onOpenGame: (gameId: string) => void
  onOpenTeam: (teamId: string) => void
}

export function DetailOverlay({
  target,
  onClose,
  onAsk,
  askDraft,
  onAskDraftChange,
  onReference,
  referenceFocusKey = 0,
  onOpenPlayer,
  onOpenPlayerGame,
  onOpenGame,
  onOpenTeam,
}: DetailOverlayProps) {
  const askInputRef = useRef<HTMLInputElement>(null)
  const askFooterRef = useRef<HTMLElement>(null)

  const focusAskBar = useCallback(() => {
    askFooterRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    window.setTimeout(() => askInputRef.current?.focus(), 150)
  }, [])

  useEffect(() => {
    if (referenceFocusKey > 0) {
      askInputRef.current?.focus()
    }
  }, [referenceFocusKey])

  const playerGameTargetEarly =
    target?.type === "player-game" ? target : null
  const playerForGameHook = playerGameTargetEarly
    ? getPlayerProfile(playerGameTargetEarly.playerId)
    : null
  const playerRowForHook =
    playerForGameHook?.kind === "followed-player" ? playerForGameHook : null
  const stagingNbaGameId =
    playerGameTargetEarly?.gameId && playerRowForHook
      ? parseStagingGameId(playerGameTargetEarly.gameId)
      : null
  const { snapshot: gameSnapshot, fromApi: gameFromApi } = useStagingPlayerGame(
    playerRowForHook?.id ?? playerGameTargetEarly?.playerId ?? "",
    playerRowForHook,
    stagingNbaGameId,
  )

  const gameTargetEarly = target?.type === "game" ? target : null
  const stagingGameNbaId = gameTargetEarly ? parseStagingGameId(gameTargetEarly.id) : null
  const {
    summary: stagingGameSummary,
    boxForTeam,
    teamStats,
    fromApi: stagingGameFromApi,
  } = useStagingGame(stagingGameNbaId)

  if (!target) return null

  const gameDetail =
    target.type === "game" ? getGameDetail(target.id) ?? null : null
  const stagingGameDetail =
    stagingGameSummary && stagingGameNbaId
      ? stagingSummaryToGameDetail(stagingGameSummary)
      : null
  const playerGameTarget = target.type === "player-game" ? target : null
  const playerProfileTarget = target.type === "player" ? target : null
  const player = playerGameTarget
    ? getPlayerProfile(playerGameTarget.playerId)
    : playerProfileTarget
      ? getPlayerProfile(playerProfileTarget.id)
      : null
  const teamProfile =
    target.type === "team" ? getTeamProfile(target.id) ?? null : null

  const playerRow =
    player && player.kind === "followed-player"
      ? player
      : gameSnapshot?.player ?? null
  const activeGameId = playerGameTarget?.gameId

  const teamLiveGameId =
    teamProfile?.abbr === "BOS"
      ? LIVE_FEED.find((i) => i.id === "game-celtics")
        ? "game-celtics"
        : undefined
      : undefined

  const title = trackedGameTitle(LIVE_FEED, gameDetail, playerRow)
  const playerLiveGameId =
    playerRow && isPlayerInLiveGame(playerRow, LIVE_FEED)
      ? resolvePlayerGameId(playerRow, LIVE_FEED)
      : undefined

  const profileStatus = playerRow
    ? resolvePlayerProfileStatus(playerRow, LIVE_FEED)
    : null

  const playerGameTitle =
    gameSnapshot != null
      ? `${gameSnapshot.gameDateLabel} · ${gameSnapshot.matchup}`
      : activeGameId && playerRow
        ? trackedGameTitle(LIVE_FEED, getGameDetail(activeGameId) ?? null, playerRow)
        : null

  const gameOpponentAbbr = gameSnapshot?.player.opponentAbbr ?? playerRow?.opponentAbbr

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-ds-bg">
      <header
        className={`relative shrink-0 border-b border-ds-border px-4 py-3 ${
          playerRow || teamProfile ? "min-h-[4.5rem]" : ""
        }`}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-2 text-ds-muted hover:bg-ds-raised hover:text-ds-text"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>
        {playerRow && playerGameTarget ? (
          <>
            <div className="pr-12">
              <p className="text-[10px] font-bold uppercase tracking-wider text-ds-live">
                Player game
              </p>
              <p className="mt-0.5 text-xs text-ds-muted">
                {activeGameId ? (
                  <button
                    type="button"
                    onClick={() => onOpenGame(activeGameId)}
                    className="text-left text-ds-accent underline-offset-2 hover:underline"
                  >
                    {playerGameTitle}
                  </button>
                ) : (
                  playerGameTitle
                )}
              </p>
            </div>
            <div className="absolute left-1/2 top-1/2 max-w-[calc(100%-7rem)] -translate-x-1/2 -translate-y-1/2 text-center">
              <h1 className="flex flex-wrap items-center justify-center gap-x-2 text-2xl font-bold tracking-tight sm:text-3xl">
                <button
                  type="button"
                  onClick={() => onOpenPlayer(playerRow.id)}
                  className="text-ds-accent underline-offset-2 transition hover:underline"
                >
                  {playerRow.name}
                </button>
                <span className="font-normal text-ds-muted">vs</span>
                <ReferencedLabel
                  label={gameOpponentAbbr ?? "—"}
                  onReference={onReference}
                />
              </h1>
            </div>
          </>
        ) : playerRow ? (
          <>
            <div className="pr-12">
              <p className="text-[10px] font-bold uppercase tracking-wider text-ds-muted">
                Player profile
              </p>
              <p className="mt-0.5 text-xs text-ds-muted">
                {playerLiveGameId ? (
                  <button
                    type="button"
                    onClick={() =>
                      onOpenPlayerGame(playerRow.id, playerLiveGameId)
                    }
                    className="text-left text-ds-accent underline-offset-2 hover:underline"
                  >
                    Live: {title}
                  </button>
                ) : (
                  `${playerRow.teamAbbr} · 2024-25 season`
                )}
              </p>
            </div>
            <div className="absolute left-1/2 top-1/2 flex max-w-[calc(100%-7rem)] -translate-x-1/2 -translate-y-1/2 items-center justify-center gap-3">
              <h1 className="text-center text-2xl font-bold tracking-tight sm:text-3xl">
                <ReferencedLabel label={playerRow.name} onReference={onReference} />
              </h1>
              <div className="flex shrink-0 items-stretch gap-2">
                <div
                  className="rounded-lg border border-ds-accent/35 bg-ds-accent/10 px-3 py-1 text-center"
                  title="Season average game score and league rank"
                >
                  <p className="text-[9px] font-semibold uppercase tracking-wide text-ds-muted">
                    Season GS
                  </p>
                  <p className="font-mono text-lg font-bold leading-tight tabular-nums text-ds-accent">
                    {playerRow.seasonAvgGameScore.toFixed(1)}
                  </p>
                  <p className="mt-0.5 font-mono text-[11px] font-semibold leading-tight tabular-nums text-ds-text">
                    #{playerRow.seasonGameScoreRank}
                    {playerRow.seasonGameScoreRankTotal != null && (
                      <span className="font-sans font-normal text-ds-muted">
                        {" "}
                        of {playerRow.seasonGameScoreRankTotal}
                      </span>
                    )}
                  </p>
                </div>
                {profileStatus && (
                  <div className="rounded-lg border border-ds-border bg-ds-raised/80 px-2.5 py-1 text-center">
                    <p className="text-[9px] font-semibold uppercase tracking-wide text-ds-muted">
                      Status
                    </p>
                    <p
                      className={`text-sm font-bold leading-tight ${playerStatusClass(profileStatus.statusTone)}`}
                    >
                      {profileStatus.statusLabel}
                    </p>
                    <p className="max-w-[8.5rem] text-[9px] leading-snug text-ds-muted">
                      {profileStatus.metaLine}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : teamProfile ? (
          <>
            <div className="pr-12">
              <p className="text-[10px] font-bold uppercase tracking-wider text-ds-muted">
                Team profile
              </p>
              <p className="mt-0.5 text-xs text-ds-muted">{teamProfile.seasonLabel} season</p>
            </div>
            <div className="absolute left-1/2 top-1/2 max-w-[calc(100%-7rem)] -translate-x-1/2 -translate-y-1/2 text-center">
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                <ReferencedLabel
                  label={`${teamProfile.city} ${teamProfile.name}`}
                  onReference={onReference}
                />
              </h1>
              <p className="inline-flex items-center justify-center gap-0.5 font-mono text-sm text-ds-accent">
                {teamProfile.abbr}
                <AskReferenceButton label={teamProfile.abbr} onReference={onReference} />
              </p>
            </div>
          </>
        ) : stagingGameDetail && stagingGameSummary ? (
          <div className="pr-12">
            <div className="flex items-center gap-1">
              <StagingBadge show={stagingGameFromApi} />
              <p className="text-[10px] font-bold uppercase tracking-wider text-ds-muted">
                Game · {stagingGameSummary.status}
              </p>
            </div>
            <h1 className="text-lg font-bold">
              {stagingGameSummary.gameDateLabel} · {stagingGameSummary.away.abbr} @{" "}
              {stagingGameSummary.home.abbr}
            </h1>
            <p className="mt-0.5 font-mono text-sm text-ds-muted">
              {stagingGameSummary.away.score}–{stagingGameSummary.home.score}
            </p>
          </div>
        ) : (
          <div className="pr-12">
            <p className="text-[10px] font-bold uppercase tracking-wider text-ds-live">
              Live detail
            </p>
            <h1 className="text-lg font-bold">{title}</h1>
          </div>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {teamProfile && (
          <TeamDetail
            profile={teamProfile}
            liveGameId={teamLiveGameId}
            onOpenGame={onOpenGame}
            onReference={onReference}
          />
        )}
        {playerRow && playerGameTarget && activeGameId && (
          <PlayerGameDetail
            player={playerRow}
            gameId={activeGameId}
            gameSnapshot={gameSnapshot}
            fromApi={gameFromApi}
            onOpenGame={onOpenGame}
            onAsk={focusAskBar}
          />
        )}
        {playerRow && playerProfileTarget && (
          <PlayerProfileDetail
            player={playerRow}
            onOpenPlayerGame={onOpenPlayerGame}
            onReference={onReference}
            onAsk={focusAskBar}
          />
        )}
        {gameDetail && (
          <TeamGameDetail
            game={gameDetail}
            onOpenPlayerGame={onOpenPlayerGame}
            onOpenTeam={onOpenTeam}
            onReference={onReference}
          />
        )}
        {!gameDetail && stagingGameDetail && stagingGameNbaId && (
          <StagingGameDetail
            game={stagingGameDetail}
            gameOverlayId={stagingGameOverlayId(stagingGameNbaId)}
            boxForTeam={boxForTeam}
            teamStats={teamStats}
            fromApi={stagingGameFromApi}
            onOpenPlayerGame={onOpenPlayerGame}
            onOpenTeam={onOpenTeam}
            onReference={onReference}
          />
        )}
      </div>

      <footer
        ref={askFooterRef}
        className="shrink-0 border-t border-ds-border bg-ds-panel p-4"
      >
        <p className="mb-2 text-center text-xs text-ds-muted">
          Questions about what you see? Ask below — opens in the main analyzer with context.
        </p>
        <form
          className="mx-auto flex max-w-xl gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            const q = askDraft.trim()
            if (!q) return
            onAsk(
              playerRow && playerGameTarget
                ? `About ${playerRow.name} in ${playerGameTitle ?? "this game"}: ${q}`
                : playerRow
                  ? `About ${playerRow.name}: ${q}`
                  : teamProfile
                    ? `About the ${teamProfile.city} ${teamProfile.name}: ${q}`
                    : stagingGameSummary
                      ? `About ${stagingGameSummary.gameDateLabel} ${stagingGameSummary.away.abbr} @ ${stagingGameSummary.home.abbr}: ${q}`
                      : `About the live game (${title}): ${q}`,
            )
            onClose()
          }}
        >
          <input
            ref={askInputRef}
            name="ask"
            value={askDraft}
            onChange={(e) => onAskDraftChange(e.target.value)}
            placeholder="Ask DataSport… reference names with the magnifying glass"
            className="flex-1 rounded-xl border-2 border-ds-accent/50 bg-ds-raised px-4 py-3 text-sm outline-none focus:border-ds-accent"
          />
          <button
            type="submit"
            className="rounded-xl bg-ds-accent px-5 py-3 text-sm font-semibold text-ds-bg hover:bg-ds-accent-dim"
          >
            Ask
          </button>
        </form>
      </footer>
    </div>
  )
}

function StagingGameDetail({
  game,
  gameOverlayId,
  boxForTeam,
  teamStats,
  fromApi,
  onOpenPlayerGame,
  onOpenTeam,
  onReference,
}: {
  game: GameDetailView
  gameOverlayId: string
  boxForTeam: (abbr: string, tab: GameLogTab) => import("../data/teamBoxScoreMock").TeamBoxRow[]
  teamStats: (abbr: string, tab: GameLogTab) => Record<string, string | number>
  fromApi: boolean
  onOpenPlayerGame: (playerId: string, gameId: string) => void
  onOpenTeam: (teamId: string) => void
  onReference: (label: string) => void
}) {
  const [statsTab, setStatsTab] = useState<GameLogTab>("general")

  const openPlayer = (playerId: string) => {
    const nbaId = resolveNbaPlayerId(playerId)
    onOpenPlayerGame(nbaId ? mockPlayerIdFromNba(nbaId) : playerId, gameOverlayId)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <GameScoreboard
        game={game}
        statsTab={statsTab}
        onStatsTabChange={setStatsTab}
        onOpenTeam={(abbr) => onOpenTeam(teamProfileIdFromAbbr(abbr))}
        onReference={onReference}
        isFinal
        statTabs={["general", "advanced"]}
        awayTeamValues={teamStats(game.away.abbr, statsTab)}
        homeTeamValues={teamStats(game.home.abbr, statsTab)}
      />
      <div className="grid gap-4 lg:grid-cols-2 lg:items-stretch">
        <TeamBoxScoreTable
          teamAbbr={game.away.abbr}
          tab={statsTab}
          rows={boxForTeam(game.away.abbr, statsTab)}
          subtitle={fromApi ? "Final box score · staging data" : "Final box score"}
          onOpenPlayer={openPlayer}
          onReference={onReference}
        />
        <TeamBoxScoreTable
          teamAbbr={game.home.abbr}
          tab={statsTab}
          rows={boxForTeam(game.home.abbr, statsTab)}
          subtitle={fromApi ? "Final box score · staging data" : "Final box score"}
          onOpenPlayer={openPlayer}
          onReference={onReference}
        />
      </div>
    </div>
  )
}

function TeamGameDetail({
  game,
  onOpenPlayerGame,
  onOpenTeam,
  onReference,
}: {
  game: GameDetailView
  onOpenPlayerGame: (playerId: string, gameId: string) => void
  onOpenTeam: (teamId: string) => void
  onReference: (label: string) => void
}) {
  const [statsTab, setStatsTab] = useState<GameLogTab>("general")
  const playByPlay = PLAY_BY_PLAY[game.id] ?? [
    "— timeout",
    "— made 3PT",
    "— driving layup",
  ]

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <GameScoreboard
        game={game}
        statsTab={statsTab}
        onStatsTabChange={setStatsTab}
        onOpenTeam={(abbr) => onOpenTeam(teamProfileIdFromAbbr(abbr))}
        onReference={onReference}
      />
      <div className="grid gap-4 lg:grid-cols-2 lg:items-stretch">
        <TeamBoxScoreTable
          teamAbbr={game.away.abbr}
          tab={statsTab}
          onOpenPlayer={(playerId) => onOpenPlayerGame(playerId, game.id)}
          onReference={onReference}
        />
        <TeamBoxScoreTable
          teamAbbr={game.home.abbr}
          tab={statsTab}
          onOpenPlayer={(playerId) => onOpenPlayerGame(playerId, game.id)}
          onReference={onReference}
        />
      </div>

      <TeamGameChartsSection
        awayAbbr={game.away.abbr}
        homeAbbr={game.home.abbr}
      />

      <TeamGameShotChart awayAbbr={game.away.abbr} homeAbbr={game.home.abbr} />

      <section className="rounded-xl border border-ds-border bg-ds-panel p-4">
        <h3 className="text-sm font-semibold">Play-by-play (placeholder)</h3>
        <ul className="mt-2 space-y-1 text-sm text-ds-muted">
          {playByPlay.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}

