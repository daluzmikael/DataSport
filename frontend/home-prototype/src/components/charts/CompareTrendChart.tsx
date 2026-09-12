import type { CompareTrendRow, FieldSpec } from "../../api/chartSpec"
import { formatValue, seriesColor, shortSeason } from "../../api/chartSpec"

/* Multi-series line. `PlayerTrendChart` is single-series and reads a fixed TrendPoint,
 * so the geometry is shared by eye rather than by import — same viewBox, same padding,
 * same tick treatment. */
const W = 520
const H = 220
const PAD = { top: 12, right: 16, bottom: 40, left: 40 }
const PLOT_W = W - PAD.left - PAD.right
const PLOT_H = H - PAD.top - PAD.bottom

interface CompareTrendChartProps {
  rows: CompareTrendRow[]
  series: string[]
  yField?: FieldSpec | null
}

export function CompareTrendChart({ rows, series, yField }: CompareTrendChartProps) {
  if (!rows.length || !series.length) {
    return <p className="py-12 text-center text-sm text-ds-muted">No comparable seasons.</p>
  }

  const values: number[] = []
  for (const row of rows) {
    for (const key of series) {
      const v = row[key]
      if (typeof v === "number" && Number.isFinite(v)) values.push(v)
    }
  }
  if (!values.length) {
    return <p className="py-12 text-center text-sm text-ds-muted">No comparable values.</p>
  }

  const minV = Math.min(...values)
  const maxV = Math.max(...values)
  const padV = (maxV - minV) * 0.1 || Math.abs(maxV) * 0.1 || 1
  const yMin = minV - padV
  const yMax = maxV + padV

  const xAt = (i: number) => PAD.left + (i / Math.max(1, rows.length - 1)) * PLOT_W
  const yAt = (v: number) => PAD.top + PLOT_H - ((v - yMin) / (yMax - yMin)) * PLOT_H

  const yTicks = 4
  const yTickValues = Array.from(
    { length: yTicks + 1 },
    (_, i) => yMin + ((yMax - yMin) * i) / yTicks,
  )

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label={`${series.join(" versus ")} ${yField?.label ?? ""} by season`}
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
                stroke="var(--color-ds-border)"
                strokeWidth={1}
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

        {series.map((key, si) => {
          const color = seriesColor(si)
          const points = rows
            .map((row, i) => ({ i, v: row[key] }))
            .filter((p): p is { i: number; v: number } => typeof p.v === "number")
          if (!points.length) return null
          const path = points
            .map((p, k) => `${k === 0 ? "M" : "L"} ${xAt(p.i)} ${yAt(p.v)}`)
            .join(" ")
          return (
            <g key={key}>
              <path
                d={path}
                fill="none"
                stroke={color}
                strokeWidth={2.5}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {points.map((p) => (
                <circle key={p.i} cx={xAt(p.i)} cy={yAt(p.v)} r={3.5} fill={color}>
                  <title>{`${key} · ${rows[p.i]?.season}: ${formatValue(p.v, yField)}`}</title>
                </circle>
              ))}
            </g>
          )
        })}

        {rows.map((row, i) =>
          i === 0 || i === rows.length - 1 || i % 2 === 0 ? (
            <text
              key={row.season}
              x={xAt(i)}
              y={H - 22}
              textAnchor="middle"
              fill="var(--color-ds-muted)"
              fontSize={8}
              fontFamily="DM Sans, sans-serif"
            >
              {shortSeason(row.season)}
            </text>
          ) : null,
        )}
      </svg>

      <div className="mt-1 flex flex-wrap justify-center gap-x-4 gap-y-1">
        {series.map((key, si) => (
          <span key={key} className="flex items-center gap-1.5 text-[10px] text-ds-muted">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: seriesColor(si) }}
            />
            {key}
          </span>
        ))}
      </div>
    </div>
  )
}
