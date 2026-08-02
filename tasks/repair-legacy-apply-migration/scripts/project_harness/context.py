"""Compact Project and Task handoff context construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .documents import clean_value, file_digest, markdown_table, scalar, section
from .errors import HarnessError
from .lifecycle import current_task_states, report_handoff
from .observability import record_event
from .repository import task_path


def next_actions(items: list[dict[str, str]]) -> list[str]:
    """Return concise state-derived actions without embedding static CLI documentation."""
    actions: list[str] = []
    for item in items:
        name = item["task"]
        if item["project"] == "todo" and item["task_status"] == "todo":
            actions.append("prepare and activate Task: " + name)
        elif item["project"] == "doing" and item["task_status"] in ("completed", "stopped"):
            actions.append("review handoff and close Task: " + name)
        elif item["project"] == "doing" and item["task_status"] == "doing":
            actions.append("continue Task session: " + name)
        elif item["project"] == "completed":
            actions.append("await explicit Promotion decision: " + name)
    return actions or ["define or create the next Task"]


def project_context(root: Path) -> dict[str, Any]:
    """Build dynamic Project context plus only handoffs awaiting Project close."""
    project_path = root / "PROJECT.md"
    state_path = root / "STATE.md"
    project = project_path.read_text()
    state = state_path.read_text()
    items = current_task_states(root)
    pending = [
        item
        for item in items
        if item["project"] == "doing" and item["task_status"] in ("completed", "stopped")
    ]
    sources = {"PROJECT.md": file_digest(project_path), "STATE.md": file_digest(state_path)}
    handoffs: dict[str, Any] = {}
    for item in pending:
        task = task_path(root, item["task"])
        try:
            handoffs[item["task"]] = report_handoff(task)
        except HarnessError as error:
            handoffs[item["task"]] = {"error": str(error)}
        sources["tasks/" + item["task"] + "/REPORT.md"] = file_digest(task / "REPORT.md")
        sources["tasks/" + item["task"] + "/STATUS.md"] = file_digest(task / "STATUS.md")
    record_event(root, "context", {"context_role": "project", "documents": sorted(sources)})
    return {
        "role": "project",
        "root": str(root),
        "goal": section(project, "Goal"),
        "scope": section(project, "Scope"),
        "current_goal": section(state, "Current Goal"),
        "tasks": items,
        "handoffs": handoffs,
        "next_actions": next_actions(items),
        "sources": sources,
    }


def report_condition(task: Path) -> str:
    """Return incomplete, invalid, completed, or stopped for a Task REPORT."""
    report = (task / "REPORT.md").read_text()
    try:
        outcome = clean_value(scalar(report, "Outcome"))
    except HarnessError:
        return "invalid"
    if outcome not in ("completed", "stopped") or "TBD" in report:
        return "incomplete"
    return outcome


def task_context(root: Path, task: Path) -> dict[str, Any]:
    """Build Task-local contract and current work context for a fresh Task session."""
    task_path_value = task / "TASK.md"
    status_path = task / "STATUS.md"
    report_path = task / "REPORT.md"
    contract = task_path_value.read_text()
    status = status_path.read_text()
    rows = markdown_table(section(status, "Work Plan"))
    current_status = scalar(status, "Status")
    action = (
        "perform Current Work; keep STATUS current"
        if current_status == "doing"
        else "return to Project session for close"
        if current_status in ("completed", "stopped")
        else "return to Project session for activation"
    )
    sources = {
        "TASK.md": file_digest(task_path_value),
        "STATUS.md": file_digest(status_path),
        "REPORT.md": file_digest(report_path),
    }
    record_event(
        root,
        "context",
        {"context_role": "task", "context_task": task.name, "documents": sorted(sources)},
    )
    return {
        "role": "task",
        "root": str(root),
        "task": task.name,
        "status": current_status,
        "final_goal": scalar(status, "Final Goal"),
        "work_plan": [
            {"work": row[0], "status": row[1]} for row in rows if len(row) == 2
        ],
        "current_work": scalar(status, "Current Work"),
        "contract": {
            heading.lower().replace(" ", "_"): section(contract, heading)
            for heading in ("Scope", "Inputs", "Data", "Workflow", "Outputs", "Completion Criteria")
        },
        "report": report_condition(task),
        "report_contract": {
            "outcome": ["completed", "stopped"],
            "required_sections": [
                "Summary", "Final Goal and Result", "Findings", "Work and Validation",
                "Relevant Files", "Limitations", "Project Follow-up",
            ],
            "relevant_files_columns": ["Path", "Type", "Purpose"],
        },
        "next_actions": [action],
        "sources": sources,
    }


def resolve_context(root: Path, requested_task: str | None, cwd: Path | None = None) -> dict[str, Any]:
    """Resolve Project or Task context from an explicit Task name or current directory."""
    current = (cwd or Path.cwd()).resolve()
    task = task_path(root, requested_task) if requested_task else None
    if task is not None and not task.is_dir():
        raise HarnessError("Task does not exist: " + str(requested_task))
    try:
        relative = current.relative_to(root / "tasks")
        if task is None and relative.parts and relative.parts[0] != "_template":
            candidate = task_path(root, relative.parts[0])
            if candidate.is_dir():
                task = candidate
    except ValueError:
        pass
    return task_context(root, task) if task else project_context(root)


def render_context(payload: dict[str, Any]) -> str:
    """Render a context payload as compact human-readable text."""
    lines = ["ROLE: " + payload["role"], "ROOT: " + payload["root"]]
    for key, value in payload.items():
        if key in ("role", "root"):
            continue
        lines.extend(
            [
                "",
                key.upper().replace("_", " ") + ":",
                json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
                if isinstance(value, (dict, list))
                else str(value),
            ]
        )
    return "\n".join(lines) + "\n"
