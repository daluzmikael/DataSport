import { ChevronLeft, ChevronRight } from "lucide-react"

import { useState, type ReactNode } from "react"

import type { PlayerLive } from "../types"

import type { SeasonBubbleSet } from "../data/playerSeasonAverages"



function PfStlBlkBubble({ pf, stl, blk }: { pf: number | string; stl: number | string; blk: number | string }) {

  return (

    <div className="rounded-lg border border-ds-border bg-ds-panel p-3">

      <p className="text-[10px] uppercase tracking-wide text-ds-muted">PF | STL | BLK</p>

      <p className="mt-1 font-mono text-lg font-bold tabular-nums">

        {pf}

        <span className="mx-2 font-normal text-ds-muted">|</span>

        {stl}

        <span className="mx-2 font-normal text-ds-muted">|</span>

        {blk}

      </p>

    </div>

  )

}



function StatBubble({

  label,

  primary,

  secondary,

  subline,

}: {

  label: string

  primary: string

  secondary?: string

  subline?: string

}) {

  return (

    <div className="rounded-lg border border-ds-border bg-ds-panel p-3">

      <p className="text-[10px] uppercase text-ds-muted">{label}</p>

      <p className="mt-1 font-mono text-lg font-bold tabular-nums">

        {primary}

        {secondary && (

          <span className="ml-2 text-sm font-semibold text-ds-muted">{secondary}</span>

        )}

      </p>

      {subline && <p className="mt-0.5 font-mono text-[11px] text-ds-muted">{subline}</p>}

    </div>

  )

}



type BubbleView = "general" | "advanced" | "hustle" | "per36" | "per100"



const BUBBLE_VIEWS: BubbleView[] = ["general", "advanced", "hustle", "per36", "per100"]



const BUBBLE_SLIDE_OFFSET: Record<BubbleView, string> = {

  general: "0%",

  advanced: "-20%",

  hustle: "-40%",

  per36: "-60%",

  per100: "-80%",

}



function BubbleNavButton({

  onClick,

  children,

  align = "left",

}: {

  onClick: () => void

  children: ReactNode

  align?: "left" | "right"

}) {

  return (

    <button

      type="button"

      onClick={onClick}

      className={`flex items-center gap-1 rounded-md border border-ds-border bg-ds-raised/80 px-2 py-1 text-[11px] font-medium text-ds-muted transition hover:border-ds-accent/40 hover:text-ds-text ${

        align === "right" ? "ml-auto" : ""

      }`}

    >

      {children}

    </button>

  )

}



interface PlayerStatBubblesProps {

  mode: "game" | "season"

  player?: PlayerLive

  season?: SeasonBubbleSet

  /** Shown on the same row as view nav (e.g. “2024-25 season”). */

  sectionLabel?: string

  /** Left side of the nav row (e.g. season picker + log tabs). */

  headerLeft?: ReactNode

}



const GRID_CLASS = "grid w-1/5 shrink-0 grid-cols-2 gap-3 sm:grid-cols-4"



function viewIndex(view: BubbleView): number {

  return BUBBLE_VIEWS.indexOf(view)

}



function BubbleViewNav({

  view,

  onViewChange,

}: {

  view: BubbleView

  onViewChange: (next: BubbleView) => void

}) {

  const idx = viewIndex(view)

  const prev = idx > 0 ? BUBBLE_VIEWS[idx - 1] : null

  const next = idx < BUBBLE_VIEWS.length - 1 ? BUBBLE_VIEWS[idx + 1] : null



  const prevLabel: Record<BubbleView, string> = {

    general: "",

    advanced: "To general",

    hustle: "To advanced",

    per36: "To hustle",

    per100: "To per 36",

  }

  const nextLabel: Record<BubbleView, string> = {

    general: "To advanced",

    advanced: "To hustle",

    hustle: "To per 36",

    per36: "To per 100",

    per100: "",

  }



  return (

    <div className="ml-auto flex items-center gap-1">

      {prev && (

        <BubbleNavButton onClick={() => onViewChange(prev)}>

          <ChevronLeft className="h-3.5 w-3.5" />

          {prevLabel[view]}

        </BubbleNavButton>

      )}

      {view === "hustle" && (

        <>

          <button

            type="button"

            onClick={() => onViewChange("per36")}

            className="rounded-md border border-ds-border bg-ds-raised/80 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-ds-muted transition hover:border-ds-accent/40 hover:text-ds-text"

          >

            Per 36

          </button>

          <button

            type="button"

            onClick={() => onViewChange("per100")}

            className="rounded-md border border-ds-border bg-ds-raised/80 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-ds-muted transition hover:border-ds-accent/40 hover:text-ds-text"

          >

            Per 100

          </button>

        </>

      )}

      {next && (

        <BubbleNavButton onClick={() => onViewChange(next)}>

          {nextLabel[view]}

          <ChevronRight className="h-3.5 w-3.5" />

        </BubbleNavButton>

      )}

    </div>

  )

}



function RateBubbleGrid({ s, label }: { s: SeasonBubbleSet; label: "per36" | "per100" }) {

  const pts = label === "per36" ? s.per36Pts : s.per100Pts

  const reb = label === "per36" ? s.per36Reb : s.per100Reb

  const ast = label === "per36" ? s.per36Ast : s.per100Ast

  const stl = label === "per36" ? s.per36Stl : s.per100Stl

  const blk = label === "per36" ? s.per36Blk : s.per100Blk

  const tov = label === "per36" ? s.per36Tov : s.per100Tov

  const title = label === "per36" ? "Per 36 min" : "Per 100 poss"



  return (

    <>

      <StatBubble label={`${title} · PTS`} primary={pts} />

      <StatBubble label={`${title} · REB`} primary={reb} />

      <StatBubble label={`${title} · AST`} primary={ast} secondary={`${tov} TOV`} />

      <PfStlBlkBubble pf={s.pf} stl={stl} blk={blk} />

      <StatBubble label="FG%" primary={s.fgPct} subline={s.fg} />

      <StatBubble label="3P%" primary={s.fg3Pct} subline={s.fg3} />

      <StatBubble label="FT%" primary={s.ftPct} subline={s.ft} />

      <StatBubble label="MPG" primary={s.minutes} />

    </>

  )

}



export function PlayerStatBubbles({

  mode,

  player,

  season,

  sectionLabel,

  headerLeft,

}: PlayerStatBubblesProps) {

  const [view, setView] = useState<BubbleView>("general")

  if (mode === "game" && !player) return null

  if (mode === "season" && !season) return null



  const p = player!

  const s = season!



  const nav = <BubbleViewNav view={view} onViewChange={setView} />



  return (

    <div>

      {sectionLabel ? (

        <div className="mb-1.5 flex items-center justify-between gap-3">

          <p className="shrink-0 text-[10px] font-bold uppercase tracking-wider text-ds-muted">

            {sectionLabel}

          </p>

          <div className="flex min-w-0 flex-1 items-center justify-end gap-2">{nav}</div>

        </div>

      ) : headerLeft ? (

        <div className="mb-2 flex min-h-[28px] items-center gap-3">

          <div className="flex min-w-0 items-center gap-3">{headerLeft}</div>

          {nav}

        </div>

      ) : (

        <div className="mb-2 flex min-h-[28px] items-center">{nav}</div>

      )}

      <div className="overflow-hidden">

        <div

          className="flex w-[500%] transition-transform duration-300 ease-out"

          style={{ transform: `translateX(${BUBBLE_SLIDE_OFFSET[view]})` }}

        >

          <div className={GRID_CLASS}>

            {mode === "game" ? (

              <>

                <StatBubble label="PTS" primary={String(p.pts)} />

                <StatBubble label="FG" primary={p.fg} secondary={p.fgPct} />

                <StatBubble label="3P" primary={p.fg3} secondary={p.fg3Pct} />

                <StatBubble label="FT" primary={p.ft} secondary={p.ftPct} />

                <StatBubble

                  label="REB"

                  primary={String(p.reb)}

                  subline={`${p.oreb} oreb · ${p.dreb} dreb`}

                />

                <StatBubble label="AST" primary={String(p.ast)} secondary={`${p.tov} TOV`} />

                <PfStlBlkBubble pf={p.pf} stl={p.stl} blk={p.blk} />

                <StatBubble label="+/-" primary={p.plusMinus} />

              </>

            ) : (

              <>

                <StatBubble label="PPG" primary={s.pts} />

                <StatBubble label="FG" primary={s.fg} secondary={s.fgPct} />

                <StatBubble label="3P" primary={s.fg3} secondary={s.fg3Pct} />

                <StatBubble label="FT" primary={s.ft} secondary={s.ftPct} />

                <StatBubble

                  label="RPG"

                  primary={s.reb}

                  subline={`${s.oreb} oreb · ${s.dreb} dreb`}

                />

                <StatBubble label="APG" primary={s.ast} secondary={`${s.tov} TOV`} />

                <PfStlBlkBubble pf={s.pf} stl={s.stl} blk={s.blk} />

                <StatBubble label="+/-" primary={s.plusMinus} />

              </>

            )}

          </div>

          <div className={GRID_CLASS}>

            {mode === "game" ? (

              <>

                <StatBubble label="TS%" primary={p.tsPct} />

                <StatBubble label="eFG%" primary={p.efgPct} />

                <StatBubble label="USG%" primary={p.usgPct} />

                <StatBubble label="AST%" primary={p.astPct} />

                <StatBubble label="AST/TOV" primary={p.astToTov} />

                <StatBubble label="OREB%" primary={p.orebPct} />

                <StatBubble label="DREB%" primary={p.drebPct} />

                <StatBubble label="PIE" primary={p.pie} />

              </>

            ) : (

              <>

                <StatBubble label="TS%" primary={s.tsPct} />

                <StatBubble label="eFG%" primary={s.efgPct} />

                <StatBubble label="USG%" primary={s.usgPct} />

                <StatBubble label="AST%" primary={s.astPct} />

                <StatBubble label="AST/TOV" primary={s.astToTov} />

                <StatBubble label="OREB%" primary={s.orebPct} />

                <StatBubble label="DREB%" primary={s.drebPct} />

                <StatBubble label="PIE" primary={s.pie} />

              </>

            )}

          </div>

          <div className={GRID_CLASS}>

            {mode === "game" ? (

              <>

                <StatBubble

                  label="Contested"

                  primary={String(p.contestedShots)}

                  subline={`${p.contestedShots2pt} 2PT · ${p.contestedShots3pt} 3PT`}

                />

                <StatBubble label="Deflections" primary={String(p.deflections)} />

                <StatBubble

                  label="Screens"

                  primary={String(p.screenAssists)}

                  secondary={`${p.screenAssistPoints} pts`}

                />

                <StatBubble

                  label="Box outs"

                  primary={String(p.boxOuts)}

                  subline={`${p.offensiveBoxOuts} off · ${p.defensiveBoxOuts} def`}

                />

                <StatBubble

                  label="Loose balls"

                  primary={String(p.looseBallsRecoveredTotal)}

                  subline={`${p.looseBallsRecoveredOffensive} off · ${p.looseBallsRecoveredDefensive} def`}

                />

                <StatBubble label="Charges" primary={String(p.chargesDrawn)} />

                <StatBubble

                  label="BOX REB"

                  primary={`${p.boxOutPlayerTeamRebounds} · ${p.boxOutPlayerRebounds}`}

                  subline="team reb · player reb"

                />

                <StatBubble label="MIN" primary={String(p.minutes)} />

              </>

            ) : (

              <>

                <StatBubble

                  label="Contested"

                  primary={s.contestedShots}

                  subline={`${s.contestedShots2pt} 2PT · ${s.contestedShots3pt} 3PT`}

                />

                <StatBubble label="Deflections" primary={s.deflections} />

                <StatBubble

                  label="Screens"

                  primary={s.screenAssists}

                  secondary={`${s.screenAssistPoints} pts`}

                />

                <StatBubble

                  label="Box outs"

                  primary={s.boxOuts}

                  subline={`${s.offensiveBoxOuts} off · ${s.defensiveBoxOuts} def`}

                />

                <StatBubble

                  label="Loose balls"

                  primary={s.looseBallsRecoveredTotal}

                  subline={`${s.looseBallsRecoveredOffensive} off · ${s.looseBallsRecoveredDefensive} def`}

                />

                <StatBubble label="Charges" primary={s.chargesDrawn} />

                <StatBubble

                  label="BOX REB"

                  primary={`${s.boxOutPlayerTeamRebounds} · ${s.boxOutPlayerRebounds}`}

                  subline="team reb · player reb"

                />

                <StatBubble label="MPG" primary={s.minutes} />

              </>

            )}

          </div>

          <div className={GRID_CLASS}>

            {mode === "season" ? (

              <RateBubbleGrid s={s} label="per36" />

            ) : (

              <p className="col-span-full text-xs text-ds-muted">Per 36 rates — season view only</p>

            )}

          </div>

          <div className={GRID_CLASS}>

            {mode === "season" ? (

              <RateBubbleGrid s={s} label="per100" />

            ) : (

              <p className="col-span-full text-xs text-ds-muted">Per 100 poss — season view only</p>

            )}

          </div>

        </div>

      </div>

    </div>

  )

}

