import type { ReactNode } from "react"
import {
  buildPaintFtScatter,
  buildTeamCompareRadar,
} from "../../data/teamGameChartsMock"
import { TeamCompareRadar } from "./TeamCompareRadar"
import { TeamPaintFtScatter } from "./TeamPaintFtScatter"

const CHART_HINT =
  "Want a different view? Ask in the analyzer below — e.g. swap axes, try per-36, or pick another chart type."

interface TeamGameChartsSectionProps {
  awayAbbr: string
  homeAbbr: string
}

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-ds-border bg-ds-panel">
      <div className="border-b border-ds-border/60 bg-ds-raised/40 px-3 py-2">
        <p className="text-[10px] leading-snug text-ds-muted">{CHART_HINT}</p>
      </div>
      <div className="border-b border-ds-border px-3 py-2">
        <h3 className="text-sm font-semibold text-ds-text">{title}</h3>
        <p className="text-[10px] text-ds-muted">{subtitle}</p>
      </div>
      <div className="flex-1 px-2 py-3">{children}</div>
    </article>
  )
}

export function TeamGameChartsSection({
  awayAbbr,
  homeAbbr,
}: TeamGameChartsSectionProps) {
  const scatter = buildPaintFtScatter(awayAbbr, homeAbbr)
  const radar = buildTeamCompareRadar(awayAbbr, homeAbbr)

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard
        title="Paint points vs free throw attempts"
        subtitle={`Tonight · ${awayAbbr} & ${homeAbbr} players`}
      >
        <TeamPaintFtScatter points={scatter} awayAbbr={awayAbbr} homeAbbr={homeAbbr} />
      </ChartCard>

      <ChartCard
        title="Team skill profile"
        subtitle={`Live game comparison · ${awayAbbr} vs ${homeAbbr}`}
      >
        <TeamCompareRadar data={radar} awayAbbr={awayAbbr} homeAbbr={homeAbbr} />
      </ChartCard>
    </div>
  )
}
