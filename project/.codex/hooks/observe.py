#!/usr/bin/env python3
"""Record content-free Codex Hook metadata and always allow work to continue."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
MARKDOWN_PATH = re.compile(r"(?<![A-Za-z0-9_])(?:\.{0,2}/)?[A-Za-z0-9_./-]+\.md(?![A-Za-z0-9_])")
PROJECTCTL_ACTION = re.compile(
    r"projectctl\.py(?:\s+--root\s+\S+)?\s+"
    r"(context|check|session\s+(?:project|task)|task\s+(?:create|validate|activate|baseline|audit|handoff|close|status)|promotion\s+record|observe\s+(?:mark|list|report))"
)


def repository_root() -> Path:
    """Return the repository that owns this checked-in Hook."""
    return Path(__file__).resolve().parents[2]


def metadata_directory(root: Path) -> Path | None:
    """Return the repository Git metadata directory, or None on lookup failure."""
    result = subprocess.run(
        ("git", "rev-parse", "--git-dir"), cwd=root, text=True, capture_output=True
    )
    if result.returncode:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else root / path


def safe_run_id(payload: dict[str, Any]) -> str | None:
    """Select a filesystem-safe launcher run id or fall back to the session id."""
    launcher = os.environ.get("HARNESS_RUN_ID")
    if launcher and SAFE_ID.fullmatch(launcher):
        return launcher
    session = str(payload.get("session_id") or "")
    candidate = "session-" + re.sub(r"[^A-Za-z0-9._-]", "-", session)[:100]
    return candidate if session and SAFE_ID.fullmatch(candidate) else None


def inferred_role(root: Path, cwd: str) -> tuple[str | None, str | None]:
    """Return launcher role and Task name, inferring them from cwd when absent."""
    role = os.environ.get("HARNESS_SESSION_ROLE")
    task = os.environ.get("HARNESS_TASK_NAME")
    if role:
        return role, task
    try:
        relative = Path(cwd).resolve().relative_to(root / "tasks")
        if relative.parts and relative.parts[0] != "_template":
            return "task", relative.parts[0]
    except (OSError, ValueError):
        pass
    return "project", None


def command_metadata(payload: dict[str, Any]) -> tuple[list[str], str | None]:
    """Extract Markdown paths and a projectctl action without retaining a command."""
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")
    if tool_name != "Bash" or not isinstance(tool_input, dict):
        return [], None
    command = tool_input.get("command")
    if not isinstance(command, str):
        return [], None
    documents = list(dict.fromkeys(MARKDOWN_PATH.findall(command)))
    match = PROJECTCTL_ACTION.search(command)
    action = re.sub(r"\s+", ".", match.group(1)) if match else None
    return documents, action


def tool_category(tool_name: str) -> str | None:
    """Map a Hook tool name to a coarse, content-free category."""
    if not tool_name:
        return None
    if tool_name == "Bash":
        return "shell"
    if tool_name == "apply_patch":
        return "edit"
    if tool_name.startswith("mcp__"):
        return "mcp"
    return "other"


def event_from(payload: dict[str, Any], root: Path, run_id: str) -> dict[str, Any]:
    """Normalize an allowed Hook payload subset into the shared event schema."""
    cwd = str(payload.get("cwd") or root)
    role, task = inferred_role(root, cwd)
    documents, action = command_metadata(payload)
    event: dict[str, Any] = {
        "schema_version": 1,
        "event": "hook",
        "hook_event": payload.get("hook_event_name"),
        "time": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "session_id": payload.get("session_id"),
        "turn_id": payload.get("turn_id"),
        "role": role,
        "task": task,
        "cwd": cwd,
        "model": payload.get("model"),
        "permission_mode": payload.get("permission_mode"),
        "source": payload.get("source"),
        "trigger": payload.get("trigger"),
        "tool_name": payload.get("tool_name"),
        "tool_category": tool_category(str(payload.get("tool_name") or "")),
        "tool_use_id": payload.get("tool_use_id"),
        "documents": documents,
        "projectctl_action": action,
        "subagent_type": payload.get("agent_type") or payload.get("subagent_type"),
        "subagent_id": payload.get("agent_id") or payload.get("subagent_id"),
    }
    return {key: value for key, value in event.items() if value not in (None, [], "")}


def append_event(path: Path, event: dict[str, Any]) -> None:
    """Append one compact JSON object with a single O_APPEND write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode()
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, data)
    finally:
        os.close(descriptor)


def main() -> int:
    """Read one Hook payload, record safe metadata if possible, and always return zero."""
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return 0
        root = repository_root()
        metadata = metadata_directory(root)
        run_id = safe_run_id(payload)
        if metadata is None or run_id is None:
            return 0
        path = metadata / "harness/observability" / run_id / "events.jsonl"
        append_event(path, event_from(payload, root, run_id))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
