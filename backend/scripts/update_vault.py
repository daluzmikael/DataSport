"""
Refresh the stats vault for the season in progress: pull everything new from
stats.nba.com, then stage it. Meant to run nightly (or weekly) during the season.

Run from DataSport/backend/ with the venv active:

  python -m scripts.update_vault                 # current season, every table
  python -m scripts.update_vault --dry-run       # show what would be re-pulled
  python -m scripts.update_vault --skip shots,lineups   # faster nightly run
  python -m scripts.update_vault --weekly        # + awards, franchise history, all-time leaders

Why this is not just `pull_all --phase all`:

  The pull checkpoint (data/manifests/pull_state.json) marks every slice "completed"
  once it has been written, and the pullers skip completed keys. That is right for
  finished seasons but wrong for the one being played — its season totals, standings,
  shot charts and careers change every night and would never be fetched again.

  So this script first un-marks the current season's slices (and the careers of the
  players in it), then runs the normal pullers for that season only. Per-game tables
  (game_context, *_game_advanced) are keyed by game id, so only games that have not
  been pulled yet are fetched — finished games never change.

Tables covered (all 27 staged tables):
  phase 1  player_season_stats, team_season_stats, team_standings,
           player_shot_zones, team_shot_zones
  phase 2  player_game_logs, team_game_logs
  phase 3  game_context, player_game_advanced, team_game_advanced   (new games only)
  phase 4  player_career                                            (players in season)
  phase 5  court_shots
  phase 6  player_tracking, team_tracking, lineups, player_on_off,
           player_estimated_metrics, team_estimated_metrics
  phase 7  team_roster, player_bio (new players)   --weekly: player_awards, franchise_history
  phase 8  player_synergy, team_synergy
  phase 9  player_shot_chart
  legacy   all_time_leaders (--weekly)   legacy_season_stats is pre-1996 and never changes
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
import urllib.request
from datetime import date, datetime

from ingestion.config import (
    LOGS_ROOT,
    PULL_STATE_FILE,
    RAW_TABLE_DIRS,
    SEASON_TYPES,
    START_SEASON,
    STAGING_ROOT,
    SYNERGY_START_SEASON,
    ensure_data_dirs,
)
from ingestion.utils import checkpoint
from ingestion.utils.checkpoint import PullAlreadyRunning, pull_lock
from ingestion.utils.seasons import iter_seasons, season_type_slug

logger = logging.getLogger("update_vault")

# Checkpoint key prefixes whose second field is the season ("prefix|season|...").
# Un-marking these makes the pullers fetch the current season's slices again.
SEASON_KEY_PREFIXES = (
    "player_dash", "player_clutch", "player_hustle",
    "team_dash", "team_clutch", "team_hustle",
    "standings", "player_shot_zones", "team_shot_zones",
    "player_game_logs", "team_game_logs",
    "court_shots",
    "player_tracking", "team_tracking", "lineups", "player_on_off",
    "player_estimated", "team_estimated",
    "team_roster",
    "player_synergy", "team_synergy",
    "player_shot_chart",
)

# --skip names → phases they cover (for faster nightly runs).
SKIP_GROUPS = {
    "games": {"3"},
    "careers": {"4"},
    "shots": {"5", "9"},
    "tracking": {"6"},
    "lineups": {"6-lineups"},
    "rosters": {"7"},
    "synergy": {"8"},
}


def current_season(today: date | None = None) -> str:
    """NBA season label for a date: October onward belongs to the new season."""
    today = today or date.today()
    start = today.year if today.month >= 10 else today.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def _setup_logging() -> None:
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOGS_ROOT / f"update_vault_{stamp}.log", encoding="utf-8"),
        ],
    )


def _season_keys(completed: list[str], season: str) -> list[str]:
    out = []
    for key in completed:
        parts = key.split("|")
        if len(parts) >= 2 and parts[0] in SEASON_KEY_PREFIXES and parts[1] == season:
            out.append(key)
    return out


def _unmark(keys: set[str], dry_run: bool) -> None:
    """Drop keys from the checkpoint's completed list in one atomic write."""
    if not keys:
        return
    if dry_run:
        return
    state = checkpoint.load_checkpoint(PULL_STATE_FILE)
    state["completed"] = [k for k in state.get("completed", []) if k not in keys]
    checkpoint._save(PULL_STATE_FILE, state)  # atomic temp-file + rename


def _new_game_ids(season: str) -> list[str]:
    """Game ids in this season's game logs that have not been pulled yet."""
    import pandas as pd

    ids: set[str] = set()
    for table in ("player_game_logs", "team_game_logs"):
        for season_type in SEASON_TYPES:
            path = RAW_TABLE_DIRS[table] / season / f"{season_type_slug(season_type)}.parquet"
            if not path.exists():
                continue
            df = pd.read_parquet(path)
            col = "GAME_ID" if "GAME_ID" in df.columns else "game_id"
            if col in df.columns:
                ids.update(df[col].astype(str).str.zfill(10).unique())
    completed = set(checkpoint.load_checkpoint(PULL_STATE_FILE).get("completed", []))
    fresh = [
        gid for gid in sorted(ids, reverse=True)
        if not (
            f"game_context|{gid}" in completed
            and f"player_game_advanced|{gid}" in completed
            and f"team_game_advanced|{gid}" in completed
        )
    ]
    return fresh


def _stage(phases: list[str]) -> None:
    from ingestion.stage_all import PHASE_RUNNERS

    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    for phase in phases:
        logger.info("=== Staging phase %s ===", phase)
        PHASE_RUNNERS[phase]()


# --------------------------------------------------------------------------
# Incremental staging. The full stagers re-read every raw file: ~38k per-game
# files for each phase-3 table and ~29k per-player-season files for phases 5/9,
# which is hours. A finished game never changes and older seasons do not move,
# so those tables only need the new slice swapped in.
# --------------------------------------------------------------------------
def _merge_slice(table: str, new_path, drop_where: str) -> None:
    """Replace rows matching `drop_where` in staged `table` with the rows in `new_path`."""
    import os

    import duckdb

    out = STAGING_ROOT / f"{table}.parquet"
    if not out.exists():
        os.replace(new_path, out)
        return
    tmp = STAGING_ROOT / f".{table}.merge.parquet"
    con = duckdb.connect()
    try:
        old_sql = str(out).replace("'", "''")
        new_sql = str(new_path).replace("'", "''")
        con.execute(
            f"COPY (SELECT * FROM read_parquet('{old_sql}') WHERE NOT ({drop_where}) "
            f"UNION ALL BY NAME SELECT * FROM read_parquet('{new_sql}')) "
            f"TO '{str(tmp).replace(chr(39), chr(39) * 2)}' (FORMAT PARQUET)"
        )
        rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{str(tmp).replace(chr(39), chr(39) * 2)}')").fetchone()[0]
    finally:
        con.close()
    os.replace(tmp, out)  # atomic: readers see the old or the new table, never half
    os.remove(new_path)
    logger.info("merged %s -> %s (%s rows)", new_path.name, out.name, rows)


def _sql_list(values: list[str]) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


def _stage_games_incremental(game_ids: list[str]) -> None:
    from ingestion.stagers._helpers import concat_parquet_files_batched
    from ingestion.stagers.phase3 import enrich_game_id, game_context_frame

    if not game_ids:
        return
    ids = _sql_list(game_ids)

    files = [RAW_TABLE_DIRS["game_context"] / f"{gid}.json" for gid in game_ids]
    frame = game_context_frame([f for f in files if f.exists()])
    if frame is not None:
        tmp = STAGING_ROOT / ".game_context.new.parquet"
        frame.to_parquet(tmp, index=False)
        _merge_slice("game_context", tmp, f"game_id IN ({ids})")

    for table in ("player_game_advanced", "team_game_advanced"):
        files = [RAW_TABLE_DIRS[table] / f"{gid}.parquet" for gid in game_ids]
        files = [f for f in files if f.exists()]
        if not files:
            continue
        tmp = STAGING_ROOT / f".{table}.new.parquet"
        concat_parquet_files_batched(files, tmp, enrich=enrich_game_id, log_label=table)
        _merge_slice(table, tmp, f"game_id IN ({ids})")


def _stage_season_incremental(season: str, phases: set[str]) -> None:
    from ingestion.stagers._helpers import concat_parquet_files_batched, normalize_team_identity
    from ingestion.stagers.phase5 import enrich_court_shot
    from ingestion.stagers.phase9 import shot_chart_season_frame

    where = f"season = '{season}'"
    if "5" in phases:
        files = sorted((RAW_TABLE_DIRS["court_shots"] / season).rglob("*.parquet"))
        if files:
            tmp = STAGING_ROOT / ".court_shots.new.parquet"
            concat_parquet_files_batched(files, tmp, enrich=enrich_court_shot, log_label="court_shots")
            _merge_slice("court_shots", tmp, where)
    if "9" in phases:
        frame = shot_chart_season_frame(RAW_TABLE_DIRS["player_shot_chart"] / season)
        if frame is not None:
            tmp = STAGING_ROOT / ".player_shot_chart.new.parquet"
            normalize_team_identity(frame).to_parquet(tmp, index=False)
            _merge_slice("player_shot_chart", tmp, where)


def _stage_changed(season: str, ran: set[str], game_ids: list[str]) -> None:
    """Stage only what this run touched; fall back to a full phase stage on any error."""
    full = [p for p in ("1", "2", "4", "6", "7", "8") if p in ran]
    _stage(full)
    incremental = [
        ("3", lambda: _stage_games_incremental(game_ids)),
        ("5", lambda: _stage_season_incremental(season, {"5"})),
        ("9", lambda: _stage_season_incremental(season, {"9"})),
    ]
    for phase, fn in incremental:
        if phase not in ran or (phase == "3" and not game_ids):
            continue
        logger.info("=== Staging phase %s (incremental) ===", phase)
        try:
            fn()
        except Exception:  # noqa: BLE001 — correctness over speed
            logger.exception("incremental staging of phase %s failed; running full stage", phase)
            _stage([phase])


def _refresh_local_views() -> None:
    """Make this process's DuckDB views see freshly staged parquet."""
    try:
        from Executer.duckdb_store import refresh_views

        refresh_views()
    except Exception as exc:  # noqa: BLE001 — only matters for phases 7/9 player lists
        logger.warning("Could not refresh local DuckDB views: %s", exc)


def _notify_api(url: str) -> None:
    """Ask a running API to re-read staging (POST /api/staging/refresh)."""
    try:
        req = urllib.request.Request(f"{url.rstrip('/')}/api/staging/refresh", method="POST")
        with urllib.request.urlopen(req, timeout=60) as res:
            logger.info("API refreshed: %s %s", url, res.status)
    except Exception as exc:  # noqa: BLE001 — the API may simply not be running
        logger.info("API not refreshed (%s): %s", url, exc)


def run(args) -> int:
    season = args.season
    seasons = [season]
    skip: set[str] = set()
    for name in filter(None, (s.strip() for s in args.skip.split(","))):
        if name not in SKIP_GROUPS:
            raise SystemExit(f"Unknown --skip {name!r}. Choose from: {', '.join(SKIP_GROUPS)}")
        skip |= SKIP_GROUPS[name]

    def want(phase: str) -> bool:
        return phase not in skip

    started = time.time()
    logger.info("Updating vault for %s%s", season, " (dry run)" if args.dry_run else "")

    # 1. Re-open the current season's slices.
    completed = checkpoint.load_checkpoint(PULL_STATE_FILE).get("completed", [])
    season_keys = set(_season_keys(completed, season))
    logger.info("Re-pulling %d current-season checkpoint keys", len(season_keys))
    _unmark(season_keys, args.dry_run)

    if args.dry_run:
        by_prefix: dict[str, int] = {}
        for k in season_keys:
            by_prefix[k.split("|", 1)[0]] = by_prefix.get(k.split("|", 1)[0], 0) + 1
        for prefix, n in sorted(by_prefix.items()):
            logger.info("  %-22s %d", prefix, n)
        logger.info("New games to pull (from current logs): %d", len(_new_game_ids(season)))
        return 0

    from ingestion.pull_all import (  # imported late: pulls in nba_api
        pull_court_shots,
        pull_franchise_history,
        pull_game_advanced,
        pull_game_context,
        pull_lineups,
        pull_player_awards,
        pull_player_bio,
        pull_player_career_stats,
        pull_player_estimated_metrics,
        pull_player_game_logs,
        pull_player_on_off,
        pull_player_season_stats,
        pull_player_shot_chart,
        pull_player_shot_zones,
        pull_player_synergy,
        pull_player_tracking,
        pull_team_estimated_metrics,
        pull_team_game_logs,
        pull_team_roster,
        pull_team_season_stats,
        pull_team_shot_zones,
        pull_team_standings,
        pull_team_synergy,
        pull_team_tracking,
    )
    from ingestion.pullers.game_logs import build_game_id_manifest
    from ingestion.pullers.season_stats import _collect_player_ids

    # 2. Season-level tables, then stage them so the player lists below include
    #    anyone new this season (phases 7 and 9 read players from staged data).
    logger.info("=== Phase 1: season stats, standings, shot zones ===")
    pull_player_season_stats(seasons)
    pull_team_season_stats(seasons)
    pull_team_standings(seasons)
    pull_player_shot_zones(seasons)
    pull_team_shot_zones(seasons)
    _stage(["1"])  # staged now (not at the end) so phases 7/9 see new players
    _refresh_local_views()
    ran: set[str] = {"2"}
    game_ids: list[str] = []

    logger.info("=== Phase 2: game logs ===")
    pull_player_game_logs(seasons)
    pull_team_game_logs(seasons)

    if want("3"):
        ran.add("3")
        game_ids = _new_game_ids(season)
        logger.info("=== Phase 3: %d new games (context + advanced box) ===", len(game_ids))
        if game_ids:
            pull_game_context(game_ids=game_ids)
            pull_game_advanced(game_ids=game_ids)

    if want("4"):
        ran.add("4")
        # Careers change every game for active players only.
        active = _collect_player_ids(seasons)
        _unmark({f"player_career|{pid}" for pid in active}, dry_run=False)
        logger.info("=== Phase 4: careers for %d players in %s ===", len(active), season)
        pull_player_career_stats(seasons)

    if want("5"):
        ran.add("5")
        logger.info("=== Phase 5: court_shots zones ===")
        pull_court_shots(seasons)

    if want("6"):
        ran.add("6")
        logger.info("=== Phase 6: tracking, on/off, estimated metrics ===")
        pull_player_tracking(seasons)
        pull_team_tracking(seasons)
        pull_player_on_off(seasons)
        pull_player_estimated_metrics(seasons)
        pull_team_estimated_metrics(seasons)
        if want("6-lineups"):
            pull_lineups(seasons)

    if want("7"):
        ran.add("7")
        logger.info("=== Phase 7: rosters, bios for new players ===")
        pull_team_roster(seasons)
        pull_player_bio()  # only players without a bio yet
        if args.weekly:
            active = [int(p) for p in _collect_player_ids(seasons)]
            _unmark({f"player_awards|{pid}" for pid in active} | {"franchise_history|all"}, False)
            pull_player_awards(active)
            pull_franchise_history()

    if want("8") and season >= SYNERGY_START_SEASON:
        ran.add("8")
        logger.info("=== Phase 8: Synergy play types ===")
        pull_player_synergy(seasons)
        pull_team_synergy(seasons)

    if want("9"):
        ran.add("9")
        logger.info("=== Phase 9: player_shot_chart (LOC_X/LOC_Y) ===")
        pull_player_shot_chart(seasons)

    if args.weekly:
        logger.info("=== Legacy: all-time leaders ===")
        from ingestion.pullers.legacy import pull_all_time_leaders
        from ingestion.stagers.legacy import stage_all_time_leaders

        pull_all_time_leaders()
        stage_all_time_leaders()

    # Keep the full manifest consistent for any later `pull_all --phase 3` run.
    build_game_id_manifest(iter_seasons(START_SEASON, season))

    # 3. Stage what changed: full rebuilds for the small tables, slice merges for
    #    the per-game and per-player-season ones (see _stage_changed).
    _stage_changed(season, ran, game_ids)

    failed = [
        e for e in checkpoint.load_checkpoint(PULL_STATE_FILE).get("failed", [])
        if f"|{season}|" in e.get("key", "") or e.get("key", "").startswith("game_")
    ]
    logger.info(
        "Vault update for %s finished in %.1f min. Failed keys logged: %d",
        season, (time.time() - started) / 60, len(failed),
    )

    for url in args.notify:
        _notify_api(url)
    if args.upload:
        try:
            from scripts import upload_staging  # noqa: F401 — lives on the deploy branch
        except ImportError:
            logger.warning("--upload: scripts.upload_staging not found on this branch")
        else:
            import subprocess

            subprocess.run([sys.executable, "-m", "scripts.upload_staging"], check=False)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull + stage the current NBA season")
    parser.add_argument("--season", default=current_season(), help="default: %(default)s")
    parser.add_argument("--dry-run", action="store_true", help="report what would be re-pulled")
    parser.add_argument(
        "--skip", default="",
        help=f"comma list to skip for a faster run: {', '.join(SKIP_GROUPS)}",
    )
    parser.add_argument(
        "--weekly", action="store_true",
        help="also refresh awards, franchise history and all-time leaders",
    )
    parser.add_argument(
        "--notify", action="append", default=["http://127.0.0.1:8000"],
        help="API base URL to POST /api/staging/refresh afterwards (repeatable)",
    )
    parser.add_argument("--upload", action="store_true", help="upload staging to R2 afterwards")
    args = parser.parse_args()

    _setup_logging()
    ensure_data_dirs()
    try:
        with pull_lock(PULL_STATE_FILE):
            return run(args)
    except PullAlreadyRunning as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
