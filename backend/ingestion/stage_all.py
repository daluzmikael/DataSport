"""
Build unified tables from data/raw/ into data/staging/.

  python -m ingestion.stage_all --phase 1
  python -m ingestion.stage_all --phase all
"""
from __future__ import annotations

import argparse
import logging
import sys

from ingestion.config import STAGING_ROOT, ensure_data_dirs
from ingestion.stagers.phase1 import (
    run_phase1,
    stage_player_season_stats,
    stage_player_shot_zones,
    stage_team_season_stats,
    stage_team_shot_zones,
    stage_team_standings,
)
from ingestion.stagers.phase2 import (
    run_phase2,
    stage_player_game_logs,
    stage_team_game_logs,
)
from ingestion.stagers.phase3 import (
    run_phase3,
    stage_game_context,
    stage_player_game_advanced,
    stage_team_game_advanced,
)
from ingestion.stagers.phase4 import run_phase4, stage_player_career
from ingestion.stagers.phase5 import run_phase5, stage_court_shots

PHASE_RUNNERS = {
    "1": run_phase1,
    "2": run_phase2,
    "3": run_phase3,
    "4": run_phase4,
    "5": run_phase5,
}

TABLE_STAGERS = {
    "player_season_stats": stage_player_season_stats,
    "team_season_stats": stage_team_season_stats,
    "team_standings": stage_team_standings,
    "player_shot_zones": stage_player_shot_zones,
    "team_shot_zones": stage_team_shot_zones,
    "player_game_logs": stage_player_game_logs,
    "team_game_logs": stage_team_game_logs,
    "game_context": stage_game_context,
    "player_game_advanced": stage_player_game_advanced,
    "team_game_advanced": stage_team_game_advanced,
    "player_career": stage_player_career,
    "court_shots": stage_court_shots,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage raw NBA pulls into unified tables")
    parser.add_argument(
        "--phase",
        choices=("1", "2", "3", "4", "5", "all"),
        default="1",
        help="Staging phase (1=season, 2=game logs, 3=game context/advanced, 4=career, 5=court shots)",
    )
    parser.add_argument(
        "--tables",
        default="",
        help="Comma-separated subset of staging table names (see --help in README)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    ensure_data_dirs()
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)

    if args.tables.strip():
        names = [t.strip() for t in args.tables.split(",") if t.strip()]
        for name in names:
            fn = TABLE_STAGERS.get(name)
            if not fn:
                raise SystemExit(
                    f"Unknown table: {name}. Choose from: {', '.join(TABLE_STAGERS)}"
                )
            fn()
    elif args.phase == "all":
        for phase in ("1", "2", "3", "4", "5"):
            logging.info("=== Staging phase %s ===", phase)
            PHASE_RUNNERS[phase]()
    else:
        logging.info("=== Staging phase %s ===", args.phase)
        PHASE_RUNNERS[args.phase]()

    logging.info("Staging complete. Output: %s", STAGING_ROOT)


if __name__ == "__main__":
    main()
