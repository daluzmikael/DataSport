import type { LeaderboardEntry } from "../../api/playerLeaderboardData"

const W = 520
const ROW_H = 28
const PAD = { top: 12, right: 52, bottom: 8, left: 108 }
const BAR_COLOR = "#3ecf8e"
const HIGHLIGHT_COLOR = "#f5c542"

interface PlayerLeaderboardChartProps {
  entries: LeaderboardEntry[]
  title: string
  subtitle: string
  statLabel: string
  highlightPlayerId?: string
}

function shortName(fullName: string): string {
  const parts = fullName.trim().split(/\s+/)
  if (parts.length <= 1) return fullName
  return parts[parts.length - 1] ?? fullName
}

export function PlayerLeaderboardChart({
  entries,
  title,
  subtitle,
  statLabel,
  highlightPlayerId,
}: PlayerLeaderboardChartProps) {
  if (!entries.length) {
    return (
      <p className="py-12 text-center text-sm text-ds-muted">No leaderboard data available.</p>
    )
  }

  const values = entries.map((e) => e.value)
  const maxV = Math.max(...values, 1)
  const plotW = W - PAD.left - PAD.right
  const H = PAD.top + PAD.bottom + entries.length * ROW_H

  const barW = (v: number) => (v / maxV) * plotW

  return (
    <div>
      <div className="mb-2">
        <h3 className="text-sm font-semibold text-ds-text">{title}</h3>
        <p className="text-[10px] text-ds-muted">{subtitle}</p>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full max-w-[520px]"
        role="img"
        aria-label={title}
      >
        {entries.map((entry, i) => {
          const y = PAD.top + i * ROW_H + ROW_H / 2
          const highlighted =
            highlightPlayerId != null && entry.playerId === highlightPlayerId
          const fill = highlighted ? HIGHLIGHT_COLOR : BAR_COLOR
          const bw = barW(entry.value)
          return (
            <g key={`${entry.playerId}-${entry.rank}`}>
              <text
                x={PAD.left - 8}
                y={y}
                textAnchor="end"
                dominantBaseline="middle"
                fill={highlighted ? HIGHLIGHT_COLOR : "rgba(255,255,255,0.75)"}
                fontSize={10}
                fontWeight={highlighted ? 700 : 500}
                fontFamily="DM Sans, sans-serif"
              >
                {shortName(entry.playerName)}
              </text>
              <text
                x={4}
                y={y}
                dominantBaseline="middle"
                fill="rgba(255,255,255,0.35)"
                fontSize={8}
                fontFamily="DM Sans, sans-serif"
              >
                {entry.rank}
              </text>
              <rect
                x={PAD.left}
                y={y - 9}
                width={bw}
                height={18}
                rx={4}
                fill={fill}
                fillOpacity={highlighted ? 0.85 : 0.55}
              />
              <text
                x={PAD.left + bw + 6}
                y={y}
                dominantBaseline="middle"
                fill="rgba(255,255,255,0.65)"
                fontSize={9}
                fontFamily="DM Sans, sans-serif"
              >
                {entry.value.toFixed(1)}
              </text>
              <title>{`${entry.playerName} (${entry.teamAbbr}) · ${statLabel}: ${entry.value}`}</title>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
