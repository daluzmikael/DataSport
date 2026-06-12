import { useMemo, useState } from "react"
import type { MockShot } from "../data/mockShots"

const PADDING = 20
const COURT_LEFT = -250
const COURT_RIGHT = 250
const COURT_TOP = 422
const COURT_BOTTOM = -52
const SVG_W = COURT_RIGHT - COURT_LEFT + PADDING * 2
const SVG_H = COURT_TOP - COURT_BOTTOM + PADDING * 2
const HEX_RADIUS = 8

export type ShotChartMode = "volume" | "accuracy" | "hotspots" | "coldspots"
export type ShotChartKind = "heatmap" | "zones"

function toSvg(apiX: number, apiY: number): [number, number] {
  return [apiX - COURT_LEFT + PADDING, COURT_TOP - apiY + PADDING]
}

function getColor(value: number, mode: ShotChartMode): string {
  if (mode === "accuracy") {
    if (value < 0.5) {
      const t = value / 0.5
      const r = Math.round(200 - t * 60)
      const g = Math.round(40 + t * 80)
      const b = Math.round(40 + t * 60)
      return `rgb(${r},${g},${b})`
    }
    const t = (value - 0.5) / 0.5
    const r = Math.round(140 - t * 110)
    const g = Math.round(120 + t * 120)
    const b = Math.round(100 - t * 50)
    return `rgb(${r},${g},${b})`
  }
  if (mode === "hotspots") {
    if (value < 0.33) {
      const t = value / 0.33
      return `rgb(${Math.round(80 - t * 40)}, ${Math.round(110 + t * 50)}, 60)`
    }
    if (value < 0.66) {
      const t = (value - 0.33) / 0.33
      return `rgb(${Math.round(40 - t * 20)}, ${Math.round(160 + t * 50)}, 60)`
    }
    const t = (value - 0.66) / 0.34
    return `rgb(${Math.round(20 - t * 10)}, ${Math.round(210 + t * 30)}, ${Math.round(60 + t * 20)})`
  }
  if (mode === "coldspots") {
    if (value < 0.33) {
      const t = value / 0.33
      return `rgb(${Math.round(230 - t * 40)}, ${Math.round(30 + t * 20)}, ${Math.round(30 + t * 10)})`
    }
    if (value < 0.66) {
      const t = (value - 0.33) / 0.33
      return `rgb(${Math.round(190 - t * 35)}, ${Math.round(50 + t * 15)}, ${Math.round(40 + t * 15)})`
    }
    const t = (value - 0.66) / 0.34
    return `rgb(${Math.round(155 - t * 35)}, ${Math.round(65 + t * 10)}, ${Math.round(55 + t * 10)})`
  }
  if (value < 0.2) {
    const t = value / 0.2
    return `rgb(${Math.round(60 + t * 20)}, ${Math.round(30 + t * 10)}, ${Math.round(90 + t * 30)})`
  }
  if (value < 0.4) {
    const t = (value - 0.2) / 0.2
    return `rgb(${Math.round(50 + t * 70)}, ${Math.round(15 + t * 10)}, ${Math.round(100 + t * 30)})`
  }
  if (value < 0.6) {
    const t = (value - 0.4) / 0.2
    return `rgb(${Math.round(120 + t * 60)}, ${Math.round(25 + t * 20)}, ${Math.round(130 - t * 30)})`
  }
  if (value < 0.8) {
    const t = (value - 0.6) / 0.2
    return `rgb(${Math.round(180 + t * 50)}, ${Math.round(45 + t * 80)}, ${Math.round(100 - t * 70)})`
  }
  const t = (value - 0.8) / 0.2
  return `rgb(${Math.round(230 + t * 25)}, ${Math.round(125 + t * 120)}, ${Math.round(30 + t * 20)})`
}

function hexPoints(cx: number, cy: number, r: number): string {
  const points: string[] = []
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 6
    points.push(`${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`)
  }
  return points.join(" ")
}

type HexBin = { x: number; y: number; made: number; total: number; pct: number }

function buildHexBins(shots: MockShot[], radius: number, mode: ShotChartMode): HexBin[] {
  const bins: Record<string, { x: number; y: number; made: number; total: number }> = {}
  const hexW = radius * 2
  const hexH = Math.sqrt(3) * radius

  for (const shot of shots) {
    const apiX = shot.loc_x
    const apiY = shot.loc_y
    if (apiY > 420 || apiY < -52) continue

    const [px, py] = toSvg(apiX, apiY)
    const col = Math.round(px / (hexW * 0.75))
    const row = Math.round((py - (col % 2 === 0 ? 0 : hexH / 2)) / hexH)
    const key = `${col}_${row}`

    if (!bins[key]) {
      const cx = col * hexW * 0.75
      const cy = row * hexH + (col % 2 === 0 ? 0 : hexH / 2)
      bins[key] = { x: cx, y: cy, made: 0, total: 0 }
    }
    bins[key].total += 1
    if (shot.shot_made_flag === 1) bins[key].made += 1
  }

  let binList = Object.values(bins).filter((b) => b.total >= 1)

  if (mode === "hotspots") {
    const qualified = binList.filter((b) => b.total >= 5)
    if (qualified.length === 0) return binList.map((b) => ({ ...b, pct: b.made / b.total }))
    qualified.sort((a, b) => a.made / a.total - b.made / b.total)
    const cutoff = Math.max(1, Math.floor(qualified.length * 0.35))
    return qualified.slice(-cutoff).map((b) => ({ ...b, pct: b.made / b.total }))
  }

  if (mode === "coldspots") {
    const qualified = binList.filter((b) => b.total >= 5)
    if (qualified.length === 0) return binList.map((b) => ({ ...b, pct: b.made / b.total }))
    qualified.sort((a, b) => a.made / a.total - b.made / b.total)
    const cutoff = Math.max(1, Math.floor(qualified.length * 0.35))
    return qualified.slice(0, cutoff).map((b) => ({ ...b, pct: b.made / b.total }))
  }

  if (mode === "accuracy") {
    binList = binList.filter((b) => b.total >= 3)
  }

  return binList.map((b) => ({ ...b, pct: b.made / b.total }))
}

function pointsOnArc(
  cx: number,
  cy: number,
  radius: number,
  startAngleDeg: number,
  endAngleDeg: number,
  steps: number,
): string {
  const points: string[] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const angleDeg = startAngleDeg + t * (endAngleDeg - startAngleDeg)
    const angleRad = (angleDeg * Math.PI) / 180
    const apiX = cx + radius * Math.cos(angleRad)
    const apiY = cy + radius * Math.sin(angleRad)
    const [sx, sy] = toSvg(apiX, apiY)
    points.push(`${sx},${sy}`)
  }
  return points.join(" ")
}

function CourtLines() {
  const lineColor = "rgba(255,255,255,0.55)"
  const softLineColor = "rgba(255,255,255,0.4)"
  const rimColor = "rgba(255,140,0,0.75)"

  const [bx, by] = toSvg(0, 0)
  const [courtL, courtBot] = toSvg(-250, -47)
  const [courtR] = toSvg(250, -47)
  const [, courtTop] = toSvg(0, 422)
  const [paintL] = toSvg(-80, 0)
  const [paintR] = toSvg(80, 0)
  const [, paintTop] = toSvg(0, 143)

  const THREE_R = 237.5
  const cornerAngle = Math.acos(220 / THREE_R) * (180 / Math.PI)
  const arcStartY = THREE_R * Math.sin((cornerAngle * Math.PI) / 180)

  const [cornerLX, cornerLBot] = toSvg(-220, -47)
  const [cornerRX, cornerRBot] = toSvg(220, -47)
  const [, cornerLTop] = toSvg(-220, arcStartY)
  const [, cornerRTop] = toSvg(220, arcStartY)

  const threeArcPoints = pointsOnArc(0, 0, THREE_R, cornerAngle, 180 - cornerAngle, 60)
  const raArcPoints = pointsOnArc(0, 0, 40, 0, 180, 30)
  const [raLX, raLY] = toSvg(-40, 0)
  const [raRX, raRY] = toSvg(40, 0)
  const ftTopPoints = pointsOnArc(0, 143, 60, 0, 180, 30)
  const ftBotPoints = pointsOnArc(0, 143, 60, 180, 360, 30)
  const ccPoints = pointsOnArc(0, 422, 60, 180, 360, 30)

  return (
    <g stroke={lineColor} strokeWidth={2.5} fill="none">
      <rect x={courtL} y={courtTop} width={courtR - courtL} height={courtBot - courtTop} />
      <rect x={paintL} y={paintTop} width={paintR - paintL} height={courtBot - paintTop} />
      <polyline points={ftTopPoints} />
      <polyline points={ftBotPoints} strokeDasharray="8 6" />
      <line x1={bx - 30} y1={by + 15} x2={bx + 30} y2={by + 15} strokeWidth={2} stroke={softLineColor} />
      <circle cx={bx} cy={by} r={7.5} strokeWidth={1.8} stroke={rimColor} />
      <polyline points={raArcPoints} />
      <line x1={raLX} y1={raLY} x2={raLX} y2={courtBot} />
      <line x1={raRX} y1={raRY} x2={raRX} y2={courtBot} />
      <line x1={cornerLX} y1={cornerLBot} x2={cornerLX} y2={cornerLTop} />
      <line x1={cornerRX} y1={cornerRBot} x2={cornerRX} y2={cornerRTop} />
      <polyline points={threeArcPoints} />
      <polyline points={ccPoints} />
    </g>
  )
}

const MODE_LABELS: Record<ShotChartMode, string> = {
  volume: "Shot frequency",
  accuracy: "Shooting accuracy",
  hotspots: "Best shooting zones",
  coldspots: "Worst shooting zones",
}

interface ShotChartCourtProps {
  shots: MockShot[]
  playerName: string
  subtitle?: string
  chartKind?: ShotChartKind
  defaultMode?: ShotChartMode
  legendId?: string
}

export function ShotChartCourt({
  shots,
  playerName,
  subtitle,
  chartKind = "heatmap",
  defaultMode,
  legendId = "protoShotLegend",
}: ShotChartCourtProps) {
  const initialMode =
    defaultMode ?? (chartKind === "zones" ? "hotspots" : "volume")
  const [mode, setMode] = useState<ShotChartMode>(initialMode)

  const modeOptions: ShotChartMode[] =
    chartKind === "zones" ? ["hotspots", "coldspots"] : ["volume", "accuracy"]

  const bins = useMemo(() => buildHexBins(shots, HEX_RADIUS, mode), [shots, mode])
  const maxVal = useMemo(
    () => (mode === "volume" ? Math.max(...bins.map((b) => b.total), 1) : 1),
    [bins, mode],
  )

  const made = shots.filter((s) => s.shot_made_flag === 1).length
  const fgPct = shots.length ? ((made / shots.length) * 100).toFixed(1) : "0.0"
  const modeLabel = MODE_LABELS[mode]
  const legendColors = [0, 0.25, 0.5, 0.75, 1].map((v) => getColor(v, mode))
  const legendLeft =
    mode === "volume" ? "Few" : mode === "accuracy" ? "Cold" : mode === "coldspots" ? "Worst" : "Good"
  const legendRight =
    mode === "volume" ? "Many" : mode === "accuracy" ? "Hot" : mode === "coldspots" ? "Bad" : "Best"
  const title = chartKind === "zones" ? "Shooting zones" : "Shot heat map"

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          <p className="text-[11px] text-ds-muted">
            {subtitle ?? "Season"} · {modeLabel} · {shots.length.toLocaleString()} FGA · {fgPct}%
            FG
          </p>
        </div>
        <div className="flex rounded-lg border border-ds-border p-0.5 text-[11px]">
          {modeOptions.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`rounded-md px-2.5 py-1 font-medium transition ${
                mode === m
                  ? "bg-ds-accent/20 text-ds-accent"
                  : "text-ds-muted hover:text-ds-text"
              }`}
            >
              {m === "volume"
                ? "Frequency"
                : m === "accuracy"
                  ? "Accuracy"
                  : m === "hotspots"
                    ? "Best"
                    : "Worst"}
            </button>
          ))}
        </div>
      </div>

      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        className="mx-auto h-auto w-full max-w-[520px] rounded-xl"
        style={{ background: "#0a0c10" }}
        role="img"
        aria-label={`${playerName} ${title}`}
      >
        <CourtLines />
        {bins.map((bin, i) => {
          let colorVal: number
          let size: number

          if (mode === "volume") {
            colorVal = bin.total / maxVal
            size = HEX_RADIUS * (0.5 + 0.5 * (bin.total / maxVal))
          } else if (mode === "accuracy") {
            colorVal = Math.min(1, Math.max(0, bin.pct / 0.9))
            size = HEX_RADIUS * (0.5 + 0.5 * Math.min(1, bin.total / Math.max(maxVal * 0.3, 1)))
          } else if (mode === "hotspots") {
            const minPct = Math.min(...bins.map((b) => b.pct))
            const maxPct = Math.max(...bins.map((b) => b.pct))
            const range = maxPct - minPct || 0.01
            colorVal = (bin.pct - minPct) / range
            size = HEX_RADIUS * (0.45 + 0.55 * colorVal)
          } else {
            const minPct = Math.min(...bins.map((b) => b.pct))
            const maxPct = Math.max(...bins.map((b) => b.pct))
            const range = maxPct - minPct || 0.01
            const normalized = (bin.pct - minPct) / range
            colorVal = normalized
            size = HEX_RADIUS * (0.45 + 0.55 * (1 - normalized))
          }

          return (
            <g key={i}>
              <polygon
                points={hexPoints(bin.x, bin.y, size)}
                fill={getColor(colorVal, mode)}
                opacity={0.92}
                stroke={getColor(colorVal, mode)}
                strokeWidth={0.3}
              />
              <title>{`${bin.made}/${bin.total} (${(bin.pct * 100).toFixed(1)}%)`}</title>
            </g>
          )
        })}
        <g transform={`translate(${SVG_W - 170}, ${SVG_H - 28})`}>
          <text fill="rgba(255,255,255,0.45)" fontSize={9} fontFamily="DM Sans, sans-serif" y={-2}>
            {legendLeft}
          </text>
          <defs>
            <linearGradient id={legendId}>
              {legendColors.map((c, i) => (
                <stop key={i} offset={`${i * 25}%`} stopColor={c} />
              ))}
            </linearGradient>
          </defs>
          <rect x={28} y={-10} width={90} height={8} rx={2} fill={`url(#${legendId})`} />
          <text
            fill="rgba(255,255,255,0.45)"
            fontSize={9}
            fontFamily="DM Sans, sans-serif"
            x={123}
            y={-2}
          >
            {legendRight}
          </text>
        </g>
      </svg>
    </div>
  )
}
