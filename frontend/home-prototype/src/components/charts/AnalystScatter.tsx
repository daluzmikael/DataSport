import type { FieldSpec, ScatterRow } from "../../api/chartSpec"
import { formatValue } from "../../api/chartSpec"

/* `TeamPaintFtScatter` is hard-bound to paint points vs free-throw attempts for two
 * named teams, so its `scaleLinear` approach is reproduced here against arbitrary x/y
 * rather than imported and bent out of shape. */
const W = 520
const H = 300
const PAD = { top: 16, right: 20, bottom: 46, left: 52 }
const DOT_COLOR = "#3ecf8e"

interface AnalystScatterProps {
  rows: ScatterRow[]
  xField?: FieldSpec | null
  yField?: FieldSpec | null
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
  return (v: number) => range[0] + ((v - lo) / (hi - lo)) * (range[1] - range[0])
}

export function AnalystScatter({ rows, xField, yField }: AnalystScatterProps) {
  if (!rows.length) {
    return <p className="py-12 text-center text-sm text-ds-muted">No points to plot.</p>
  }

  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom

  const xs = rows.map((r) => r.x)
  const ys = rows.map((r) => r.y)
  const xScale = scaleLinear(xs, [PAD.left, PAD.left + plotW])
  const yScale = scaleLinear(ys, [PAD.top + plotH, PAD.top])

  const ticks = 4
  const tickVals = (vals: number[]) => {
    const min = Math.min(...vals)
    const max = Math.max(...vals)
    return Array.from({ length: ticks + 1 }, (_, i) => min + ((max - min) * i) / ticks)
  }

  // Past a few hundred dots the labels are noise, so only the extremes get named.
  const labelled = new Set<number>()
  if (rows.length <= 12) {
    rows.forEach((_, i) => labelled.add(i))
  } else {
    const byY = [...rows.keys()].sort((a, b) => (rows[b]!.y ?? 0) - (rows[a]!.y ?? 0))
    byY.slice(0, 3).forEach((i) => labelled.add(i))
    const byX = [...rows.keys()].sort((a, b) => (rows[b]!.x ?? 0) - (rows[a]!.x ?? 0))
    byX.slice(0, 3).forEach((i) => labelled.add(i))
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-auto w-full"
      role="img"
      aria-label={`${yField?.label ?? "y"} against ${xField?.label ?? "x"}`}
    >
      {tickVals(ys).map((v, i) => {
        const y = yScale(v)
        return (
          <g key={`y${i}`}>
            <line
              x1={PAD.left}
              y1={y}
              x2={PAD.left + plotW}
              y2={y}
              stroke="var(--color-ds-border)"
            />
            <text
              x={PAD.left - 6}
              y={y}
              textAnchor="end"
              dominantBaseline="middle"
              fill="var(--color-ds-muted)"
              fontSize={9}
              fontFamily="DM Sans, sans-serif"
            >
              {formatValue(v, yField)}
            </text>
          </g>
        )
      })}

      {tickVals(xs).map((v, i) => (
        <text
          key={`x${i}`}
          x={xScale(v)}
          y={H - 26}
          textAnchor="middle"
          fill="var(--color-ds-muted)"
          fontSize={9}
          fontFamily="DM Sans, sans-serif"
        >
          {formatValue(v, xField)}
        </text>
      ))}

      {rows.map((row, i) => (
        <g key={`${row.name}-${i}`}>
          <circle
            cx={xScale(row.x)}
            cy={yScale(row.y)}
            r={4}
            fill={DOT_COLOR}
            fillOpacity={0.62}
          >
            <title>{`${row.name}${row.teamAbbr ? ` (${row.teamAbbr})` : ""} · ${formatValue(row.x, xField)}, ${formatValue(row.y, yField)}`}</title>
          </circle>
          {labelled.has(i) && (
            <text
              x={xScale(row.x) + 6}
              y={yScale(row.y) - 5}
              fill="var(--color-ds-muted)"
              fontSize={8}
              fontFamily="DM Sans, sans-serif"
            >
              {row.name.split(/\s+/).slice(-1)[0]}
            </text>
          )}
        </g>
      ))}

      <text
        x={PAD.left + plotW / 2}
        y={H - 8}
        textAnchor="middle"
        fill="var(--color-ds-muted)"
        fontSize={10}
        fontFamily="DM Sans, sans-serif"
      >
        {xField?.label ?? ""}
      </text>
      <text
        x={12}
        y={PAD.top + plotH / 2}
        textAnchor="middle"
        transform={`rotate(-90 12 ${PAD.top + plotH / 2})`}
        fill="var(--color-ds-muted)"
        fontSize={10}
        fontFamily="DM Sans, sans-serif"
      >
        {yField?.label ?? ""}
      </text>
    </svg>
  )
}
