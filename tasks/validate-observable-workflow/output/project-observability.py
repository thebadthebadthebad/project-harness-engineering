"""Privacy-conscious JSONL recording and human-readable run reports."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .documents import atomic_write_text
from .errors import HarnessError
from .repository import git_dir


RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
EXPECTED_HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "SubagentStart",
    "SubagentStop",
    "Stop",
)


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


def runs_directory(root: Path) -> Path:
    """Return the Git-local directory that contains all observability runs."""
    return git_dir(root) / "harness/observability"


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


def list_runs(root: Path) -> list[dict[str, Any]]:
    """Return available runs newest first with their event file size and mtime."""
    directory = runs_directory(root)
    if not directory.is_dir():
        return []
    runs = []
    for child in directory.iterdir():
        events = child / "events.jsonl"
        if child.is_dir() and RUN_ID.fullmatch(child.name) and events.is_file():
            stat = events.stat()
            runs.append(
                {
                    "run_id": child.name,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "bytes": stat.st_size,
                }
            )
    return sorted(runs, key=lambda item: (item["modified"], item["run_id"]), reverse=True)


def read_events(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read JSON object events and return valid entries plus malformed line metadata."""
    events: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("event is not an object")
            events.append(value)
        except (json.JSONDecodeError, ValueError) as error:
            malformed.append({"line": number, "error": str(error)})
    return events, malformed


def _timeline_detail(event: dict[str, Any]) -> str:
    """Return one content-free detail label for a timeline event."""
    for key in (
        "hook_event", "skill", "context_role", "projectctl_action", "tool_category",
        "subagent_type", "source",
    ):
        if event.get(key):
            return str(event[key])
    return "-"


def summarize_run(run_id: str, events: list[dict[str, Any]], malformed: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate one event stream into deterministic counts and a compact timeline."""
    event_types: Counter[str] = Counter()
    hooks: Counter[str] = Counter()
    documents: Counter[str] = Counter()
    skills: Counter[str] = Counter()
    lifecycle: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    compactions: Counter[str] = Counter()
    subagents: Counter[str] = Counter()
    timeline = []
    seen_documents: set[tuple[str, str]] = set()
    seen_lifecycle: set[tuple[str, str]] = set()
    for index, event in enumerate(events, 1):
        kind = str(event.get("event") or "unknown")
        event_types[kind] += 1
        hook = event.get("hook_event")
        if hook:
            hooks[str(hook)] += 1
            if hook in ("PreCompact", "PostCompact"):
                compactions[str(hook)] += 1
            if hook in ("SubagentStart", "SubagentStop"):
                subagents[str(hook)] += 1
        for path in event.get("documents") or []:
            if isinstance(path, str):
                identity = str(event.get("tool_use_id") or "event-" + str(index))
                key = (identity, path)
                if key not in seen_documents:
                    documents[path] += 1
                    seen_documents.add(key)
        if event.get("skill"):
            skills[str(event["skill"])] += 1
        if event.get("projectctl_action"):
            action = str(event["projectctl_action"])
            identity = str(event.get("tool_use_id") or "event-" + str(index))
            key = (identity, action)
            if key not in seen_lifecycle:
                lifecycle[action] += 1
                seen_lifecycle.add(key)
        if event.get("role"):
            roles[str(event["role"])] += 1
        timeline.append(
            {
                "time": event.get("time"),
                "event": kind,
                "detail": _timeline_detail(event),
            }
        )
    observed = [name for name in EXPECTED_HOOK_EVENTS if hooks[name]]
    return {
        "run_id": run_id,
        "total_events": len(events),
        "malformed": malformed,
        "event_types": dict(sorted(event_types.items())),
        "hook_events": dict(sorted(hooks.items())),
        "document_visits": dict(sorted(documents.items())),
        "skills": dict(sorted(skills.items())),
        "lifecycle_actions": dict(sorted(lifecycle.items())),
        "roles": dict(sorted(roles.items())),
        "compactions": dict(sorted(compactions.items())),
        "subagents": dict(sorted(subagents.items())),
        "coverage": {
            "expected_hook_events": list(EXPECTED_HOOK_EVENTS),
            "observed_hook_events": observed,
            "missing_hook_events": [name for name in EXPECTED_HOOK_EVENTS if name not in observed],
        },
        "timeline": timeline,
    }


def render_report(summary: dict[str, Any]) -> str:
    """Render one run summary as a human-readable Markdown report."""
    lines = [
        "# Harness Observability Report",
        "",
        "- Run: `" + summary["run_id"] + "`",
        "- Events: " + str(summary["total_events"]),
        "- Malformed lines: " + str(len(summary["malformed"])),
        "",
        "## Coverage",
        "",
        "- Observed Hook events: " + (", ".join(summary["coverage"]["observed_hook_events"]) or "None"),
        "- Missing Hook events: " + (", ".join(summary["coverage"]["missing_hook_events"]) or "None"),
        "",
        "## Counts",
        "",
        "| Category | Name | Count |",
        "| --- | --- | ---: |",
    ]
    categories = (
        ("event", summary["event_types"]),
        ("hook", summary["hook_events"]),
        ("document", summary["document_visits"]),
        ("skill", summary["skills"]),
        ("lifecycle", summary["lifecycle_actions"]),
        ("role", summary["roles"]),
    )
    added = False
    for category, values in categories:
        for name, count in values.items():
            lines.append("| " + category + " | `" + name.replace("|", "\\|") + "` | " + str(count) + " |")
            added = True
    if not added:
        lines.append("| - | - | 0 |")
    lines.extend(["", "## Timeline", "", "| Time | Event | Detail |", "| --- | --- | --- |"])
    for event in summary["timeline"]:
        lines.append(
            "| " + str(event["time"] or "-") + " | " + event["event"] + " | `"
            + event["detail"].replace("|", "\\|") + "` |"
        )
    if not summary["timeline"]:
        lines.append("| - | - | - |")
    lines.extend(
        [
            "",
            "이 보고서는 메타데이터만 집계한다. 사용자 프롬프트, 도구 출력, patch 본문, 전체 shell 명령은 기록하지 않는다.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(
    root: Path,
    run_id: str | None = None,
    latest: bool = False,
    output: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Summarize one selected run, write REPORT.md and summary.json, and return both."""
    runs = list_runs(root)
    if latest:
        if not runs:
            raise HarnessError("no observability runs")
        selected = runs[0]["run_id"]
    elif run_id and RUN_ID.fullmatch(run_id):
        selected = run_id
    else:
        raise HarnessError("provide a valid run id or --latest")
    path = event_path(root, selected)
    if not path.is_file():
        raise HarnessError("observability run does not exist: " + selected)
    events, malformed = read_events(path)
    summary = summarize_run(selected, events, malformed)
    destination = (output or root / ".harness/observability" / selected).resolve()
    atomic_write_text(
        destination / "summary.json",
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    report = destination / "REPORT.md"
    atomic_write_text(report, render_report(summary))
    return report, summary
