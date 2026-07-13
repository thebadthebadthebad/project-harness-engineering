"""Command-line interface for deterministic Project/Task operations."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .context import render_context, resolve_context
from .documents import scalar
from .errors import HarnessError
from .lifecycle import (
    activate_task,
    audit_task,
    baseline_task,
    check_project,
    close_task,
    create_task,
    current_task_states,
    promotion_record,
    report_handoff,
    require_task,
)
from .observability import record_event
from .repository import find_project_root, task_path


Handler = Callable[[argparse.Namespace], None]


def _root(args: argparse.Namespace) -> Path:
    """Resolve the Project root from parsed CLI arguments."""
    return find_project_root(args.root)


def _print_json(value: Any) -> None:
    """Print stable UTF-8 JSON for command output."""
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def context_command(args: argparse.Namespace) -> None:
    """Print one compact Project or Task context payload."""
    payload = resolve_context(_root(args), args.task)
    if args.json:
        _print_json(payload)
    else:
        print(render_context(payload), end="")


def session_command(args: argparse.Namespace) -> None:
    """Launch one full-access Codex session with explicit harness role metadata."""
    root = _root(args)
    cwd = root if args.role == "project" else task_path(root, args.name)
    if not cwd.is_dir():
        raise HarnessError("Task does not exist")
    command = ["codex", "-C", str(cwd), "--dangerously-bypass-approvals-and-sandbox"]
    if args.print_command:
        prefix = [
            "env",
            "HARNESS_SESSION_ROLE=" + args.role,
            "HARNESS_RUN_ID=<generated-run-id>",
        ]
        if args.name:
            prefix.append("HARNESS_TASK_NAME=" + args.name)
        print(shlex.join(prefix + command))
        return
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    environment = os.environ.copy()
    environment["HARNESS_SESSION_ROLE"] = args.role
    environment["HARNESS_RUN_ID"] = run_id
    if args.name:
        environment["HARNESS_TASK_NAME"] = args.name
    else:
        environment.pop("HARNESS_TASK_NAME", None)
    os.execvpe(command[0], command, environment)


def create_command(args: argparse.Namespace) -> None:
    """Create one Task and report its relative path."""
    create_task(_root(args), args.name, args.goal, args.copy_code, args.link_data)
    print("created tasks/" + args.name)


def validate_command(args: argparse.Namespace) -> None:
    """Validate one Task at an explicit lifecycle phase."""
    require_task(_root(args), args.name, args.phase)
    print(args.name + ": " + args.phase + " validation passed")


def activate_command(args: argparse.Namespace) -> None:
    """Activate one ready Task."""
    activate_task(_root(args), args.name)
    print("activated; commit before baseline")


def baseline_command(args: argparse.Namespace) -> None:
    """Capture one Task's clean Git and linked-data baseline."""
    print("baseline " + baseline_task(_root(args), args.name))


def audit_command(args: argparse.Namespace) -> None:
    """Fail if one Task crossed its baseline boundary or changed linked data."""
    errors = audit_task(_root(args), args.name)
    if errors:
        raise HarnessError("\n".join("- " + error for error in errors))
    print(args.name + ": audit passed")


def status_command(args: argparse.Namespace) -> None:
    """Print current Project and Task-local statuses."""
    items = current_task_states(_root(args))
    if args.json:
        _print_json(items)
        return
    for item in items:
        alert = (
            " [return to Project session]"
            if item["project"] == "doing" and item["task_status"] in ("completed", "stopped")
            else ""
        )
        print("%(task)s: Project=%(project)s, Task=%(task_status)s" % item + alert)


def handoff_command(args: argparse.Namespace) -> None:
    """Validate and print one finished Task's REPORT handoff."""
    root = _root(args)
    task = task_path(root, args.name)
    outcome = scalar((task / "STATUS.md").read_text(), "Status")
    if outcome not in ("completed", "stopped"):
        raise HarnessError("Task must be completed or stopped")
    require_task(root, args.name, outcome)
    payload = {"task": args.name, **report_handoff(task)}
    if args.json:
        _print_json(payload)
    else:
        _print_json(payload)


def close_command(args: argparse.Namespace) -> None:
    """Close one finished and audited Task."""
    root = _root(args)
    outcome = scalar((task_path(root, args.name) / "STATUS.md").read_text(), "Status")
    close_task(root, args.name)
    print("closed " + args.name + " as " + outcome)


def check_command(args: argparse.Namespace) -> None:
    """Check deterministic Project structure and naming rules."""
    errors = check_project(_root(args))
    if args.json:
        _print_json({"ok": not errors, "errors": errors})
    if errors:
        raise HarnessError("\n".join("- " + error for error in errors))
    if not args.json:
        print("Project check passed")


def promotion_record_command(args: argparse.Namespace) -> None:
    """Record, but never make, a completed Promotion decision."""
    path = promotion_record(_root(args), args.name, args.decision, args.paths)
    print("recorded " + args.decision + " in " + str(path))


def observe_mark_command(args: argparse.Namespace) -> None:
    """Append one explicitly declared Skill-use marker to the active run."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.name):
        raise HarnessError("marker name must use lowercase kebab-case")
    if not record_event(_root(args), "skill", {"skill": args.name}):
        raise HarnessError("no active HARNESS_RUN_ID or event log is unavailable")
    print("marked skill " + args.name)


def _set_handler(parser: argparse.ArgumentParser, handler: Handler, guard: str) -> None:
    """Attach a handler and Task-session guard category to an argparse parser."""
    parser.set_defaults(handler=handler, guard=guard)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the public ``projectctl`` argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    commands = parser.add_subparsers(dest="command", required=True)

    context_parser = commands.add_parser("context")
    context_parser.add_argument("--json", action="store_true")
    context_parser.add_argument("--task")
    _set_handler(context_parser, context_command, "context")

    session = commands.add_parser("session")
    roles = session.add_subparsers(dest="role", required=True)
    project = roles.add_parser("project")
    project.add_argument("--print", dest="print_command", action="store_true")
    _set_handler(project, session_command, "project")
    project.set_defaults(name=None)
    task_session = roles.add_parser("task")
    task_session.add_argument("name")
    task_session.add_argument("--print", dest="print_command", action="store_true")
    _set_handler(task_session, session_command, "project")

    task = commands.add_parser("task")
    tasks = task.add_subparsers(dest="task_command", required=True)
    create = tasks.add_parser("create")
    create.add_argument("name")
    create.add_argument("--goal", required=True)
    create.add_argument("--copy-code", nargs=2, action="append", metavar=("SOURCE", "DEST"))
    create.add_argument("--link-data", nargs=2, action="append", metavar=("SOURCE", "NAME"))
    _set_handler(create, create_command, "project")
    validate = tasks.add_parser("validate")
    validate.add_argument("name")
    validate.add_argument(
        "--phase",
        choices=("created", "ready", "doing", "completed", "stopped"),
        default="created",
    )
    _set_handler(validate, validate_command, "task-validate")
    for name, handler in (
        ("activate", activate_command),
        ("baseline", baseline_command),
        ("audit", audit_command),
        ("close", close_command),
    ):
        command = tasks.add_parser(name)
        command.add_argument("name")
        _set_handler(command, handler, "project")
    status = tasks.add_parser("status")
    status.add_argument("--json", action="store_true")
    _set_handler(status, status_command, "project")
    handoff = tasks.add_parser("handoff")
    handoff.add_argument("name")
    handoff.add_argument("--json", action="store_true")
    _set_handler(handoff, handoff_command, "project")

    check = commands.add_parser("check")
    check.add_argument("--json", action="store_true")
    _set_handler(check, check_command, "project")

    promotion = commands.add_parser("promotion")
    promotion_commands = promotion.add_subparsers(dest="promotion_command", required=True)
    record = promotion_commands.add_parser("record")
    record.add_argument("name")
    record.add_argument("--decision", choices=("promoted", "not-promoted"), required=True)
    record.add_argument("--path", dest="paths", action="append")
    _set_handler(record, promotion_record_command, "project")

    observe = commands.add_parser("observe")
    observe_commands = observe.add_subparsers(dest="observe_command", required=True)
    mark = observe_commands.add_parser("mark")
    mark_types = mark.add_subparsers(dest="marker_type", required=True)
    skill = mark_types.add_parser("skill")
    skill.add_argument("name")
    _set_handler(skill, observe_mark_command, "observe-mark")
    return parser


def enforce_session_role(args: argparse.Namespace) -> None:
    """Reject Project lifecycle mutations from a launcher-declared Task session."""
    role = os.environ.get("HARNESS_SESSION_ROLE")
    if role != "task":
        return
    guard = getattr(args, "guard", "project")
    active_task = os.environ.get("HARNESS_TASK_NAME")
    if guard == "project":
        raise HarnessError("Project lifecycle command is unavailable in a Task session")
    if guard == "task-validate" and active_task and args.name != active_task:
        raise HarnessError("Task session may validate only " + active_task)
    if guard == "context" and args.task and active_task and args.task != active_task:
        raise HarnessError("Task session may inspect only " + active_task)


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv``, enforce the role guard, run one command, and return an exit code."""
    try:
        args = build_parser().parse_args(argv)
        enforce_session_role(args)
        args.handler(args)
        return 0
    except (HarnessError, OSError, json.JSONDecodeError, StopIteration) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1
