import { canonicalMockPlayerId } from "../api/nbaIds"

/** Prototype copy for AI-generated live game & season summaries (replace with analyzer API). */

const TATUM_LIVE_GAME_INSIGHT = `Tatum has shot poorly from three (2-of-6) but has been efficient inside the arc and at the line (9-of-12 on twos and free throws). He has had success getting to the rim — 6 paint attempts so far with strong finishing.

He is playmaking well with 7 assists, which leads the game, and he is doing so without many turnovers (3.5 assist-to-turnover ratio).

It is a close game and Tatum has only 22 minutes, so expect him on the court often as we reach the fourth quarter.`

const TATUM_SEASON_INSIGHT = `Jayson Tatum is the Celtics' star forward and franchise cornerstone — a six-time All-Star and four-time All-NBA First Team selection. He won a championship with Boston after being drafted 3rd overall in 2017.

This season he has continued his two-way impact: 27.4 points per game on solid efficiency, steady playmaking, and top-tier game-score marks that keep Boston near the top of the East.`

const DURANT_LIVE_GAME_INSIGHT = `Durant is scoring efficiently on 9-of-14 shooting with strong mid-range and paint touch. He has been selective from three (2-of-4) while getting to the line without a miss (4-of-4).

He is also creating for teammates with 4 assists and has protected the rim with a block — a balanced two-way line for 26 minutes in a tight game.

Expect heavy fourth-quarter usage if Phoenix needs a closer; his shot diet and matchup hunting are below in the live game log.`

const DURANT_SEASON_INSIGHT = `Kevin Durant is a two-time champion, two-time Finals MVP, and the Suns' primary scoring hub — one of the most efficient high-volume scorers in league history.

This season he continues to post elite efficiency and usage with top-tier game-score marks. His full vault-backed game log and season stat bubbles below cover every NBA season on file.`

const GENERIC_LIVE_INSIGHT = `Live tracking is building a picture of this player's night — shot profile, usage, and how they are impacting the game on both ends.

Follow live stats below for shot profile and usage as the game progresses.`

const GENERIC_SEASON_INSIGHT = `Season-long trends, role, and accolades will appear here once the analyzer is wired to your vault.

Season averages and game log below add more context.`

export function getPlayerLiveGameInsight(
  playerId: string,
  _gameId: string,
): string {
  const key = canonicalMockPlayerId(playerId)
  if (key === "player-tatum" || key.startsWith("player-tatum")) {
    return TATUM_LIVE_GAME_INSIGHT
  }
  if (key === "player-durant" || key.startsWith("player-durant")) {
    return DURANT_LIVE_GAME_INSIGHT
  }
  return GENERIC_LIVE_INSIGHT
}

export function getPlayerSeasonInsight(playerId: string): string {
  const key = canonicalMockPlayerId(playerId)
  if (key === "player-tatum" || key.startsWith("player-tatum")) {
    return TATUM_SEASON_INSIGHT
  }
  if (key === "player-durant" || key.startsWith("player-durant")) {
    return DURANT_SEASON_INSIGHT
  }
  if (key === "player-jokic") {
    return `Nikola Jokic is a three-time MVP and the engine of the Nuggets' offense — elite passing, rebounding, and efficiency from the center position.

This season he continues to post top-tier game scores and usage as Denver pushes for playoff positioning.

His game logs and season shot chart are below.`
  }
  return GENERIC_SEASON_INSIGHT
}
