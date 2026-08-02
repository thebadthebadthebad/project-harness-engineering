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
from .observability import list_runs, record_event, write_report
from .repository import find_project_root, task_path
from .v2 import (
    apply_promotion,
    approve_promotion,
    authority_mode,
    create_v2_task,
    initialize_v2,
    migration_apply,
    migration_inspect,
    migration_plan,
    migration_rollback,
    migration_switch,
    migration_verify,
    prepare_promotion,
    render_handoff_review,
    render_project,
    render_promotion,
    render_task,
    start_v2_task,
    submit_handoff,
)


Handler = Callable[[argparse.Namespace], None]


def _root(args: argparse.Namespace) -> Path:
    """Resolve the Project root from parsed CLI arguments."""
    return find_project_root(args.root)


def _print_json(value: Any) -> None:
    """Print stable UTF-8 JSON for command output."""
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def _require_legacy_writer(root: Path) -> None:
    """Prevent split-brain writes after v2 becomes authoritative."""
    if authority_mode(root) == "v2":
        raise HarnessError("legacy lifecycle writer is disabled under v2 authority")


def init_command(args: argparse.Namespace) -> None:
    """Initialize a newly installed Project with v2 authority."""
    payload = initialize_v2(
        _root(args),
        args.project_id,
        args.goal,
        args.scope,
        args.canonical_root,
        args.harness_version,
    )
    _print_json(payload)


def show_project_command(args: argparse.Namespace) -> None:
    """Render the canonical Project state for human review."""
    print(render_project(_root(args)), end="")


def migrate_command(args: argparse.Namespace) -> None:
    """Run one explicit legacy-to-v2 migration phase."""
    root = _root(args)
    if args.migrate_command == "inspect":
        payload = migration_inspect(root)
    elif args.migrate_command == "plan":
        payload = migration_plan(root)
    elif args.migrate_command == "apply":
        payload = {"candidate": str(migration_apply(root, args.migration_id))}
    elif args.migrate_command == "verify":
        payload = migration_verify(root, args.migration_id)
    elif args.migrate_command == "switch":
        payload = migration_switch(root, args.migration_id, args.harness_version)
    elif args.migrate_command == "rollback":
        payload = migration_rollback(root, args.migration_id)
    else:
        payload = {"authority": authority_mode(root)}
    _print_json(payload)


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
    root = _root(args)
    if authority_mode(root) == "v2":
        commands = [shlex.split(item) for item in (args.validation_command or [])]
        payload = create_v2_task(
            root,
            args.name,
            args.goal,
            args.scope or "",
            args.output or [],
            args.acceptance or [],
            args.owned_path or [],
            commands,
        )
        _print_json(payload)
        return
    create_task(root, args.name, args.goal, args.copy_code, args.link_data)
    print("created tasks/" + args.name)


def task_show_command(args: argparse.Namespace) -> None:
    """Render one v2 Task contract and state."""
    print(render_task(_root(args), args.name), end="")


def task_start_command(args: argparse.Namespace) -> None:
    """Create one isolated manual Task worktree."""
    _print_json(start_v2_task(_root(args), args.name))


def task_submit_command(args: argparse.Namespace) -> None:
    """Import and validate one typed Task handoff."""
    _print_json(submit_handoff(_root(args), args.name, args.handoff))


def task_review_command(args: argparse.Namespace) -> None:
    """Render a typed Task handoff for parent-Agent review."""
    print(render_handoff_review(_root(args), args.name), end="")


def validate_command(args: argparse.Namespace) -> None:
    """Validate one Task at an explicit lifecycle phase."""
    root = _root(args)
    _require_legacy_writer(root)
    require_task(root, args.name, args.phase)
    print(args.name + ": " + args.phase + " validation passed")


def activate_command(args: argparse.Namespace) -> None:
    """Activate one ready Task."""
    root = _root(args)
    _require_legacy_writer(root)
    activate_task(root, args.name)
    print("activated; commit before baseline")


def baseline_command(args: argparse.Namespace) -> None:
    """Capture one Task's clean Git and linked-data baseline."""
    root = _root(args)
    _require_legacy_writer(root)
    print("baseline " + baseline_task(root, args.name))


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
    _require_legacy_writer(root)
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
    root = _root(args)
    _require_legacy_writer(root)
    path = promotion_record(root, args.name, args.decision, args.paths)
    print("recorded " + args.decision + " in " + str(path))


def promotion_prepare_command(args: argparse.Namespace) -> None:
    """Build an exact-diff packet for selected candidates."""
    _print_json(prepare_promotion(_root(args), args.task, args.candidate))


def promotion_show_command(args: argparse.Namespace) -> None:
    """Render an exact-diff Promotion packet."""
    print(render_promotion(_root(args), args.promotion_id), end="")


def promotion_approve_command(args: argparse.Namespace) -> None:
    """Approve the current exact diff and validation packet."""
    _print_json(approve_promotion(_root(args), args.promotion_id, args.actor))


def promotion_apply_command(args: argparse.Namespace) -> None:
    """Integrate one still-current approved Promotion."""
    _print_json(apply_promotion(_root(args), args.promotion_id))


def observe_mark_command(args: argparse.Namespace) -> None:
    """Append one explicitly declared Skill-use marker to the active run."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.name):
        raise HarnessError("marker name must use lowercase kebab-case")
    if not record_event(_root(args), "skill", {"skill": args.name}):
        raise HarnessError("no active HARNESS_RUN_ID or event log is unavailable")
    print("marked skill " + args.name)


def observe_list_command(args: argparse.Namespace) -> None:
    """List Git-local observability runs newest first."""
    runs = list_runs(_root(args))
    if args.json:
        _print_json(runs)
        return
    for item in runs:
        print(item["run_id"] + "\t" + item["modified"] + "\t" + str(item["bytes"]) + " bytes")


def observe_report_command(args: argparse.Namespace) -> None:
    """Write a metadata-only Markdown and JSON report for one run."""
    path, summary = write_report(_root(args), args.run_id, args.latest, args.output)
    if args.json:
        _print_json(summary)
    else:
        print(path)


def _set_handler(parser: argparse.ArgumentParser, handler: Handler, guard: str) -> None:
    """Attach a handler and Task-session guard category to an argparse parser."""
    parser.set_defaults(handler=handler, guard=guard)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the public ``projectctl`` argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--project-id", required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--scope", action="append", required=True)
    init.add_argument("--canonical-root", action="append", default=[])
    init.add_argument("--harness-version", default="development")
    _set_handler(init, init_command, "project")

    show = commands.add_parser("show")
    show_commands = show.add_subparsers(dest="show_command", required=True)
    show_project = show_commands.add_parser("project")
    _set_handler(show_project, show_project_command, "project")

    migrate = commands.add_parser("migrate")
    migrate_commands = migrate.add_subparsers(dest="migrate_command", required=True)
    for name in ("inspect", "plan", "status"):
        command = migrate_commands.add_parser(name)
        _set_handler(command, migrate_command, "project")
    for name in ("apply", "verify", "rollback"):
        command = migrate_commands.add_parser(name)
        command.add_argument("migration_id")
        _set_handler(command, migrate_command, "project")
    switch = migrate_commands.add_parser("switch")
    switch.add_argument("migration_id")
    switch.add_argument("--harness-version", required=True)
    _set_handler(switch, migrate_command, "project")

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
    create.add_argument("--scope")
    create.add_argument("--output", action="append")
    create.add_argument("--acceptance", action="append")
    create.add_argument("--owned-path", action="append")
    create.add_argument("--validation-command", action="append")
    _set_handler(create, create_command, "project")
    show_task = tasks.add_parser("show")
    show_task.add_argument("name")
    _set_handler(show_task, task_show_command, "project")
    start_task = tasks.add_parser("start")
    start_task.add_argument("name")
    _set_handler(start_task, task_start_command, "project")
    submit_task = tasks.add_parser("submit")
    submit_task.add_argument("name")
    submit_task.add_argument("--handoff", type=Path, required=True)
    _set_handler(submit_task, task_submit_command, "project")
    review_task = tasks.add_parser("review")
    review_task.add_argument("name")
    _set_handler(review_task, task_review_command, "project")
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
    prepare = promotion_commands.add_parser("prepare")
    prepare.add_argument("--task", required=True)
    prepare.add_argument("--candidate", action="append", required=True)
    _set_handler(prepare, promotion_prepare_command, "project")
    show_promotion = promotion_commands.add_parser("show")
    show_promotion.add_argument("promotion_id")
    _set_handler(show_promotion, promotion_show_command, "project")
    approve = promotion_commands.add_parser("approve")
    approve.add_argument("promotion_id")
    approve.add_argument("--actor", required=True)
    _set_handler(approve, promotion_approve_command, "project")
    apply = promotion_commands.add_parser("apply")
    apply.add_argument("promotion_id")
    _set_handler(apply, promotion_apply_command, "project")

    observe = commands.add_parser("observe")
    observe_commands = observe.add_subparsers(dest="observe_command", required=True)
    list_command = observe_commands.add_parser("list")
    list_command.add_argument("--json", action="store_true")
    _set_handler(list_command, observe_list_command, "project")
    report = observe_commands.add_parser("report")
    report.add_argument("run_id", nargs="?")
    report.add_argument("--latest", action="store_true")
    report.add_argument("--output", type=Path)
    report.add_argument("--json", action="store_true")
    _set_handler(report, observe_report_command, "project")
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
