"""Deterministic Task lifecycle and Project integrity operations."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .documents import (
    atomic_write_text,
    clean_value,
    file_digest,
    format_table,
    markdown_table,
    replace_section,
    scalar,
    section,
)
from .errors import HarnessError
from .repository import (
    git_dir,
    relative_source,
    run_command,
    safe_relative,
    task_path,
)


TASK_STATUSES = ("todo", "doing", "completed", "stopped")
PROJECT_STATUSES = ("todo", "doing", "completed")
WORK_STATUSES = ("todo", "doing", "completed")
TASK_FILES = ("AGENTS.md", "TASK.md", "STATUS.md", "REPORT.md")
TASK_DIRECTORIES = ("scripts", "data", "docs/research", "docs/notes", "output")


def state_rows(root: Path) -> list[list[str]]:
    """Return ``STATE.md`` Current Tasks rows."""
    return markdown_table(section((root / "STATE.md").read_text(), "Current Tasks"))


def write_state(root: Path, rows: Iterable[list[str]]) -> None:
    """Atomically replace only the Current Tasks table in ``STATE.md``."""
    path = root / "STATE.md"
    text = path.read_text()
    intro = section(text, "Current Tasks").split("| Task |", 1)[0].rstrip()
    intro = re.sub(r"\n{3,}", "\n\n", intro)
    body = intro + "\n\n" + format_table(("Task", "Status"), rows)
    atomic_write_text(path, replace_section(text, "Current Tasks", body))


def change_state(root: Path, name: str, old: str, new: str | None = None) -> None:
    """Change or remove exactly one Task row whose current state equals ``old``."""
    rows = state_rows(root)
    matches = [row for row in rows if len(row) == 2 and row[0] == name]
    if len(matches) != 1 or matches[0][1] != old:
        raise HarnessError("Project STATE must be " + old)
    if new is None:
        rows.remove(matches[0])
    else:
        matches[0][1] = new
    write_state(root, rows)


def create_task(
    root: Path,
    name: str,
    goal: str,
    copy_code: list[tuple[str, str]] | None = None,
    link_data: list[tuple[str, str]] | None = None,
) -> Path:
    """Create one staged Task from the template and append its Project state row."""
    task = task_path(root, name)
    if task.exists() or any(row and row[0] == name for row in state_rows(root)):
        raise HarnessError("Task already exists")
    code = [
        (
            relative_source(root, source, ("src", "tools", "project/src", "project/tools")),
            safe_relative(destination),
            source,
            destination,
        )
        for source, destination in copy_code or []
    ]
    data = [
        (
            relative_source(root, source, ("data", "project/data")),
            safe_relative(destination),
            source,
            destination,
        )
        for source, destination in link_data or []
    ]
    stage = Path(tempfile.mkdtemp(prefix="." + name + "-", dir=root / "tasks"))
    old_state = (root / "STATE.md").read_text()
    try:
        shutil.copytree(root / "tasks/_template", stage, dirs_exist_ok=True)
        ignore = shutil.ignore_patterns(
            ".git", ".codex", ".env", ".env.*", "*.pem", "*.key",
            "__pycache__", ".venv", "venv", "node_modules",
        )
        for source, destination, _, _ in code:
            target = stage / "scripts" / destination
            if source.is_dir():
                shutil.copytree(source, target, ignore=ignore)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        for source, destination, _, _ in data:
            target = stage / "data" / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(os.path.relpath(source, target.parent))

        status_path = stage / "STATUS.md"
        atomic_write_text(
            status_path,
            replace_section(status_path.read_text(), "Final Goal", goal),
        )
        task_path_value = stage / "TASK.md"
        contract = task_path_value.read_text()
        inputs = [(source, "scripts/" + destination) for _, _, source, destination in code]
        links = [(source, "data/" + destination) for _, _, source, destination in data]
        contract = replace_section(
            contract,
            "Inputs",
            format_table(("Project Source", "Task Snapshot"), inputs or [("None", "None")]),
        )
        contract = replace_section(
            contract,
            "Data",
            format_table(("Project Data", "Task Link"), links or [("None", "None")]),
        )
        atomic_write_text(task_path_value, contract)
        stage.rename(task)
        write_state(root, state_rows(root) + [[name, "todo"]])
    except Exception:
        atomic_write_text(root / "STATE.md", old_state)
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(task, ignore_errors=True)
        raise
    return task


def _validate_work(status: str, current_work: str, phase: str, errors: list[str]) -> None:
    """Append Work Plan consistency errors for one lifecycle phase."""
    try:
        rows = markdown_table(section(status, "Work Plan"))
    except HarnessError as error:
        errors.append(str(error))
        return
    if not rows:
        errors.append("Work Plan is empty")
        return
    if any(len(row) != 2 or row[1] not in WORK_STATUSES for row in rows):
        errors.append("invalid Work Plan")
        return
    if phase == "ready":
        if any(row[1] != "todo" for row in rows):
            errors.append("ready Work Plan must contain only todo items")
        if current_work not in [row[0] for row in rows if row[1] == "todo"]:
            errors.append("Current Work must name a todo Work Plan item")
    elif phase == "doing":
        doing = [row[0] for row in rows if row[1] == "doing"]
        if len(doing) != 1:
            errors.append("doing Task must have exactly one doing Work Plan item")
        elif current_work != doing[0]:
            errors.append("Current Work must match the doing Work Plan item")
    elif phase == "completed":
        if any(row[1] != "completed" for row in rows):
            errors.append("completed Task must have all Work Plan items completed")
        if current_work != "None":
            errors.append("completed Task Current Work must be None")
    elif phase == "stopped":
        if current_work != "None":
            errors.append("stopped Task Current Work must be None")
        if any(row[1] == "doing" for row in rows):
            errors.append("stopped Task must not have a doing Work Plan item")


def report_handoff(task: Path) -> dict[str, Any]:
    """Return the stable Project-facing fields from a Task REPORT."""
    report = (task / "REPORT.md").read_text()
    return {
        "outcome": clean_value(scalar(report, "Outcome")),
        "summary": section(report, "Summary"),
        "final_goal_and_result": section(report, "Final Goal and Result"),
        "findings": section(report, "Findings"),
        "work_and_validation": section(report, "Work and Validation"),
        "relevant_files": [
            {"path": clean_value(row[0]), "type": row[1], "purpose": row[2]}
            for row in markdown_table(section(report, "Relevant Files"))
            if len(row) == 3
        ],
        "limitations": section(report, "Limitations"),
        "project_follow_up": section(report, "Project Follow-up"),
    }


def _validate_report(task: Path, outcome: str, errors: list[str]) -> None:
    """Append REPORT completeness and referenced-file errors."""
    report = (task / "REPORT.md").read_text()
    try:
        if clean_value(scalar(report, "Outcome")) != outcome:
            errors.append("REPORT Outcome must be " + outcome)
    except HarnessError as error:
        errors.append(str(error))
    for heading in (
        "Summary", "Final Goal and Result", "Findings", "Work and Validation",
        "Relevant Files", "Limitations", "Project Follow-up",
    ):
        try:
            if "TBD" in section(report, heading):
                errors.append("REPORT " + heading + " is incomplete")
        except HarnessError as error:
            errors.append(str(error))
    try:
        rows = markdown_table(section(report, "Relevant Files"))
        if not rows:
            errors.append("REPORT Relevant Files is empty")
        for row in rows:
            if len(row) != 3:
                errors.append("invalid REPORT Relevant Files row")
                continue
            raw = clean_value(row[0])
            relative = Path(raw)
            if not raw or raw == "TBD" or relative.is_absolute() or ".." in relative.parts:
                errors.append("invalid Relevant Files path: " + raw)
            elif not (task / relative).exists():
                errors.append("Relevant Files path does not exist: " + raw)
    except HarnessError as error:
        errors.append(str(error))


def validate_task(root: Path, name: str, phase: str) -> list[str]:
    """Return all deterministic Task contract errors for ``phase``."""
    task = task_path(root, name)
    errors: list[str] = []
    for relative in TASK_FILES:
        if not (task / relative).is_file():
            errors.append("missing " + relative)
    for relative in TASK_DIRECTORIES:
        if not (task / relative).is_dir():
            errors.append("missing " + relative + "/")
    if errors:
        return errors
    contract = (task / "TASK.md").read_text()
    status = (task / "STATUS.md").read_text()
    try:
        task_status = scalar(status, "Status")
        if task_status not in TASK_STATUSES:
            errors.append("invalid Task status")
        if scalar(status, "Final Goal") == "TBD":
            errors.append("Final Goal is incomplete")
        current_work = scalar(status, "Current Work")
    except HarnessError as error:
        errors.append(str(error))
        task_status = ""
        current_work = ""
    rows = [row for row in state_rows(root) if row and row[0] == name]
    if len(rows) != 1 or len(rows[0]) != 2 or rows[0][1] not in PROJECT_STATUSES:
        errors.append("STATE row is missing, duplicated, or invalid")
        project_status = ""
    else:
        project_status = rows[0][1]
    if phase in ("ready", "doing", "completed", "stopped"):
        for heading in ("Scope", "Workflow", "Outputs", "Completion Criteria"):
            try:
                if "TBD" in section(contract, heading):
                    errors.append(heading + " is incomplete")
            except HarnessError as error:
                errors.append(str(error))
    if phase == "ready":
        if task_status != "todo":
            errors.append("ready Task must be todo")
        if project_status != "todo":
            errors.append("ready Project Task must be todo")
    elif phase == "doing":
        if task_status != "doing" or project_status != "doing":
            errors.append("Task and Project must be doing")
    elif phase in ("completed", "stopped"):
        if task_status != phase:
            errors.append(phase + " Task must be " + phase)
        if project_status != "doing":
            errors.append("finished Task must still be doing in Project STATE")
        _validate_report(task, phase, errors)
    _validate_work(status, current_work, phase, errors)
    return errors


def require_task(root: Path, name: str, phase: str) -> None:
    """Raise HarnessError containing every Task validation error for ``phase``."""
    errors = validate_task(root, name, phase)
    if errors:
        raise HarnessError("\n".join("- " + error for error in errors))


def activate_task(root: Path, name: str) -> None:
    """Move a ready Task and its first Work Plan item to doing."""
    task = task_path(root, name)
    require_task(root, name, "ready")
    path = task / "STATUS.md"
    old_status = path.read_text()
    old_state = (root / "STATE.md").read_text()
    try:
        rows = markdown_table(section(old_status, "Work Plan"))
        next(row for row in rows if row[1] == "todo")[1] = "doing"
        body = format_table(("Work", "Status"), rows)
        body += "\n\nWork Status는 `todo`, `doing`, `completed` 중 하나를 사용한다."
        updated = replace_section(old_status, "Work Plan", body)
        updated = replace_section(
            updated,
            "Status",
            "doing\n\n허용값은 `todo`, `doing`, `completed`, `stopped`다.",
        )
        atomic_write_text(path, updated)
        change_state(root, name, "todo", "doing")
    except Exception:
        atomic_write_text(path, old_status)
        atomic_write_text(root / "STATE.md", old_state)
        raise


def linked_data_hashes(task: Path) -> dict[str, str]:
    """Return stable checksums keyed by link path plus target-relative file path."""
    output: dict[str, str] = {}
    for link in sorted(path for path in (task / "data").rglob("*") if path.is_symlink()):
        target = link.resolve()
        if target.is_file():
            files = [(None, target)]
        elif target.exists():
            files = [(path.relative_to(target), path) for path in sorted(target.rglob("*")) if path.is_file()]
        else:
            files = []
        link_name = str(link.relative_to(task))
        if not files:
            output[link_name] = "MISSING"
        for relative, path in files:
            key = link_name if relative is None else link_name + ":" + relative.as_posix()
            output[key] = file_digest(path)
    return output


def task_metadata_path(root: Path, name: str) -> Path:
    """Return the Git-local lifecycle metadata path for one Task."""
    return git_dir(root) / "harness/tasks" / (name + ".json")


def baseline_task(root: Path, name: str) -> str:
    """Save the clean Git commit and linked-data checksums for a doing Task."""
    task = task_path(root, name)
    require_task(root, name, "doing")
    if run_command(root, ("git", "status", "--porcelain")):
        raise HarnessError("Git worktree must be clean")
    commit = run_command(root, ("git", "rev-parse", "HEAD"))
    path = task_metadata_path(root, name)
    atomic_write_text(
        path,
        json.dumps(
            {"commit": commit, "linked_data": linked_data_hashes(task)},
            indent=2,
            sort_keys=True,
        ) + "\n",
    )
    run_command(root, ("git", "update-ref", "refs/harness/tasks/" + name, commit))
    return commit


def audit_task(root: Path, name: str) -> list[str]:
    """Return Task boundary and linked-data changes since its baseline."""
    task = task_path(root, name)
    path = task_metadata_path(root, name)
    if not path.is_file():
        return ["missing baseline"]
    saved = json.loads(path.read_text())
    changed = run_command(root, ("git", "diff", "--name-only", saved["commit"], "--")).splitlines()
    changed += run_command(root, ("git", "ls-files", "--others", "--exclude-standard")).splitlines()
    prefix = "tasks/" + name + "/"
    errors = [
        "unexpected Project change: " + item
        for item in sorted(set(changed))
        if item and not item.startswith(prefix)
    ]
    current = linked_data_hashes(task)
    errors.extend(
        "linked data changed: " + key
        for key in sorted(set(saved["linked_data"]) | set(current))
        if saved["linked_data"].get(key) != current.get(key)
    )
    return errors


def task_state(root: Path, row: list[str]) -> dict[str, str]:
    """Return Project and Task-local status for one Current Tasks row."""
    name, project_status = row
    task = task_path(root, name)
    task_status = scalar((task / "STATUS.md").read_text(), "Status") if task.is_dir() else "missing"
    return {"task": name, "project": project_status, "task_status": task_status}


def current_task_states(root: Path) -> list[dict[str, str]]:
    """Return the current Project Task table enriched with Task-local status."""
    return [task_state(root, row) for row in state_rows(root) if len(row) == 2]


def close_task(root: Path, name: str) -> Path:
    """Validate and close a completed or stopped Task, returning its History path."""
    task = task_path(root, name)
    outcome = scalar((task / "STATUS.md").read_text(), "Status")
    if outcome not in ("completed", "stopped"):
        raise HarnessError("Task must be completed or stopped")
    require_task(root, name, outcome)
    errors = audit_task(root, name)
    if errors:
        raise HarnessError("\n".join("- " + error for error in errors))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    history = root / "docs/history" / (stamp + "-" + outcome + "-" + name + ".md")
    if history.exists():
        raise HarnessError("History record already exists: " + str(history.relative_to(root)))
    state_path = root / "STATE.md"
    old_state = state_path.read_text()
    try:
        change_state(root, name, "doing", "completed" if outcome == "completed" else None)
        atomic_write_text(
            history,
            "# Task " + outcome + ": " + name + "\n\n"
            + "- Task: tasks/" + name + "\n"
            + "- Report: tasks/" + name + "/REPORT.md\n"
            + "- Promotion: not evaluated\n",
        )
    except Exception:
        atomic_write_text(state_path, old_state)
        history.unlink(missing_ok=True)
        raise
    return history


def promotion_record(
    root: Path,
    name: str,
    decision: str,
    official_paths: list[str] | None = None,
) -> Path:
    """Record a completed human Promotion decision without making Project changes."""
    task_path(root, name)
    paths = official_paths or []
    if decision == "promoted" and not paths:
        raise HarnessError("promoted decision requires at least one --path")
    safe_paths = []
    for raw in paths:
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts:
            raise HarnessError("invalid official path: " + raw)
        safe_paths.append(path.as_posix())
    histories = sorted((root / "docs/history").glob("*-completed-" + name + ".md"))
    if len(histories) != 1:
        raise HarnessError("expected one completed History record for Task")
    history = histories[0]
    text = history.read_text()
    if "- Promotion: not evaluated" not in text:
        raise HarnessError("Promotion decision is already recorded")
    replacement = "- Promotion: " + decision
    if safe_paths:
        replacement += "\n- Official paths: " + ", ".join(safe_paths)
    atomic_write_text(history, text.replace("- Promotion: not evaluated", replacement, 1))
    return history


def check_project(root: Path) -> list[str]:
    """Return deterministic structure, state, naming, and config integrity errors."""
    errors: list[str] = []
    required_files = ("AGENTS.md", "PROJECT.md", "README.md", "STATE.md", "STRUCTURE.md", "tools/projectctl.py")
    required_directories = ("src", "tools", "data", "docs/adr", "docs/history", "tasks/_template")
    for relative in required_files:
        if not (root / relative).is_file():
            errors.append("missing " + relative)
    for relative in required_directories:
        if not (root / relative).is_dir():
            errors.append("missing " + relative + "/")
    template = root / "tasks/_template"
    for relative in TASK_FILES:
        if not (template / relative).is_file():
            errors.append("missing tasks/_template/" + relative)
    for relative in TASK_DIRECTORIES:
        if not (template / relative).is_dir():
            errors.append("missing tasks/_template/" + relative + "/")
    for path, headings in (
        (root / "PROJECT.md", ("Goal", "Scope")),
        (root / "STATE.md", ("Current Goal", "Current Tasks")),
        (template / "TASK.md", ("Scope", "Inputs", "Data", "Workflow", "Outputs", "Completion Criteria")),
        (template / "STATUS.md", ("Status", "Final Goal", "Work Plan", "Current Work")),
        (template / "REPORT.md", ("Outcome", "Summary", "Final Goal and Result", "Findings", "Work and Validation", "Relevant Files", "Limitations", "Project Follow-up")),
    ):
        if not path.is_file():
            continue
        text = path.read_text()
        for heading in headings:
            try:
                section(text, heading)
            except HarnessError as error:
                errors.append(str(path.relative_to(root)) + ": " + str(error))
    try:
        rows = state_rows(root)
        names: set[str] = set()
        for row in rows:
            if len(row) != 2:
                errors.append("invalid STATE Current Tasks row")
                continue
            name, status = row
            try:
                path = task_path(root, name)
            except HarnessError as error:
                errors.append(str(error))
                continue
            if name in names:
                errors.append("duplicate STATE Task: " + name)
            names.add(name)
            if status not in PROJECT_STATUSES:
                errors.append("invalid Project Task status: " + status)
            if not path.is_dir():
                errors.append("missing Task directory: tasks/" + name)
    except HarnessError as error:
        errors.append(str(error))
    for path in sorted((root / "docs/adr").glob("*.md")):
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.md", path.name):
            errors.append("invalid ADR filename: " + path.name)
    history_pattern = re.compile(
        r"\d{4}-\d{2}-\d{2}-\d{4}-(?:completed|stopped)-[a-z0-9]+(?:-[a-z0-9]+)*\.md"
    )
    for path in sorted((root / "docs/history").glob("*.md")):
        if not history_pattern.fullmatch(path.name):
            errors.append("invalid History filename: " + path.name)
    hooks_config = root / ".codex/hooks.json"
    if hooks_config.exists():
        try:
            payload = json.loads(hooks_config.read_text())
            if not isinstance(payload.get("hooks"), dict):
                errors.append(".codex/hooks.json: hooks must be an object")
        except json.JSONDecodeError as error:
            errors.append(".codex/hooks.json: " + str(error))
    return errors
