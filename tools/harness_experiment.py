#!/usr/bin/env python3
"""Run controlled Codex sessions and summarize observable actions."""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


class Error(RuntimeError):
    pass


READ_COMMANDS = {"cat", "sed", "head", "tail", "less", "rg", "find"}
READ_TOOL = re.compile(r"(?<![\w-])(cat|sed|head|tail|less|rg|find)(?![\w-])")


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


def shell_segments(command, depth=0):
    """Split a shell string into token lists without treating quoted separators as commands."""
    if depth > 4:
        return []
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    segments = []
    current = []
    for token in tokens:
        if token in (";", "&&", "||", "|", "\n"):
            if current:
                segments.append(current)
                current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    expanded = []
    for segment in segments:
        if segment and Path(segment[0]).name in ("bash", "sh", "zsh"):
            command_index = next(
                (index for index, token in enumerate(segment[1:], 1) if token == "-c" or (token.startswith("-") and "c" in token[1:])),
                None,
            )
            if command_index is not None and command_index + 1 < len(segment):
                expanded.extend(shell_segments(segment[command_index + 1], depth + 1))
                continue
        expanded.append(segment)
    return expanded


def markdown_path(token):
    """Return whether a shell argument names a Markdown path rather than an option."""
    return bool(re.fullmatch(r"(?:\.{0,2}/)?[A-Za-z0-9_./-]+\.md", token))


def rg_paths(arguments):
    """Return explicit rg search paths while excluding patterns and glob option values."""
    if "--files" in arguments:
        return []
    option_values = {"-g", "--glob", "--iglob", "-t", "--type", "-T", "--type-not", "-e", "--regexp", "-f", "--file"}
    positional = []
    skip = False
    options_done = False
    for token in arguments:
        if skip:
            skip = False
            continue
        if not options_done and token == "--":
            options_done = True
            continue
        if not options_done and token in option_values:
            skip = True
            continue
        if not options_done and any(token.startswith(option + "=") for option in option_values if option.startswith("--")):
            continue
        if not options_done and token.startswith("-"):
            continue
        positional.append(token)
    return positional[1:] if positional else []


def command_reads(command):
    """Return Markdown content reads and parent traversal paths from a shell command."""
    paths = []
    parents = []
    for tokens in shell_segments(command):
        index = next(
            (position for position, token in enumerate(tokens) if Path(token).name in READ_COMMANDS),
            None,
        )
        if index is None:
            continue
        name = Path(tokens[index]).name
        arguments = tokens[index + 1:]
        if name == "rg":
            candidates = rg_paths(arguments)
        elif name == "find":
            candidates = []
        else:
            candidates = [token for token in arguments if not token.startswith("-")]
        paths.extend(token for token in candidates if markdown_path(token))
        if name == "find":
            traversal = []
            for token in arguments:
                if token.startswith("-") or token in ("(", ")", "!"):
                    break
                traversal.append(token)
        elif name == "rg":
            traversal = candidates
        else:
            traversal = candidates
        parents.extend(token for token in traversal if token == ".." or token.startswith("../"))
    return list(dict.fromkeys(paths)), list(dict.fromkeys(parents))


def normalize_log(path, actions_path):
    events, malformed = read_events(path)
    actions = []
    usage = Counter()
    item_types = Counter()
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
        item_types[str(item_type or "unknown")] += 1
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
        "item_types": dict(item_types),
    }


def summarize(results):
    totals = Counter()
    usage = Counter()
    read_counts = Counter()
    item_types = Counter()
    sessions = []
    for name, result in results.items():
        commands = [action for action in result["actions"] if action["type"] == "command"]
        reads = [path for action in commands for path in action["markdown_reads"]]
        read_commands = sum(bool(action["markdown_reads"]) for action in commands)
        parents = [path for action in commands for path in action["parent_reads"]]
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
            and re.search(
                r"projectctl\.py\s+(?:--root\s+\S+\s+)?task\s+(?:activate|baseline|audit|close)(?:\s|['\"]|$)",
                action["command"],
            )
        )
        projectctl_source_commands = sum(
            1
            for action in commands
            if "projectctl.py" in action["command"]
            and READ_TOOL.search(action["command"])
            and re.search(r"(?:sed|cat|head|tail|less).*projectctl\.py", action["command"])
        )
        usage.update(result["usage"])
        item_types.update(result["item_types"])
        read_counts.update(reads)
        totals.update(
            {
                "commands": len(commands),
                "failed_commands": sum(
                    action.get("exit_code") not in (None, 0) for action in commands
                ),
                "file_changes": sum(action["type"] == "file_change" for action in result["actions"]),
                "markdown_reads": len(reads),
                "markdown_read_commands": read_commands,
                "parent_reads": len(parents),
                "context_calls": context_calls,
                "projectctl_source_reads": projectctl_source_commands,
                "task_project_lifecycle_commands": boundary_commands,
                "malformed": len(result["malformed"]),
            }
        )
        sessions.append(
            {
                "name": name,
                "thread_id": result["thread_id"],
                "commands": len(commands),
                "failed_commands": sum(
                    action.get("exit_code") not in (None, 0) for action in commands
                ),
                "markdown_reads": len(reads),
                "markdown_read_commands": read_commands,
                "unchanged_repeated_reads": repeated,
                "parent_reads": parents,
                "context_calls": context_calls,
                "projectctl_source_reads": projectctl_source_commands,
                "task_project_lifecycle_commands": boundary_commands,
                "usage": result["usage"],
                "malformed": result["malformed"],
            }
        )
    acceptance = {
        "no_parent_reads": totals["parent_reads"] == 0,
        "no_projectctl_source_reads": totals["projectctl_source_reads"] == 0,
        "no_unchanged_repeated_markdown_reads": all(
            not session["unchanged_repeated_reads"] for session in sessions
        ),
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
        "normalized_schema_coverage": {"item_types": dict(sorted(item_types.items()))},
    }


EXPECTED_HOOK_EVENTS = (
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PreCompact", "PostCompact", "SubagentStart", "SubagentStop", "Stop",
)


def summarize_observability(paths):
    """Summarize metadata-only Hook/context logs keyed by experiment session name."""
    sessions = []
    totals = Counter()
    all_hooks = Counter()
    for name, path in sorted(paths.items()):
        events, malformed = read_events(path)
        kinds = Counter()
        hooks = Counter()
        documents = Counter()
        skills = Counter()
        lifecycle = Counter()
        seen_documents = set()
        seen_lifecycle = set()
        for line, event in events:
            kinds[str(event.get("event") or "unknown")] += 1
            if event.get("hook_event"):
                hooks[str(event["hook_event"])] += 1
            for document in event.get("documents") or []:
                if isinstance(document, str):
                    identity = event.get("tool_use_id") or "event-" + str(line)
                    key = (identity, document)
                    if key not in seen_documents:
                        documents[document] += 1
                        seen_documents.add(key)
            if event.get("skill"):
                skills[str(event["skill"])] += 1
            if event.get("projectctl_action"):
                action = str(event["projectctl_action"])
                identity = event.get("tool_use_id") or "event-" + str(line)
                key = (identity, action)
                if key not in seen_lifecycle:
                    lifecycle[action] += 1
                    seen_lifecycle.add(key)
        all_hooks.update(hooks)
        totals.update({"events": len(events), "malformed": len(malformed)})
        sessions.append(
            {
                "name": name,
                "events": len(events),
                "malformed": malformed,
                "event_types": dict(sorted(kinds.items())),
                "hook_events": dict(sorted(hooks.items())),
                "document_visits": dict(sorted(documents.items())),
                "skills": dict(sorted(skills.items())),
                "lifecycle_actions": dict(sorted(lifecycle.items())),
            }
        )
    return {
        "sessions": sessions,
        "totals": dict(totals),
        "coverage": {
            "expected_hook_events": list(EXPECTED_HOOK_EVENTS),
            "observed_hook_events": [name for name in EXPECTED_HOOK_EVENTS if all_hooks[name]],
            "missing_hook_events": [name for name in EXPECTED_HOOK_EVENTS if not all_hooks[name]],
        },
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
                "- Failed commands: " + str(session["failed_commands"]),
                "- Markdown reads: " + str(session["markdown_reads"]),
                "- Markdown read commands: " + str(session["markdown_read_commands"]),
                "- Context calls: " + str(session["context_calls"]),
                "- Task Project-lifecycle commands: " + str(session["task_project_lifecycle_commands"]),
                "- Parent reads: " + json.dumps(session["parent_reads"], ensure_ascii=False),
                "- Unchanged repeated reads: " + json.dumps(
                    session["unchanged_repeated_reads"], ensure_ascii=False, sort_keys=True
                ),
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
    observability = summary.get("observability")
    if observability:
        lines.extend(["", "## Hook and Context Observability", ""])
        lines.append(
            "- Observed Hook events: "
            + (", ".join(observability["coverage"]["observed_hook_events"]) or "None")
        )
        lines.append(
            "- Missing Hook events: "
            + (", ".join(observability["coverage"]["missing_hook_events"]) or "None")
        )
        lines.append("")
        for session in observability["sessions"]:
            lines.extend(
                [
                    "### " + session["name"] + " metadata",
                    "",
                    "- Events: " + str(session["events"]),
                    "- Hook events: " + json.dumps(session["hook_events"], sort_keys=True),
                    "- Document visits: " + json.dumps(session["document_visits"], sort_keys=True),
                    "- Skills: " + json.dumps(session["skills"], sort_keys=True),
                    "- Lifecycle actions: " + json.dumps(session["lifecycle_actions"], sort_keys=True),
                    "",
                ]
            )
    return "\n".join(lines) + "\n"


def analyze(paths, output, observability_paths=None):
    """Normalize Codex JSONL and optional metadata-only observability logs."""
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for path in paths:
        name = safe_name(path.stem)
        results[name] = normalize_log(path, output / "actions" / (name + ".jsonl"))
    summary = summarize(results)
    if observability_paths:
        summary["observability"] = summarize_observability(observability_paths)
        observed_sessions = summary["observability"]["sessions"]
        summary["acceptance"]["observability_no_malformed_jsonl"] = all(
            not session["malformed"] for session in observed_sessions
        )
        summary["acceptance"]["session_prompt_stop_hooks_observed"] = all(
            all(session["hook_events"].get(event, 0) >= 1 for event in ("SessionStart", "UserPromptSubmit", "Stop"))
            for session in observed_sessions
        ) and len(observed_sessions) == len(results)
    dump(output / "summary.json", summary)
    (output / "REPORT.md").write_text(render_report(summary))
    return summary


def nested_value(value, path):
    """Return an integer from a nested summary path, defaulting missing values to zero."""
    current = value
    for key in path.split("."):
        current = current.get(key, {}) if isinstance(current, dict) else {}
    return current if isinstance(current, int) else 0


def compare_summaries(before, after):
    """Return explicit metric and acceptance deltas between two experiment summaries."""
    metric_paths = (
        "totals.commands",
        "totals.failed_commands",
        "totals.file_changes",
        "totals.markdown_reads",
        "totals.markdown_read_commands",
        "totals.parent_reads",
        "totals.context_calls",
        "totals.projectctl_source_reads",
        "totals.task_project_lifecycle_commands",
        "usage.input_tokens",
        "usage.output_tokens",
    )
    metrics = {}
    for path in metric_paths:
        old = nested_value(before, path)
        new = nested_value(after, path)
        metrics[path] = {"before": old, "after": new, "delta": new - old}
    acceptance_keys = sorted(set(before.get("acceptance", {})) | set(after.get("acceptance", {})))
    acceptance = {
        key: {
            "before": before.get("acceptance", {}).get(key),
            "after": after.get("acceptance", {}).get(key),
        }
        for key in acceptance_keys
    }
    return {"metrics": metrics, "acceptance": acceptance}


def render_comparison(comparison):
    """Render a compact Markdown comparison report."""
    lines = [
        "# Harness Experiment Comparison",
        "",
        "## Metrics",
        "",
        "| Metric | Before | After | Delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, values in comparison["metrics"].items():
        lines.append(
            "| " + name + " | " + str(values["before"]) + " | "
            + str(values["after"]) + " | " + str(values["delta"]) + " |"
        )
    lines.extend(["", "## Acceptance", "", "| Check | Before | After |", "| --- | --- | --- |"])
    for name, values in comparison["acceptance"].items():
        lines.append("| " + name + " | " + str(values["before"]) + " | " + str(values["after"]) + " |")
    return "\n".join(lines) + "\n"


def compare_files(before_path, after_path, output):
    """Compare two summary.json files and write JSON plus Markdown results."""
    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())
    comparison = compare_summaries(before, after)
    output.mkdir(parents=True, exist_ok=True)
    dump(output / "comparison.json", comparison)
    (output / "REPORT.md").write_text(render_comparison(comparison))
    return comparison


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


def verify_hook_bundle(template):
    """Verify the local metadata-only Hook bundle before bypassing interactive trust."""
    template = template.resolve()
    config = template / ".codex/hooks.json"
    script = template / ".codex/hooks/observe.py"
    if not config.is_file() or not script.is_file():
        raise Error("template Hook bundle is incomplete")
    payload = json.loads(config.read_text())
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict) or set(hooks) != set(EXPECTED_HOOK_EVENTS):
        raise Error("template Hook events do not match the approved observer bundle")
    expected_command = 'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/observe.py"'
    handler_count = 0
    for event, groups in hooks.items():
        if not isinstance(groups, list) or not groups:
            raise Error("invalid Hook groups for " + event)
        for group in groups:
            handlers = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(handlers, list) or not handlers:
                raise Error("invalid Hook handlers for " + event)
            for handler in handlers:
                handler_count += 1
                if (
                    not isinstance(handler, dict)
                    or handler.get("type") != "command"
                    or handler.get("command") != expected_command
                    or not isinstance(handler.get("timeout"), int)
                    or not 1 <= handler["timeout"] <= 10
                ):
                    raise Error("Hook trust bypass refused for " + event)
    resolved = script.resolve()
    try:
        resolved.relative_to(template)
    except ValueError as error:
        raise Error("Hook script resolves outside template") from error
    return {
        "config": str(config.relative_to(template)),
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "script": str(script.relative_to(template)),
        "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "handlers": handler_count,
        "events": sorted(hooks),
    }


def session_role(spec, relative):
    """Return an explicit scenario role or infer Project/Task from the session cwd."""
    role = spec.get("role")
    if role not in (None, "project", "task"):
        raise Error("session role must be project or task")
    if role:
        return role
    return "task" if relative.parts and relative.parts[0] == "tasks" else "project"


def run_experiment(args):
    scenario_path = args.scenario.resolve()
    scenario = json.loads(scenario_path.read_text())
    sessions = scenario.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        raise Error("scenario must contain at least one session")
    template = args.template.resolve()
    hook_bundle = verify_hook_bundle(template)
    output = args.output.resolve()
    if output.exists():
        raise Error("output already exists: " + str(output))
    output.mkdir(parents=True)
    workspace = output / "workspace"
    copy_template(template, workspace)
    subprocess.run(("git", "init"), cwd=workspace, check=True, capture_output=True)
    subprocess.run(("git", "config", "user.email", "harness@example.invalid"), cwd=workspace, check=True)
    subprocess.run(("git", "config", "user.name", "Harness Experiment"), cwd=workspace, check=True)
    subprocess.run(("git", "add", "."), cwd=workspace, check=True)
    subprocess.run(("git", "commit", "-m", "experiment baseline"), cwd=workspace, check=True, capture_output=True)

    raw_dir = output / "sessions"
    raw_dir.mkdir()
    observation_dir = output / "observability"
    observation_dir.mkdir()
    observability_paths = {}
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
        role = session_role(spec, relative)
        run_id = safe_name(str(scenario.get("name") or "experiment")) + "-" + name
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
                "--dangerously-bypass-hook-trust",
                "-o", str(last),
            ]
            if args.model:
                command.extend(("-m", args.model))
            command.extend((threads.get(resume, "<session:" + resume + ">"), prompt))
        else:
            command = [
                "codex", "exec", "--json",
                "--dangerously-bypass-approvals-and-sandbox",
                "--dangerously-bypass-hook-trust",
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
            environment = os.environ.copy()
            environment["HARNESS_RUN_ID"] = run_id
            environment["HARNESS_SESSION_ROLE"] = role
            if role == "task" and len(relative.parts) >= 2 and relative.parts[0] == "tasks":
                environment["HARNESS_TASK_NAME"] = relative.parts[1]
            else:
                environment.pop("HARNESS_TASK_NAME", None)
            with raw.open("w") as stdout, stderr.open("w") as errors:
                return_code = subprocess.run(
                    command,
                    cwd=cwd,
                    env=environment,
                    text=True,
                    stdout=stdout,
                    stderr=errors,
                ).returncode
        metadata_raw = git_value(workspace, "rev-parse", "--git-dir")
        metadata = Path(metadata_raw) if metadata_raw else workspace / ".git"
        if not metadata.is_absolute():
            metadata = workspace / metadata
        observed = metadata / "harness/observability" / run_id / "events.jsonl"
        copied = observation_dir / (name + ".jsonl")
        if not args.dry_run and observed.is_file():
            shutil.copy2(observed, copied)
        else:
            copied.write_text("")
        observability_paths[name] = copied
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
                "run_id": run_id,
                "role": role,
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
                "template": str(template),
                "template_commit": git_value(template, "rev-parse", "HEAD"),
                "template_dirty": bool(git_value(template, "status", "--porcelain", "--", ".")),
                "template_snapshot_sha256": tree_digest(template),
                "scenario_sha256": hashlib.sha256(scenario_path.read_bytes()).hexdigest(),
                "codex_version": subprocess.run(("codex", "--version"), text=True, capture_output=True).stdout.strip(),
                "model": args.model,
                "full_access": True,
                "hook_trust": "bypassed-after-local-verification",
                "hook_bundle": hook_bundle,
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
        analyze(sorted(raw_dir.glob("*.jsonl")), output, observability_paths)
    return output


def parser():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    analyze_parser = commands.add_parser("analyze")
    analyze_parser.add_argument("logs", nargs="+", type=Path)
    analyze_parser.add_argument("--output", required=True, type=Path)
    compare_parser = commands.add_parser("compare")
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("after", type=Path)
    compare_parser.add_argument("--output", required=True, type=Path)
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
        elif args.command == "compare":
            compare_files(args.before, args.after, args.output)
            print(args.output / "REPORT.md")
        else:
            print(run_experiment(args))
        return 0
    except (Error, OSError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
