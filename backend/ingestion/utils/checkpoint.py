"""Resume state for long pulls."""
from __future__ import annotations

import json
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


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
