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


def _v2_authority(root: Path) -> bool:
    """Return whether canonical v2 state owns this Project."""
    path = root / ".harness/install.json"
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("authority") == "v2"


def v2_project_context(root: Path) -> dict[str, Any]:
    """Build Project context exclusively from canonical v2 records."""
    from .v2 import harness_root, read_json, validate_record

    base = harness_root(root)
    project_path = base / "project.json"
    project = read_json(project_path)
    validate_record(project, "project")
    tasks: list[dict[str, Any]] = []
    handoffs: dict[str, Any] = {}
    sources = {".harness/project.json": project["content_digest"]}
    for path in sorted((base / "tasks").glob("*/task.json")):
        task = read_json(path)
        validate_record(task, "task")
        task_id = str(task["id"])
        status = str(task.get("state", {}).get("task_status"))
        tasks.append(
            {
                "task": task_id,
                "status": status,
                "goal": task.get("goal", ""),
                "dependencies": task.get("dependencies", []),
                "decision_id": task.get("state", {}).get("decision_id"),
            }
        )
        sources[str(path.relative_to(root))] = task["content_digest"]
        handoff_path = path.parent / "handoff.json"
        if status == "review" and handoff_path.is_file():
            handoff = read_json(handoff_path)
            validate_record(handoff, "handoff")
            handoffs[task_id] = {
                "status": handoff.get("status"),
                "summary": handoff.get("summary"),
                "findings": handoff.get("findings", []),
                "limitations": handoff.get("limitations", []),
            }
            sources[str(handoff_path.relative_to(root))] = handoff["content_digest"]
    actions: list[str] = []
    for task in tasks:
        status = task["status"]
        if status == "ready":
            actions.append("start or amend Task: " + task["task"])
        elif status == "active":
            actions.append("continue active Task: " + task["task"])
        elif status == "review":
            actions.append("review handoff and prepare Promotion: " + task["task"])
        elif status == "needs_decision":
            actions.append("resolve Task decision: " + task["task"])
        elif status == "blocked":
            actions.append("inspect blocked Task: " + task["task"])
    record_event(root, "context", {"context_role": "project", "documents": sorted(sources)})
    return {
        "role": "project",
        "root": str(root),
        "authority": "v2",
        "goal": project.get("goal", ""),
        "scope": project.get("scope", []),
        "current_goal": project.get("current_objective", ""),
        "project_revision": project.get("revision"),
        "last_amendment": project.get("last_amendment"),
        "tasks": tasks,
        "handoffs": handoffs,
        "next_actions": actions or ["define or create the next Task"],
        "sources": sources,
    }


def v2_task_context(root: Path, task_id: str) -> dict[str, Any]:
    """Build one Task context exclusively from its canonical v2 contract."""
    from .v2 import read_task, task_record_path

    task = read_task(root, task_id)
    status = str(task.get("state", {}).get("task_status"))
    path = task_record_path(root, task_id)
    actions = {
        "ready": "start or amend this Task",
        "active": "continue this Task in its isolated worktree",
        "needs_decision": "resolve the pending decision before continuing",
        "blocked": "resolve the blocker or amend the paused contract",
        "review": "parent Agent reviews handoff and prepares Promotion",
        "completed": "retain result and Promotion evidence",
        "stopped": "create a replacement Task if work should resume",
    }
    sources = {str(path.relative_to(root)): task["content_digest"]}
    record_event(
        root,
        "context",
        {"context_role": "task", "context_task": task_id, "documents": sorted(sources)},
    )
    return {
        "role": "task",
        "root": str(root),
        "authority": "v2",
        "task": task_id,
        "status": status,
        "revision": task.get("revision"),
        "final_goal": task.get("goal", ""),
        "contract": {
            key: task.get(key)
            for key in (
                "scope", "inputs", "outputs", "acceptance", "dependencies",
                "context_refs", "owned_write_paths", "validation_commands", "execution",
            )
        },
        "state": task.get("state", {}),
        "last_amendment": task.get("last_amendment"),
        "next_actions": [actions.get(status, "inspect Task state")],
        "sources": sources,
    }


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
    if _v2_authority(root):
        return v2_task_context(root, requested_task) if requested_task else v2_project_context(root)
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
