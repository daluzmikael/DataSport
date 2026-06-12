import { useMemo } from "react"
import {
  CartesianGrid,
  Scatter,
  ScatterChart,
  Tooltip,
  TooltipProps,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../ui/card"
import { ChartConfig, ChartContainer } from "../ui/chart"

/** PLAYER-CHARTS-AI-TODO: see ../playerChartsAiTodo.ts — scatter defaults are staging-only until AI is wired. */

export interface ScatterChartConfig {
  statDisplayName?: string
  xAxisLabel?: string
  yAxisLabel?: string
  timeFrame?: string
}

interface ScatterProps {
  data: Record<string, unknown>[]
  config: ScatterChartConfig
}

function toNumeric(v: unknown): number | null {
  if (v === null || v === undefined) return null
  if (typeof v === "number") return Number.isFinite(v) ? v : null
  const s = String(v).trim()
  if (s === "") return null
  const n = Number(s)
  return Number.isFinite(n) ? n : null
}

function deterministicJitter(seed: string): number {
  let h = 2166136261 >>> 0
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return ((h >>> 0) / 0xffffffff) * 0.9 - 0.45
}

interface ScatterRow {
  player_name: string
  x_value: number
  y_value: number
}

const HARD_RENDER_CAP = 750

const CustomTooltip = ({
  active,
  payload,
  isSingleAxis,
  xAxisLabel,
  yAxisLabel,
}: TooltipProps<number, string> & {
  isSingleAxis: boolean
  xAxisLabel?: string
  yAxisLabel?: string
}) => {
  if (!active || !payload || payload.length === 0) return null
  const p = payload[0]?.payload as ScatterRow | undefined
  if (!p) return null

  return (
    <div className="rounded-lg border bg-background p-2 text-xs shadow-sm">
      <div className="font-semibold">{p.player_name}</div>
      {!isSingleAxis && xAxisLabel && (
        <div className="text-muted-foreground">
          {xAxisLabel}:{" "}
          <span className="font-medium text-foreground">{formatValue(p.x_value, xAxisLabel)}</span>
        </div>
      )}
      <div className="text-muted-foreground">
        {yAxisLabel || "Value"}:{" "}
        <span className="font-medium text-foreground">{formatValue(p.y_value, yAxisLabel)}</span>
      </div>
    </div>
  )
}

function formatValue(v: number, label?: string): string {
  if (!Number.isFinite(v)) return "—"

  const isPercent =
    label &&
    (label.toLowerCase().includes("%") ||
      label.toLowerCase().includes("pct") ||
      label.toLowerCase().includes("rate"))

  if (isPercent && Math.abs(v) > 0 && Math.abs(v) <= 1) {
    return (v * 100).toFixed(1) + "%"
  }

  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString()
  if (Number.isInteger(v)) return v.toString()
  return v.toFixed(1)
}

const chartConfig = {
  point: { label: "Player", color: "hsl(var(--chart-1))" },
} satisfies ChartConfig

/** Same scatter chart as `ai_analyst` dashboard `Scatter` chart type. */
export default function ScatterComponent({ data, config }: ScatterProps) {
  const {
    statDisplayName = "Scatter Plot",
    xAxisLabel = "",
    yAxisLabel = "",
    timeFrame,
  } = config || {}

  const dotColor = "#ffffff"

  const { rows, isSingleAxis, capped } = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) {
      return { rows: [] as ScatterRow[], isSingleAxis: false, capped: false }
    }

    const hasXValue = data.some(
      (r) =>
        r &&
        Object.prototype.hasOwnProperty.call(r, "x_value") &&
        r.x_value !== null &&
        r.x_value !== undefined &&
        r.x_value !== "",
    )
    const isSingleAxis = !hasXValue

    const cleaned: ScatterRow[] = []
    for (const r of data) {
      if (!r) continue
      const player = (r.player_name ?? r.full_name ?? "").toString().trim()
      if (!player) continue

      const yNum = toNumeric(r.y_value)
      if (yNum === null) continue

      let xNum: number | null
      if (isSingleAxis) {
        xNum = deterministicJitter(player)
      } else {
        xNum = toNumeric(r.x_value)
        if (xNum === null) continue
      }

      cleaned.push({ player_name: player, x_value: xNum, y_value: yNum })
    }

    let capped = false
    let final = cleaned
    if (cleaned.length > HARD_RENDER_CAP) {
      capped = true
      final = cleaned.slice(0, HARD_RENDER_CAP)
    }
    return { rows: final, isSingleAxis, capped }
  }, [data])

  if (!data || data.length === 0) {
    return <div>No data available</div>
  }

  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{statDisplayName}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            No numeric data points to display. The query returned {data.length} rows but none
            contained valid x/y values.
          </div>
        </CardContent>
      </Card>
    )
  }

  const yValues = rows.map((r) => r.y_value)
  const yMin = Math.min(...yValues)
  const yMax = Math.max(...yValues)
  const yPadding = (yMax - yMin) * 0.05 || 1
  const yDomain: [number, number] = [yMin - yPadding, yMax + yPadding]

  let xDomain: [number, number] = [-0.5, 0.5]
  if (!isSingleAxis) {
    const xValues = rows.map((r) => r.x_value)
    const xMin = Math.min(...xValues)
    const xMax = Math.max(...xValues)
    const xPadding = (xMax - xMin) * 0.05 || 1
    xDomain = [xMin - xPadding, xMax + xPadding]
  }

  return (
    <Card className="w-full min-w-0 border-ds-border/60 bg-ds-raised/30 py-4 shadow-none">
      <CardHeader className="gap-1 px-4">
        <CardTitle className="text-sm">{statDisplayName}</CardTitle>
        <CardDescription className="text-[10px]">
          {timeFrame ? `${timeFrame} • ` : ""}
          {rows.length} {rows.length === 1 ? "player" : "players"}
          {capped ? ` (showing first ${HARD_RENDER_CAP})` : ""}
          {isSingleAxis ? " — distribution view" : ""}
        </CardDescription>
      </CardHeader>
      <CardContent className="px-2">
        <ChartContainer config={chartConfig} className="h-[360px] w-full min-h-[360px]">
          <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 20 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x_value"
              name={xAxisLabel || "X"}
              domain={xDomain}
              hide={isSingleAxis}
              tick={{ fontSize: 12, fill: "rgba(255,255,255,0.55)" }}
              label={
                !isSingleAxis && xAxisLabel
                  ? {
                      value: xAxisLabel,
                      position: "insideBottom",
                      offset: -10,
                      style: { fontSize: 13 },
                    }
                  : undefined
              }
              tickFormatter={(v) => formatValue(v, xAxisLabel)}
            />
            <YAxis
              type="number"
              dataKey="y_value"
              name={yAxisLabel || "Y"}
              domain={yDomain}
              tick={{ fontSize: 12, fill: "rgba(255,255,255,0.55)" }}
              label={
                yAxisLabel
                  ? {
                      value: yAxisLabel,
                      angle: -90,
                      position: "insideLeft",
                      style: { fontSize: 13, textAnchor: "middle" },
                    }
                  : undefined
              }
              tickFormatter={(v) => formatValue(v, yAxisLabel)}
              width={70}
            />
            <ZAxis range={[40, 40]} />
            <Tooltip
              content={
                <CustomTooltip
                  isSingleAxis={isSingleAxis}
                  xAxisLabel={xAxisLabel}
                  yAxisLabel={yAxisLabel}
                />
              }
              cursor={{ strokeDasharray: "3 3" }}
            />
            <Scatter
              name={statDisplayName}
              data={rows}
              fill={dotColor}
              fillOpacity={0.65}
              stroke={dotColor}
              strokeOpacity={0.85}
              strokeWidth={0.5}
            />
          </ScatterChart>
        </ChartContainer>
      </CardContent>
      <CardFooter className="flex-col items-start gap-1 px-4 text-[10px] text-muted-foreground">
        <div>Tap or hover any point to see the player.</div>
        {isSingleAxis && (
          <div>
            Horizontal positions are randomized to spread overlapping points; only the vertical
            axis is meaningful.
          </div>
        )}
      </CardFooter>
    </Card>
  )
}
