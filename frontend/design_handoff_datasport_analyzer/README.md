# Handoff: DataSport Analyzer Prototype

## Overview
A clickable prototype for DataSport, an NBA analytics assistant. Covers three linked screens: an "Analyzer" home (ask bar + live game board), a Team profile, and a Player profile, with animated transitions between the home board and detail screens. Mock data is Celtics–Heat (2024-25 season).

## About the Design Files
The files in this bundle are **design references built in HTML** (a custom internal prototyping format, flattened here to plain HTML/CSS/JS) — they show intended layout, styling, and interaction behavior, not production code to copy directly. Recreate this design in your codebase's existing environment (React, Vue, native, etc.) using its established components and patterns. If no frontend exists yet, choose the framework best suited to the project.

## Fidelity
**High-fidelity.** Colors, typography, spacing, and interactions in `DataSport Redesign.dc.html` are final — reproduce pixel-accurately using your codebase's design system/component library, applying the token values below.

## Screens / Views

### 1. Analyzer home (`isHomeScreen`)
- **Purpose:** Entry screen — user asks a free-text question about any stat, and sees a "live board" of followed teams/players in a right rail.
- **Layout:** Root is a flex row: fixed 76px-wide dark nav rail (sticky, full height) + main content area. Main content is itself a flex row: center column (`flex:1`, `max-width:760px`, centered, padding `40px 32px 72px`) and a fixed `340px` right aside (padding `24px 20px`, left border hairline).
- **Components:**
  - Kicker "DataSport · Analyst mode" (`.card-kicker`, 12px).
  - H1 "Ask about any stat" — 48px, heading font, margin-bottom 20px.
  - Ask bar: text input (`.input`, flex:1, placeholder "Ask DataSport… e.g. Celtics 3PT shooting tonight") + primary button "Ask" (`.btn.btn-primary`), gap 10px, margin-bottom 28px.
  - Assistant reply card: `.card` on `var(--color-bg)`, `var(--shadow-sm)`, padding 20px — kicker "Assistant" + welcome/instruction paragraph (16px).
  - Suggested-prompt chips row (wraps, gap 8px, margin-top 16px): 3 pill chips, 1px accent border, accent text, 12px, radius `calc(var(--radius-md) * 0.75)`, padding `5px 10px`. Copy: "Celtics 3PT shooting tonight", "Jordan best 3PT season", "Tatum vs Brown usage 2024-25".
  - Right aside "Your live board": kicker, H4 "Live now", muted helper line "Teams & players you follow — tap for full stats." (12px).
  - **Live board card** (clickable button, full width, navigates to Team profile): surface bg, `var(--shadow-sm)`, 1px divider border, radius `var(--radius-md)`, padding 14px.
    - Row 1: `.tag.tag-accent` "Live · Following" + right-aligned "Q3 · 5:46" (11px, neutral-600).
    - Row 2 (heading font): left "Heat / MIA", center score "82 – 87" (22px bold), right "Celtics / BOS" (BOS in accent-700).
    - Hairline `.hr`.
    - 3-column stat grid (PTS / AST / REB), each: kicker label, top scorer bold, second scorer muted (11px).

### 2. Team profile (`isTeamScreen`)
- **Purpose:** Full team stat page reached by clicking the live-board card. Slides in from the right (see Interactions).
- **Layout:** `flex:1, max-width:1040px`, centered, padding `32px 24px 72px`.
- **Components:**
  - Back link "← Analyzer" (13px) → home.
  - Header card (`.card`, bg, shadow-sm, padding `24px 28px`, flex row wrap gap 40px):
    - Left: kicker "Franchise", H1 "{city} {name}" (48px), sub-line "{abbr} · {season} season" (20px heading, accent-700).
    - Right: 3 stat blocks (flex gap 36px) — Standing, Record, "Best player (GS)" (name 19px + big GS value 26px accent).
  - Tab row (bottom border divider): Overview / Season Leaders / Game Log / Roster. Active tab: 2px accent underline, full-opacity text; inactive: transparent underline, 55%-opacity text. `padding:10px 18px 10px 0`, margin-right 20px, 15px heading font weight 600.
  - **Overview tab:** "Season leaders" H3 + 3-col grid of top-3 leader cards (kicker=stat, title=player 19px, big value 30px accent, meta "Per game · {season}"). Below: "Key stats" H3 + hairline + 6-col grid (Record/PPG/RPG/APG/FG%/3P%), each kicker + 24px bold value.
  - **Season Leaders tab:** table (12 rows: PTS, REB, AST, STL, BLK, 3PM, TS%, USG%, FG%, 3P%, TOV, MIN) — Stat / Leader (name links to Player profile only when leader is Jayson Tatum) / Value.
  - **Game Log tab:** sub-tab pill row (General/Advanced, pill radius 999px, 13px). General table: Game, W/L, MIN, PTS, FG%, 3P%, REB, AST, STL, +/- , with a highlighted "Season avg" row (accent-tinted bg 8%) pinned above 9 game rows, first game labeled "LIVE vs MIA". Advanced table: Game, OFF RTG, DEF RTG, NET RTG, TS%, eFG%, PACE, same season-avg-row pattern.
  - **Roster tab:** helper text "{count} players" + table (#, Name, Pos, Ht) for 14 players; Jayson Tatum's name links to Player profile.

### 3. Player profile (`isPlayerScreen`)
- **Purpose:** Individual player stat page, reached from Team Leaders/Roster tables. Slides in from the right.
- **Layout:** `flex:1, max-width:900px`, centered, padding `32px 24px 72px`.
- **Components:**
  - Two back links: "← {team} roster" → Team profile (roster tab) and "← Analyzer" → home, separated by a "·" divider.
  - Header card: name H1 (48px), "{team} · {season} season" sub-line, right-side boxed "Season GS" stat (30px accent value + rank "#{rank} of {total}").
  - "Career accolades" H3 + 4-col card grid (Championships, All-NBA, All-Star, Draft), each kicker + 28px value + 12px subline.
  - "Game log" H3 + General/Advanced sub-tabs, same table pattern as team (General: Game/W-L/MIN/PTS/FG%/3P%/REB/AST/STL/+-, 7 games + season-avg row; Advanced: Game/TS%/eFG%/USG%/PIE).

### Nav rail (persistent, all screens)
- 76px wide, full viewport height, sticky, dark bg (`var(--color-neutral-900)`), padding `20px 0`, flex column centered.
- "DS" monogram badge (34×34, 1px accent-400 border, radius `--radius-md`, accent-400 text, heading font 14px bold), margin-bottom 24px.
- 4 icon buttons (Lucide icons, 19×19, stroke-width 1.75), gap 6px: Analyzer (bookmark/panel icon, active on home), Following (star icon, active on team/player), Dashboard and Social (both disabled/"soon", muted color, cursor not-allowed).
- Active icon: 40×40, radius `--radius-md`, bg = accent-400 at 22% mix, icon color accent-400. Inactive: transparent bg, neutral-300 icon. Disabled/muted: neutral-700 icon, no bg.
- Bottom-pinned (margin-top:auto), separated by 1px neutral-700 top border: Account and Settings icon buttons (both disabled, muted style).

## Interactions & Behavior
- **Home → Team:** clicking the live-board card sets screen to "team"; the Team profile container animates in with `slideInFromBoard` (translateX 100%→0 + opacity 0→1, 0.45s, cubic-bezier(0.22,1,0.36,1)) — reads as sliding out from the live board on the right.
- **Team/Player → Home:** clicking "← Analyzer" triggers a 2-step transition: set `leaving:true` (screen stays visible, animates `slideOutToBoard` — translateX 0→100%, opacity 1→0, 0.42s, cubic-bezier(0.4,0,1,1)), then after 430ms setState to `screen:"home", leaving:false`. This produces a slide-out-to-the-right before the home screen reappears (no flash/pop).
- **Team → Player** and **Player → Team (roster tab)**: instant screen swap, no animation (only the home↔detail transition is animated).
- **Tabs** (Team: Overview/Leaders/Game Log/Roster; Game Log & Player Game Log sub-tabs General/Advanced): simple state toggles, no transition — active tab gets accent underline or accent pill border.
- **Nav rail icons:** Analyzer and Following are clickable (routed via `goHome`/`goTeam`); Dashboard, Social, Account, Settings are disabled placeholders (`cursor:not-allowed`, muted color) — not yet built.
- **Links inside tables:** only the row matching "Jayson Tatum" renders as a clickable link to the Player profile; all other names render as plain (non-interactive) text — this is deliberate, not a bug, since only one player has profile data in the mock.
- No loading states, no error states, no form validation — the ask bar's input/button are visual only (not wired to a real query in this prototype).
- No responsive breakpoints authored — layout assumes a desktop viewport (nav rail + fixed-width aside).

## State Management
Single component state object:
- `screen`: `"home" | "team" | "player"` — which top-level view is shown.
- `leaving`: boolean — true during the home-return slide-out animation window.
- `teamTab`: `"overview" | "leaders" | "gamelog" | "roster"`.
- `teamLogTab`: `"general" | "advanced"` (Team Game Log sub-tab).
- `playerLogTab`: `"general" | "advanced"` (Player Game Log sub-tab).

Transitions: `goHome` (only from team/player, runs the 430ms leave-then-switch sequence), `goTeam` (home → team, resets `leaving`), `goPlayer` (→ player, tab unchanged), `goTeamRoster` (→ team with `teamTab` forced to `"roster"`, used by the Player profile's back link).

Data requirements for a real backend: team record/standing/season averages, team game log (general + advanced box scores per game, with a live/in-progress row), team season leaders (per-stat), full roster, player profile (accolades, season averages, game log general + advanced). All of this is currently static mock data (Celtics/Heat, Tatum-centric) — see `DataSport Redesign.dc.html`'s embedded `TEAM`, `PLAYER`, `TEAM_GAMES_GENERAL`, `TEAM_GAMES_ADVANCED`, `TEAM_LEADERS_RAW`, `ROSTER_RAW`, `PLAYER_GAMES_GENERAL`, `PLAYER_GAMES_ADVANCED` constants for exact shape and sample values.

## Design Tokens
Full token sheet: `design-system/styles.css` (source of truth) and `design-system/readme.md` (usage guidance). Key values used in this design:

**Color**
- Ground/background: `--color-bg` (#f3f2f2 near-white), `--color-surface` (page ground behind nav), `--color-neutral-900` (dark nav rail).
- Text: `--color-text` (#201f1d).
- Accent: `--color-accent` (#b68235, gold), with tonal ramp `--color-accent-100…900`; accent-400 used for nav-rail active states on dark bg, accent-700 for accent text on light bg (contrast-safe), accent-600 for hover/pressed.
- Dividers/borders: `--color-divider`, `--color-neutral-600/700` (muted labels, disabled icons).
- Shadows: `--shadow-sm` on all cards (whisper-level elevation only).

**Type**
- Headings: `--font-heading` (Cormorant Garamond), weight capped at 600 (semibold), used for all numeric stat values, H1/H3, tab labels, card titles.
- Body: `--font-body` (Lora), used for paragraphs, table cells, buttons, links.
- Sizes in use: 48px (screen H1), 30px/28px/26px (feature stat numbers), 24px (key-stat grid), 22px/19px/18px (sub-headers, score), 15-16px (body/table), 12-13px (meta/kicker/links), 11px (uppercase micro-labels, letter-spacing 0.08em).

**Spacing / Radius**
- `--radius-md` for cards, buttons, nav icon backgrounds; `999px` (full pill) for Game Log sub-tab buttons.
- Density follows the design system's 1.15× spacing scale (`--space-*`); this design mostly uses literal px values matching that scale (8/10/12/14/16/20/24/28/32/36/40px gaps and paddings) — carry these forward as spacing-token equivalents in your codebase rather than re-deriving from scratch.

**Components used from the design system** (recreate with your library's equivalents, matching the token values above): `.card`, `.card-kicker`, `.card-title`, `.card-meta`, `.btn`/`.btn-primary`, `.input`, `.tag`/`.tag-accent`, `.table`, `.hr`.

## Assets
No image/photo assets — icons only. All icons are inline SVG, Lucide icon set (https://lucide.dev), stroke-based, 19×19px, stroke-width 1.75, round caps/joins. Icons used: panel/dashboard-left (Analyzer), star-badge (Following), grid/layout-dashboard (Dashboard), users (Social), user-circle (Account), settings-gear (Settings).

## Files
- `DataSport Redesign.dc.html` — the full prototype (all 3 screens, all mock data, all interaction logic) in one file. This is the authoritative reference for exact markup, inline styles, and state logic — read it alongside this README.
- `design-system/styles.css` — token source (colors, type, spacing, radius, shadows, base component classes).
- `design-system/readme.md` — design system usage guide (component list, do/don't rules).
