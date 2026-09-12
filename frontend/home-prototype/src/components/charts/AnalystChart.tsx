import type {
  ChartSpec,
  CompareRadarRow,
  CompareTrendRow,
  LeaderboardRow,
  RadarRow,
  ScatterRow,
  ShotChartRow,
  ShotPointRow,
  TrendRow,
} from "../../api/chartSpec"
import { formatValue, seriesKeys } from "../../api/chartSpec"
import type { LeaderboardEntry } from "../../api/playerLeaderboardData"
import type { SkillCompareRow, SkillRadarCategory } from "../../api/playerSkillProfile"
import type { TrendPoint } from "../../api/playerTrendData"
import type { ShotChartMode } from "../ShotChartCourt"
import type { ShotPoint } from "../../data/schema/shots"
import { ShotChartCourt } from "../ShotChartCourt"
import { AnalystScatter } from "./AnalystScatter"
import { AnalystTable } from "./AnalystTable"
import { CompareTrendChart } from "./CompareTrendChart"
import { PlayerLeaderboardChart } from "./PlayerLeaderboardChart"
import { PlayerSkillRadarCompare, PlayerSkillRadarSolo } from "./PlayerSkillRadar"
import { PlayerTrendChart } from "./PlayerTrendChart"

/** One switchboard: ChartSpec -> renderer, wrapped in shared chrome.
 *
 * The frame owns the header for every kind, so the reused profile components get their
 * own titles suppressed rather than showing two.
 *
 * Unknown kinds fall through to the table, never to nothing. The Team45 dashboard
 * dispatched with a chain of `chartType === "X" &&` blocks and no default branch, so a
 * kind the frontend did not recognise rendered a silent blank.
 */
interface AnalystChartProps {
  spec: ChartSpec
}

export function AnalystChart({ spec }: AnalystChartProps) {
  const yField = spec.y?.[0] ?? null
  const fmt = (v: number) => formatValue(v, yField)

  return (
    <figure className="my-3 rounded-xl border border-ds-border bg-ds-panel p-4">
      <figcaption className="mb-3">
        <h3 className="text-sm font-semibold text-ds-text">{spec.title}</h3>
        {spec.subtitle && (
          <p className="text-[10px] text-ds-muted">{spec.subtitle}</p>
        )}
      </figcaption>

      {renderPlot(spec, fmt)}

      {(spec.notes?.length || spec.citation) && (
        <div className="mt-3 border-t border-ds-border/60 pt-2">
          {spec.notes?.map((note) => (
            <p key={note} className="text-[10px] leading-relaxed text-ds-muted">
              {note}
            </p>
          ))}
          {spec.citation && (
            <p className="mt-0.5 text-[10px] leading-relaxed text-ds-muted/70">
              {spec.citation}
            </p>
          )}
        </div>
      )}
    </figure>
  )
}

function renderPlot(spec: ChartSpec, fmt: (v: number) => string) {
  const yField = spec.y?.[0] ?? null

  switch (spec.kind) {
    case "leaderboard": {
      const rows = spec.rows as unknown as LeaderboardRow[]
      // LeaderboardEntry wants a playerId for highlighting; the plan carries no ids, so
      // a stable synthetic key is enough and nothing is highlighted.
      const entries: LeaderboardEntry[] = rows.map((r) => ({
        rank: r.rank,
        playerId: `${r.name}-${r.rank}`,
        playerName: r.name,
        teamAbbr: r.teamAbbr,
        value: r.value,
      }))
      return (
        <PlayerLeaderboardChart
          entries={entries}
          title=""
          subtitle=""
          statLabel={yField?.label ?? "Value"}
          showHeader={false}
          formatValue={fmt}
        />
      )
    }

    case "trend": {
      const data = spec.rows as unknown as TrendRow[] as TrendPoint[]
      return (
        <PlayerTrendChart
          data={data}
          playerName={spec.title}
          statLabel={yField?.label ?? "Value"}
          showHeader={false}
          formatValue={fmt}
        />
      )
    }

    case "compare_trend": {
      const rows = spec.rows as unknown as CompareTrendRow[]
      return (
        <CompareTrendChart
          rows={rows}
          series={seriesKeys(spec.rows, "season")}
          yField={yField}
        />
      )
    }

    case "radar": {
      const data = spec.rows as unknown as RadarRow[] as SkillRadarCategory[]
      return <PlayerSkillRadarSolo data={data} playerName={spec.series ?? ""} title="" />
    }

    case "compare_radar": {
      const rows = spec.rows as unknown as CompareRadarRow[]
      const keys = seriesKeys(spec.rows, "category")
      if (keys.length < 2) return <AnalystTable rows={spec.rows} columns={spec.y ?? []} />
      return (
        <PlayerSkillRadarCompare
          rows={rows as unknown as SkillCompareRow[]}
          seasonLabel={keys[0]!}
          compareLabel={keys[1]!}
          title=""
        />
      )
    }

    case "scatter": {
      const rows = spec.rows as unknown as ScatterRow[]
      return <AnalystScatter rows={rows} xField={spec.x} yField={yField} />
    }

    case "shot_chart": {
      const cells = spec.rows as unknown as ShotChartRow[]
      const shots = (spec.points ?? []) as unknown as ShotPointRow[]
      // "Makes and misses" is only offered when the individual attempts came through;
      // ShotChartCourt drops it from the toggles otherwise.
      return (
        <ShotChartCourt
          bins={cells}
          shots={shots.length ? (shots as unknown as ShotPoint[]) : undefined}
          playerName={spec.series ?? ""}
          subtitle={spec.subtitle ?? undefined}
          defaultMode={(spec.mode as ShotChartMode) ?? "volume"}
          modes={["makes", "volume", "accuracy", "hotspots", "coldspots"]}
        />
      )
    }

    case "table":
    default:
      return <AnalystTable rows={spec.rows} columns={spec.y ?? []} />
  }
}
