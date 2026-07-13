"""Privacy-conscious JSONL event recording for harness sessions."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .repository import git_dir


RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def active_run_id() -> str | None:
    """Return a safe session run identifier from the environment, if present."""
    value = os.environ.get("HARNESS_RUN_ID")
    return value if value and RUN_ID.fullmatch(value) else None


def event_path(root: Path, run_id: str) -> Path:
    """Return the Git-local JSONL event path for ``run_id``."""
    return git_dir(root) / "harness/observability" / run_id / "events.jsonl"


def record_event(root: Path, event: str, details: dict[str, Any] | None = None) -> bool:
    """Append one metadata-only event; return False instead of disrupting work on failure."""
    run_id = active_run_id()
    if not run_id:
        return False
    payload: dict[str, Any] = {
        "event": event,
        "time": utc_now(),
        "run_id": run_id,
        "role": os.environ.get("HARNESS_SESSION_ROLE"),
        "task": os.environ.get("HARNESS_TASK_NAME"),
    }
    payload.update(details or {})
    try:
        path = event_path(root, run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return True
    except (OSError, RuntimeError):
        return False
