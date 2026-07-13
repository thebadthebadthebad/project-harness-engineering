#!/usr/bin/env python3
"""Run controlled Codex sessions and summarize observable actions."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


class Error(RuntimeError):
    pass


READ_TOOL = re.compile(r"(?<![\w-])(cat|sed|head|tail|less|rg|find)(?![\w-])")
MARKDOWN_PATH = re.compile(r"(?<![\w])(?:\.{0,2}/)?[\w./-]+\.md(?![\w])")
PARENT_PATH = re.compile(r"(?:^|[\s'\"=])(\.\.(?:/[^\s'\";|]*)?)")


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def safe_name(raw):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", raw):
        raise Error("session names must use lowercase kebab-case: " + raw)
    return raw


def read_events(path):
    events = []
    malformed = []
    for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        try:
            events.append((number, json.loads(line)))
        except json.JSONDecodeError as error:
            malformed.append({"line": number, "error": str(error)})
    return events, malformed


def command_reads(command):
    paths = []
    parents = []
    for segment in re.split(r"&&|\|\||;|\n", command):
        if not READ_TOOL.search(segment):
            continue
        found = MARKDOWN_PATH.findall(segment)
        paths.extend(found)
        parents.extend(PARENT_PATH.findall(segment))
    return list(dict.fromkeys(paths)), list(dict.fromkeys(parents))


def normalize_log(path, actions_path):
    events, malformed = read_events(path)
    actions = []
    usage = Counter()
    thread_id = None
    for line, event in events:
        kind = event.get("type")
        if kind == "thread.started":
            thread_id = event.get("thread_id")
        if kind == "turn.completed":
            usage.update(event.get("usage") or {})
            continue
        if kind != "item.completed":
            continue
        item = event.get("item") or {}
        item_type = item.get("type")
        if item_type == "command_execution":
            command = item.get("command") or ""
            reads, parents = command_reads(command)
            actions.append(
                {
                    "line": line,
                    "type": "command",
                    "command": command,
                    "exit_code": item.get("exit_code"),
                    "status": item.get("status"),
                    "markdown_reads": reads,
                    "parent_reads": parents,
                    "projectctl": "projectctl.py" in command,
                    "context": bool(re.search(r"projectctl\.py\s+(?:--root\s+\S+\s+)?context(?:\s|['\"]|$)", command)),
                    "confidence": "high" if not ("&&" in command or ";" in command) else "medium",
                }
            )
        elif item_type == "file_change":
            for change in item.get("changes") or []:
                actions.append(
                    {
                        "line": line,
                        "type": "file_change",
                        "path": change.get("path"),
                        "kind": change.get("kind"),
                        "status": item.get("status"),
                        "confidence": "high",
                    }
                )
    actions_path.parent.mkdir(parents=True, exist_ok=True)
    with actions_path.open("w") as handle:
        for action in actions:
            handle.write(json.dumps(action, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "source": str(path),
        "thread_id": thread_id,
        "events": len(events),
        "malformed": malformed,
        "actions": actions,
        "usage": dict(usage),
    }


def summarize(results):
    totals = Counter()
    usage = Counter()
    read_counts = Counter()
    sessions = []
    for name, result in results.items():
        commands = [action for action in result["actions"] if action["type"] == "command"]
        reads = [path for action in commands for path in action["markdown_reads"]]
        read_commands = sum(bool(action["markdown_reads"]) for action in commands)
        parents = [path for action in commands for path in action["parent_reads"]]
        source_reads = [
            path for path in reads
            if path.endswith("projectctl.py") or "projectctl.py" in path
        ]
        context_calls = sum(action["context"] for action in commands)
        changes = []
        versioned_reads = Counter()
        for action in result["actions"]:
            if action["type"] == "file_change" and action.get("path"):
                changes.append(str(action["path"]).lstrip("./"))
            elif action["type"] == "command":
                for path in action["markdown_reads"]:
                    clean = path.lstrip("./")
                    generation = sum(
                        changed == clean
                        or changed.endswith("/" + clean)
                        or clean.endswith("/" + changed)
                        for changed in changes
                    )
                    versioned_reads[(clean, generation)] += 1
        repeated = {}
        for (path, _generation), count in versioned_reads.items():
            if count > 1:
                repeated[path] = max(repeated.get(path, 0), count)
        boundary_commands = sum(
            1
            for action in commands
            if name.startswith("task")
            and re.search(r"projectctl\.py\s+task\s+(?:activate|baseline|audit|close)(?:\s|['\"]|$)", action["command"])
        )
        projectctl_source_commands = sum(
            1
            for action in commands
            if "projectctl.py" in action["command"]
            and READ_TOOL.search(action["command"])
            and re.search(r"(?:sed|cat|head|tail|less).*projectctl\.py", action["command"])
        )
        usage.update(result["usage"])
        read_counts.update(reads)
        totals.update(
            {
                "commands": len(commands),
                "file_changes": sum(action["type"] == "file_change" for action in result["actions"]),
                "markdown_reads": len(reads),
                "markdown_read_commands": read_commands,
                "parent_reads": len(parents),
                "context_calls": context_calls,
                "projectctl_source_reads": projectctl_source_commands + len(source_reads),
                "task_project_lifecycle_commands": boundary_commands,
                "malformed": len(result["malformed"]),
            }
        )
        sessions.append(
            {
                "name": name,
                "thread_id": result["thread_id"],
                "commands": len(commands),
                "markdown_reads": len(reads),
                "markdown_read_commands": read_commands,
                "repeated_reads": repeated,
                "parent_reads": parents,
                "context_calls": context_calls,
                "projectctl_source_reads": projectctl_source_commands + len(source_reads),
                "task_project_lifecycle_commands": boundary_commands,
                "usage": result["usage"],
                "malformed": result["malformed"],
            }
        )
    acceptance = {
        "markdown_read_commands_at_most_9": totals["markdown_read_commands"] <= 9,
        "no_parent_reads": totals["parent_reads"] == 0,
        "no_projectctl_source_reads": totals["projectctl_source_reads"] == 0,
        "no_repeated_markdown_reads": all(not session["repeated_reads"] for session in sessions),
        "no_task_project_lifecycle_commands": totals["task_project_lifecycle_commands"] == 0,
        "context_used_in_each_session": all(session["context_calls"] >= 1 for session in sessions),
        "no_malformed_jsonl": totals["malformed"] == 0,
    }
    return {
        "sessions": sessions,
        "totals": dict(totals),
        "usage": dict(usage),
        "markdown_reads_by_path": dict(read_counts),
        "acceptance": acceptance,
    }


def render_report(summary):
    lines = [
        "# Harness Experiment Action Report",
        "",
        "이 보고서는 Codex JSONL에 노출된 액션만 집계한다. 내부 AGENTS 주입과 shell 내부의 간접 파일 접근은 포함하지 않는다.",
        "",
        "## Acceptance",
        "",
    ]
    for name, passed in summary["acceptance"].items():
        lines.append("- " + ("PASS" if passed else "FAIL") + ": " + name)
    lines.extend(
        [
            "",
            "## Totals",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key, value in sorted(summary["totals"].items()):
        lines.append("| " + key + " | " + str(value) + " |")
    lines.extend(["", "## Sessions", ""])
    for session in summary["sessions"]:
        lines.extend(
            [
                "### " + session["name"],
                "",
                "- Thread: " + str(session["thread_id"]),
                "- Commands: " + str(session["commands"]),
                "- Markdown reads: " + str(session["markdown_reads"]),
                "- Markdown read commands: " + str(session["markdown_read_commands"]),
                "- Context calls: " + str(session["context_calls"]),
                "- Task Project-lifecycle commands: " + str(session["task_project_lifecycle_commands"]),
                "- Parent reads: " + json.dumps(session["parent_reads"], ensure_ascii=False),
                "- Repeated reads: " + json.dumps(session["repeated_reads"], ensure_ascii=False, sort_keys=True),
                "- Usage: " + json.dumps(session["usage"], ensure_ascii=False, sort_keys=True),
                "",
            ]
        )
    lines.extend(["## Markdown Reads by Path", ""])
    if summary["markdown_reads_by_path"]:
        for path, count in sorted(summary["markdown_reads_by_path"].items()):
            lines.append("- " + path + ": " + str(count))
    else:
        lines.append("- None observed")
    return "\n".join(lines) + "\n"


def analyze(paths, output):
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for path in paths:
        name = safe_name(path.stem)
        results[name] = normalize_log(path, output / "actions" / (name + ".jsonl"))
    summary = summarize(results)
    dump(output / "summary.json", summary)
    (output / "REPORT.md").write_text(render_report(summary))
    return summary


def copy_template(source, destination):
    ignore = shutil.ignore_patterns(".git", ".harness", "__pycache__", "*.pyc")
    shutil.copytree(source, destination, ignore=ignore)


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        digest.update(str(relative).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def execute_setup(commands, cwd, log):
    with log.open("a") as handle:
        for argv in commands:
            if not isinstance(argv, list) or not all(isinstance(part, str) for part in argv):
                raise Error("before commands must be argv arrays")
            handle.write("$ " + shlex_join(argv) + "\n")
            result = subprocess.run(argv, cwd=cwd, text=True, stdout=handle, stderr=subprocess.STDOUT)
            if result.returncode:
                raise Error("before command failed: " + shlex_join(argv))


def shlex_join(argv):
    import shlex
    return shlex.join(argv)


def git_value(cwd, *args):
    result = subprocess.run(("git", *args), cwd=cwd, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


def run_experiment(args):
    scenario_path = args.scenario.resolve()
    scenario = json.loads(scenario_path.read_text())
    sessions = scenario.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        raise Error("scenario must contain at least one session")
    output = args.output.resolve()
    if output.exists():
        raise Error("output already exists: " + str(output))
    output.mkdir(parents=True)
    workspace = output / "workspace"
    copy_template(args.template.resolve(), workspace)
    subprocess.run(("git", "init"), cwd=workspace, check=True, capture_output=True)
    subprocess.run(("git", "config", "user.email", "harness@example.invalid"), cwd=workspace, check=True)
    subprocess.run(("git", "config", "user.name", "Harness Experiment"), cwd=workspace, check=True)
    subprocess.run(("git", "add", "."), cwd=workspace, check=True)
    subprocess.run(("git", "commit", "-m", "experiment baseline"), cwd=workspace, check=True, capture_output=True)

    raw_dir = output / "sessions"
    raw_dir.mkdir()
    threads = {}
    records = []
    seen_names = set()
    for spec in sessions:
        name = safe_name(spec["name"])
        if name in seen_names:
            raise Error("duplicate session name: " + name)
        seen_names.add(name)
        relative = Path(spec.get("cwd", "."))
        if relative.is_absolute() or ".." in relative.parts:
            raise Error("invalid session cwd: " + str(relative))
        cwd = workspace / relative
        if args.dry_run:
            with (output / "setup.log").open("a") as handle:
                for argv in spec.get("before") or []:
                    handle.write("[dry-run] $ " + shlex_join(argv) + "\n")
        else:
            execute_setup(spec.get("before") or [], workspace, output / "setup.log")
        if not cwd.is_dir() and not args.dry_run:
            raise Error("session cwd does not exist: " + str(relative))
        prompt = spec.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise Error("session prompt is required: " + name)
        raw = raw_dir / (name + ".jsonl")
        stderr = raw_dir / (name + ".stderr")
        last = raw_dir / (name + ".last.md")
        resume = spec.get("resume")
        if resume:
            if resume not in threads and not args.dry_run:
                raise Error("unknown resume session: " + resume)
            command = [
                "codex", "exec", "resume", "--json",
                "--dangerously-bypass-approvals-and-sandbox",
                "-o", str(last),
            ]
            if args.model:
                command.extend(("-m", args.model))
            command.extend((threads.get(resume, "<session:" + resume + ">"), prompt))
        else:
            command = [
                "codex", "exec", "--json",
                "--dangerously-bypass-approvals-and-sandbox",
                "-C", str(cwd), "-o", str(last),
            ]
            if args.model:
                command.extend(("-m", args.model))
            command.append(prompt)
        started = datetime.now(timezone.utc).isoformat()
        if args.dry_run:
            raw.write_text("")
            stderr.write_text("")
            return_code = 0
        else:
            with raw.open("w") as stdout, stderr.open("w") as errors:
                return_code = subprocess.run(command, cwd=cwd, text=True, stdout=stdout, stderr=errors).returncode
        events, _ = read_events(raw)
        thread = next(
            (event.get("thread_id") for _, event in events if event.get("type") == "thread.started"),
            None,
        )
        if thread:
            threads[name] = thread
        records.append(
            {
                "name": name,
                "cwd": str(relative),
                "resume": resume,
                "thread_id": thread,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "command": command[:-1] + ["<prompt>"],
                "started": started,
                "finished": datetime.now(timezone.utc).isoformat(),
                "exit_code": return_code,
            }
        )
        dump(
            output / "manifest.json",
            {
                "scenario": scenario.get("name"),
                "template": str(args.template.resolve()),
                "template_commit": git_value(args.template.resolve(), "rev-parse", "HEAD"),
                "template_dirty": bool(git_value(args.template.resolve(), "status", "--porcelain", "--", ".")),
                "template_snapshot_sha256": tree_digest(args.template.resolve()),
                "scenario_sha256": hashlib.sha256(scenario_path.read_bytes()).hexdigest(),
                "codex_version": subprocess.run(("codex", "--version"), text=True, capture_output=True).stdout.strip(),
                "model": args.model,
                "full_access": True,
                "sessions": records,
            },
        )
        if return_code and not spec.get("continue_on_error", False):
            raise Error("Codex session failed: " + name)
    if args.dry_run:
        (output / "REPORT.md").write_text(
            "# Harness Experiment Dry Run\n\nNo Codex session was executed; acceptance was not evaluated.\n"
        )
    else:
        analyze(sorted(raw_dir.glob("*.jsonl")), output)
    return output


def parser():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    analyze_parser = commands.add_parser("analyze")
    analyze_parser.add_argument("logs", nargs="+", type=Path)
    analyze_parser.add_argument("--output", required=True, type=Path)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--template", required=True, type=Path)
    run_parser.add_argument("--scenario", required=True, type=Path)
    run_parser.add_argument("--output", required=True, type=Path)
    run_parser.add_argument("--model")
    run_parser.add_argument("--dry-run", action="store_true")
    return parser


def main():
    try:
        args = parser().parse_args()
        if args.command == "analyze":
            analyze(args.logs, args.output)
            print(args.output / "REPORT.md")
        else:
            print(run_experiment(args))
        return 0
    except (Error, OSError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
