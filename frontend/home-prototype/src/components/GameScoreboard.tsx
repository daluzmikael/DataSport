import type { GameLogTab } from "../data/teamBoxScoreMock"
import type { GameDetailView, LineScore, TeamGameLive } from "../types"
import { AskReferenceButton } from "./AskReferenceButton"
import { TeamLiveGameStats } from "./TeamLiveGameStats"

function BasketballIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={className}
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
    >
      <circle cx="8" cy="8" r="6.5" />
      <path d="M8 1.5v13M1.5 8h13" />
      <path d="M3.2 3.2c2.8 2.8 6.8 2.8 9.6 0M3.2 12.8c2.8-2.8 6.8-2.8 9.6 0" />
    </svg>
  )
}

type QuarterKey = "q1" | "q2" | "q3" | "q4"

function quarterKeys(line: LineScore): QuarterKey[] {
  const keys: QuarterKey[] = ["q1", "q2", "q3"]
  if (line.q4 != null) keys.push("q4")
  return keys
}

function quarterLabel(key: QuarterKey): string {
  return key.toUpperCase()
}

function quarterWinner(
  away: number,
  home: number,
): "away" | "home" | "tie" {
  if (away > home) return "away"
  if (home > away) return "home"
  return "tie"
}

function LineScoreCompare({
  game,
  onReference,
}: {
  game: GameDetailView
  onReference?: (label: string) => void
}) {
  const keys = quarterKeys(game.away.line)
  const currentQ = game.period.replace(/\s/g, "").toUpperCase() as QuarterKey

  return (
    <table className="border-separate border-spacing-x-2.5 border-spacing-y-0 text-[11px] tabular-nums">
        <thead>
          <tr className="text-[10px] uppercase tracking-wide text-ds-muted">
            <th className="pb-1 text-left font-medium" />
            {keys.map((k) => (
              <th
                key={k}
                className={`pb-1 text-center font-medium ${
                  k === currentQ ? "text-ds-accent" : ""
                }`}
              >
                {quarterLabel(k)}
              </th>
            ))}
            <th className="pb-1 text-center font-medium text-ds-muted">T</th>
          </tr>
        </thead>
        <tbody>
          {(
            [
              { side: "away" as const, abbr: game.away.abbr, line: game.away.line, total: game.away.score },
              { side: "home" as const, abbr: game.home.abbr, line: game.home.line, total: game.home.score },
            ] as const
          ).map(({ side, abbr, line, total }) => (
            <tr key={side}>
              <td className="pr-1 text-left font-semibold text-ds-text">
                <span className="inline-flex items-center gap-0.5">
                  {abbr}
                  {onReference && (
                    <AskReferenceButton label={abbr} onReference={onReference} />
                  )}
                </span>
              </td>
              {keys.map((k) => {
                const awayPts = game.away.line[k] as number
                const homePts = game.home.line[k] as number
                const winner = quarterWinner(awayPts, homePts)
                const won = winner === side
                const lost = winner !== side && winner !== "tie"
                return (
                  <td
                    key={k}
                    className={`text-center ${
                      k === currentQ ? "rounded bg-ds-accent/10 px-1" : ""
                    } ${
                      won
                        ? "font-bold text-ds-accent"
                        : lost
                          ? "text-ds-muted/70"
                          : "text-ds-muted"
                    }`}
                  >
                    {line[k]}
                  </td>
                )
              })}
              <td className="text-center font-bold text-ds-text">{total}</td>
            </tr>
          ))}
        </tbody>
      </table>
  )
}

function TeamSide({
  abbr,
  score,
  hasPossession,
  align,
  className = "",
  onOpenTeam,
  onReference,
}: {
  abbr: string
  score: number
  hasPossession: boolean
  align: "left" | "right"
  className?: string
  onOpenTeam?: (abbr: string) => void
  onReference?: (label: string) => void
}) {
  const abbrEl = onOpenTeam ? (
    <span className="inline-flex items-center gap-0.5">
      <button
        type="button"
        onClick={() => onOpenTeam(abbr)}
        className="text-base font-bold tracking-wide text-ds-muted underline-offset-2 transition hover:text-ds-accent hover:underline sm:text-lg"
      >
        {abbr}
      </button>
      {onReference && <AskReferenceButton label={abbr} onReference={onReference} />}
    </span>
  ) : (
    <span className="inline-flex items-center gap-0.5">
      <p className="text-base font-bold tracking-wide text-ds-muted sm:text-lg">{abbr}</p>
      {onReference && <AskReferenceButton label={abbr} onReference={onReference} />}
    </span>
  )

  return (
    <div
      className={`flex items-center gap-2 ${
        align === "right" ? "justify-end text-right" : "justify-start text-left"
      } ${className}`}
    >
      {hasPossession && align === "left" && (
        <BasketballIcon className="h-6 w-6 shrink-0 text-ds-nba" />
      )}
      <div>
        {abbrEl}
        <p className="text-5xl font-bold tabular-nums leading-none sm:text-6xl">{score}</p>
      </div>
      {hasPossession && align === "right" && (
        <BasketballIcon className="h-6 w-6 shrink-0 text-ds-nba" />
      )}
    </div>
  )
}

interface GameScoreboardProps {
  game: GameDetailView
  statsTab: GameLogTab
  onStatsTabChange: (tab: GameLogTab) => void
  onOpenTeam?: (abbr: string) => void
  onReference?: (label: string) => void
  isFinal?: boolean
  awayTeamValues?: Record<string, string | number>
  homeTeamValues?: Record<string, string | number>
  statTabs?: GameLogTab[]
}

export function GameScoreboard({
  game,
  statsTab,
  onStatsTabChange,
  onOpenTeam,
  onReference,
  isFinal = false,
  awayTeamValues,
  homeTeamValues,
  statTabs,
}: GameScoreboardProps) {
  const awayHasBall = !isFinal && game.possession === "away"
  const homeHasBall = !isFinal && game.possession === "home"

  return (
    <div className="overflow-hidden rounded-xl border border-ds-border bg-ds-panel font-mono">
      <div className="px-4 py-3">
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
          <TeamSide
            abbr={game.away.abbr}
            score={game.away.score}
            hasPossession={awayHasBall}
            align="left"
            className="justify-self-start"
            onOpenTeam={onOpenTeam}
            onReference={onReference}
          />

          <div className="flex flex-col items-center gap-1.5 justify-self-center">
            <div className="flex items-center gap-2.5 text-center text-[10px] text-ds-muted">
              <p>
                TO <span className="tabular-nums text-ds-text">{game.awayTimeouts}</span>
                <span className="mx-0.5 text-ds-border">·</span>
                F <span className="tabular-nums text-ds-text">{game.awayTeamFouls}</span>
              </p>
              <div>
                <p className="text-base font-bold tabular-nums leading-tight text-ds-text">
                  {game.period}{" "}
                  <span className="text-ds-accent">{game.clock}</span>
                </p>
                {game.isLive && (
                  <p className="text-[8px] font-bold uppercase leading-none tracking-wide text-ds-live">
                    Live
                  </p>
                )}
              </div>
              <p>
                TO <span className="tabular-nums text-ds-text">{game.homeTimeouts}</span>
                <span className="mx-0.5 text-ds-border">·</span>
                F <span className="tabular-nums text-ds-text">{game.homeTeamFouls}</span>
              </p>
            </div>
            <LineScoreCompare game={game} onReference={onReference} />
          </div>

          <TeamSide
            abbr={game.home.abbr}
            score={game.home.score}
            hasPossession={homeHasBall}
            align="right"
            className="justify-self-end"
            onOpenTeam={onOpenTeam}
            onReference={onReference}
          />
        </div>
      </div>

      <TeamLiveGameStats
        awayAbbr={game.away.abbr}
        homeAbbr={game.home.abbr}
        tab={statsTab}
        onTabChange={onStatsTabChange}
        awayValues={awayTeamValues}
        homeValues={homeTeamValues}
        hideSeasonAvg={isFinal}
        tabs={statTabs}
      />
    </div>
  )
}
