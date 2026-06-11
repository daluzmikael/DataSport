/** Prototype copy for AI-generated live game & season summaries (replace with analyzer API). */

const TATUM_LIVE_GAME_INSIGHT = `Tatum has shot poorly from three (2-of-6) but has been efficient inside the arc and at the line (9-of-12 on twos and free throws). He has had success getting to the rim — 6 paint attempts so far with strong finishing.

He is playmaking well with 7 assists, which leads the game, and he is doing so without many turnovers (3.5 assist-to-turnover ratio).

It is a close game and Tatum has only 22 minutes, so expect him on the court often as we reach the fourth quarter.`

const TATUM_SEASON_INSIGHT = `Jayson Tatum is the Celtics' star forward and franchise cornerstone — a six-time All-Star and four-time All-NBA First Team selection. He won a championship with Boston after being drafted 3rd overall in 2017.

This season he has continued his two-way impact: 27.4 points per game on solid efficiency, steady playmaking, and top-tier game-score marks that keep Boston near the top of the East.`

const GENERIC_LIVE_INSIGHT = `Live tracking is building a picture of this player's night — shot profile, usage, and how they are impacting the game on both ends.

Follow live stats below for shot profile and usage as the game progresses.`

const GENERIC_SEASON_INSIGHT = `Season-long trends, role, and accolades will appear here once the analyzer is wired to your vault.

Season averages and game log below add more context.`

export function getPlayerLiveGameInsight(
  playerId: string,
  _gameId: string,
): string {
  if (playerId === "player-tatum" || playerId.startsWith("player-tatum")) {
    return TATUM_LIVE_GAME_INSIGHT
  }
  return GENERIC_LIVE_INSIGHT
}

export function getPlayerSeasonInsight(playerId: string): string {
  if (playerId === "player-tatum" || playerId.startsWith("player-tatum")) {
    return TATUM_SEASON_INSIGHT
  }
  if (playerId === "player-jokic") {
    return `Nikola Jokic is a three-time MVP and the engine of the Nuggets' offense — elite passing, rebounding, and efficiency from the center position.

This season he continues to post top-tier game scores and usage as Denver pushes for playoff positioning.

His game logs and season shot chart are below.`
  }
  return GENERIC_SEASON_INSIGHT
}
