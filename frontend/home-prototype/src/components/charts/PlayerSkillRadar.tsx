import type { SkillCompareRow, SkillRadarCategory } from "../../api/playerSkillProfile"

const SIZE = 280
const CX = SIZE / 2
const CY = SIZE / 2
const R = 100
const LEVELS = 4

const PLAYER_COLOR = "#3ecf8e"
const CAREER_COLOR = "#c9a227"

function polar(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)]
}

function polygonPath(values: number[], maxVal = 100): string {
  const n = values.length
  if (n === 0) return ""
  return (
    values
      .map((v, i) => {
        const angle = (360 / n) * i
        const r = (Math.min(maxVal, Math.max(0, v)) / maxVal) * R
        const [x, y] = polar(angle, r)
        return `${i === 0 ? "M" : "L"} ${x} ${y}`
      })
      .join(" ") + " Z"
  )
}

function RadarGrid({ categories }: { categories: string[] }) {
  const n = categories.length
  return (
    <>
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
    </>
  )
}

interface PlayerSkillRadarSoloProps {
  data: SkillRadarCategory[]
  playerName: string
  title?: string
}

export function PlayerSkillRadarSolo({
  data,
  playerName,
  title = "Skill profile",
}: PlayerSkillRadarSoloProps) {
  const categories = data.map((d) => d.category)
  const values = data.map((d) => d.normalized)

  return (
    <div>
      <p className="mb-2 text-center text-xs font-medium text-ds-text">{title}</p>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="mx-auto h-auto w-full max-w-[300px]"
        role="img"
        aria-label={`${playerName} skill profile`}
      >
        <RadarGrid categories={categories} />
        <path
          d={polygonPath(values)}
          fill={PLAYER_COLOR}
          fillOpacity={0.28}
          stroke={PLAYER_COLOR}
          strokeWidth={2}
        />
        {data.map((point, i) => {
          const angle = (360 / categories.length) * i
          const r = (point.normalized / 100) * R
          const [x, y] = polar(angle, r)
          return (
            <circle key={point.category} cx={x} cy={y} r={3} fill={PLAYER_COLOR}>
              <title>{`${point.category}: ${point.raw} (${point.normalized}/100)`}</title>
            </circle>
          )
        })}
      </svg>
      <p className="mt-2 text-center text-[10px] font-medium text-ds-accent">{playerName}</p>
    </div>
  )
}

interface PlayerSkillRadarCompareProps {
  rows: SkillCompareRow[]
  seasonLabel: string
  compareLabel: string
  title?: string
}

export function PlayerSkillRadarCompare({
  rows,
  seasonLabel,
  compareLabel,
  title = "vs career",
}: PlayerSkillRadarCompareProps) {
  const categories = rows.map((r) => r.category)
  const seasonValues = rows.map((r) => Number(r[seasonLabel]) || 0)
  const careerValues = rows.map((r) => Number(r[compareLabel]) || 0)

  return (
    <div>
      <p className="mb-2 text-center text-xs font-medium text-ds-text">{title}</p>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="mx-auto h-auto w-full max-w-[300px]"
        role="img"
        aria-label={`${seasonLabel} compared to career`}
      >
        <RadarGrid categories={categories} />
        <path
          d={polygonPath(careerValues)}
          fill={CAREER_COLOR}
          fillOpacity={0.15}
          stroke={CAREER_COLOR}
          strokeWidth={1.5}
          strokeDasharray="4 3"
        />
        <path
          d={polygonPath(seasonValues)}
          fill={PLAYER_COLOR}
          fillOpacity={0.28}
          stroke={PLAYER_COLOR}
          strokeWidth={2}
        />
      </svg>
      <div className="mt-2 flex justify-center gap-4 text-[10px] text-ds-muted">
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: PLAYER_COLOR }}
          />
          {seasonLabel}
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2 w-2 rounded-full border border-dashed"
            style={{ backgroundColor: CAREER_COLOR }}
          />
          {compareLabel}
        </span>
      </div>
    </div>
  )
}
