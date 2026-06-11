import type { RadarCategory } from "../../data/teamGameChartsMock"
import { teamChartColor } from "../../data/teamGameChartsMock"

const SIZE = 280
const CX = SIZE / 2
const CY = SIZE / 2
const R = 100
const LEVELS = 4

interface TeamCompareRadarProps {
  data: RadarCategory[]
  awayAbbr: string
  homeAbbr: string
  title?: string
}

function polar(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)]
}

function polygonPath(values: number[], maxVal: number): string {
  const n = values.length
  return values
    .map((v, i) => {
      const angle = (360 / n) * i
      const r = (Math.min(maxVal, Math.max(0, v)) / maxVal) * R
      const [x, y] = polar(angle, r)
      return `${i === 0 ? "M" : "L"} ${x} ${y}`
    })
    .join(" ") + " Z"
}

export function TeamCompareRadar({
  data,
  awayAbbr,
  homeAbbr,
  title = "Team skill profile",
}: TeamCompareRadarProps) {
  const categories = data.map((d) => d.category)
  const n = categories.length
  const teams = [awayAbbr, homeAbbr]

  const teamValues = (abbr: string) =>
    data.map((row) => Number(row[abbr]) || 0)

  return (
    <div>
      <p className="mb-2 text-center text-xs font-medium text-ds-text">{title}</p>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="mx-auto h-auto w-full max-w-[320px]" role="img" aria-label="Team comparison radar">
        {Array.from({ length: LEVELS }, (_, li) => {
          const levelR = (R / LEVELS) * (li + 1)
          const pts = categories
            .map((_, i) => {
              const [x, y] = polar((360 / n) * i, levelR)
              return `${x},${y}`
            })
            .join(" ")
          return (
            <polygon
              key={li}
              points={pts}
              fill="none"
              stroke="rgba(255,255,255,0.1)"
              strokeWidth={1}
            />
          )
        })}

        {categories.map((cat, i) => {
          const [x, y] = polar((360 / n) * i, R)
          const [lx, ly] = polar((360 / n) * i, R + 18)
          return (
            <g key={cat}>
              <line x1={CX} y1={CY} x2={x} y2={y} stroke="rgba(255,255,255,0.12)" />
              <text
                x={lx}
                y={ly}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="rgba(255,255,255,0.55)"
                fontSize={10}
                fontWeight={600}
              >
                {cat}
              </text>
            </g>
          )
        })}

        {teams.map((abbr) => (
          <path
            key={abbr}
            d={polygonPath(teamValues(abbr), 100)}
            fill={teamChartColor(abbr)}
            fillOpacity={0.25}
            stroke={teamChartColor(abbr)}
            strokeWidth={2}
          />
        ))}
      </svg>

      <div className="mt-2 flex justify-center gap-4 text-[10px] text-ds-muted">
        {teams.map((abbr) => (
          <span key={abbr} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: teamChartColor(abbr) }}
            />
            {abbr}
          </span>
        ))}
      </div>
      <p className="mt-1 text-center text-[9px] text-ds-muted/80">
        Scaled to game totals · PTS / AST / REB / STL / BLK
      </p>
    </div>
  )
}
