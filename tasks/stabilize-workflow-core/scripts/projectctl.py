#!/usr/bin/env python3
"""Deterministic Project/Task lifecycle operations."""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TASK_STATUSES = ("todo", "doing", "completed", "stopped")
PROJECT_STATUSES = ("todo", "doing", "completed")
WORK_STATUSES = ("todo", "doing", "completed")


class Error(RuntimeError):
    pass


def run(root, *args):
    result = subprocess.run(args, cwd=root, text=True, capture_output=True)
    if result.returncode:
        raise Error(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def is_root(path):
    return (path / "STATE.md").is_file() and (path / "tasks/_template").is_dir()


def root_at(raw=None):
    if raw:
        root = Path(raw).resolve()
        if not is_root(root):
            raise Error("not a Project root")
        return root
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if is_root(candidate):
            return candidate
    raise Error("not inside a Project")


def task_at(root, name):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise Error("Task name must use lowercase kebab-case")
    return root / "tasks" / name


def section(text, name):
    match = re.search(r"(?ms)^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)", text)
    if not match:
        raise Error("missing section: " + name)
    return match.group(1).strip()


def replace(text, name, body):
    pattern = re.compile(r"(?ms)(^## " + re.escape(name) + r"\s*\n).*?(?=^## |\Z)")
    if not pattern.search(text):
        raise Error("missing section: " + name)
    return pattern.sub(lambda m: m.group(1) + "\n" + body.strip() + "\n\n", text).rstrip() + "\n"


def scalar(text, name):
    lines = [
        line.strip() for line in section(text, name).splitlines()
        if line.strip() and not line.startswith("허용값")
    ]
    if not lines:
        raise Error("empty section: " + name)
    return lines[0]


def table(body):
    rows = []
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            rows.append(cells)
    return rows[1:] if rows else []


def format_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def state_rows(root):
    return table(section((root / "STATE.md").read_text(), "Current Tasks"))


def write_state(root, rows):
    path = root / "STATE.md"
    text = path.read_text()
    intro = section(text, "Current Tasks").split("| Task |", 1)[0].rstrip()
    intro = re.sub(r"\n{3,}", "\n\n", intro)
    body = intro + "\n\n" + format_table(("Task", "Status"), rows)
    path.write_text(replace(text, "Current Tasks", body))


def change_state(root, name, old, new=None):
    rows = state_rows(root)
    matches = [row for row in rows if len(row) == 2 and row[0] == name]
    if len(matches) != 1 or matches[0][1] != old:
        raise Error("Project STATE must be " + old)
    if new is None:
        rows.remove(matches[0])
    else:
        matches[0][1] = new
    write_state(root, rows)


def source_at(root, raw, allowed):
    path = (root / raw).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise Error("source is outside Project: " + raw) from error
    if not any(relative == Path(base) or Path(base) in relative.parents for base in allowed):
        raise Error("source is outside allowed roots: " + raw)
    if not path.exists():
        raise Error("source does not exist: " + raw)
    return path


def destination(raw):
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise Error("invalid Task destination: " + raw)
    return path


def create(args):
    root = root_at(args.root)
    task = task_at(root, args.name)
    if task.exists() or any(row and row[0] == args.name for row in state_rows(root)):
        raise Error("Task already exists")
    code = [
        (source_at(root, src, ("src", "tools", "project/src", "project/tools")), destination(dst), src, dst)
        for src, dst in (args.copy_code or [])
    ]
    data = [
        (source_at(root, src, ("data", "project/data")), destination(dst), src, dst)
        for src, dst in (args.link_data or [])
    ]
    stage = Path(tempfile.mkdtemp(prefix="." + args.name + "-", dir=root / "tasks"))
    old_state = (root / "STATE.md").read_text()
    try:
        shutil.copytree(root / "tasks/_template", stage, dirs_exist_ok=True)
        ignore = shutil.ignore_patterns(
            ".git", ".codex", ".env", ".env.*", "*.pem", "*.key",
            "__pycache__", ".venv", "venv", "node_modules",
        )
        for source, dest, _, _ in code:
            target = stage / "scripts" / dest
            if source.is_dir():
                shutil.copytree(source, target, ignore=ignore)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        for source, dest, _, _ in data:
            target = stage / "data" / dest
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(os.path.relpath(source, target.parent))

        status = stage / "STATUS.md"
        status.write_text(replace(status.read_text(), "Final Goal", args.goal))
        contract = stage / "TASK.md"
        text = contract.read_text()
        inputs = [(src, "scripts/" + dst) for _, _, src, dst in code] or [("None", "None")]
        links = [(src, "data/" + dst) for _, _, src, dst in data] or [("None", "None")]
        text = replace(text, "Inputs", format_table(("Project Source", "Task Snapshot"), inputs))
        contract.write_text(replace(text, "Data", format_table(("Project Data", "Task Link"), links)))
        stage.rename(task)
        write_state(root, state_rows(root) + [[args.name, "todo"]])
    except Exception:
        (root / "STATE.md").write_text(old_state)
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(task, ignore_errors=True)
        raise
    print("created tasks/" + args.name)


def validate_work(status, current_work, phase, errors):
    try:
        rows = table(section(status, "Work Plan"))
    except Error as error:
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


def clean_value(raw):
    return raw.strip().strip("\u0060")


def validate_report(task, report, outcome, errors):
    try:
        if clean_value(scalar(report, "Outcome")) != outcome:
            errors.append("REPORT Outcome must be " + outcome)
    except Error as error:
        errors.append(str(error))
    for heading in (
        "Summary", "Final Goal and Result", "Findings", "Work and Validation",
        "Relevant Files", "Limitations", "Project Follow-up",
    ):
        try:
            if "TBD" in section(report, heading):
                errors.append("REPORT " + heading + " is incomplete")
        except Error as error:
            errors.append(str(error))
    try:
        rows = table(section(report, "Relevant Files"))
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
    except Error as error:
        errors.append(str(error))


def validate(root, name, phase):
    task = task_at(root, name)
    errors = []
    for relative in ("AGENTS.md", "TASK.md", "STATUS.md", "REPORT.md"):
        if not (task / relative).is_file():
            errors.append("missing " + relative)
    for relative in ("scripts", "data", "docs/research", "docs/notes", "output"):
        if not (task / relative).is_dir():
            errors.append("missing " + relative + "/")
    if errors:
        return errors
    contract = (task / "TASK.md").read_text()
    status = (task / "STATUS.md").read_text()
    report = (task / "REPORT.md").read_text()
    try:
        task_status = scalar(status, "Status")
        if task_status not in TASK_STATUSES:
            errors.append("invalid Task status")
        if scalar(status, "Final Goal") == "TBD":
            errors.append("Final Goal is incomplete")
        current_work = scalar(status, "Current Work")
    except Error as error:
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
            except Error as error:
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
        validate_report(task, report, phase, errors)
    validate_work(status, current_work, phase, errors)
    return errors


def require(root, name, phase):
    errors = validate(root, name, phase)
    if errors:
        raise Error("\n".join("- " + error for error in errors))


def validate_cmd(args):
    root = root_at(args.root)
    require(root, args.name, args.phase)
    print(args.name + ": " + args.phase + " validation passed")


def activate(args):
    root = root_at(args.root)
    task = task_at(root, args.name)
    require(root, args.name, "ready")
    path = task / "STATUS.md"
    old_status = path.read_text()
    old_state = (root / "STATE.md").read_text()
    try:
        rows = table(section(old_status, "Work Plan"))
        next(row for row in rows if row[1] == "todo")[1] = "doing"
        body = format_table(("Work", "Status"), rows)
        body += "\n\nWork Status는 \u0060todo\u0060, \u0060doing\u0060, \u0060completed\u0060 중 하나를 사용한다."
        updated = replace(old_status, "Work Plan", body)
        updated = replace(
            updated, "Status",
            "doing\n\n허용값은 \u0060todo\u0060, \u0060doing\u0060, \u0060completed\u0060, \u0060stopped\u0060다.",
        )
        path.write_text(updated)
        change_state(root, args.name, "todo", "doing")
    except Exception:
        path.write_text(old_status)
        (root / "STATE.md").write_text(old_state)
        raise
    print("activated; commit before baseline")


def linked_hashes(task):
    output = {}
    for link in sorted(path for path in (task / "data").rglob("*") if path.is_symlink()):
        target = link.resolve()
        files = [target] if target.is_file() else (
            sorted(path for path in target.rglob("*") if path.is_file()) if target.exists() else []
        )
        if not files:
            output[str(link.relative_to(task))] = "MISSING"
        for path in files:
            output[str(link.relative_to(task)) + ":" + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return output


def meta(root, name):
    git_dir = Path(run(root, "git", "rev-parse", "--git-dir"))
    if not git_dir.is_absolute():
        git_dir = root / git_dir
    return git_dir / "harness/tasks" / (name + ".json")


def baseline(args):
    root = root_at(args.root)
    task = task_at(root, args.name)
    require(root, args.name, "doing")
    if run(root, "git", "status", "--porcelain"):
        raise Error("Git worktree must be clean")
    commit = run(root, "git", "rev-parse", "HEAD")
    path = meta(root, args.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"commit": commit, "linked_data": linked_hashes(task)}, indent=2, sort_keys=True) + "\n")
    run(root, "git", "update-ref", "refs/harness/tasks/" + args.name, commit)
    print("baseline " + commit)


def audit_errors(root, name):
    task = task_at(root, name)
    path = meta(root, name)
    if not path.is_file():
        return ["missing baseline"]
    saved = json.loads(path.read_text())
    changed = run(root, "git", "diff", "--name-only", saved["commit"], "--").splitlines()
    changed += run(root, "git", "ls-files", "--others", "--exclude-standard").splitlines()
    prefix = "tasks/" + name + "/"
    errors = [
        "unexpected Project change: " + item
        for item in sorted(set(changed)) if item and not item.startswith(prefix)
    ]
    current = linked_hashes(task)
    errors.extend(
        "linked data changed: " + key
        for key in sorted(set(saved["linked_data"]) | set(current))
        if saved["linked_data"].get(key) != current.get(key)
    )
    return errors


def audit(args):
    errors = audit_errors(root_at(args.root), args.name)
    if errors:
        raise Error("\n".join("- " + error for error in errors))
    print(args.name + ": audit passed")


def task_state(root, row):
    name, project_status = row
    task = task_at(root, name)
    task_status = scalar((task / "STATUS.md").read_text(), "Status") if task.is_dir() else "missing"
    return {"task": name, "project": project_status, "task_status": task_status}


def status_cmd(args):
    root = root_at(args.root)
    items = [task_state(root, row) for row in state_rows(root)]
    if args.json:
        print(json.dumps(items, indent=2))
        return
    for item in items:
        alert = (
            " [return to Project session]"
            if item["project"] == "doing" and item["task_status"] in ("completed", "stopped")
            else ""
        )
        print("%(task)s: Project=%(project)s, Task=%(task_status)s" % item + alert)


def close(args):
    root = root_at(args.root)
    task = task_at(root, args.name)
    outcome = scalar((task / "STATUS.md").read_text(), "Status")
    if outcome not in ("completed", "stopped"):
        raise Error("Task must be completed or stopped")
    require(root, args.name, outcome)
    errors = audit_errors(root, args.name)
    if errors:
        raise Error("\n".join("- " + error for error in errors))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    history = root / "docs/history" / (stamp + "-" + outcome + "-" + args.name + ".md")
    if history.exists():
        raise Error("History record already exists: " + str(history.relative_to(root)))
    state_path = root / "STATE.md"
    old_state = state_path.read_text()
    try:
        change_state(root, args.name, "doing", "completed" if outcome == "completed" else None)
        history.parent.mkdir(parents=True, exist_ok=True)
        history.write_text(
            "# Task " + outcome + ": " + args.name + "\n\n"
            + "- Task: tasks/" + args.name + "\n"
            + "- Report: tasks/" + args.name + "/REPORT.md\n"
            + "- Promotion: not evaluated\n"
        )
    except Exception:
        state_path.write_text(old_state)
        history.unlink(missing_ok=True)
        raise
    print("closed " + args.name + " as " + outcome)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def next_actions(items):
    actions = []
    for item in items:
        name = item["task"]
        if item["project"] == "todo" and item["task_status"] == "todo":
            actions.append("context --task " + name + "; task validate " + name + " --phase ready; then task activate " + name)
        elif item["project"] == "doing" and item["task_status"] in ("completed", "stopped"):
            actions.append(
                "review handoff; task validate " + name + " --phase "
                + item["task_status"] + "; task audit " + name + "; task close " + name
            )
        elif item["project"] == "doing" and item["task_status"] == "doing":
            actions.append("continue Task session: " + name)
        elif item["project"] == "completed":
            actions.append("eligible for user-requested Promotion review: " + name)
    return actions or ["define or create the next Task"]


def report_handoff(task):
    report = (task / "REPORT.md").read_text()
    return {
        "outcome": clean_value(scalar(report, "Outcome")),
        "summary": section(report, "Summary"),
        "final_goal_and_result": section(report, "Final Goal and Result"),
        "findings": section(report, "Findings"),
        "work_and_validation": section(report, "Work and Validation"),
        "relevant_files": [
            {"path": clean_value(row[0]), "type": row[1], "purpose": row[2]}
            for row in table(section(report, "Relevant Files")) if len(row) == 3
        ],
        "limitations": section(report, "Limitations"),
        "project_follow_up": section(report, "Project Follow-up"),
    }


def project_context(root):
    project_path = root / "PROJECT.md"
    state_path = root / "STATE.md"
    project = project_path.read_text()
    state = state_path.read_text()
    items = [task_state(root, row) for row in state_rows(root)]
    finished = [
        item for item in items if item["task_status"] in ("completed", "stopped")
    ]
    sources = {"PROJECT.md": digest(project_path), "STATE.md": digest(state_path)}
    handoffs = {}
    for item in finished:
        task = task_at(root, item["task"])
        try:
            handoffs[item["task"]] = report_handoff(task)
        except Error as error:
            handoffs[item["task"]] = {"error": str(error)}
        sources["tasks/" + item["task"] + "/REPORT.md"] = digest(task / "REPORT.md")
        sources["tasks/" + item["task"] + "/STATUS.md"] = digest(task / "STATUS.md")
    return {
        "role": "project",
        "root": str(root),
        "goal": section(project, "Goal"),
        "scope": section(project, "Scope"),
        "current_goal": section(state, "Current Goal"),
        "tasks": items,
        "handoffs": handoffs,
        "next_actions": next_actions(items),
        "lifecycle_commands": {
            "create": "python3 tools/projectctl.py task create <name> --goal <goal>",
            "inspect_created_task": "python3 tools/projectctl.py context --task <name>",
            "activate": "python3 tools/projectctl.py task validate <name> --phase ready; python3 tools/projectctl.py task activate <name>",
            "baseline": "commit activation, then python3 tools/projectctl.py task baseline <name>",
            "finish": "python3 tools/projectctl.py task close <name>",
            "status": "python3 tools/projectctl.py task status --json",
        },
        "sources": sources,
    }


def report_condition(task):
    report = (task / "REPORT.md").read_text()
    try:
        outcome = clean_value(scalar(report, "Outcome"))
    except Error:
        return "invalid"
    if outcome not in ("completed", "stopped") or "TBD" in report:
        return "incomplete"
    return outcome


def task_context(root, task):
    task_path = task / "TASK.md"
    status_path = task / "STATUS.md"
    report_path = task / "REPORT.md"
    contract = task_path.read_text()
    status = status_path.read_text()
    rows = table(section(status, "Work Plan"))
    current_status = scalar(status, "Status")
    action = (
        "perform Current Work; keep STATUS current"
        if current_status == "doing"
        else "return to Project session for task close " + task.name
        if current_status in ("completed", "stopped")
        else "return to Project session for activation"
    )
    return {
        "role": "task",
        "root": str(root),
        "task": task.name,
        "status": current_status,
        "final_goal": scalar(status, "Final Goal"),
        "work_plan": [{"work": row[0], "status": row[1]} for row in rows if len(row) == 2],
        "current_work": scalar(status, "Current Work"),
        "contract": {
            heading.lower().replace(" ", "_"): section(contract, heading)
            for heading in ("Scope", "Inputs", "Data", "Workflow", "Outputs", "Completion Criteria")
        },
        "report": report_condition(task),
        "report_contract": {
            "outcome": ["completed", "stopped"],
            "required_sections": [
                "Summary", "Final Goal and Result", "Findings",
                "Work and Validation", "Relevant Files", "Limitations",
                "Project Follow-up",
            ],
            "relevant_files_columns": ["Path", "Type", "Purpose"],
        },
        "session_boundary": {
            "finish_here": "write Task outputs and REPORT; set STATUS, Work Plan, and Current Work consistently",
            "do_not_run": ["task activate", "task baseline", "task audit", "task close"],
            "handoff": "stop after Task status is completed or stopped; the user returns to a Project session",
        },
        "next_actions": [action],
        "sources": {
            "TASK.md": digest(task_path),
            "STATUS.md": digest(status_path),
            "REPORT.md": digest(report_path),
        },
    }


def context_cmd(args):
    root = root_at(args.root)
    cwd = Path.cwd().resolve()
    task = task_at(root, args.task) if args.task else None
    if task is not None and not task.is_dir():
        raise Error("Task does not exist: " + args.task)
    try:
        relative = cwd.relative_to(root / "tasks")
        if task is None and relative.parts and relative.parts[0] != "_template":
            candidate = task_at(root, relative.parts[0])
            if candidate.is_dir():
                task = candidate
    except ValueError:
        pass
    payload = task_context(root, task) if task else project_context(root)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return
    print("ROLE: " + payload["role"])
    print("ROOT: " + payload["root"])
    for key, value in payload.items():
        if key in ("role", "root"):
            continue
        print("\n" + key.upper().replace("_", " ") + ":")
        print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value)


def session_cmd(args):
    root = root_at(args.root)
    cwd = root if args.role == "project" else task_at(root, args.name)
    if not cwd.is_dir():
        raise Error("Task does not exist")
    command = ["codex", "-C", str(cwd), "--dangerously-bypass-approvals-and-sandbox"]
    if args.print_command:
        print(shlex.join(command))
        return
    os.execvp(command[0], command)


def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    commands = parser.add_subparsers(required=True)
    context = commands.add_parser("context")
    context.add_argument("--json", action="store_true")
    context.add_argument("--task")
    context.set_defaults(fn=context_cmd)
    session = commands.add_parser("session")
    roles = session.add_subparsers(dest="role", required=True)
    project = roles.add_parser("project")
    project.add_argument("--print", dest="print_command", action="store_true")
    project.set_defaults(fn=session_cmd, name=None)
    task_session = roles.add_parser("task")
    task_session.add_argument("name")
    task_session.add_argument("--print", dest="print_command", action="store_true")
    task_session.set_defaults(fn=session_cmd)

    task = commands.add_parser("task")
    tasks = task.add_subparsers(required=True)
    create_parser = tasks.add_parser("create")
    create_parser.add_argument("name")
    create_parser.add_argument("--goal", required=True)
    create_parser.add_argument("--copy-code", nargs=2, action="append", metavar=("SOURCE", "DEST"))
    create_parser.add_argument("--link-data", nargs=2, action="append", metavar=("SOURCE", "NAME"))
    create_parser.set_defaults(fn=create)
    validate_parser = tasks.add_parser("validate")
    validate_parser.add_argument("name")
    validate_parser.add_argument(
        "--phase", choices=("created", "ready", "doing", "completed", "stopped"), default="created"
    )
    validate_parser.set_defaults(fn=validate_cmd)
    for name, function in (("activate", activate), ("baseline", baseline), ("audit", audit), ("close", close)):
        command = tasks.add_parser(name)
        command.add_argument("name")
        command.set_defaults(fn=function)
    status = tasks.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(fn=status_cmd)
    return parser


def main():
    try:
        args = parser().parse_args()
        args.fn(args)
        return 0
    except (Error, OSError, json.JSONDecodeError, StopIteration) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
