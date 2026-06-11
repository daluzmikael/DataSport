import { TAB_CONFIG, type GameLogTab } from "../data/playerGameLogMock"

import {

  getTeamSeasonAvg,

  getTeamSeasonLabel,

} from "../data/teamBoxScoreMock"

import { getTeamGameStatsByTab, teamGameStatCells } from "../data/teamGameStatsMock"



const TABS: GameLogTab[] = ["general", "advanced", "per36", "per100"]



interface TeamLiveGameStatsProps {

  awayAbbr: string

  homeAbbr: string

  tab: GameLogTab

  onTabChange: (tab: GameLogTab) => void

  awayValues?: Record<string, string | number>

  homeValues?: Record<string, string | number>

  hideSeasonAvg?: boolean

  tabs?: GameLogTab[]

}



function parseStatValue(v: string | number | undefined): number | null {

  if (v === undefined || v === "—" || v === "–" || v === "") return null

  if (typeof v === "number") return v

  const cleaned = String(v).replace(/[^0-9.+-]/g, "")

  if (!cleaned || cleaned === "+" || cleaned === "-") return null

  const n = parseFloat(cleaned)

  return Number.isNaN(n) ? null : n

}



function valueColorClass(

  awayVal: string | number | undefined,

  homeVal: string | number | undefined,

  side: "away" | "home",

): string {

  const a = parseStatValue(awayVal)

  const h = parseStatValue(homeVal)

  if (a == null || h == null) return "text-ds-muted"

  if (a === h) return "text-ds-muted"

  if (side === "away" && a > h) return "font-semibold text-ds-accent"

  if (side === "home" && h > a) return "font-semibold text-ds-accent"

  return "text-ds-muted"

}



export function TeamLiveGameStats({

  awayAbbr,

  homeAbbr,

  tab,

  onTabChange,

  awayValues: awayValuesProp,

  homeValues: homeValuesProp,

  hideSeasonAvg = false,

  tabs: tabsProp,

}: TeamLiveGameStatsProps) {

  const cells = teamGameStatCells(tab)

  const awayValues = awayValuesProp ?? getTeamGameStatsByTab(awayAbbr, tab)

  const homeValues = homeValuesProp ?? getTeamGameStatsByTab(homeAbbr, tab)

  const seasonLabel = getTeamSeasonLabel(awayAbbr)

  const tabs = tabsProp ?? TABS



  const liveRows = [

    { abbr: awayAbbr, side: "away" as const, values: awayValues },

    { abbr: homeAbbr, side: "home" as const, values: homeValues },

  ]



  const seasonRows = [

    { abbr: awayAbbr, values: getTeamSeasonAvg(awayAbbr, tab) },

    { abbr: homeAbbr, values: getTeamSeasonAvg(homeAbbr, tab) },

  ]



  return (

    <div className="border-t border-ds-border bg-ds-raised/50">

      <div className="overflow-x-auto px-3 pt-2 pb-1">

        <table className="w-max min-w-full border-collapse text-[10px] tabular-nums">

          <thead>

            <tr className="text-[9px] uppercase tracking-wide text-ds-muted">

              <th className="sticky left-0 z-10 bg-ds-raised/95 py-1 pr-4 text-left font-medium">

                Team

              </th>

              {cells.map((cell) => (

                <th

                  key={cell.id}

                  className="px-3 py-1 text-left font-medium"

                  style={{ minWidth: cell.minWidth ?? 44 }}

                >

                  {cell.label}

                </th>

              ))}

            </tr>

          </thead>

          <tbody>

            {liveRows.map(({ abbr, side, values }) => (

              <tr key={abbr} className="border-t border-ds-border/40">

                <td className="sticky left-0 z-10 bg-ds-raised/95 py-1.5 pr-4 font-semibold text-ds-text">

                  {abbr}

                </td>

                {cells.map((cell) => {

                  const awayV = awayValues[cell.id]

                  const homeV = homeValues[cell.id]

                  const display = values[cell.id] ?? "—"

                  return (

                    <td

                      key={cell.id}

                      className={`px-3 py-1.5 ${valueColorClass(awayV, homeV, side)}`}

                      style={{ minWidth: cell.minWidth ?? 44 }}

                    >

                      {display}

                    </td>

                  )

                })}

              </tr>

            ))}

          </tbody>

        </table>

      </div>



      <div className="flex justify-center gap-0.5 border-t border-ds-border/50 px-2 py-1.5">

        {tabs.map((id) => (

          <button

            key={id}

            type="button"

            onClick={() => onTabChange(id)}

            className={`rounded px-2.5 py-0.5 text-[9px] font-medium transition ${

              tab === id

                ? "bg-ds-accent/20 text-ds-accent"

                : "text-ds-muted hover:text-ds-text"

            }`}

          >

            {TAB_CONFIG[id].label}

          </button>

        ))}

      </div>



      {!hideSeasonAvg && (

      <div className="overflow-x-auto border-t border-ds-border/50 bg-ds-raised/70 px-3 py-1.5">

        <p className="mb-1 text-[9px] uppercase tracking-wide text-ds-muted">

          {seasonLabel} season avg

        </p>

        <table className="w-max min-w-full border-collapse text-[10px] tabular-nums">

          <tbody>

            {seasonRows.map(({ abbr, values }) => (

              <tr key={`${abbr}-season`} className="border-t border-ds-border/30 first:border-t-0">

                <td className="sticky left-0 z-10 bg-ds-raised/95 py-1 pr-4">

                  <span className="font-semibold text-ds-text">{abbr}</span>

                  <span className="ml-1.5 text-[8px] font-medium text-ds-accent">avg</span>

                </td>

                {cells.map((cell) => (

                  <td

                    key={cell.id}

                    className="px-3 py-1 font-medium text-ds-accent"

                    style={{ minWidth: cell.minWidth ?? 44 }}

                  >

                    {values[cell.id] ?? "—"}

                  </td>

                ))}

              </tr>

            ))}

          </tbody>

        </table>

      </div>

      )}

    </div>

  )

}

