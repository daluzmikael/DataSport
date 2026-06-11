"""
Overnight NBA stats pull orchestrator.

Run from DataSport/backend/ with venv active:

  python -m ingestion.pull_all --phase 1
  python -m ingestion.pull_all --phase all --log-file
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from ingestion.config import END_SEASON, GAME_PULL_ORDER, START_SEASON, ensure_data_dirs
from ingestion.pullers.court_shots import pull_court_shots
from ingestion.pullers.game_advanced import pull_game_advanced
from ingestion.pullers.game_context import pull_game_context
from ingestion.pullers.game_logs import build_game_id_manifest, pull_player_game_logs, pull_team_game_logs
from ingestion.pullers.season_stats import (
    pull_player_career_stats,
    pull_player_season_stats,
    pull_team_season_stats,
)
from ingestion.pullers.shot_zones import pull_player_shot_zones, pull_team_shot_zones
from ingestion.pullers.standings import pull_team_standings
from ingestion.utils.seasons import iter_seasons


def _setup_logging(log_file: bool) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        from ingestion.config import LOGS_ROOT

        LOGS_ROOT.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        handlers.append(logging.FileHandler(LOGS_ROOT / f"pull_{stamp}.log", encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull NBA stats into backend/data/raw/")
    parser.add_argument(
        "--phase",
        choices=("1", "2", "3", "4", "5", "all"),
        default="all",
        help="Which pull phase to run",
    )
    parser.add_argument("--start-season", default=START_SEASON)
    parser.add_argument("--end-season", default=END_SEASON)
    parser.add_argument("--game-limit", type=int, default=None, help="Cap games for phase 3")
    parser.add_argument(
        "--game-order",
        choices=("recent", "oldest"),
        default=GAME_PULL_ORDER,
        help="Phase 3 game pull order (default: recent = newest seasons first)",
    )
    parser.add_argument("--max-shot-players", type=int, default=None, help="Cap players for phase 5")
    parser.add_argument(
        "--retry-failed-careers",
        action="store_true",
        help="Phase 4: only retry player_career keys marked failed in pull_state.json",
    )
    parser.add_argument(
        "--retry-failed-court-shots",
        action="store_true",
        help="Phase 5: only retry court_shots keys marked failed in pull_state.json",
    )
    parser.add_argument("--log-file", action="store_true", help="Also write data/logs/pull_*.log")
    args = parser.parse_args()

    _setup_logging(args.log_file)
    ensure_data_dirs()
    seasons = iter_seasons(args.start_season, args.end_season)
    logging.info("Seasons %s .. %s (%s total)", args.start_season, args.end_season, len(seasons))

    phase = args.phase
    if phase in ("1", "all"):
        logging.info("=== Phase 1: season + standings + shot zones ===")
        pull_player_season_stats(seasons)
        pull_team_season_stats(seasons)
        pull_team_standings(seasons)
        pull_player_shot_zones(seasons)
        pull_team_shot_zones(seasons)

    if phase in ("2", "all"):
        logging.info("=== Phase 2: game logs + game_id manifest ===")
        pull_player_game_logs(seasons)
        pull_team_game_logs(seasons)
        build_game_id_manifest(seasons)

    if phase in ("3", "all"):
        logging.info("=== Phase 3: game context + game advanced (order=%s) ===", args.game_order)
        pull_game_context(limit=args.game_limit, order=args.game_order)
        pull_game_advanced(limit=args.game_limit, order=args.game_order)

    if phase in ("4", "all"):
        logging.info(
            "=== Phase 4: player career (playercareerstats%s) ===",
            ", retry failed only" if args.retry_failed_careers else "",
        )
        pull_player_career_stats(seasons, retry_failed_only=args.retry_failed_careers)

    if phase in ("5", "all"):
        logging.info(
            "=== Phase 5: court_shots%s ===",
            ", retry failed only" if args.retry_failed_court_shots else "",
        )
        pull_court_shots(
            seasons,
            max_players=args.max_shot_players,
            retry_failed_only=args.retry_failed_court_shots,
        )

    logging.info("Done.")


if __name__ == "__main__":
    main()
