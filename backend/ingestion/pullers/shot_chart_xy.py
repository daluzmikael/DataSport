"""player_shot_chart <- ShotChartDetail (LOC_X / LOC_Y coordinates).

DELIBERATELY SEPARATE FROM `court_shots`. That table is a zone GRID — one row per
player per season per zone, carrying FGA/FGM/FG_PCT and no coordinates — and it is
correct as it stands. This is per-SHOT data with x/y positions for drawing an actual
shot chart. Different grain, different purpose, different table. Nothing here writes
to court_shots.

Two traps in this endpoint:

* It returns TWO result sets. Set 0 is `Shot_Chart_Detail` (the shots). Set 1 is
  `LeagueAverages` (20 rows of league-wide zone baselines) — saving that instead is
  an easy and silent mistake.
* `team_id=0` means "all teams". Passing a real team id would drop the shots a
  traded player took for his other team that season.
"""
from __future__ import annotations

import logging

from nba_api.stats.endpoints import shotchartdetail

from ingestion.config import (
    API_TIMEOUT_SEC,
    LEAGUE_ID,
    PULL_STATE_FILE,
    RAW_TABLE_DIRS,
    SEASON_TYPES,
)
from ingestion.utils.checkpoint import is_done, mark_done, mark_failed
from ingestion.utils.nba_client import (
    call_with_retry,
    is_resultset_unavailable,
    save_parquet,
)

logger = logging.getLogger(__name__)

# "FGA" returns every attempt, made and missed. Anything narrower silently drops shots.
_CONTEXT_MEASURE = "FGA"

# All teams — see module docstring.
_ALL_TEAMS = 0


def _player_seasons(seasons: list[str] | None = None) -> list[tuple[int, str]]:
    """(player_id, season) pairs the vault actually knows about.

    Driving off the staged season table rather than a roster endpoint keeps the work
    bounded to players the app can ask about, and makes the run resumable and stable.
    """
    from Executer.data_backend import get_connection

    sql = (
        "SELECT DISTINCT PLAYER_ID, season FROM player_season_stats "
        "WHERE PLAYER_ID IS NOT NULL"
    )
    rows = get_connection().execute(sql).fetchall()
    pairs = [(int(r[0]), str(r[1])) for r in rows]
    if seasons:
        wanted = set(seasons)
        pairs = [p for p in pairs if p[1] in wanted]
    return sorted(pairs, key=lambda p: (p[1], p[0]))


def pull_player_shot_chart(
    seasons: list[str] | None = None,
    season_types: tuple[str, ...] = SEASON_TYPES,
    limit: int | None = None,
) -> None:
    out_dir = RAW_TABLE_DIRS["player_shot_chart"]
    pairs = _player_seasons(seasons)
    if limit:
        pairs = pairs[:limit]

    total = len(pairs) * len(season_types)
    logger.info("player_shot_chart: %s player-season-type reads planned", total)
    done = 0

    for player_id, season in pairs:
        for season_type in season_types:
            done += 1
            st_slug = "regular_season" if season_type == "Regular Season" else "playoffs"
            key = f"player_shot_chart|{season}|{st_slug}|{player_id}"
            out_path = out_dir / season / st_slug / f"{player_id}.parquet"
            if is_done(PULL_STATE_FILE, key) and out_path.exists():
                continue
            try:
                ep = call_with_retry(
                    lambda p=player_id, s=season, st=season_type: (
                        shotchartdetail.ShotChartDetail(
                            team_id=_ALL_TEAMS,
                            player_id=p,
                            season_nullable=s,
                            season_type_all_star=st,
                            context_measure_simple=_CONTEXT_MEASURE,
                            league_id=LEAGUE_ID,
                            timeout=API_TIMEOUT_SEC,
                        )
                    ),
                    key,
                )
                frames = ep.get_data_frames()
                # Set 0 only. Set 1 is LeagueAverages.
                df = frames[0] if frames else None
                if df is None or df.empty:
                    # A player with no shots in a season type (DNP, or no playoffs)
                    # is a real answer — mark done so it is not retried every run.
                    mark_done(PULL_STATE_FILE, key)
                    continue
                df["season"] = season
                df["season_type"] = season_type
                save_parquet(df, out_path)
                mark_done(PULL_STATE_FILE, key)
            except Exception as exc:  # noqa: BLE001
                if is_resultset_unavailable(exc):
                    mark_done(PULL_STATE_FILE, key)
                    continue
                mark_failed(PULL_STATE_FILE, key, str(exc))
                logger.warning("player_shot_chart failed %s: %s", key, exc)
            if done % 200 == 0:
                logger.info("player_shot_chart progress %s/%s", done, total)
