import type { ScatterPoint } from "../../data/teamGameChartsMock"
import { teamChartColor } from "../../data/teamGameChartsMock"

const W = 420
const H = 260
const PAD = { top: 16, right: 20, bottom: 44, left: 48 }

interface TeamPaintFtScatterProps {
  points: ScatterPoint[]
  awayAbbr: string
  homeAbbr: string
}

function scaleLinear(
  values: number[],
  range: [number, number],
  padding = 0.08,
): (v: number) => number {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const lo = min - span * padding
  const hi = max + span * padding
  return (v) => range[0] + ((v - lo) / (hi - lo)) * (range[1] - range[0])
}

export function TeamPaintFtScatter({ points, awayAbbr, homeAbbr }: TeamPaintFtScatterProps) {
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom

  if (points.length === 0) {
    return (
      <p className="py-8 text-center text-xs text-ds-muted">No player data for scatter</p>
    )
  }

  const xScale = scaleLinear(
    points.map((p) => p.paintPts),
    [PAD.left, PAD.left + plotW],
  )
  const yScale = scaleLinear(
    points.map((p) => p.fta),
    [PAD.top + plotH, PAD.top],
  )

  const xTicks = [0, 8, 16, 24].filter((t) => t <= Math.max(...points.map((p) => p.paintPts)) + 4)
  const yTicks = [0, 2, 4, 6, 8, 10].filter((t) => t <= Math.max(...points.map((p) => p.fta)) + 2)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Paint points vs free throw attempts">
      <defs>
        <pattern id="scatterGrid" width="24" height="24" patternUnits="userSpaceOnUse">
          <path d="M 24 0 L 0 0 0 24" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect x={PAD.left} y={PAD.top} width={plotW} height={plotH} fill="url(#scatterGrid)" rx={4} />

      {yTicks.map((t) => {
        const y = yScale(t)
        return (
          <g key={`y-${t}`}>
            <line
              x1={PAD.left}
              x2={PAD.left + plotW}
              y1={y}
              y2={y}
              stroke="rgba(255,255,255,0.08)"
              strokeDasharray="4 4"
            />
            <text x={PAD.left - 6} y={y + 3} textAnchor="end" fill="rgba(255,255,255,0.45)" fontSize={9}>
              {t}
            </text>
          </g>
        )
      })}

      {xTicks.map((t) => {
        const x = xScale(t)
        return (
          <g key={`x-${t}`}>
            <line
              x1={x}
              x2={x}
              y1={PAD.top}
              y2={PAD.top + plotH}
              stroke="rgba(255,255,255,0.08)"
              strokeDasharray="4 4"
            />
            <text x={x} y={H - 18} textAnchor="middle" fill="rgba(255,255,255,0.45)" fontSize={9}>
              {t}
            </text>
          </g>
        )
      })}

      <text
        x={PAD.left + plotW / 2}
        y={H - 4}
        textAnchor="middle"
        fill="rgba(255,255,255,0.55)"
        fontSize={10}
        fontWeight={500}
      >
        Paint points
      </text>
      <text
        x={14}
        y={PAD.top + plotH / 2}
        textAnchor="middle"
        fill="rgba(255,255,255,0.55)"
        fontSize={10}
        fontWeight={500}
        transform={`rotate(-90, 14, ${PAD.top + plotH / 2})`}
      >
        Free throw attempts
      </text>

      {points.map((p) => (
        <circle
          key={`${p.teamAbbr}-${p.playerName}`}
          cx={xScale(p.paintPts)}
          cy={yScale(p.fta)}
          r={5}
          fill={teamChartColor(p.teamAbbr)}
          fillOpacity={0.55}
          stroke={teamChartColor(p.teamAbbr)}
          strokeWidth={1}
        >
          <title>
            {p.playerName} ({p.teamAbbr}) — paint {p.paintPts}, FTA {p.fta}
          </title>
        </circle>
      ))}

      <g transform={`translate(${PAD.left + plotW - 72}, ${PAD.top + 4})`}>
        {[awayAbbr, homeAbbr].map((abbr) => (
          <g key={abbr} transform={`translate(0, ${abbr === homeAbbr ? 14 : 0})`}>
            <circle cx={4} cy={4} r={4} fill={teamChartColor(abbr)} fillOpacity={0.7} />
            <text x={12} y={7} fill="rgba(255,255,255,0.6)" fontSize={9}>
              {abbr}
            </text>
          </g>
        ))}
      </g>
    </svg>
  )
}
