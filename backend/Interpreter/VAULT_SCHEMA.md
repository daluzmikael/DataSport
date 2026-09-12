# Vault schema map

Generated 2026-09-03 by `scripts/generate_vault_schema.py` directly from the live DuckDB views. Do not hand-edit — re-run the script.

**Read this before choosing a table.** Every column, slice value and season range below is what the data actually contains, not what it is expected to contain. If a stat is not listed here, it is not in the vault; say so rather than substituting a different stat.

27 tables registered.

## Where to find a stat

| If the question is about | Use this table |
|---|---|
| A player's season box score (points, rebounds, shooting splits, clutch, hustle) | `player_season_stats` |
| A team's season box score | `team_season_stats` |
| Player season efficiency / impact ratings (E_ prefixed) | `player_estimated_metrics` |
| Team season efficiency / pace | `team_estimated_metrics` |
| One player in one game, or game-by-game form | `player_game_logs` |
| One team in one game, or schedule/results | `team_game_logs` |
| Standings, record, seeding, streaks | `team_standings` |
| Shooting broken out by court zone | `player_shot_zones / team_shot_zones` |
| Tracking (drives, touches, rim defense, catch-and-shoot) | `player_tracking / team_tracking` |
| Five-man lineup units, and the only TS%/EFG%/PIE at season grain | `lineups` |
| Game-level advanced (true shooting, usage, PIE per game) | `player_game_advanced` |

## Tables

### `all_time_leaders`

- rows: **9,500**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Andre Miller', 'Nick Van Exel', 'Kevin Porter'
- **no `season` column** — cannot be filtered by season.
- columns: **7** total

  `PLAYER_ID`, `PLAYER_NAME`, `STAT`, `VALUE`, `IS_ACTIVE`, `SOURCE_GRID`

  - plus 1 × `*_RANK` (league rank)

### `court_shots`

- rows: **591,155**
- name column: **NONE — this table cannot be filtered by a person's or team's name.** Do not route a named-entity question here.
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- columns: **10** total

  `season`, `season_type`, `player_id`, `GRID_TYPE`, `SHOT_ZONE_BASIC`, `SHOT_ZONE_AREA`, `SHOT_ZONE_RANGE`, `FGA`, `FGM`, `FG_PCT`

### `franchise_history`

- rows: **74**
- name column: `TEAM_NAME` — filterable by name. Values look like: 'Grizzlies', 'Heat', 'Nets'
- **no `season` column** — cannot be filtered by season.
- columns: **16** total

  `LEAGUE_ID`, `TEAM_ID`, `TEAM_CITY`, `TEAM_NAME`, `TEAM_FULL_NAME`, `START_YEAR`, `END_YEAR`, `YEARS`, `GAMES`, `WINS`, `LOSSES`, `WIN_PCT`, `PO_APPEARANCES`, `DIV_TITLES`, `CONF_TITLES`, `LEAGUE_TITLES`

### `game_context`

- rows: **741,532**
- name column: `teamName` — filterable by name. Values look like: 'Rockets', 'Cavaliers', 'Hawks'
- **no `season` column** — cannot be filtered by season.
- columns: **81** total

  `game_id`, `dataset`, `gameId`, `gameCode`, `gameStatus`, `gameStatusText`, `period`, `gameClock`, `gameTimeUTC`, `gameEt`, `awayTeamId`, `homeTeamId`, `duration`, `attendance`, `sellout`, `gameDate`, `gameDuration`, `arenaId`, `arenaName`, `arenaCity`, `arenaState`, `arenaCountry`, `arenaTimezone`, `teamId`, `teamCity`, `teamName`, `teamTricode`, `teamSlug`, `teamWins`, `teamLosses`, `period1Score`, `period2Score`, `period3Score`, `period4Score`, `score`, `recencyOrder`, `awayTeamCity`, `awayTeamName`, `awayTeamTricode`, `awayTeamScore`, `awayTeamWins`, `awayTeamLosses`, `homeTeamCity`, `homeTeamName`, `homeTeamTricode`, `homeTeamScore`, `homeTeamWins`, `homeTeamLosses`, `points`, `reboundsTotal`, `assists`, `steals`, `blocks`, `turnovers`, `fieldGoalsPercentage`, `threePointersPercentage`, `freeThrowsPercentage`, `pointsInThePaint`, `pointsSecondChance`, `pointsFastBreak`, `biggestLead`, `leadChanges`, `timesTied`, `biggestScoringRun`, `turnoversTeam`, `turnoversTotal`, `reboundsTeam`, `pointsFromTurnovers`, `benchPoints`, `videoAvailableFlag`, `ptAvailable`, `ptXYZAvailable`, `whStatus`, `hustleStatus`, `historicalStatus`, `personId`, `firstName`, `familyName`, `jerseyNum`, `name`, `nameI`

### `legacy_season_stats`

- rows: **15,078**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Bob Harrison', 'Jack Coleman', 'Billy Gabor'
- season coverage: **1951-52 → 1995-96**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `Totals`
- columns: **27** total

  `PLAYER_ID`, `PLAYER_NAME`, `season`, `season_type`, `per_mode`, `TEAM_ID`, `TEAM_ABBREVIATION`, `GP`, `MIN`, `FGM`, `FGA`, `FG_PCT`, `FG3M`, `FG3A`, `FG3_PCT`, `FTM`, `FTA`, `FT_PCT`, `OREB`, `DREB`, `REB`, `AST`, `STL`, `BLK`, `TOV`, `PF`, `PTS`

### `lineups`

- rows: **717,588**
- name column: `GROUP_NAME` — filterable by name. Values look like: 'R. Horry - B. Bowen - T. Duncan - M. Ginobili - T. Parker', 'K. Garnett - R. Allen - P. Pierce - J. Posey - E. House', 'R. Wallace - R. Hamilton - T. Prince - J. Maxiell - R. Stuckey'
- season coverage: **2007-08 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `PerGame`, `Totals`
- `measure_type` values present: `Advanced`, `Base`, `Four Factors`, `Misc`, `Opponent`, `Scoring`
- `group_quantity` values present: `5`
- columns: **193** total

  `GROUP_ID`, `season`, `season_type`, `group_quantity`, `measure_type`, `per_mode`, `GROUP_SET`, `GROUP_NAME`, `TEAM_ID`, `TEAM_ABBREVIATION`, `GP`, `W`, `L`, `W_PCT`, `MIN`, `E_OFF_RATING`, `OFF_RATING`, `E_DEF_RATING`, `DEF_RATING`, `E_NET_RATING`, `NET_RATING`, `AST_PCT`, `AST_TO`, `AST_RATIO`, `OREB_PCT`, `DREB_PCT`, `REB_PCT`, `TM_TOV_PCT`, `EFG_PCT`, `TS_PCT`, `E_PACE`, `PACE`, `PACE_PER40`, `POSS`, `PIE`, `SUM_TIME_PLAYED`, `FGM`, `FGA`, `FG_PCT`, `FG3M`, `FG3A`, `FG3_PCT`, `FTM`, `FTA`, `FT_PCT`, `OREB`, `DREB`, `REB`, `AST`, `TOV`, `STL`, `BLK`, `BLKA`, `PF`, `PFD`, `PTS`, `PLUS_MINUS`, `FTA_RATE`, `OPP_EFG_PCT`, `OPP_FTA_RATE`, `OPP_TOV_PCT`, `OPP_OREB_PCT`, `PTS_OFF_TOV`, `PTS_2ND_CHANCE`, `PTS_FB`, `PTS_PAINT`, `OPP_PTS_OFF_TOV`, `OPP_PTS_2ND_CHANCE`, `OPP_PTS_FB`, `OPP_PTS_PAINT`, `OPP_FGM`, `OPP_FGA`, `OPP_FG_PCT`, `OPP_FG3M`, `OPP_FG3A`, `OPP_FG3_PCT`, `OPP_FTM`, `OPP_FTA`, `OPP_FT_PCT`, `OPP_OREB`, `OPP_DREB`, `OPP_REB`, `OPP_AST`, `OPP_TOV`, `OPP_STL`, `OPP_BLK`, `OPP_BLKA`, `OPP_PF`, `OPP_PFD`, `OPP_PTS`, `PCT_FGA_2PT`, `PCT_FGA_3PT`, `PCT_PTS_2PT`, `PCT_PTS_2PT_MR`, `PCT_PTS_3PT`, `PCT_PTS_FB`, `PCT_PTS_FT`, `PCT_PTS_OFF_TOV`, `PCT_PTS_PAINT`, `PCT_AST_2PM`, `PCT_UAST_2PM`, `PCT_AST_3PM`, `PCT_UAST_3PM`, `PCT_AST_FGM`, `PCT_UAST_FGM`

  - plus 88 × `*_RANK` (league rank)

### `player_awards`

- rows: **5,722**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Arvydas Macijauskas', 'Gerard King', 'Willy Hernangomez'
- **no `season` column** — cannot be filtered by season.
- columns: **17** total

  `PERSON_ID`, `PLAYER_NAME`, `FIRST_NAME`, `LAST_NAME`, `TEAM`, `DESCRIPTION`, `ALL_NBA_TEAM_NUMBER`, `SEASON`, `MONTH`, `WEEK`, `CONFERENCE`, `TYPE`, `SUBTYPE1`, `SUBTYPE2`, `SUBTYPE3`, `SEASON_END_YEAR`, `IS_SEASON_AWARD`

### `player_bio`

- rows: **2,860**
- name column: `TEAM_NAME` — filterable by name. Values look like: '', 'Rockets', 'Pacers'
- **no `season` column** — cannot be filtered by season.
- columns: **39** total

  `PERSON_ID`, `FIRST_NAME`, `LAST_NAME`, `DISPLAY_FIRST_LAST`, `DISPLAY_LAST_COMMA_FIRST`, `DISPLAY_FI_LAST`, `PLAYER_SLUG`, `BIRTHDATE`, `SCHOOL`, `COUNTRY`, `LAST_AFFILIATION`, `HEIGHT`, `WEIGHT`, `SEASON_EXP`, `JERSEY`, `POSITION`, `ROSTERSTATUS`, `GAMES_PLAYED_CURRENT_SEASON_FLAG`, `TEAM_ID`, `TEAM_NAME`, `TEAM_ABBREVIATION`, `TEAM_CODE`, `TEAM_CITY`, `PLAYERCODE`, `FROM_YEAR`, `TO_YEAR`, `DLEAGUE_FLAG`, `NBA_FLAG`, `GAMES_PLAYED_FLAG`, `DRAFT_YEAR`, `DRAFT_ROUND`, `DRAFT_NUMBER`, `GREATEST_75_FLAG`, `SUPPLEMENTAL_STATUS`, `HEIGHT_INCHES`, `WEIGHT_LBS`, `DRAFT_YEAR_NUM`, `DRAFT_ROUND_NUM`, `DRAFT_NUMBER_NUM`

### `player_career`

- rows: **208,828**
- name column: **NONE — this table cannot be filtered by a person's or team's name.** Do not route a named-entity question here.
- **no `season` column** — cannot be filtered by season.
- columns: **62** total

  `player_id`, `dataset`, `unavailable`, `PLAYER_ID_1`, `SEASON_ID`, `LEAGUE_ID`, `TEAM_ID`, `TEAM_ABBREVIATION`, `PLAYER_AGE`, `GP`, `GS`, `MIN`, `FGM`, `FGA`, `FG_PCT`, `FG3M`, `FG3A`, `FG3_PCT`, `FTM`, `FTA`, `FT_PCT`, `OREB`, `DREB`, `REB`, `AST`, `STL`, `BLK`, `TOV`, `PF`, `PTS`, `RANK_MIN`, `RANK_FGM`, `RANK_FGA`, `RANK_FG_PCT`, `RANK_FG3M`, `RANK_FG3A`, `RANK_FG3_PCT`, `RANK_FTM`, `RANK_FTA`, `RANK_FT_PCT`, `RANK_OREB`, `RANK_DREB`, `RANK_REB`, `RANK_AST`, `RANK_STL`, `RANK_BLK`, `RANK_TOV`, `RANK_PTS`, `RANK_EFF`, `GAME_DATE`, `VS_TEAM_ID`, `VS_TEAM_CITY`, `VS_TEAM_NAME`, `VS_TEAM_ABBREVIATION`, `STAT`, `STATS_VALUE`, `STAT_ORDER`, `DATE_EST`, `GAME_ID`, `STAT_VALUE`, `ORGANIZATION_ID`, `SCHOOL_NAME`

### `player_estimated_metrics`

- rows: **20,668**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Greg Ostertag', 'Chris Childs', 'Robert Horry'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- columns: **34** total

  `PLAYER_ID`, `season`, `season_type`, `PLAYER_NAME`, `GP`, `W`, `L`, `W_PCT`, `MIN`, `E_OFF_RATING`, `E_DEF_RATING`, `E_NET_RATING`, `E_AST_RATIO`, `E_OREB_PCT`, `E_DREB_PCT`, `E_REB_PCT`, `E_TOV_PCT`, `E_USG_PCT`, `E_PACE`

  - plus 15 × `*_RANK` (league rank)

### `player_game_advanced`

- rows: **993,749**
- name column: `teamName` — filterable by name. Values look like: 'Thunder', 'Magic', 'Bulls'
- **no `season` column** — cannot be filtered by season.
- columns: **66** total

  `game_id`, `gameId`, `teamId`, `teamCity`, `teamName`, `teamTricode`, `teamSlug`, `personId`, `firstName`, `familyName`, `nameI`, `playerSlug`, `position`, `comment`, `jerseyNum`, `minutes`, `estimatedOffensiveRating`, `offensiveRating`, `estimatedDefensiveRating`, `defensiveRating`, `estimatedNetRating`, `netRating`, `assistPercentage`, `assistToTurnover`, `assistRatio`, `offensiveReboundPercentage`, `defensiveReboundPercentage`, `reboundPercentage`, `turnoverRatio`, `effectiveFieldGoalPercentage`, `trueShootingPercentage`, `usagePercentage`, `estimatedUsagePercentage`, `estimatedPace`, `pace`, `pacePer40`, `possessions`, `PIE`, `pointsOffTurnovers`, `pointsSecondChance`, `pointsFastBreak`, `pointsPaint`, `oppPointsOffTurnovers`, `oppPointsSecondChance`, `oppPointsFastBreak`, `oppPointsPaint`, `blocks`, `blocksAgainst`, `foulsPersonal`, `foulsDrawn`, `points`

  - plus 15 × `hustle_*` (hustle stat)

### `player_game_logs`

- rows: **786,664**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Alonzo Mourning', 'Buck Williams', 'Nick Van Exel'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- columns: **72** total

  `SEASON_YEAR`, `PLAYER_ID`, `PLAYER_NAME`, `NICKNAME`, `TEAM_ID`, `TEAM_ABBREVIATION`, `TEAM_NAME`, `GAME_ID`, `GAME_DATE`, `MATCHUP`, `WL`, `MIN`, `FGM`, `FGA`, `FG_PCT`, `FG3M`, `FG3A`, `FG3_PCT`, `FTM`, `FTA`, `FT_PCT`, `OREB`, `DREB`, `REB`, `AST`, `TOV`, `STL`, `BLK`, `BLKA`, `PF`, `PFD`, `PTS`, `PLUS_MINUS`, `NBA_FANTASY_PTS`, `DD2`, `TD3`, `WNBA_FANTASY_PTS`, `AVAILABLE_FLAG`, `MIN_SEC`, `TEAM_COUNT`, `season`, `season_type`

  - plus 30 × `*_RANK` (league rank)

### `player_on_off`

- rows: **62,626**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Acie Law', 'Sam Cassell', 'Brandon Wallace'
- season coverage: **2007-08 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `PerGame`, `Totals`
- columns: **16** total

  `PLAYER_ID`, `season`, `season_type`, `per_mode`, `TEAM_ID`, `GROUP_SET`, `TEAM_ABBREVIATION`, `TEAM_NAME`, `PLAYER_NAME`, `COURT_STATUS`, `GP`, `MIN`, `PLUS_MINUS`, `OFF_RATING`, `DEF_RATING`, `NET_RATING`

### `player_season_stats`

- rows: **103,340**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Alonzo Mourning', 'Buck Williams', 'Chris Robinson'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `Per100Possessions`, `Per36`, `Per40`, `PerGame`, `Totals`
- columns: **413** total

  `PLAYER_ID`, `season`, `season_type`, `per_mode`, `PLAYER_NAME`, `NICKNAME`, `TEAM_ID`, `TEAM_ABBREVIATION`, `AGE`, `GP`, `W`, `L`, `W_PCT`, `MIN`, `FGM`, `FGA`, `FG_PCT`, `FG3M`, `FG3A`, `FG3_PCT`, `FTM`, `FTA`, `FT_PCT`, `OREB`, `DREB`, `REB`, `AST`, `TOV`, `STL`, `BLK`, `BLKA`, `PF`, `PFD`, `PTS`, `PLUS_MINUS`, `NBA_FANTASY_PTS`, `DD2`, `TD3`, `WNBA_FANTASY_PTS`, `TEAM_COUNT`, `GROUP_SET`, `PLAYER_NAME_clutch_dup`, `NICKNAME_clutch_dup`, `TEAM_ABBREVIATION_clutch_dup`, `AGE_clutch_dup`, `E_OFF_RATING`, `OFF_RATING`, `E_DEF_RATING`, `DEF_RATING`, `E_NET_RATING`, `NET_RATING`, `AST_PCT`, `AST_TO`, `AST_RATIO`, `OREB_PCT`, `DREB_PCT`, `REB_PCT`, `TM_TOV_PCT`, `E_TOV_PCT`, `EFG_PCT`, `TS_PCT`, `USG_PCT`, `E_USG_PCT`, `E_PACE`, `PACE`, `PACE_PER40`, `PIE`, `POSS`, `PCT_FGM`, `PCT_FGA`, `PCT_FG3M`, `PCT_FG3A`, `PCT_FTM`, `PCT_FTA`, `PCT_OREB`, `PCT_DREB`, `PCT_REB`, `PCT_AST`, `PCT_TOV`, `PCT_STL`, `PCT_BLK`, `PCT_BLKA`, `PCT_PF`, `PCT_PFD`, `PCT_PTS`, `PTS_OFF_TOV`, `PTS_2ND_CHANCE`, `PTS_FB`, `PTS_PAINT`, `OPP_PTS_OFF_TOV`, `OPP_PTS_2ND_CHANCE`, `OPP_PTS_FB`, `OPP_PTS_PAINT`, `PCT_FGA_2PT`, `PCT_FGA_3PT`, `PCT_PTS_2PT`, `PCT_PTS_2PT_MR`, `PCT_PTS_3PT`, `PCT_PTS_FB`, `PCT_PTS_FT`, `PCT_PTS_OFF_TOV`, `PCT_PTS_PAINT`, `PCT_AST_2PM`, `PCT_UAST_2PM`, `PCT_AST_3PM`, `PCT_UAST_3PM`, `PCT_AST_FGM`, `PCT_UAST_FGM`, `DEF_WS`, `DEF_WS_RAW`, `PLAYER_NAME_hustle_dup`, `TEAM_ABBREVIATION_hustle_dup`, `AGE_hustle_dup`

  - plus 92 × `*_RANK` (league rank)
  - plus 185 × `clutch_*` (clutch split)
  - plus 23 × `hustle_*` (hustle stat)

### `player_shot_chart`

- rows: **6,328,668**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Khaman Maluach', 'Rocco Zikarsky', 'Max Shulga'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- columns: **24** total

  `GAME_ID`, `GAME_EVENT_ID`, `GAME_DATE`, `PLAYER_ID`, `PLAYER_NAME`, `TEAM_ID`, `TEAM_NAME`, `PERIOD`, `MINUTES_REMAINING`, `SECONDS_REMAINING`, `EVENT_TYPE`, `ACTION_TYPE`, `SHOT_TYPE`, `SHOT_ZONE_BASIC`, `SHOT_ZONE_AREA`, `SHOT_ZONE_RANGE`, `SHOT_DISTANCE`, `LOC_X`, `LOC_Y`, `SHOT_MADE_FLAG`, `HTM`, `VTM`, `season`, `season_type`

### `player_shot_zones`

- rows: **41,326**
- name column: `player_name` — filterable by name. Values look like: 'Bo Outlaw', 'Chris Webber', 'Corie Blount'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `PerGame`, `Totals`
- columns: **33** total

  `player_id`, `season`, `season_type`, `per_mode`, `player_name`, `team_id`, `team_abbreviation`, `age`, `nickname`, `restricted_area_fgm`, `restricted_area_fga`, `restricted_area_fg_pct`, `in_the_paint_nonra_fgm`, `in_the_paint_nonra_fga`, `in_the_paint_nonra_fg_pct`, `midrange_fgm`, `midrange_fga`, `midrange_fg_pct`, `left_corner_3_fgm`, `left_corner_3_fga`, `left_corner_3_fg_pct`, `right_corner_3_fgm`, `right_corner_3_fga`, `right_corner_3_fg_pct`, `above_the_break_3_fgm`, `above_the_break_3_fga`, `above_the_break_3_fg_pct`, `backcourt_fgm`, `backcourt_fga`, `backcourt_fg_pct`, `corner_3_fgm`, `corner_3_fga`, `corner_3_fg_pct`

### `player_synergy`

- rows: **88,523**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Enes Freedom', 'Richard Jefferson', 'DeMarre Carroll'
- season coverage: **2015-16 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `Totals`
- columns: **29** total

  `PLAYER_ID`, `season`, `season_type`, `play_type`, `type_grouping`, `per_mode`, `SEASON_ID`, `PLAYER_NAME`, `TEAM_ID`, `TEAM_ABBREVIATION`, `TEAM_NAME`, `PLAY_TYPE_1`, `TYPE_GROUPING_1`, `PERCENTILE`, `GP`, `POSS_PCT`, `PPP`, `FG_PCT`, `FT_POSS_PCT`, `TOV_POSS_PCT`, `SF_POSS_PCT`, `PLUSONE_POSS_PCT`, `SCORE_POSS_PCT`, `EFG_PCT`, `POSS`, `PTS`, `FGM`, `FGA`, `FGMX`

### `player_tracking`

- rows: **275,942**
- name column: `PLAYER_NAME` — filterable by name. Values look like: 'Alonzo Mourning', 'Buck Williams', 'Dennis Scott'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `PerGame`, `Totals`
- `pt_measure_type` values present: `CatchShoot`, `Defense`, `Drives`, `Efficiency`, `ElbowTouch`, `PaintTouch`, `Passing`, `Possessions`, `PostTouch`, `PullUpShot`, `Rebounding`, `SpeedDistance`
- per-slice season coverage:
  - `CatchShoot`: 1996-97 → 2025-26 (41,336 rows)
  - `Defense`: 2013-14 → 2025-26 (19,518 rows)
  - `Drives`: 2013-14 → 2025-26 (19,518 rows)
  - `Efficiency`: 2013-14 → 2025-26 (19,518 rows)
  - `ElbowTouch`: 2013-14 → 2025-26 (19,518 rows)
  - `PaintTouch`: 2013-14 → 2025-26 (19,518 rows)
  - `Passing`: 2013-14 → 2025-26 (19,518 rows)
  - `Possessions`: 2013-14 → 2025-26 (19,518 rows)
  - `PostTouch`: 2013-14 → 2025-26 (19,518 rows)
  - `PullUpShot`: 1996-97 → 2025-26 (41,336 rows)
  - `Rebounding`: 2013-14 → 2025-26 (17,608 rows)
  - `SpeedDistance`: 2013-14 → 2025-26 (19,518 rows)
- columns: **157** total

  `PLAYER_ID`, `season`, `season_type`, `pt_measure_type`, `per_mode`, `PLAYER_NAME`, `TEAM_ID`, `TEAM_ABBREVIATION`, `GP`, `W`, `L`, `MIN`, `CATCH_SHOOT_FGM`, `CATCH_SHOOT_FGA`, `CATCH_SHOOT_FG_PCT`, `CATCH_SHOOT_PTS`, `CATCH_SHOOT_FG3M`, `CATCH_SHOOT_FG3A`, `CATCH_SHOOT_FG3_PCT`, `CATCH_SHOOT_EFG_PCT`, `STL`, `BLK`, `DREB`, `DEF_RIM_FGM`, `DEF_RIM_FGA`, `DEF_RIM_FG_PCT`, `DRIVES`, `DRIVE_FGM`, `DRIVE_FGA`, `DRIVE_FG_PCT`, `DRIVE_FTM`, `DRIVE_FTA`, `DRIVE_FT_PCT`, `DRIVE_PTS`, `DRIVE_PTS_PCT`, `DRIVE_PASSES`, `DRIVE_PASSES_PCT`, `DRIVE_AST`, `DRIVE_AST_PCT`, `DRIVE_TOV`, `DRIVE_TOV_PCT`, `DRIVE_PF`, `DRIVE_PF_PCT`, `POINTS`, `PULL_UP_PTS`, `PULL_UP_FG_PCT`, `PAINT_TOUCH_PTS`, `PAINT_TOUCH_FG_PCT`, `POST_TOUCH_PTS`, `POST_TOUCH_FG_PCT`, `ELBOW_TOUCH_PTS`, `ELBOW_TOUCH_FG_PCT`, `EFF_FG_PCT`, `TOUCHES`, `ELBOW_TOUCHES`, `ELBOW_TOUCH_FGM`, `ELBOW_TOUCH_FGA`, `ELBOW_TOUCH_FTM`, `ELBOW_TOUCH_FTA`, `ELBOW_TOUCH_FT_PCT`, `ELBOW_TOUCH_PASSES`, `ELBOW_TOUCH_AST`, `ELBOW_TOUCH_AST_PCT`, `ELBOW_TOUCH_TOV`, `ELBOW_TOUCH_TOV_PCT`, `ELBOW_TOUCH_FOULS`, `ELBOW_TOUCH_PASSES_PCT`, `ELBOW_TOUCH_FOULS_PCT`, `ELBOW_TOUCH_PTS_PCT`, `PAINT_TOUCHES`, `PAINT_TOUCH_FGM`, `PAINT_TOUCH_FGA`, `PAINT_TOUCH_FTM`, `PAINT_TOUCH_FTA`, `PAINT_TOUCH_FT_PCT`, `PAINT_TOUCH_PTS_PCT`, `PAINT_TOUCH_PASSES`, `PAINT_TOUCH_PASSES_PCT`, `PAINT_TOUCH_AST`, `PAINT_TOUCH_AST_PCT`, `PAINT_TOUCH_TOV`, `PAINT_TOUCH_TOV_PCT`, `PAINT_TOUCH_FOULS`, `PAINT_TOUCH_FOULS_PCT`, `PASSES_MADE`, `PASSES_RECEIVED`, `AST`, `FT_AST`, `SECONDARY_AST`, `POTENTIAL_AST`, `AST_POINTS_CREATED`, `AST_ADJ`, `AST_TO_PASS_PCT`, `AST_TO_PASS_PCT_ADJ`, `AST_PTS_CREATED`, `FRONT_CT_TOUCHES`, `TIME_OF_POSS`, `AVG_SEC_PER_TOUCH`, `AVG_DRIB_PER_TOUCH`, `PTS_PER_TOUCH`, `POST_TOUCHES`, `PTS_PER_ELBOW_TOUCH`, `PTS_PER_POST_TOUCH`, `PTS_PER_PAINT_TOUCH`, `POST_TOUCH_FGM`, `POST_TOUCH_FGA`, `POST_TOUCH_FTM`, `POST_TOUCH_FTA`, `POST_TOUCH_FT_PCT`, `POST_TOUCH_PTS_PCT`, `POST_TOUCH_PASSES`, `POST_TOUCH_PASSES_PCT`, `POST_TOUCH_AST`, `POST_TOUCH_AST_PCT`, `POST_TOUCH_TOV`, `POST_TOUCH_TOV_PCT`, `POST_TOUCH_FOULS`, `POST_TOUCH_FOULS_PCT`, `PULL_UP_FGM`, `PULL_UP_FGA`, `PULL_UP_FG3M`, `PULL_UP_FG3A`, `PULL_UP_FG3_PCT`, `PULL_UP_EFG_PCT`, `OREB`, `OREB_CONTEST`, `OREB_UNCONTEST`, `OREB_CONTEST_PCT`, `OREB_CHANCES`, `OREB_CHANCE_PCT`, `OREB_CHANCE_DEFER`, `OREB_CHANCE_PCT_ADJ`, `AVG_OREB_DIST`, `DREB_CONTEST`, `DREB_UNCONTEST`, `DREB_CONTEST_PCT`, `DREB_CHANCES`, `DREB_CHANCE_PCT`, `DREB_CHANCE_DEFER`, `DREB_CHANCE_PCT_ADJ`, `AVG_DREB_DIST`, `REB`, `REB_CONTEST`, `REB_UNCONTEST`, `REB_CONTEST_PCT`, `REB_CHANCES`, `REB_CHANCE_PCT`, `REB_CHANCE_DEFER`, `REB_CHANCE_PCT_ADJ`, `AVG_REB_DIST`, `DIST_FEET`, `DIST_MILES`, `DIST_MILES_OFF`, `DIST_MILES_DEF`, `AVG_SPEED`, `AVG_SPEED_OFF`, `AVG_SPEED_DEF`

### `team_estimated_metrics`

- rows: **1,372**
- name column: `TEAM_NAME` — filterable by name. Values look like: 'Portland Trail Blazers', 'Oklahoma City Thunder', 'Golden State Warriors'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- columns: **32** total

  `TEAM_ID`, `season`, `season_type`, `TEAM_NAME`, `GP`, `W`, `L`, `W_PCT`, `MIN`, `E_OFF_RATING`, `E_DEF_RATING`, `E_NET_RATING`, `E_PACE`, `E_AST_RATIO`, `E_OREB_PCT`, `E_DREB_PCT`, `E_REB_PCT`, `E_TM_TOV_PCT`

  - plus 14 × `*_RANK` (league rank)

### `team_game_advanced`

- rows: **125,248**
- name column: `teamName` — filterable by name. Values look like: 'Heat', 'Grizzlies', 'Rockets'
- **no `season` column** — cannot be filtered by season.
- columns: **59** total

  `game_id`, `gameId`, `teamId`, `teamCity`, `teamName`, `teamTricode`, `teamSlug`, `minutes`, `estimatedOffensiveRating`, `offensiveRating`, `estimatedDefensiveRating`, `defensiveRating`, `estimatedNetRating`, `netRating`, `assistPercentage`, `assistToTurnover`, `assistRatio`, `offensiveReboundPercentage`, `defensiveReboundPercentage`, `reboundPercentage`, `estimatedTeamTurnoverPercentage`, `turnoverRatio`, `effectiveFieldGoalPercentage`, `trueShootingPercentage`, `usagePercentage`, `estimatedUsagePercentage`, `estimatedPace`, `pace`, `pacePer40`, `possessions`, `PIE`, `pointsOffTurnovers`, `pointsSecondChance`, `pointsFastBreak`, `pointsPaint`, `oppPointsOffTurnovers`, `oppPointsSecondChance`, `oppPointsFastBreak`, `oppPointsPaint`, `blocks`, `blocksAgainst`, `foulsPersonal`, `foulsDrawn`, `points`

  - plus 15 × `hustle_*` (hustle stat)

### `team_game_logs`

- rows: **75,962**
- name column: `TEAM_NAME` — filterable by name. Values look like: 'Detroit Pistons', 'Portland Trail Blazers', 'Oklahoma City Thunder'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- columns: **59** total

  `SEASON_YEAR`, `TEAM_ID`, `TEAM_ABBREVIATION`, `TEAM_NAME`, `GAME_ID`, `GAME_DATE`, `MATCHUP`, `WL`, `MIN`, `FGM`, `FGA`, `FG_PCT`, `FG3M`, `FG3A`, `FG3_PCT`, `FTM`, `FTA`, `FT_PCT`, `OREB`, `DREB`, `REB`, `AST`, `TOV`, `STL`, `BLK`, `BLKA`, `PF`, `PFD`, `PTS`, `PLUS_MINUS`, `AVAILABLE_FLAG`, `season`, `season_type`

  - plus 26 × `*_RANK` (league rank)

### `team_roster`

- rows: **13,268**
- name column: `TEAM_NAME` — filterable by name. Values look like: 'New York Knicks', 'Detroit Pistons', 'Sacramento Kings'
- season coverage: **1996-97 → 2025-26**
- columns: **19** total

  `TeamID`, `LeagueID`, `PLAYER`, `NICKNAME`, `PLAYER_SLUG`, `NUM`, `POSITION`, `HEIGHT`, `WEIGHT`, `BIRTH_DATE`, `AGE`, `EXP`, `SCHOOL`, `PLAYER_ID`, `HOW_ACQUIRED`, `SUPPLEMENTAL_STATUS`, `season`, `TEAM_NAME`, `TEAM_ABBREVIATION`

### `team_season_stats`

- rows: **6,857**
- name column: `TEAM_NAME` — filterable by name. Values look like: 'Cleveland Cavaliers', 'Dallas Mavericks', 'Sacramento Kings'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `Per100Possessions`, `Per36`, `Per40`, `PerGame`, `Totals`
- columns: **289** total

  `TEAM_ID`, `season`, `season_type`, `per_mode`, `TEAM_NAME`, `GP`, `W`, `L`, `W_PCT`, `MIN`, `FGM`, `FGA`, `FG_PCT`, `FG3M`, `FG3A`, `FG3_PCT`, `FTM`, `FTA`, `FT_PCT`, `OREB`, `DREB`, `REB`, `AST`, `TOV`, `STL`, `BLK`, `BLKA`, `PF`, `PFD`, `PTS`, `PLUS_MINUS`, `TEAM_NAME_clutch_dup`, `E_OFF_RATING`, `OFF_RATING`, `E_DEF_RATING`, `DEF_RATING`, `E_NET_RATING`, `NET_RATING`, `AST_PCT`, `AST_TO`, `AST_RATIO`, `OREB_PCT`, `DREB_PCT`, `REB_PCT`, `TM_TOV_PCT`, `EFG_PCT`, `TS_PCT`, `E_PACE`, `PACE`, `PACE_PER40`, `POSS`, `PIE`, `PTS_OFF_TOV`, `PTS_2ND_CHANCE`, `PTS_FB`, `PTS_PAINT`, `OPP_PTS_OFF_TOV`, `OPP_PTS_2ND_CHANCE`, `OPP_PTS_FB`, `OPP_PTS_PAINT`, `PCT_FGA_2PT`, `PCT_FGA_3PT`, `PCT_PTS_2PT`, `PCT_PTS_2PT_MR`, `PCT_PTS_3PT`, `PCT_PTS_FB`, `PCT_PTS_FT`, `PCT_PTS_OFF_TOV`, `PCT_PTS_PAINT`, `PCT_AST_2PM`, `PCT_UAST_2PM`, `PCT_AST_3PM`, `PCT_UAST_3PM`, `PCT_AST_FGM`, `PCT_UAST_FGM`, `TEAM_NAME_hustle_dup`

  - plus 63 × `*_RANK` (league rank)
  - plus 132 × `clutch_*` (clutch split)
  - plus 18 × `hustle_*` (hustle stat)

### `team_shot_zones`

- rows: **2,744**
- name column: `team_name` — filterable by name. Values look like: 'Toronto Raptors', 'Cleveland Cavaliers', 'Dallas Mavericks'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `PerGame`, `Totals`
- columns: **29** total

  `team_id`, `season`, `season_type`, `per_mode`, `team_name`, `restricted_area_fgm`, `restricted_area_fga`, `restricted_area_fg_pct`, `in_the_paint_nonra_fgm`, `in_the_paint_nonra_fga`, `in_the_paint_nonra_fg_pct`, `midrange_fgm`, `midrange_fga`, `midrange_fg_pct`, `left_corner_3_fgm`, `left_corner_3_fga`, `left_corner_3_fg_pct`, `right_corner_3_fgm`, `right_corner_3_fga`, `right_corner_3_fg_pct`, `above_the_break_3_fgm`, `above_the_break_3_fga`, `above_the_break_3_fg_pct`, `backcourt_fgm`, `backcourt_fga`, `backcourt_fg_pct`, `corner_3_fgm`, `corner_3_fga`, `corner_3_fg_pct`

### `team_standings`

- rows: **892**
- name column: `TeamName` — filterable by name. Values look like: 'Heat', 'Grizzlies', 'Clippers'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Regular Season`
- columns: **131** total

  `TeamID`, `season`, `season_type`, `LeagueID`, `SeasonID`, `TeamCity`, `TeamName`, `TeamSlug`, `Conference`, `ConferenceRecord`, `PlayoffRank`, `ClinchIndicator`, `Division`, `DivisionRecord`, `DivisionRank`, `WINS`, `LOSSES`, `WinPCT`, `LeagueRank`, `Record`, `HOME`, `ROAD`, `L10`, `Last10Home`, `Last10Road`, `OT`, `ThreePTSOrLess`, `TenPTSOrMore`, `LongHomeStreak`, `strLongHomeStreak`, `LongRoadStreak`, `strLongRoadStreak`, `LongWinStreak`, `LongLossStreak`, `CurrentHomeStreak`, `strCurrentHomeStreak`, `CurrentRoadStreak`, `strCurrentRoadStreak`, `CurrentStreak`, `strCurrentStreak`, `ConferenceGamesBack`, `DivisionGamesBack`, `ClinchedConferenceTitle`, `ClinchedDivisionTitle`, `ClinchedPlayoffBirth`, `ClinchedPlayIn`, `EliminatedConference`, `EliminatedDivision`, `AheadAtHalf`, `BehindAtHalf`, `TiedAtHalf`, `AheadAtThird`, `BehindAtThird`, `TiedAtThird`, `Score100PTS`, `OppScore100PTS`, `OppOver500`, `LeadInFGPCT`, `LeadInReb`, `FewerTurnovers`, `PointsPG`, `OppPointsPG`, `DiffPointsPG`, `vsEast`, `vsAtlantic`, `vsCentral`, `vsWest`, `vsPacific`, `vsMidwest`, `Jan`, `Feb`, `Mar`, `Apr`, `May`, `Jun`, `Jul`, `Aug`, `Sep`, `Oct`, `Nov`, `Dec`, `Score_80_Plus`, `Opp_Score_80_Plus`, `Score_Below_80`, `Opp_Score_Below_80`, `LeagueGamesBack`, `PlayoffSeeding`, `ClinchedPostSeason`, `NEUTRAL`, `vsSoutheast`, `vsNorthwest`, `vsSouthwest`, `TotalPoints`, `OppTotalPoints`, `DiffTotalPoints`, `ReturnToPlay_East_PI_Flag`, `ReturnToPlay_West_PI_Flag`, `ReturnToPlay_Already_Eliminated`, `Seeding_Game_1_Outcome`, `Seeding_Game_2_Outcome`, `Seeding_Game_3_Outcome`, `Seeding_Game_4_Outcome`, `Seeding_Game_5_Outcome`, `Seeding_Game_6_Outcome`, `Seeding_Game_7_Outcome`, `Seeding_Game_8_Outcome`, `Seeding_Game_1_ID`, `Seeding_Game_2_ID`, `Seeding_Game_3_ID`, `Seeding_Game_4_ID`, `Seeding_Game_5_ID`, `Seeding_Game_6_ID`, `Seeding_Game_7_ID`, `Seeding_Game_8_ID`, `Seeding_Game_1_Opponent`, `Seeding_Game_2_Opponent`, `Seeding_Game_3_Opponent`, `Seeding_Game_4_Opponent`, `Seeding_Game_5_Opponent`, `Seeding_Game_6_Opponent`, `Seeding_Game_7_Opponent`, `Seeding_Game_8_Opponent`, `Seeding_Game_1_Label`, `Seeding_Game_2_Label`, `Seeding_Game_3_Label`, `Seeding_Game_4_Label`, `Seeding_Game_5_Label`, `Seeding_Game_6_Label`, `Seeding_Game_7_Label`, `Seeding_Game_8_Label`, `TEAM_FULL_NAME`

### `team_synergy`

- rows: **11,218**
- name column: `TEAM_NAME` — filterable by name. Values look like: 'New York Knicks', 'Memphis Grizzlies', 'Golden State Warriors'
- season coverage: **2015-16 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `Totals`
- columns: **27** total

  `TEAM_ID`, `season`, `season_type`, `play_type`, `type_grouping`, `per_mode`, `SEASON_ID`, `TEAM_ABBREVIATION`, `TEAM_NAME`, `PLAY_TYPE_1`, `TYPE_GROUPING_1`, `PERCENTILE`, `GP`, `POSS_PCT`, `PPP`, `FG_PCT`, `FT_POSS_PCT`, `TOV_POSS_PCT`, `SF_POSS_PCT`, `PLUSONE_POSS_PCT`, `SCORE_POSS_PCT`, `EFG_PCT`, `POSS`, `PTS`, `FGM`, `FGA`, `FGMX`

### `team_tracking`

- rows: **17,278**
- name column: `TEAM_NAME` — filterable by name. Values look like: 'New York Knicks', 'Cleveland Cavaliers', 'Dallas Mavericks'
- season coverage: **1996-97 → 2025-26**
- `season_type` values present: `Playoffs`, `Regular Season`
- `per_mode` values present: `PerGame`, `Totals`
- `pt_measure_type` values present: `CatchShoot`, `Defense`, `Drives`, `Efficiency`, `ElbowTouch`, `PaintTouch`, `Passing`, `Possessions`, `PostTouch`, `PullUpShot`, `Rebounding`, `SpeedDistance`
- per-slice season coverage:
  - `CatchShoot`: 1996-97 → 2025-26 (2,744 rows)
  - `Defense`: 2013-14 → 2025-26 (1,196 rows)
  - `Drives`: 2013-14 → 2025-26 (1,196 rows)
  - `Efficiency`: 2013-14 → 2025-26 (1,196 rows)
  - `ElbowTouch`: 2013-14 → 2025-26 (1,196 rows)
  - `PaintTouch`: 2013-14 → 2025-26 (1,196 rows)
  - `Passing`: 2013-14 → 2025-26 (1,196 rows)
  - `Possessions`: 2013-14 → 2025-26 (1,196 rows)
  - `PostTouch`: 2013-14 → 2025-26 (1,196 rows)
  - `PullUpShot`: 1996-97 → 2025-26 (2,744 rows)
  - `Rebounding`: 2013-14 → 2025-26 (1,026 rows)
  - `SpeedDistance`: 2013-14 → 2025-26 (1,196 rows)
- columns: **156** total

  `TEAM_ID`, `season`, `season_type`, `pt_measure_type`, `per_mode`, `TEAM_ABBREVIATION`, `TEAM_NAME`, `GP`, `W`, `L`, `MIN`, `CATCH_SHOOT_FGM`, `CATCH_SHOOT_FGA`, `CATCH_SHOOT_FG_PCT`, `CATCH_SHOOT_PTS`, `CATCH_SHOOT_FG3M`, `CATCH_SHOOT_FG3A`, `CATCH_SHOOT_FG3_PCT`, `CATCH_SHOOT_EFG_PCT`, `STL`, `BLK`, `DREB`, `DEF_RIM_FGM`, `DEF_RIM_FGA`, `DEF_RIM_FG_PCT`, `DRIVES`, `DRIVE_FGM`, `DRIVE_FGA`, `DRIVE_FG_PCT`, `DRIVE_FTM`, `DRIVE_FTA`, `DRIVE_FT_PCT`, `DRIVE_PTS`, `DRIVE_PTS_PCT`, `DRIVE_PASSES`, `DRIVE_PASSES_PCT`, `DRIVE_AST`, `DRIVE_AST_PCT`, `DRIVE_TOV`, `DRIVE_TOV_PCT`, `DRIVE_PF`, `DRIVE_PF_PCT`, `POINTS`, `PULL_UP_PTS`, `PULL_UP_FG_PCT`, `PAINT_TOUCH_PTS`, `PAINT_TOUCH_FG_PCT`, `POST_TOUCH_PTS`, `POST_TOUCH_FG_PCT`, `ELBOW_TOUCH_PTS`, `ELBOW_TOUCH_FG_PCT`, `EFF_FG_PCT`, `TOUCHES`, `ELBOW_TOUCHES`, `ELBOW_TOUCH_FGM`, `ELBOW_TOUCH_FGA`, `ELBOW_TOUCH_FTM`, `ELBOW_TOUCH_FTA`, `ELBOW_TOUCH_FT_PCT`, `ELBOW_TOUCH_PASSES`, `ELBOW_TOUCH_AST`, `ELBOW_TOUCH_AST_PCT`, `ELBOW_TOUCH_TOV`, `ELBOW_TOUCH_TOV_PCT`, `ELBOW_TOUCH_FOULS`, `ELBOW_TOUCH_PASSES_PCT`, `ELBOW_TOUCH_FOULS_PCT`, `ELBOW_TOUCH_PTS_PCT`, `PAINT_TOUCHES`, `PAINT_TOUCH_FGM`, `PAINT_TOUCH_FGA`, `PAINT_TOUCH_FTM`, `PAINT_TOUCH_FTA`, `PAINT_TOUCH_FT_PCT`, `PAINT_TOUCH_PTS_PCT`, `PAINT_TOUCH_PASSES`, `PAINT_TOUCH_PASSES_PCT`, `PAINT_TOUCH_AST`, `PAINT_TOUCH_AST_PCT`, `PAINT_TOUCH_TOV`, `PAINT_TOUCH_TOV_PCT`, `PAINT_TOUCH_FOULS`, `PAINT_TOUCH_FOULS_PCT`, `PASSES_MADE`, `PASSES_RECEIVED`, `AST`, `FT_AST`, `SECONDARY_AST`, `POTENTIAL_AST`, `AST_POINTS_CREATED`, `AST_ADJ`, `AST_TO_PASS_PCT`, `AST_TO_PASS_PCT_ADJ`, `AST_PTS_CREATED`, `FRONT_CT_TOUCHES`, `TIME_OF_POSS`, `AVG_SEC_PER_TOUCH`, `AVG_DRIB_PER_TOUCH`, `PTS_PER_TOUCH`, `POST_TOUCHES`, `PTS_PER_ELBOW_TOUCH`, `PTS_PER_POST_TOUCH`, `PTS_PER_PAINT_TOUCH`, `POST_TOUCH_FGM`, `POST_TOUCH_FGA`, `POST_TOUCH_FTM`, `POST_TOUCH_FTA`, `POST_TOUCH_FT_PCT`, `POST_TOUCH_PTS_PCT`, `POST_TOUCH_PASSES`, `POST_TOUCH_PASSES_PCT`, `POST_TOUCH_AST`, `POST_TOUCH_AST_PCT`, `POST_TOUCH_TOV`, `POST_TOUCH_TOV_PCT`, `POST_TOUCH_FOULS`, `POST_TOUCH_FOULS_PCT`, `PULL_UP_FGM`, `PULL_UP_FGA`, `PULL_UP_FG3M`, `PULL_UP_FG3A`, `PULL_UP_FG3_PCT`, `PULL_UP_EFG_PCT`, `OREB`, `OREB_CONTEST`, `OREB_UNCONTEST`, `OREB_CONTEST_PCT`, `OREB_CHANCES`, `OREB_CHANCE_PCT`, `OREB_CHANCE_DEFER`, `OREB_CHANCE_PCT_ADJ`, `AVG_OREB_DIST`, `DREB_CONTEST`, `DREB_UNCONTEST`, `DREB_CONTEST_PCT`, `DREB_CHANCES`, `DREB_CHANCE_PCT`, `DREB_CHANCE_DEFER`, `DREB_CHANCE_PCT_ADJ`, `AVG_DREB_DIST`, `REB`, `REB_CONTEST`, `REB_UNCONTEST`, `REB_CONTEST_PCT`, `REB_CHANCES`, `REB_CHANCE_PCT`, `REB_CHANCE_DEFER`, `REB_CHANCE_PCT_ADJ`, `AVG_REB_DIST`, `DIST_FEET`, `DIST_MILES`, `DIST_MILES_OFF`, `DIST_MILES_DEF`, `AVG_SPEED`, `AVG_SPEED_OFF`, `AVG_SPEED_DEF`

## Commonly-asked advanced stats — where they live

Checked against the live schema on every regeneration, so this table cannot drift from the data. A stat marked **yes** is a plain column on the season table and needs no join and no `measure_type` filter.

| Stat | On `player_season_stats`? | On `team_season_stats`? | Also available |
|---|---|---|---|
| `TS_PCT` (true shooting %) | **yes** | **yes** | `lineups`; `player_game_advanced` as `trueShootingPercentage` |
| `EFG_PCT` (effective FG %) | **yes** | **yes** | `lineups`; `player_game_advanced` |
| `USG_PCT` (usage rate) | **yes** | no | `player_estimated_metrics` as `E_USG_PCT` |
| `PIE` (player impact estimate) | **yes** | **yes** | `lineups`; `player_game_advanced` |
| `OFF_RATING` (offensive rating) | **yes** | **yes** | `player_estimated_metrics` as `E_OFF_RATING`; `lineups` |
| `DEF_RATING` (defensive rating) | **yes** | **yes** | `player_estimated_metrics` as `E_DEF_RATING`; `lineups` |
| `NET_RATING` (net rating) | **yes** | **yes** | `player_estimated_metrics` as `E_NET_RATING`; `lineups` |
| `PACE` (pace) | **yes** | **yes** | `player_estimated_metrics` as `E_PACE`; `lineups` |
| `DEF_WS` (defensive win shares) | **yes** | no | patchy — the Defense dash pull is empty for some seasons |

Player-only, because NBA publishes no team Usage slice: the `PCT_FGM` / `PCT_AST` / `PCT_PTS` usage-share family.

Genuinely absent at season grain: nothing from this list. If a question asks for a stat that is not a column anywhere above, it is an absence — say so rather than calling it a multi-table limitation.
