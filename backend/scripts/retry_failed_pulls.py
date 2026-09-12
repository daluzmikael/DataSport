"""Re-pull the game-level keys still marked failed in pull_state.json.

Most of that list is stale. An audit on 2026-08-19 found 372 failed keys but only ~11
genuinely missing files — the rest succeeded on a later pass and the failed entry was
never cleared, which made a two-minute job look like an overnight one.

Retrying all of them anyway is the cheap way to make the state file honest: the pullers
skip anything already `is_done` AND on disk, so the stale ones cost one dict lookup
each, and the survivors get marked done.

    python -m scripts.retry_failed_pulls --dry-run
    python -m scripts.retry_failed_pulls
    python -m scripts.retry_failed_pulls --only-missing   # just the real gaps

Scope is deliberately narrow: phase-3 game data only. `team_dash` failures are ignored
because those season slices are present and correctly staged.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.config import PULL_STATE_FILE, RAW_TABLE_DIRS  # noqa: E402
from ingestion.utils.checkpoint import failed_keys, load_checkpoint  # noqa: E402

FAMILIES = ("player_game_advanced", "team_game_advanced", "game_context")


def _ids_for(family: str) -> list[str]:
    """Game ids still marked failed for this family."""
    return [k.split("|", 1)[1] for k in failed_keys(PULL_STATE_FILE, f"{family}|") if "|" in k]


def _missing_on_disk(family: str, ids: list[str]) -> list[str]:
    root = Path(RAW_TABLE_DIRS[family])
    suffix = ".json" if family == "game_context" else ".parquet"
    return [g for g in ids if not (root / f"{g}{suffix}").exists()]


def _clean_stale(state: dict, *, dry_run: bool) -> int:
    """Drop failed entries the pullers can never clear on their own.

    `mark_failed` does not remove a key from `completed`, so a key that succeeded once
    and failed later sits in BOTH lists. `is_done` then returns True and every future
    run skips it — the failed entry is unreachable residue, not work outstanding. It
    has to be cleaned here or it stays forever.
    """
    completed = set(state.get("completed", []))
    failed = state.get("failed", [])

    keep, dropped = [], []
    for entry in failed:
        key = entry.get("key", "")
        family, _, gid = key.partition("|")
        root = RAW_TABLE_DIRS.get(family)
        suffix = ".json" if family == "game_context" else ".parquet"
        on_disk = bool(root and gid and (Path(root) / f"{gid}{suffix}").exists())
        (dropped if (key in completed and on_disk) else keep).append(entry)

    print(f"failed entries: {len(failed)}")
    print(f"  stale (already completed + file present): {len(dropped)}  -> drop")
    print(f"  genuine outstanding:                      {len(keep)}  -> keep")
    for e in keep[:12]:
        print(f"      {e.get('key')}")

    if dry_run:
        print("dry run - nothing written.")
        return 0

    state["failed"] = keep
    with open(PULL_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"wrote {PULL_STATE_FILE.name}: failed {len(failed)} -> {len(keep)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only, pull nothing")
    ap.add_argument(
        "--only-missing",
        action="store_true",
        help="retry only ids with no file on disk (the genuine gaps)",
    )
    ap.add_argument(
        "--clean-stale",
        action="store_true",
        help="drop failed entries that are also completed and have a file on disk",
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    state = load_checkpoint(PULL_STATE_FILE)
    before = len(state.get("failed", []))

    if args.clean_stale:
        return _clean_stale(state, dry_run=args.dry_run)

    plan: dict[str, list[str]] = {}

    print(f"failed keys in state: {before}")
    for family in FAMILIES:
        ids = _ids_for(family)
        missing = _missing_on_disk(family, ids)
        plan[family] = missing if args.only_missing else ids
        print(f"  {family:22} failed={len(ids):4}  missing on disk={len(missing):3}"
              f"  -> retrying {len(plan[family])}")

    total = sum(len(v) for v in plan.values())
    if args.dry_run:
        print(f"\ndry run — {total} id(s) would be pulled, nothing written.")
        return 0
    if not total:
        print("\nnothing to retry.")
        return 0

    # Imported here so --dry-run never touches nba_api.
    from ingestion.pullers.game_advanced import pull_game_advanced
    from ingestion.pullers.game_context import pull_game_context

    adv_ids = sorted(set(plan["player_game_advanced"]) | set(plan["team_game_advanced"]))
    if adv_ids:
        print(f"\npulling game_advanced for {len(adv_ids)} game(s)…")
        pull_game_advanced(game_ids=adv_ids)

    if plan["game_context"]:
        print(f"\npulling game_context for {len(plan['game_context'])} game(s)…")
        pull_game_context(game_ids=plan["game_context"])

    after = len(load_checkpoint(PULL_STATE_FILE).get("failed", []))
    print(f"\nfailed keys: {before} -> {after}")
    if after:
        print("Remaining failures are worth reading individually — the NBA genuinely has no "
              "data for some recent game ids, which is different from a transport error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
