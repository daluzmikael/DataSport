"""Resume state for long pulls."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_lock = threading.Lock()


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"completed": [], "failed": [], "meta": {}}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, state: dict[str, Any]) -> None:
    """Write atomically: full file to a temp path, then one rename.

    The previous version truncated the real file and streamed JSON into it, so a
    process killed mid-write left a half-written file that would not parse — which
    is exactly what happened on 2026-08-19, losing a 187k-key checkpoint. os.replace
    is atomic on Windows and POSIX, so a reader sees either the old file or the new
    one, never a partial.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_checkpoint(path: Path) -> dict[str, Any]:
    with _lock:
        return _load(path)


def is_done(path: Path, key: str) -> bool:
    with _lock:
        state = _load(path)
        return key in state.get("completed", [])


def failed_keys(path: Path, prefix: str = "") -> list[str]:
    """Unique checkpoint keys from failed entries, optionally filtered by prefix."""
    with _lock:
        state = _load(path)
    keys: set[str] = set()
    for entry in state.get("failed", []):
        key = entry.get("key", "")
        if key and (not prefix or key.startswith(prefix)):
            keys.add(key)
    return sorted(keys)


def mark_done(path: Path, key: str) -> None:
    with _lock:
        state = _load(path)
        completed = set(state.get("completed", []))
        completed.add(key)
        state["completed"] = sorted(completed)
        state["failed"] = [e for e in state.get("failed", []) if e.get("key") != key]
        state.setdefault("meta", {})["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save(path, state)


def mark_failed(path: Path, key: str, error: str) -> None:
    with _lock:
        state = _load(path)
        failed = [e for e in state.get("failed", []) if e.get("key") != key]
        failed.append({"key": key, "error": error, "at": datetime.now(timezone.utc).isoformat()})
        state["failed"] = failed
        _save(path, state)


# ---------------------------------------------------------------------------
# Cross-process guard
# ---------------------------------------------------------------------------
class PullAlreadyRunning(RuntimeError):
    """Another pull process holds the checkpoint lock."""


class pull_lock:
    """Refuse to start a second pull against the same checkpoint.

    `_lock` above is a threading.Lock — it serialises threads inside ONE process and
    does nothing across processes. Two `pull_all` runs will therefore interleave
    read-modify-write cycles on the same JSON and corrupt it. That is not theoretical:
    it happened, and cost a 187k-key checkpoint.

    Usage:
        with pull_lock(PULL_STATE_FILE):
            ...

    The lock file records the owning pid so a stale lock from a killed process can be
    identified and cleared rather than blocking forever.
    """

    def __init__(self, state_path: Path) -> None:
        self.path = state_path.with_suffix(state_path.suffix + ".lock")

    def _stale(self) -> bool:
        """True if the lock names a pid that is no longer alive."""
        try:
            pid = int(self.path.read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            return True
        if pid == os.getpid():
            return True
        try:
            os.kill(pid, 0)  # signal 0 = liveness probe, no signal delivered
        except OSError:
            return True
        except Exception:  # noqa: BLE001 — platform quirk, assume alive
            return False
        return False

    def __enter__(self) -> "pull_lock":
        if self.path.exists() and self._stale():
            self.path.unlink(missing_ok=True)
        try:
            # O_EXCL makes creation fail if another process won the race.
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            owner = ""
            try:
                owner = self.path.read_text(encoding="utf-8").strip()
            except OSError:
                pass
            raise PullAlreadyRunning(
                f"Another pull is already running ({owner}). "
                f"Run only one at a time - concurrent writes corrupt the checkpoint. "
                f"If that process is gone, delete: {self.path}"
            ) from None
        with os.fdopen(fd, "w") as f:
            f.write(f"{os.getpid()} {datetime.now(timezone.utc).isoformat()}")
        return self

    def __exit__(self, *exc: Any) -> None:
        self.path.unlink(missing_ok=True)
