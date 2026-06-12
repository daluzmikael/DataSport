import type { TrendPoint } from "../../api/playerTrendData"

const W = 520
const H = 200
const PAD = { top: 12, right: 16, bottom: 28, left: 36 }
const PLOT_W = W - PAD.left - PAD.right
const PLOT_H = H - PAD.top - PAD.bottom
const LINE_COLOR = "#3ecf8e"

interface PlayerTrendChartProps {
  data: TrendPoint[]
  playerName: string
  statLabel: string
  highlightSeason?: string
}

export function PlayerTrendChart({
  data,
  playerName,
  statLabel,
  highlightSeason,
}: PlayerTrendChartProps) {
  if (!data.length) {
    return (
      <p className="py-12 text-center text-sm text-ds-muted">No trend data for this player.</p>
    )
  }

  const values = data.map((d) => d.value)
  const minV = Math.min(...values)
  const maxV = Math.max(...values)
  const padV = (maxV - minV) * 0.1 || 1
  const yMin = minV - padV
  const yMax = maxV + padV

  const xAt = (i: number) => PAD.left + (i / Math.max(1, data.length - 1)) * PLOT_W
  const yAt = (v: number) => PAD.top + PLOT_H - ((v - yMin) / (yMax - yMin)) * PLOT_H

  const linePath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(d.value)}`)
    .join(" ")

  const areaPath = `${linePath} L ${xAt(data.length - 1)} ${PAD.top + PLOT_H} L ${xAt(0)} ${PAD.top + PLOT_H} Z`

  const yTicks = 4
  const yTickValues = Array.from({ length: yTicks + 1 }, (_, i) => {
    return yMin + ((yMax - yMin) * i) / yTicks
  })

  return (
    <div>
      <div className="mb-2">
        <h3 className="text-sm font-semibold text-ds-text">
          {playerName}: {statLabel}
        </h3>
        <p className="text-[10px] text-ds-muted">Regular season · per game · oldest → newest</p>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full max-w-[520px]"
        role="img"
        aria-label={`${playerName} ${statLabel} trend`}
      >
        {yTickValues.map((v, i) => {
          const y = yAt(v)
          return (
            <g key={i}>
              <line
                x1={PAD.left}
                y1={y}
                x2={W - PAD.right}
                y2={y}
                stroke="rgba(255,255,255,0.08)"
                strokeWidth={1}
              />
              <text
                x={PAD.left - 6}
                y={y}
                textAnchor="end"
                dominantBaseline="middle"
                fill="rgba(255,255,255,0.4)"
                fontSize={9}
                fontFamily="DM Sans, sans-serif"
              >
                {v.toFixed(1)}
              </text>
            </g>
          )
        })}

        <path d={areaPath} fill={LINE_COLOR} fillOpacity={0.15} />
        <path
          d={linePath}
          fill="none"
          stroke={LINE_COLOR}
          strokeWidth={2.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {data.map((d, i) => {
          const highlighted = highlightSeason && d.season === highlightSeason
          return (
            <g key={d.season}>
              <circle
                cx={xAt(i)}
                cy={yAt(d.value)}
                r={highlighted ? 5 : 3.5}
                fill={highlighted ? "#fff" : LINE_COLOR}
                stroke={highlighted ? LINE_COLOR : "none"}
                strokeWidth={2}
              />
              <title>{`${d.season}: ${d.value}`}</title>
              {(i === 0 || i === data.length - 1 || i % 2 === 0) && (
                <text
                  x={xAt(i)}
                  y={H - 6}
                  textAnchor="middle"
                  fill="rgba(255,255,255,0.45)"
                  fontSize={8}
                  fontFamily="DM Sans, sans-serif"
                >
                  {d.season.slice(2, 4)}–{d.season.slice(7, 9)}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
