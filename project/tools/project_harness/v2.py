"""Stage A JSON authority, migration, worktree, and Promotion operations."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .context import report_condition
from .documents import atomic_write_text, markdown_table, scalar, section
from .errors import HarnessError
from .lifecycle import report_handoff
from .repository import canonical_state_lock, contained_path, git_dir, run_command, safe_relative


SCHEMA_VERSION = 2
TASK_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RECORD_TYPES = {"project", "task", "handoff", "decision", "result", "promotion"}


def canonical_mutation(function: Callable[..., Any]) -> Callable[..., Any]:
    """Run one v2 mutation under the Project-local canonical writer lock."""
    @wraps(function)
    def locked(root: Path, *args: Any, **kwargs: Any) -> Any:
        with canonical_state_lock(root):
            return function(root, *args, **kwargs)

    return locked


def utc_now() -> str:
    """Return one stable UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_bytes(payload: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes."""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def content_digest(payload: dict[str, Any]) -> str:
    """Return a SHA-256 digest excluding the record's digest field."""
    value = dict(payload)
    value.pop("content_digest", None)
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def seal_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Return ``payload`` with the v2 schema marker and content digest."""
    value = dict(payload)
    value.setdefault("schema_version", SCHEMA_VERSION)
    value["content_digest"] = content_digest(value)
    return value


def validate_record(payload: dict[str, Any], expected_type: str | None = None) -> None:
    """Raise when one canonical record is malformed or stale."""
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise HarnessError("unsupported v2 schema version")
    record_type = payload.get("record_type")
    if record_type not in RECORD_TYPES:
        raise HarnessError("invalid v2 record type")
    if expected_type and record_type != expected_type:
        raise HarnessError("expected " + expected_type + " record")
    if not isinstance(payload.get("id"), str) or not payload["id"]:
        raise HarnessError("v2 record requires a stable id")
    if payload.get("content_digest") != content_digest(payload):
        raise HarnessError("v2 record digest mismatch: " + payload["id"])


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object or raise a user-facing error."""
    if not path.is_file():
        raise HarnessError("missing JSON record: " + str(path))
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise HarnessError("JSON record must be an object: " + str(path))
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write one stable JSON object."""
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def harness_root(root: Path) -> Path:
    """Return the tracked v2 state root."""
    return root / ".harness"


def install_path(root: Path) -> Path:
    """Return the Project-local installation marker."""
    return harness_root(root) / "install.json"


def authority_mode(root: Path) -> str:
    """Return legacy, uninitialized, or v2 authority mode."""
    path = install_path(root)
    if not path.is_file():
        return "legacy"
    return str(read_json(path).get("authority", "uninitialized"))


def require_v2(root: Path) -> None:
    """Require v2 authority for one state-changing v2 operation."""
    if authority_mode(root) != "v2":
        raise HarnessError("Project authority is not v2")


def _new_record(record_type: str, record_id: str, **values: Any) -> dict[str, Any]:
    """Build one revision-one canonical record."""
    return seal_record(
        {
            "record_type": record_type,
            "id": record_id,
            "revision": 1,
            "created_at": utc_now(),
            **values,
        }
    )


def _replace_record(path: Path, payload: dict[str, Any], **updates: Any) -> dict[str, Any]:
    """Replace the exact revision the caller read, then reseal the record."""
    validate_record(payload)
    current = read_json(path)
    validate_record(current, str(payload["record_type"]))
    if (
        current.get("revision") != payload.get("revision")
        or current.get("content_digest") != payload.get("content_digest")
    ):
        raise HarnessError("canonical record changed concurrently: " + str(payload["id"]))
    value = dict(payload)
    value.update(updates)
    value["revision"] = int(payload.get("revision", 1)) + 1
    value["updated_at"] = utc_now()
    value = seal_record(value)
    write_json(path, value)
    return value


def _bump_generation(root: Path) -> None:
    """Record one post-switch v2 mutation for rollback safety."""
    path = install_path(root)
    if not path.is_file():
        return
    payload = read_json(path)
    if payload.get("authority") != "v2":
        return
    payload["generation"] = int(payload.get("generation", 0)) + 1
    payload["updated_at"] = utc_now()
    write_json(path, payload)


@canonical_mutation
def initialize_v2(
    root: Path,
    project_id: str,
    goal: str,
    scope: Sequence[str],
    canonical_roots: Sequence[str],
    harness_version: str = "development",
) -> dict[str, Any]:
    """Initialize one new Project directly with v2 JSON authority."""
    existing_install: dict[str, Any] = {}
    if install_path(root).is_file():
        existing_install = read_json(install_path(root))
        if existing_install.get("authority", "uninitialized") != "uninitialized":
            raise HarnessError(".harness is already initialized")
    existing_entries = (
        [path for path in harness_root(root).iterdir() if path.name != "install.json"]
        if harness_root(root).is_dir()
        else []
    )
    if existing_entries:
        raise HarnessError(".harness contains state outside install metadata")
    if not TASK_ID.fullmatch(project_id):
        raise HarnessError("project id must use lowercase kebab-case")
    install = {
        **existing_install,
        "schema_version": SCHEMA_VERSION,
        "harness_version": harness_version,
        "authority": "v2",
        "generation": 0,
        "installed_at": utc_now(),
    }
    project = _new_record(
        "project",
        project_id,
        goal=goal,
        scope=list(scope),
        current_objective=goal,
        invariants=[],
        canonical_roots=list(canonical_roots),
    )
    write_json(install_path(root), install)
    write_json(harness_root(root) / "project.json", project)
    return project


def render_project(root: Path) -> str:
    """Render the v2 Project record as a human-readable Markdown view."""
    payload = read_json(harness_root(root) / "project.json")
    validate_record(payload, "project")
    lines = [
        "# Project " + payload["id"],
        "",
        "> Generated view. Authority: `.harness/project.json`",
        "> Source digest: `" + payload["content_digest"] + "`",
        "> Save this view inside the Project, edit Goal/Scope/Current Objective, then use `project amend --from-markdown` to preview it.",
        "",
        "## Goal",
        "",
        str(payload.get("goal", "")),
        "",
        "## Scope",
        "",
    ]
    lines.extend("- " + str(item) for item in payload.get("scope", []))
    lines.extend(["", "## Current Objective", "", str(payload.get("current_objective", "")), ""])
    lines.extend(["## Canonical Roots", ""])
    lines.extend("- `" + str(item) + "`" for item in payload.get("canonical_roots", []))
    amendment = payload.get("last_amendment")
    if amendment:
        lines.extend(
            [
                "",
                "## Last Amendment",
                "",
                "- Revision: " + str(payload["revision"]),
                "- Actor: " + str(amendment.get("actor")),
                "- Reason: " + str(amendment.get("reason")),
                "- Approval reference: " + str(amendment.get("approval_ref") or "direct user change"),
                "- Recorded at: " + str(amendment.get("recorded_at")),
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _proposal_list(text: str, heading: str) -> list[str]:
    """Read a simple Markdown bullet section from an amendment proposal."""
    values: list[str] = []
    for line in section(text, heading).splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        value = stripped[2:].strip()
        if value == "None":
            continue
        if value.startswith("`") and value.endswith("`"):
            value = value[1:-1]
        if value:
            values.append(value)
    return values


def project_updates_from_markdown(root: Path, proposal: str) -> dict[str, Any]:
    """Parse editable Project fields from one Project-contained Markdown proposal."""
    path = contained_path(root, proposal, must_exist=True)
    text = path.read_text(encoding="utf-8")
    updates: dict[str, Any] = {
        "goal": section(text, "Goal"),
        "scope": _proposal_list(text, "Scope"),
    }
    try:
        updates["current_objective"] = section(text, "Current Objective")
    except HarnessError:
        pass
    return updates


def task_updates_from_markdown(root: Path, proposal: str) -> dict[str, Any]:
    """Parse the editable core contract from one Task Markdown proposal."""
    path = contained_path(root, proposal, must_exist=True)
    text = path.read_text(encoding="utf-8")
    commands: list[list[str]] = []
    for raw in _proposal_list(text, "Validation Commands"):
        try:
            command = shlex.split(raw)
        except ValueError as error:
            raise HarnessError("invalid validation command in amendment proposal") from error
        if not command:
            raise HarnessError("validation command cannot be empty")
        commands.append(command)
    return {
        "goal": section(text, "Goal"),
        "scope": section(text, "Scope"),
        "outputs": _proposal_list(text, "Outputs"),
        "dependencies": _proposal_list(text, "Dependencies"),
        "owned_write_paths": _proposal_list(text, "Owned Write Paths"),
        "acceptance": _proposal_list(text, "Acceptance"),
        "validation_commands": commands,
        "context_refs": _proposal_list(text, "Context References"),
    }


def _amendment_metadata(reason: str, actor: str, approval_ref: str | None) -> dict[str, Any]:
    """Build explicit, non-authenticating provenance for one contract amendment."""
    if not reason.strip():
        raise HarnessError("amendment reason is required")
    if actor not in {"user", "agent"}:
        raise HarnessError("amendment actor must be user or agent")
    if actor == "agent" and not (approval_ref or "").strip():
        raise HarnessError("agent amendment requires a user approval reference")
    return {
        "reason": reason.strip(),
        "actor": actor,
        "approval_ref": (approval_ref or "").strip() or None,
        "recorded_at": utc_now(),
    }


def _amendment_preview(
    payload: dict[str, Any], updates: dict[str, Any], metadata: dict[str, Any]
) -> dict[str, Any]:
    """Return a stable before/after packet for changed canonical fields."""
    changes = {
        key: {"before": payload.get(key), "after": value}
        for key, value in updates.items()
        if payload.get(key) != value
    }
    if not changes:
        raise HarnessError("amendment does not change the canonical record")
    return {
        "record_type": payload["record_type"],
        "record_id": payload["id"],
        "expected_revision": payload["revision"],
        "expected_digest": payload["content_digest"],
        "changes": changes,
        "reason": metadata["reason"],
        "actor": metadata["actor"],
        "approval_ref": metadata["approval_ref"],
        "applied": False,
    }


@canonical_mutation
def amend_project(
    root: Path,
    updates: dict[str, Any],
    expected_revision: int | None,
    reason: str,
    actor: str,
    approval_ref: str | None,
    apply_change: bool,
) -> dict[str, Any]:
    """Preview or apply one controlled Project contract amendment."""
    require_v2(root)
    path = harness_root(root) / "project.json"
    payload = read_json(path)
    validate_record(payload, "project")
    allowed = {"goal", "scope", "current_objective", "invariants", "canonical_roots"}
    unknown = sorted(set(updates) - allowed)
    if unknown:
        raise HarnessError("unsupported Project amendment fields: " + ", ".join(unknown))
    normalized = dict(updates)
    for field in ("goal", "current_objective"):
        if field in normalized and (not isinstance(normalized[field], str) or not normalized[field].strip()):
            raise HarnessError("Project " + field + " cannot be empty")
    for field in ("scope", "invariants", "canonical_roots"):
        if field in normalized:
            if not isinstance(normalized[field], list) or not all(
                isinstance(item, str) and item.strip() for item in normalized[field]
            ):
                raise HarnessError("Project " + field + " must be a non-empty string list")
    if "scope" in normalized and not normalized["scope"]:
        raise HarnessError("Project scope cannot be empty")
    metadata = _amendment_metadata(reason, actor, approval_ref)
    preview = _amendment_preview(payload, normalized, metadata)
    if not apply_change:
        return preview
    if expected_revision is None:
        raise HarnessError("--expected-revision is required with --apply")
    if payload["revision"] != expected_revision:
        raise HarnessError(
            "stale Project revision: expected " + str(expected_revision)
            + ", current " + str(payload["revision"])
        )
    changed = _replace_record(path, payload, **normalized, last_amendment=metadata)
    _bump_generation(root)
    return {
        **preview,
        "applied": True,
        "new_revision": changed["revision"],
        "new_digest": changed["content_digest"],
    }


def _canonical_record_paths(root: Path) -> list[tuple[Path, str]]:
    """Return canonical v2 record paths and their expected record types."""
    base = harness_root(root)
    records: list[tuple[Path, str]] = [(base / "project.json", "project")]
    records.extend((path, "task") for path in sorted((base / "tasks").glob("*/task.json")))
    records.extend((path, "handoff") for path in sorted((base / "tasks").glob("*/handoff.json")))
    records.extend((path, "decision") for path in sorted((base / "decisions").glob("*.json")))
    records.extend((path, "result") for path in sorted((base / "results").glob("*.json")))
    records.extend((path, "promotion") for path in sorted((base / "promotions").glob("*.json")))
    legacy_history = base / "legacy-history.json"
    if legacy_history.is_file():
        records.append((legacy_history, "result"))
    return records


def _reference_exists(root: Path, reference: str) -> bool:
    """Return whether one supported internal context reference exists."""
    kind, separator, identifier = reference.partition(":")
    if not separator or not TASK_ID.fullmatch(identifier):
        return False
    paths = {
        "task": harness_root(root) / "tasks" / identifier / "task.json",
        "decision": harness_root(root) / "decisions" / (identifier + ".json"),
        "result": harness_root(root) / "results" / (identifier + ".json"),
    }
    return kind in paths and paths[kind].is_file()


def check_v2_authority(root: Path) -> list[str]:
    """Return schema, digest, reference, artifact, and index errors for v2 state."""
    errors: list[str] = []
    base = harness_root(root)
    try:
        install = read_json(install_path(root))
        if install.get("schema_version") != SCHEMA_VERSION:
            errors.append(".harness/install.json: unsupported schema version")
        if install.get("authority") != "v2":
            errors.append(".harness/install.json: authority must be v2")
        generation = install.get("generation")
        if not isinstance(generation, int) or generation < 0:
            errors.append(".harness/install.json: generation must be a non-negative integer")
        if not isinstance(install.get("harness_version"), str):
            errors.append(".harness/install.json: harness_version must be a string")
    except (HarnessError, OSError, json.JSONDecodeError) as error:
        errors.append(".harness/install.json: " + str(error))

    records: dict[Path, dict[str, Any]] = {}
    for path, expected_type in _canonical_record_paths(root):
        relative = path.relative_to(root).as_posix()
        try:
            payload = read_json(path)
            validate_record(payload, expected_type)
            records[path] = payload
        except (HarnessError, OSError, json.JSONDecodeError) as error:
            errors.append(relative + ": " + str(error))

    for directory in sorted((base / "tasks").glob("*")):
        if directory.is_dir() and not (directory / "task.json").is_file():
            errors.append(str(directory.relative_to(root)) + ": missing task.json")

    project_path = base / "project.json"
    if project_path not in records:
        errors.append(".harness/project.json: missing or invalid canonical Project record")
    else:
        project = records[project_path]
        if not isinstance(project.get("goal"), str) or not project["goal"].strip():
            errors.append(".harness/project.json: goal must be a non-empty string")
        if not isinstance(project.get("current_objective"), str) or not project["current_objective"].strip():
            errors.append(".harness/project.json: current_objective must be a non-empty string")
        for field in ("scope", "invariants", "canonical_roots"):
            if not isinstance(project.get(field), list) or not all(
                isinstance(item, str) and item.strip() for item in project.get(field, [])
            ):
                errors.append(".harness/project.json: " + field + " must be a string list")
        if not project.get("scope"):
            errors.append(".harness/project.json: scope cannot be empty")

    task_records = {
        path.parent.name: payload
        for path, payload in records.items()
        if path.name == "task.json" and path.parent.parent.name == "tasks"
    }
    decision_records = {
        payload["id"]: payload
        for path, payload in records.items()
        if path.parent.name == "decisions"
    }
    result_records = {
        payload["id"]: payload
        for path, payload in records.items()
        if path.parent.name == "results" and path.name != "index.json"
    }
    for task_id, task in task_records.items():
        if task.get("id") != task_id:
            errors.append(".harness/tasks/" + task_id + "/task.json: id does not match path")
        state = task.get("state")
        for field in ("goal", "scope"):
            if not isinstance(task.get(field), str) or not task[field].strip():
                errors.append(".harness/tasks/" + task_id + "/task.json: " + field + " must be a non-empty string")
        legacy_imported = isinstance(state, dict) and "legacy_state_extra" in state
        for field in (
            "outputs", "acceptance", "dependencies", "context_refs",
            "owned_write_paths", "validation_commands",
        ):
            allowed = (list, str) if legacy_imported and field in {"outputs", "acceptance"} else (list,)
            if not isinstance(task.get(field), allowed):
                errors.append(".harness/tasks/" + task_id + "/task.json: " + field + " must be a list")
        for dependency in task.get("dependencies", []):
            if dependency not in task_records:
                errors.append("Task " + task_id + " has missing dependency: " + str(dependency))
        for reference in task.get("context_refs", []):
            if not _reference_exists(root, str(reference)):
                errors.append("Task " + task_id + " has invalid context reference: " + str(reference))
        if not isinstance(state, dict) or state.get("task_status") not in {
            "todo", "doing", "ready", "active", "review", "needs_decision",
            "blocked", "completed", "stopped",
        }:
            errors.append("Task " + task_id + " has invalid state")
        elif state.get("decision_id") and state["decision_id"] not in decision_records:
            errors.append("Task " + task_id + " has missing pending Decision")

    for path, payload in records.items():
        amendment = payload.get("last_amendment")
        if amendment is None:
            continue
        relative = str(path.relative_to(root))
        if not isinstance(amendment, dict):
            errors.append(relative + ": last_amendment must be an object")
            continue
        if amendment.get("actor") not in {"user", "agent"}:
            errors.append(relative + ": last_amendment actor is invalid")
        if not isinstance(amendment.get("reason"), str) or not amendment["reason"].strip():
            errors.append(relative + ": last_amendment reason is required")
        if amendment.get("actor") == "agent" and not amendment.get("approval_ref"):
            errors.append(relative + ": agent amendment requires approval_ref")

    for path, handoff in (
        (path, payload) for path, payload in records.items() if path.name == "handoff.json"
    ):
        task_id = path.parent.name
        if handoff.get("task_id") != task_id or task_id not in task_records:
            errors.append(str(path.relative_to(root)) + ": handoff Task reference is invalid")

    for path, decision in (
        (path, payload) for path, payload in records.items() if path.parent.name == "decisions"
    ):
        decision_id = str(decision["id"])
        if path.name != decision_id + ".json":
            errors.append(str(path.relative_to(root)) + ": Decision id does not match path")
        if decision.get("task_id") not in task_records:
            errors.append("Decision " + decision_id + " references a missing Task")

    for path, promotion in (
        (path, payload) for path, payload in records.items() if path.parent.name == "promotions"
    ):
        if promotion.get("id") + ".json" != path.name:
            errors.append(str(path.relative_to(root)) + ": Promotion id does not match path")
        if promotion.get("task_id") not in task_records:
            errors.append("Promotion " + str(promotion.get("id")) + " references a missing Task")

    for path, result in (
        (path, payload)
        for path, payload in records.items()
        if path.parent.name == "results" and path.name != "index.json"
    ):
        result_id = str(result["id"])
        if path.name != result_id + ".json":
            errors.append(str(path.relative_to(root)) + ": Result id does not match path")
        for artifact in result.get("artifacts", []):
            if not isinstance(artifact, dict) or not artifact.get("path"):
                errors.append("Result " + result_id + " has malformed artifact provenance")
                continue
            try:
                source = contained_path(root, str(artifact["path"]), must_exist=True)
                data = source.read_bytes()
                if artifact.get("sha256") != hashlib.sha256(data).hexdigest():
                    errors.append("Result " + result_id + " artifact digest mismatch: " + str(artifact["path"]))
                if artifact.get("bytes") != len(data):
                    errors.append("Result " + result_id + " artifact size mismatch: " + str(artifact["path"]))
            except (HarnessError, OSError) as error:
                errors.append("Result " + result_id + " artifact invalid: " + str(error))
        if result.get("supersedes") and result["supersedes"] not in result_records:
            errors.append("Result " + result_id + " supersedes a missing Result")

    index_path = base / "results/index.json"
    index = records.get(index_path)
    if result_records and index is None:
        errors.append(".harness/results/index.json: missing Result index")
    elif index is not None:
        entries = index.get("entries")
        if not isinstance(entries, list):
            errors.append(".harness/results/index.json: entries must be a list")
        else:
            indexed: dict[str, dict[str, Any]] = {}
            for entry in entries:
                if not isinstance(entry, dict) or not entry.get("id"):
                    errors.append(".harness/results/index.json: malformed entry")
                    continue
                if entry["id"] in indexed:
                    errors.append(".harness/results/index.json: duplicate id " + str(entry["id"]))
                indexed[str(entry["id"])] = entry
            if set(indexed) != set(result_records):
                errors.append(".harness/results/index.json: records and index differ")
            for result_id, result in result_records.items():
                entry = indexed.get(result_id)
                if entry and entry.get("digest") != result.get("content_digest"):
                    errors.append(".harness/results/index.json: stale digest for " + result_id)
    return errors


def _legacy_task(
    root: Path,
    name: str,
    project_status: str | None,
    project_state_extra: Sequence[str],
) -> dict[str, Any]:
    """Normalize one current-format Task directory."""
    task = root / "tasks" / name
    contract_text = (task / "TASK.md").read_text()
    status_text = (task / "STATUS.md").read_text()
    report_state = report_condition(task)
    handoff = report_handoff(task) if report_state in ("completed", "stopped") else None
    return {
        "id": name,
        "project_status": project_status,
        "project_state_extra": list(project_state_extra),
        "task_status": scalar(status_text, "Status"),
        "final_goal": scalar(status_text, "Final Goal"),
        "current_work": scalar(status_text, "Current Work"),
        "work_plan": markdown_table(section(status_text, "Work Plan")),
        "contract": {
            key.lower().replace(" ", "_"): section(contract_text, key)
            for key in ("Scope", "Inputs", "Data", "Workflow", "Outputs", "Completion Criteria")
        },
        "handoff": handoff,
    }


def legacy_semantic_model(root: Path) -> dict[str, Any]:
    """Return the normalized meaning of the supported legacy Project format."""
    project = (root / "PROJECT.md").read_text()
    state = (root / "STATE.md").read_text()
    state_entries: dict[str, dict[str, Any]] = {}
    for row in markdown_table(section(state, "Current Tasks")):
        if len(row) < 2:
            raise HarnessError("invalid legacy STATE Current Tasks row")
        name, project_status, *extra = row
        if not TASK_ID.fullmatch(name):
            raise HarnessError("invalid legacy STATE Task name: " + name)
        if project_status not in {"todo", "doing", "completed"}:
            raise HarnessError("invalid legacy Project Task status: " + project_status)
        if name in state_entries:
            raise HarnessError("duplicate legacy STATE Task: " + name)
        state_entries[name] = {"project_status": project_status, "extra": extra}
    tasks = []
    for path in sorted((root / "tasks").iterdir()):
        if path.name == "_template" or not path.is_dir():
            continue
        if all((path / name).is_file() for name in ("TASK.md", "STATUS.md", "REPORT.md")):
            entry = state_entries.get(path.name, {"project_status": None, "extra": []})
            tasks.append(
                _legacy_task(
                    root,
                    path.name,
                    entry["project_status"],
                    entry["extra"],
                )
            )
    histories = []
    for path in sorted((root / "docs/history").glob("*.md")):
        histories.append({"path": path.relative_to(root).as_posix(), "text": path.read_text()})
    return {
        "project": {
            "goal": section(project, "Goal"),
            "scope": section(project, "Scope"),
            "current_goal": section(state, "Current Goal"),
        },
        "tasks": tasks,
        "histories": histories,
    }


def legacy_source_inventory(root: Path) -> dict[str, Any]:
    """Inventory legacy Task sources independently of conversion semantics."""
    state = (root / "STATE.md").read_text()
    state_task_ids = sorted(
        row[0] for row in markdown_table(section(state, "Current Tasks")) if row
    )
    task_directories = []
    partial_tasks: dict[str, list[str]] = {}
    invalid_task_directories = []
    for path in sorted((root / "tasks").iterdir()):
        if path.name == "_template" or not path.is_dir():
            continue
        task_directories.append(path.name)
        if not TASK_ID.fullmatch(path.name):
            invalid_task_directories.append(path.name)
        missing = [
            name for name in ("TASK.md", "STATUS.md", "REPORT.md") if not (path / name).is_file()
        ]
        if missing:
            partial_tasks[path.name] = missing
    missing_task_directories = sorted(set(state_task_ids) - set(task_directories))
    return {
        "state_task_ids": state_task_ids,
        "task_directories": task_directories,
        "partial_tasks": partial_tasks,
        "invalid_task_directories": invalid_task_directories,
        "missing_task_directories": missing_task_directories,
        "history_paths": [
            path.relative_to(root).as_posix()
            for path in sorted((root / "docs/history").glob("*.md"))
        ],
        "supported": not partial_tasks and not invalid_task_directories and not missing_task_directories,
    }


def _require_supported_legacy_inventory(root: Path) -> dict[str, Any]:
    """Fail before conversion when legacy Task sources would be omitted."""
    inventory = legacy_source_inventory(root)
    if inventory["partial_tasks"]:
        details = ", ".join(
            task_id + " missing " + "/".join(files)
            for task_id, files in inventory["partial_tasks"].items()
        )
        raise HarnessError("legacy inventory contains partial Tasks: " + details)
    if inventory["invalid_task_directories"]:
        raise HarnessError(
            "legacy inventory contains invalid Task directory names: "
            + ", ".join(inventory["invalid_task_directories"])
        )
    if inventory["missing_task_directories"]:
        raise HarnessError(
            "legacy STATE references missing Task directories: "
            + ", ".join(inventory["missing_task_directories"])
        )
    return inventory


def legacy_records(root: Path) -> dict[str, dict[str, Any]]:
    """Convert the supported legacy meaning into candidate v2 records."""
    model = legacy_semantic_model(root)
    project = _new_record(
        "project",
        root.name.lower().replace("_", "-"),
        goal=model["project"]["goal"],
        scope=[model["project"]["scope"]],
        current_objective=model["project"]["current_goal"],
        invariants=[],
        canonical_roots=["src", "tools", "data", "docs"],
    )
    records: dict[str, dict[str, Any]] = {"project.json": project}
    for task in model["tasks"]:
        task_record = _new_record(
            "task",
            task["id"],
            objective_id="legacy-current-goal",
            goal=task["final_goal"],
            scope=task["contract"]["scope"],
            inputs=task["contract"]["inputs"],
            data=task["contract"]["data"],
            workflow=task["contract"]["workflow"],
            outputs=task["contract"]["outputs"],
            acceptance=task["contract"]["completion_criteria"],
            dependencies=[],
            context_refs=[],
            owned_write_paths=[],
            validation_commands=[],
            state={
                "project_status": task["project_status"],
                "legacy_state_extra": task["project_state_extra"],
                "task_status": task["task_status"],
                "current_work": task["current_work"],
                "work_plan": task["work_plan"],
            },
        )
        records["tasks/" + task["id"] + "/task.json"] = task_record
        if task["handoff"] is not None:
            records["tasks/" + task["id"] + "/handoff.json"] = _new_record(
                "handoff",
                "handoff-" + task["id"],
                task_id=task["id"],
                **task["handoff"],
            )
    records["legacy-history.json"] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "result",
        "id": "legacy-history",
        "revision": 1,
        "created_at": utc_now(),
        "kind": "legacy-history",
        "items": model["histories"],
    }
    records["legacy-history.json"] = seal_record(records["legacy-history.json"])
    return records


def semantic_model_from_records(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Rebuild the comparable legacy meaning from candidate v2 records."""
    project = records["project.json"]
    tasks = []
    for path, record in sorted(records.items()):
        if not path.endswith("/task.json"):
            continue
        handoff = records.get(path.rsplit("/", 1)[0] + "/handoff.json")
        state = record["state"]
        tasks.append(
            {
                "id": record["id"],
                "project_status": state.get("project_status"),
                "project_state_extra": state.get("legacy_state_extra", []),
                "task_status": state.get("task_status"),
                "final_goal": record["goal"],
                "current_work": state.get("current_work"),
                "work_plan": state.get("work_plan", []),
                "contract": {
                    "scope": record["scope"],
                    "inputs": record["inputs"],
                    "data": record["data"],
                    "workflow": record["workflow"],
                    "outputs": record["outputs"],
                    "completion_criteria": record["acceptance"],
                },
                "handoff": (
                    {key: value for key, value in handoff.items() if key not in {
                        "schema_version", "record_type", "id", "revision", "created_at",
                        "content_digest", "task_id",
                    }}
                    if handoff else None
                ),
            }
        )
    return {
        "project": {
            "goal": project["goal"],
            "scope": project["scope"][0],
            "current_goal": project["current_objective"],
        },
        "tasks": tasks,
        "histories": records["legacy-history.json"]["items"],
    }


def migration_inspect(root: Path) -> dict[str, Any]:
    """Return a read-only inventory of the supported legacy Project."""
    model = legacy_semantic_model(root)
    inventory = legacy_source_inventory(root)
    return {
        "authority": authority_mode(root),
        "tasks": len(model["tasks"]),
        "handoffs": sum(item["handoff"] is not None for item in model["tasks"]),
        "histories": len(model["histories"]),
        "source_inventory": inventory,
        "supported": inventory["supported"],
    }


def migration_plan(root: Path) -> dict[str, Any]:
    """Return conversion paths and semantic parity without writing files."""
    inventory = _require_supported_legacy_inventory(root)
    records = legacy_records(root)
    legacy = legacy_semantic_model(root)
    converted = semantic_model_from_records(records)
    return {
        "records": sorted(records),
        "semantic_parity": legacy == converted,
        "legacy_digest": hashlib.sha256(canonical_bytes(legacy)).hexdigest(),
        "converted_digest": hashlib.sha256(canonical_bytes(converted)).hexdigest(),
        "source_inventory": inventory,
    }


@canonical_mutation
def migration_apply(root: Path, migration_id: str) -> Path:
    """Write side-by-side candidate records without switching authority."""
    _require_supported_legacy_inventory(root)
    if not TASK_ID.fullmatch(migration_id):
        raise HarnessError("migration id must use lowercase kebab-case")
    destination = harness_root(root) / "migrations" / migration_id / "candidate"
    if destination.exists():
        raise HarnessError("migration candidate already exists")
    records = legacy_records(root)
    for relative, payload in records.items():
        write_json(destination / relative, payload)
    plan = migration_plan(root)
    write_json(destination.parent / "plan.json", plan)
    return destination


def _candidate_records(root: Path, migration_id: str) -> dict[str, dict[str, Any]]:
    """Read all candidate JSON records for one migration."""
    candidate = harness_root(root) / "migrations" / migration_id / "candidate"
    if not candidate.is_dir():
        raise HarnessError("migration candidate does not exist")
    records = {}
    for path in sorted(candidate.rglob("*.json")):
        records[path.relative_to(candidate).as_posix()] = read_json(path)
    return records


def migration_verify(root: Path, migration_id: str) -> dict[str, Any]:
    """Compare current legacy meaning with one stored candidate."""
    _require_supported_legacy_inventory(root)
    legacy = legacy_semantic_model(root)
    records = _candidate_records(root, migration_id)
    for relative, payload in records.items():
        expected = (
            "project" if relative == "project.json"
            else "task" if relative.endswith("/task.json")
            else "handoff" if relative.endswith("/handoff.json")
            else "result"
        )
        validate_record(payload, expected)
    converted = semantic_model_from_records(records)
    return {
        "semantic_parity": legacy == converted,
        "legacy_digest": hashlib.sha256(canonical_bytes(legacy)).hexdigest(),
        "converted_digest": hashlib.sha256(canonical_bytes(converted)).hexdigest(),
    }


@canonical_mutation
def migration_switch(root: Path, migration_id: str, harness_version: str) -> dict[str, Any]:
    """Activate a verified candidate as v2 authority without deleting legacy files."""
    if authority_mode(root) == "v2":
        raise HarnessError("Project authority is already v2")
    verification = migration_verify(root, migration_id)
    if not verification["semantic_parity"]:
        raise HarnessError("semantic parity failed")
    if run_command(root, ("git", "status", "--porcelain", "--", ".", ":(exclude).harness")):
        raise HarnessError("Git worktree must be clean outside .harness")
    candidate = harness_root(root) / "migrations" / migration_id / "candidate"
    backup = git_dir(root) / "harness/migrations" / migration_id
    backup.mkdir(parents=True, exist_ok=True)
    write_json(
        backup / "switch.json",
        {
            "migration_id": migration_id,
            "legacy_commit": run_command(root, ("git", "rev-parse", "HEAD")),
            "switched_at": utc_now(),
        },
    )
    for relative in ("project.json", "legacy-history.json"):
        shutil.copy2(candidate / relative, harness_root(root) / relative)
    source_tasks = candidate / "tasks"
    if source_tasks.is_dir():
        shutil.copytree(source_tasks, harness_root(root) / "tasks", dirs_exist_ok=True)
    install = {
        "schema_version": SCHEMA_VERSION,
        "harness_version": harness_version,
        "authority": "v2",
        "migration_id": migration_id,
        "generation": 0,
        "switched_at": utc_now(),
    }
    write_json(install_path(root), install)
    return install


@canonical_mutation
def migration_rollback(root: Path, migration_id: str) -> dict[str, Any]:
    """Return to legacy authority only before any post-switch v2 mutation."""
    install = read_json(install_path(root))
    if install.get("authority") != "v2" or install.get("migration_id") != migration_id:
        raise HarnessError("migration is not the active authority")
    if int(install.get("generation", 0)) != 0:
        raise HarnessError("v2-only mutations require forward repair")
    install["authority"] = "legacy"
    install["rolled_back_at"] = utc_now()
    write_json(install_path(root), install)
    return install


def _task_input_records(root: Path, inputs: Sequence[str]) -> list[dict[str, Any]]:
    """Build bounded, content-addressed Task input records."""
    input_records = []
    total_input_bytes = 0
    for raw in inputs:
        relative = safe_relative(raw)
        source = contained_path(root, raw, must_exist=True)
        data = source.read_bytes()
        if len(data) > 131072:
            raise HarnessError("Task input exceeds default file limit: " + raw)
        total_input_bytes += len(data)
        if total_input_bytes > 262144:
            raise HarnessError("Task inputs exceed default total limit")
        if b"\x00" in data:
            raise HarnessError("binary Task input is unsupported: " + raw)
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise HarnessError("Task input must be UTF-8: " + raw) from error
        input_records.append(
            {
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return input_records


def _validate_task_contract(
    root: Path, task_id: str, values: dict[str, Any]
) -> dict[str, Any]:
    """Normalize and validate mutable Task contract fields."""
    normalized = dict(values)
    for field in ("goal", "scope"):
        if field in normalized and (not isinstance(normalized[field], str) or not normalized[field].strip()):
            raise HarnessError("Task " + field + " cannot be empty")
    for field in (
        "outputs", "acceptance", "dependencies", "context_refs",
        "owned_write_paths",
    ):
        if field in normalized and not isinstance(normalized[field], list):
            raise HarnessError("Task " + field + " must be a list")
        if field in normalized and not all(
            isinstance(item, str) and item for item in normalized[field]
        ):
            raise HarnessError("Task " + field + " must contain non-empty strings")
    for field in ("validation_commands", "inputs"):
        if field in normalized and not isinstance(normalized[field], list):
            raise HarnessError("Task " + field + " must be a list")
    for dependency in normalized.get("dependencies", []):
        if dependency == task_id:
            raise HarnessError("Task cannot depend on itself")
        if not task_record_path(root, dependency).is_file():
            raise HarnessError("Task dependency does not exist: " + str(dependency))
    for reference in normalized.get("context_refs", []):
        if not _reference_exists(root, str(reference)):
            raise HarnessError("invalid or missing context reference: " + str(reference))
    for raw in normalized.get("owned_write_paths", []):
        safe_relative(str(raw))
    for command in normalized.get("validation_commands", []):
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) and item for item in command
        ):
            raise HarnessError("validation commands must be non-empty argv lists")
    execution = normalized.get("execution", ...)
    if execution is not ... and execution is not None and not isinstance(execution, dict):
        raise HarnessError("Task execution contract must be an object or null")
    if isinstance(execution, dict):
        owned = list(normalized.get("owned_write_paths", []))
        if ".harness-agent-handoff.json" not in owned:
            owned.append(".harness-agent-handoff.json")
        normalized["owned_write_paths"] = owned
    return normalized


@canonical_mutation
def create_v2_task(
    root: Path,
    task_id: str,
    goal: str,
    scope: str,
    outputs: Sequence[str],
    acceptance: Sequence[str],
    owned_write_paths: Sequence[str],
    validation_commands: Sequence[Sequence[str]],
    execution: dict[str, Any] | None = None,
    context_refs: Sequence[str] = (),
    dependencies: Sequence[str] = (),
    inputs: Sequence[str] = (),
) -> dict[str, Any]:
    """Create one ready v2 Task contract."""
    require_v2(root)
    if not TASK_ID.fullmatch(task_id):
        raise HarnessError("Task id must use lowercase kebab-case")
    path = harness_root(root) / "tasks" / task_id / "task.json"
    if path.exists():
        raise HarnessError("Task already exists")
    values = _validate_task_contract(
        root,
        task_id,
        {
            "goal": goal,
            "scope": scope,
            "outputs": list(outputs),
            "acceptance": list(acceptance),
            "dependencies": list(dependencies),
            "context_refs": list(context_refs),
            "owned_write_paths": list(owned_write_paths),
            "validation_commands": [list(item) for item in validation_commands],
            "execution": execution,
        },
    )
    input_records = _task_input_records(root, inputs)
    record = _new_record(
        "task",
        task_id,
        objective_id="current",
        goal=values["goal"],
        scope=values["scope"],
        inputs=input_records,
        outputs=values["outputs"],
        acceptance=values["acceptance"],
        dependencies=values["dependencies"],
        context_refs=values["context_refs"],
        owned_write_paths=values["owned_write_paths"],
        validation_commands=values["validation_commands"],
        execution=values["execution"],
        state={"task_status": "ready", "base_commit": None},
    )
    write_json(path, record)
    _bump_generation(root)
    return record


def task_record_path(root: Path, task_id: str) -> Path:
    """Return one canonical v2 Task record path."""
    if not TASK_ID.fullmatch(task_id):
        raise HarnessError("Task id must use lowercase kebab-case")
    return harness_root(root) / "tasks" / task_id / "task.json"


def read_task(root: Path, task_id: str) -> dict[str, Any]:
    """Read and validate one v2 Task record."""
    payload = read_json(task_record_path(root, task_id))
    validate_record(payload, "task")
    return payload


def _merge_execution_contract(
    current: dict[str, Any] | None, patch: dict[str, Any]
) -> dict[str, Any]:
    """Merge a sparse CLI execution patch without discarding unrelated policy."""
    merged = dict(current or {})
    for key, value in patch.items():
        if key in {"limits", "fallback", "agent"}:
            nested = dict(merged.get(key) or {})
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


@canonical_mutation
def amend_task(
    root: Path,
    task_id: str,
    updates: dict[str, Any],
    expected_revision: int | None,
    reason: str,
    actor: str,
    approval_ref: str | None,
    apply_change: bool,
    execution_patch: dict[str, Any] | None = None,
    clear_execution: bool = False,
    input_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Preview or apply one controlled, paused-state Task contract amendment."""
    require_v2(root)
    path = task_record_path(root, task_id)
    payload = read_task(root, task_id)
    state = str(payload.get("state", {}).get("task_status"))
    if state not in {"ready", "needs_decision", "blocked"}:
        raise HarnessError(
            "Task contract can only be amended while ready, needs_decision, or blocked; current state: "
            + state
        )
    allowed = {
        "goal", "scope", "outputs", "acceptance", "dependencies", "context_refs",
        "owned_write_paths", "validation_commands",
    }
    unknown = sorted(set(updates) - allowed)
    if unknown:
        raise HarnessError("unsupported Task amendment fields: " + ", ".join(unknown))
    normalized = dict(updates)
    if input_paths is not None:
        normalized["inputs"] = _task_input_records(root, input_paths)
    if clear_execution and execution_patch:
        raise HarnessError("cannot clear and update the execution contract together")
    if clear_execution:
        normalized["execution"] = None
    elif execution_patch:
        normalized["execution"] = _merge_execution_contract(
            payload.get("execution"), execution_patch
        )
        normalized.setdefault(
            "owned_write_paths", list(payload.get("owned_write_paths", []))
        )
    normalized = _validate_task_contract(root, task_id, normalized)
    metadata = _amendment_metadata(reason, actor, approval_ref)
    preview = _amendment_preview(payload, normalized, metadata)
    if not apply_change:
        return preview
    if expected_revision is None:
        raise HarnessError("--expected-revision is required with --apply")
    if payload["revision"] != expected_revision:
        raise HarnessError(
            "stale Task revision: expected " + str(expected_revision)
            + ", current " + str(payload["revision"])
        )
    changed = _replace_record(path, payload, **normalized, last_amendment=metadata)
    _bump_generation(root)
    return {
        **preview,
        "applied": True,
        "new_revision": changed["revision"],
        "new_digest": changed["content_digest"],
    }


def _append_list(lines: list[str], heading: str, values: Sequence[Any], code: bool = False) -> None:
    """Append one readable Markdown list, including an explicit empty state."""
    lines.extend(["", "## " + heading, ""])
    if values:
        for value in values:
            text = str(value)
            lines.append("- `" + text + "`" if code else "- " + text)
    else:
        lines.append("- None")


def _append_execution_contract(lines: list[str], contract: dict[str, Any]) -> None:
    """Append a concise human View of one requested/effective Codex contract."""
    limits = contract.get("limits") or {}
    lines.extend(
        [
            "",
            "## Codex Execution Contract",
            "",
            "- Model: " + str(contract.get("model") or "CLI default"),
            "- Reasoning effort: " + str(contract.get("reasoning_effort") or "default"),
            "- Reasoning fallback: " + ", ".join(contract.get("reasoning_fallback", [])),
            "- Sandbox: " + str(contract.get("sandbox") or "default"),
            "- Approval policy: " + str(contract.get("approval_policy") or "default"),
            "- Web / network: " + str(contract.get("web_mode") or "default")
            + " / " + str(contract.get("network_access", False)).lower(),
            "- Declared tools: " + ", ".join(contract.get("allowed_tools", [])),
            "- MCP: " + (", ".join(contract.get("allowed_mcp", [])) or "None"),
            "- Skills: " + (", ".join(contract.get("allowed_skills", [])) or "None"),
            "- Hard wall-time: " + str(limits.get("seconds") or "default") + " seconds",
            "- Post-run token ceiling: " + str(limits.get("tokens") or "not set"),
            "",
            "> Shell/apply_patch declarations are Agent policy and audit expectations, not an OS-level allowlist. "
            "The token ceiling is evaluated from completed usage; wall-time is the hard execution stop.",
        ]
    )


def render_task(root: Path, task_id: str) -> str:
    """Render one Task contract and current state as Markdown."""
    task = read_task(root, task_id)
    lines = [
        "# Task " + task_id,
        "",
        "> Generated view. Source digest: `" + task["content_digest"] + "`",
        "> Save this view inside the Project, edit contract sections, then use `task amend --from-markdown` to preview it.",
        "",
        "## Goal",
        "",
        str(task["goal"]),
        "",
        "## Scope",
        "",
        str(task["scope"]),
        "",
        "## State",
        "",
        "- Status: " + str(task["state"]["task_status"]),
        "- Base commit: " + str(task["state"].get("base_commit") or "not started"),
        "",
        "## Inputs",
        "",
    ]
    inputs = task.get("inputs", [])
    if inputs:
        for item in inputs:
            path = str(item["path"])
            size = str(item["bytes"])
            digest = str(item["sha256"])
            lines.append(f"- `{path}` ({size} bytes, SHA-256 `{digest}`)")
    else:
        lines.append("- None")
    _append_list(lines, "Outputs", task.get("outputs", []), code=True)
    _append_list(lines, "Dependencies", task.get("dependencies", []), code=True)
    _append_list(lines, "Owned Write Paths", task.get("owned_write_paths", []), code=True)
    _append_list(lines, "Acceptance", task.get("acceptance", []))
    _append_list(lines, "Validation Commands", [" ".join(item) for item in task.get("validation_commands", [])], code=True)
    _append_list(lines, "Context References", task.get("context_refs", []), code=True)
    if task.get("execution") is not None:
        _append_execution_contract(lines, task["execution"])
    amendment = task.get("last_amendment")
    if amendment:
        lines.extend(
            [
                "",
                "## Last Amendment",
                "",
                "- Revision: " + str(task["revision"]),
                "- Actor: " + str(amendment.get("actor")),
                "- Reason: " + str(amendment.get("reason")),
                "- Approval reference: " + str(amendment.get("approval_ref") or "direct user change"),
                "- Recorded at: " + str(amendment.get("recorded_at")),
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _runtime_root(root: Path) -> Path:
    """Return Git-local Stage A runtime storage."""
    return git_dir(root) / "harness/v2"


def _workspace_root(root: Path) -> Path:
    """Return a repository-specific sibling worktree root."""
    identity = hashlib.sha256(str(git_dir(root).resolve()).encode()).hexdigest()[:8]
    return root.parent / ("." + root.name + "-harness-worktrees-" + identity)


def _workspace_metadata_path(root: Path, task_id: str) -> Path:
    return _runtime_root(root) / "workspaces" / (task_id + ".json")


def read_workspace(root: Path, task_id: str) -> dict[str, Any]:
    """Read local workspace metadata for one Task."""
    return read_json(_workspace_metadata_path(root, task_id))


@canonical_mutation
def start_v2_task(
    root: Path,
    task_id: str,
    allow_dirty_harness: bool = False,
) -> dict[str, Any]:
    """Create one isolated Task branch and worktree."""
    require_v2(root)
    task = read_task(root, task_id)
    if task["state"]["task_status"] != "ready":
        raise HarnessError("Task must be ready")
    if not allow_dirty_harness and run_command(
        root, ("git", "status", "--porcelain", "--", ".harness")
    ):
        raise HarnessError("canonical .harness records must be committed before Task start")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    branch = "harness/task/" + task_id + "/" + run_id
    workspace = _workspace_root(root) / "tasks" / task_id / run_id
    workspace.parent.mkdir(parents=True, exist_ok=True)
    base = run_command(root, ("git", "rev-parse", "HEAD"))
    run_command(root, ("git", "worktree", "add", "-b", branch, str(workspace), base))
    metadata = {
        "task_id": task_id,
        "run_id": run_id,
        "branch": branch,
        "workspace": str(workspace),
        "base_commit": base,
        "state": "active",
        "created_at": utc_now(),
    }
    write_json(_workspace_metadata_path(root, task_id), metadata)
    state = dict(task["state"])
    state.update({"task_status": "active", "base_commit": base, "run_id": run_id})
    _replace_record(task_record_path(root, task_id), task, state=state)
    _bump_generation(root)
    return metadata


def _path_owned(path: str, owned: Iterable[str]) -> bool:
    candidate = Path(path)
    return any(candidate == Path(raw) or Path(raw) in candidate.parents for raw in owned)


def _changed_paths(workspace: Path, base: str) -> list[str]:
    changed = run_command(workspace, ("git", "diff", "--name-only", base, "--")).splitlines()
    changed += run_command(workspace, ("git", "ls-files", "--others", "--exclude-standard")).splitlines()
    return sorted(set(item for item in changed if item))


def run_validations(
    root: Path,
    workspace: Path,
    commands: Sequence[Sequence[str]],
    evidence_key: str,
    timeout_seconds: int = 300,
) -> list[dict[str, Any]]:
    """Run bounded validation argv and preserve full Git-local evidence."""
    results = []
    evidence_root = _runtime_root(root) / "validation" / safe_relative(evidence_key)
    evidence_root.mkdir(parents=True, exist_ok=True)
    for index, command in enumerate(commands, 1):
        if not command:
            raise HarnessError("validation command cannot be empty")
        started = time.monotonic()
        timed_out = False
        try:
            process = subprocess.run(
                command,
                cwd=workspace,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )
            exit_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
        except subprocess.TimeoutExpired as error:
            timed_out = True
            exit_code = 124
            stdout = str(error.stdout or "")
            stderr = str(error.stderr or "") + "\nvalidation timed out"
        duration_ms = round((time.monotonic() - started) * 1000)
        log = (
            "argv: " + json.dumps(list(command), ensure_ascii=False) + "\n"
            + "exit_code: " + str(exit_code) + "\n"
            + "timed_out: " + str(timed_out).lower() + "\n\n"
            + "[stdout]\n" + stdout + "\n[stderr]\n" + stderr
        )
        log_path = evidence_root / (str(index).zfill(2) + ".log")
        atomic_write_text(log_path, log)
        results.append(
            {
                "argv": list(command),
                "exit_code": exit_code,
                "timed_out": timed_out,
                "duration_ms": duration_ms,
                "stdout": stdout[-4000:],
                "stderr": stderr[-4000:],
                "log_path": log_path.relative_to(git_dir(root)).as_posix(),
                "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
            }
        )
    return results


def validation_digest(results: Sequence[dict[str, Any]]) -> str:
    """Digest validation identity and full-log evidence without elapsed-time noise."""
    subjects = [
        {
            "argv": item["argv"],
            "exit_code": item["exit_code"],
            "timed_out": item.get("timed_out", False),
            "log_sha256": item.get("log_sha256"),
        }
        for item in results
    ]
    return hashlib.sha256(canonical_bytes(subjects)).hexdigest()


def submit_handoff(root: Path, task_id: str, source: Path) -> dict[str, Any]:
    """Validate actual Task changes and import one typed handoff."""
    require_v2(root)
    task = read_task(root, task_id)
    workspace = read_workspace(root, task_id)
    if workspace.get("state") != "active":
        raise HarnessError("Task workspace is not active")
    worktree = Path(workspace["workspace"])
    source_path = safe_relative(source.as_posix())
    handoff_source = contained_path(worktree, source_path.as_posix(), must_exist=True)
    payload = read_json(handoff_source)
    if payload.get("status") != "completed":
        raise HarnessError("Stage A handoff must be completed")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise HarnessError("handoff candidates must be a list")
    changed = _changed_paths(worktree, workspace["base_commit"])
    violations = [item for item in changed if not _path_owned(item, task["owned_write_paths"])]
    if violations:
        raise HarnessError("Task changed paths outside ownership: " + ", ".join(violations))
    for candidate in candidates:
        if not isinstance(candidate, dict) or not candidate.get("id"):
            raise HarnessError("invalid Promotion candidate")
        source_path = safe_relative(str(candidate.get("source", "")))
        contained_path(worktree, source_path.as_posix(), must_exist=True)
        safe_relative(str(candidate.get("target", "")))
    validation = run_validations(
        root,
        worktree,
        task.get("validation_commands", []),
        "tasks/" + task_id + "/" + str(workspace["run_id"]),
    )
    handoff = _new_record(
        "handoff",
        "handoff-" + task_id,
        task_id=task_id,
        run_id=workspace["run_id"],
        status="completed",
        summary=str(payload.get("summary", "")),
        findings=list(payload.get("findings", [])),
        candidates=candidates,
        limitations=list(payload.get("limitations", [])),
        changed_paths=changed,
        validation=validation,
    )
    with canonical_state_lock(root):
        current_task = read_task(root, task_id)
        if current_task.get("content_digest") != task.get("content_digest"):
            raise HarnessError("Task changed while handoff validation was running")
        write_json(harness_root(root) / "tasks" / task_id / "handoff.json", handoff)
        state = dict(current_task["state"])
        state["task_status"] = "review"
        _replace_record(task_record_path(root, task_id), current_task, state=state)
        workspace["state"] = "review"
        write_json(_workspace_metadata_path(root, task_id), workspace)
        _bump_generation(root)
    return handoff


def render_handoff_review(root: Path, task_id: str) -> str:
    """Render one handoff, validation, and candidate selection view."""
    handoff = read_json(harness_root(root) / "tasks" / task_id / "handoff.json")
    validate_record(handoff, "handoff")
    lines = [
        "# Task Review " + task_id,
        "",
        "## Summary",
        "",
        handoff["summary"],
    ]
    _append_list(lines, "Acceptance to Review", read_task(root, task_id).get("acceptance", []))
    _append_list(lines, "Findings", handoff.get("findings", []))
    _append_list(lines, "Limitations", handoff.get("limitations", []))
    lines.extend(["", "## Validation", ""])
    for item in handoff["validation"]:
        line = "- `" + " ".join(item["argv"]) + "`: exit " + str(item["exit_code"])
        if item.get("timed_out"):
            line += " (timed out)"
        if item.get("log_path"):
            line += " — full log `" + str(item["log_path"]) + "`"
        lines.append(line)
    lines.extend(["", "## Promotion Candidates", ""])
    for item in handoff["candidates"]:
        lines.append(
            "- **" + item["id"] + "**: `" + item["source"] + "` → `" + item["target"] + "` — " + str(item.get("rationale", ""))
        )
    lines.extend(["", "## Changed Paths", ""])
    lines.extend("- `" + item + "`" for item in handoff["changed_paths"] or ["None"])
    agent_run = handoff.get("agent_run")
    if isinstance(agent_run, dict):
        _append_execution_contract(lines, agent_run.get("effective_contract", {}))
        fallbacks = agent_run.get("fallbacks", [])
        lines.extend(["", "### Capability Fallbacks", ""])
        if fallbacks:
            lines.extend("- `" + json.dumps(item, ensure_ascii=False, sort_keys=True) + "`" for item in fallbacks)
        else:
            lines.append("- None")
        usage = agent_run.get("usage", {})
        lines.extend(["", "### Usage", "", "```json", json.dumps(usage, ensure_ascii=False, indent=2, sort_keys=True), "```"])
    return "\n".join(lines).rstrip() + "\n"


def _promotion_runtime_path(root: Path, promotion_id: str) -> Path:
    return _runtime_root(root) / "promotions" / (promotion_id + ".json")


def _promotion_diff(workspace: Path) -> str:
    return subprocess.run(
        ("git", "diff", "--binary", "HEAD", "--"),
        cwd=workspace,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


def prepare_promotion(root: Path, task_id: str, candidate_ids: Sequence[str]) -> dict[str, Any]:
    """Stage selected handoff candidates in a separate integration worktree."""
    require_v2(root)
    handoff = read_json(harness_root(root) / "tasks" / task_id / "handoff.json")
    validate_record(handoff, "handoff")
    if any(item["exit_code"] for item in handoff["validation"]):
        raise HarnessError("Task validation failed")
    if run_command(root, ("git", "status", "--porcelain")):
        raise HarnessError("official worktree must be clean before Promotion prepare")
    selected = [item for item in handoff["candidates"] if item["id"] in candidate_ids]
    if not selected or {item["id"] for item in selected} != set(candidate_ids):
        raise HarnessError("unknown or empty Promotion candidate selection")
    task_workspace = Path(read_workspace(root, task_id)["workspace"])
    promotion_id = "promotion-" + task_id + "-" + uuid.uuid4().hex[:8]
    branch = "harness/integration/" + promotion_id
    integration = _workspace_root(root) / "integration" / promotion_id
    integration.parent.mkdir(parents=True, exist_ok=True)
    base = run_command(root, ("git", "rev-parse", "HEAD"))
    run_command(root, ("git", "worktree", "add", "-b", branch, str(integration), base))
    targets = []
    for item in selected:
        source = contained_path(task_workspace, str(item["source"]), must_exist=True)
        target = contained_path(integration, str(item["target"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        targets.append(safe_relative(item["target"]).as_posix())
    run_command(integration, ("git", "add", "-N", "--", *targets))
    task = read_task(root, task_id)
    validation = run_validations(
        root,
        integration,
        task.get("validation_commands", []),
        "promotions/" + promotion_id + "/prepare",
    )
    diff = _promotion_diff(integration)
    payload = {
        "promotion_id": promotion_id,
        "task_id": task_id,
        "candidate_ids": list(candidate_ids),
        "base_commit": base,
        "branch": branch,
        "workspace": str(integration),
        "targets": targets,
        "task_digest": task["content_digest"],
        "diff": diff,
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
        "validation": validation,
        "validation_digest": validation_digest(validation),
        "status": "staged",
        "created_at": utc_now(),
    }
    write_json(_promotion_runtime_path(root, promotion_id), payload)
    return payload


def promotion_subject(payload: dict[str, Any]) -> str:
    """Return the approval subject digest for one staged Promotion."""
    return hashlib.sha256(
        canonical_bytes(
            {
                "promotion_id": payload["promotion_id"],
                "candidate_ids": payload["candidate_ids"],
                "base_commit": payload["base_commit"],
                "diff_sha256": payload["diff_sha256"],
                "validation_digest": payload["validation_digest"],
            }
        )
    ).hexdigest()


def _refresh_promotion(payload: dict[str, Any]) -> dict[str, Any]:
    """Recompute a staged Promotion's diff and validation evidence."""
    workspace = Path(payload["workspace"])
    diff = _promotion_diff(workspace)
    payload = dict(payload)
    payload["current_diff_sha256"] = hashlib.sha256(diff.encode()).hexdigest()
    return payload


def _require_current_promotion_base(root: Path, payload: dict[str, Any]) -> None:
    """Require a clean official worktree at the exact staged base commit."""
    current = run_command(root, ("git", "rev-parse", "HEAD"))
    if current != payload["base_commit"]:
        raise HarnessError("official HEAD changed; prepare a new Promotion packet")
    if run_command(root, ("git", "status", "--porcelain")):
        raise HarnessError("official worktree must be clean")
    task = read_task(root, str(payload["task_id"]))
    if task.get("content_digest") != payload.get("task_digest"):
        raise HarnessError("Task contract changed; prepare a new Promotion packet")


def approve_promotion(root: Path, promotion_id: str, actor: str) -> dict[str, Any]:
    """Record one exact-diff packet approval in Git-local runtime state."""
    path = _promotion_runtime_path(root, promotion_id)
    payload = _refresh_promotion(read_json(path))
    if payload.get("status") != "staged":
        raise HarnessError("Promotion must be staged before approval")
    _require_current_promotion_base(root, payload)
    if payload["current_diff_sha256"] != payload["diff_sha256"]:
        raise HarnessError("staged Promotion diff changed")
    task = read_task(root, str(payload["task_id"]))
    validation = run_validations(
        root,
        Path(payload["workspace"]),
        task.get("validation_commands", []),
        "promotions/" + promotion_id + "/approve",
    )
    if any(item["exit_code"] for item in validation):
        raise HarnessError("Promotion validation failed")
    payload["validation"] = validation
    payload["validation_digest"] = validation_digest(validation)
    payload["validated_at"] = utc_now()
    payload["status"] = "approved"
    payload["approval"] = {
        "actor": actor,
        "subject_digest": promotion_subject(payload),
        "approved_at": utc_now(),
    }
    write_json(path, payload)
    return payload


def apply_promotion(root: Path, promotion_id: str) -> dict[str, Any]:
    """Commit, cherry-pick, and record one approved exact-diff Promotion."""
    path = _promotion_runtime_path(root, promotion_id)
    payload = _refresh_promotion(read_json(path))
    if payload.get("status") != "approved":
        raise HarnessError("Promotion is not approved")
    _require_current_promotion_base(root, payload)
    if payload["current_diff_sha256"] != payload["diff_sha256"]:
        raise HarnessError("approved Promotion diff changed")
    if payload["approval"]["subject_digest"] != promotion_subject(payload):
        raise HarnessError("Promotion approval is stale")
    integration = Path(payload["workspace"])
    task = read_task(root, str(payload["task_id"]))
    apply_validation = run_validations(
        root,
        integration,
        task.get("validation_commands", []),
        "promotions/" + promotion_id + "/apply",
    )
    if any(item["exit_code"] for item in apply_validation):
        payload["status"] = "stale"
        payload["apply_validation"] = apply_validation
        write_json(path, payload)
        raise HarnessError("Promotion validation failed immediately before apply")
    with canonical_state_lock(root):
        payload = _refresh_promotion(read_json(path))
        _require_current_promotion_base(root, payload)
        if payload["current_diff_sha256"] != payload["diff_sha256"]:
            raise HarnessError("approved Promotion diff changed")
        if payload["approval"]["subject_digest"] != promotion_subject(payload):
            raise HarnessError("Promotion approval is stale")
        run_command(integration, ("git", "add", "--", *payload["targets"]))
        run_command(integration, ("git", "commit", "-m", "promote: " + payload["task_id"]))
        source_commit = run_command(integration, ("git", "rev-parse", "HEAD"))
        run_command(root, ("git", "cherry-pick", source_commit))
        official_commit = run_command(root, ("git", "rev-parse", "HEAD"))
        canonical = _new_record(
            "promotion",
            promotion_id,
            task_id=payload["task_id"],
            candidate_ids=payload["candidate_ids"],
            base_commit=payload["base_commit"],
            diff_sha256=payload["diff_sha256"],
            validation=apply_validation,
            approved_validation=payload["validation"],
            approval=payload["approval"],
            official_commit=official_commit,
            status="integrated",
        )
        canonical_path = harness_root(root) / "promotions" / (promotion_id + ".json")
        write_json(canonical_path, canonical)
        _bump_generation(root)
        run_command(root, ("git", "add", "--", str(canonical_path.relative_to(root)), ".harness/install.json"))
        run_command(root, ("git", "commit", "-m", "chore: record " + promotion_id))
    payload["status"] = "integrated"
    payload["apply_validation"] = apply_validation
    payload["official_commit"] = official_commit
    payload["record_commit"] = run_command(root, ("git", "rev-parse", "HEAD"))
    write_json(path, payload)
    return payload


def render_promotion(root: Path, promotion_id: str) -> str:
    """Render one staged or integrated Promotion packet."""
    runtime = _promotion_runtime_path(root, promotion_id)
    payload = read_json(runtime) if runtime.is_file() else read_json(
        harness_root(root) / "promotions" / (promotion_id + ".json")
    )
    lines = [
        "# Promotion " + promotion_id,
        "",
        "- Task: " + str(payload["task_id"]),
        "- Status: " + str(payload["status"]),
        "- Base: `" + str(payload["base_commit"]) + "`",
        "- Diff SHA-256: `" + str(payload["diff_sha256"]) + "`",
        "- Validation SHA-256: `" + str(payload.get("validation_digest") or "not recorded") + "`",
        "",
        "## Candidates",
        "",
    ]
    lines.extend("- `" + item + "`" for item in payload["candidate_ids"])
    lines.extend(["", "## Validation", ""])
    for item in payload["validation"]:
        line = "- `" + " ".join(item["argv"]) + "`: exit " + str(item["exit_code"])
        if item.get("timed_out"):
            line += " (timed out)"
        if item.get("log_path"):
            line += " — full log `" + str(item["log_path"]) + "`"
        lines.append(line)
    diff = payload.get("diff")
    if diff is None and runtime.is_file() and payload.get("status") in {"staged", "approved", "stale"}:
        diff = _promotion_diff(Path(payload["workspace"]))
    lines.extend(["", "## Exact Diff", "", "```diff", str(diff or "Diff unavailable after integration."), "```"])
    return "\n".join(lines).rstrip() + "\n"


@canonical_mutation
def request_decision(
    root: Path,
    task_id: str,
    title: str,
    reason: str,
    options: Sequence[dict[str, Any]],
    recommended: str,
    safe_default: str | None,
    deferrable: bool,
) -> dict[str, Any]:
    """Create one blocking, Task-local user decision request."""
    require_v2(root)
    task = read_task(root, task_id)
    if task["state"].get("task_status") not in {"active", "needs_decision"}:
        raise HarnessError("decision requests require an active Task")
    option_ids = [str(item.get("id", "")) for item in options]
    if not options or any(not item for item in option_ids) or len(option_ids) != len(set(option_ids)):
        raise HarnessError("decision options require unique ids")
    if recommended not in option_ids:
        raise HarnessError("recommended decision option is unavailable")
    if safe_default is not None and safe_default not in option_ids:
        raise HarnessError("safe default decision option is unavailable")
    decision_id = "decision-" + task_id + "-" + uuid.uuid4().hex[:8]
    record = _new_record(
        "decision",
        decision_id,
        task_id=task_id,
        status="pending",
        title=title,
        reason=reason,
        options=list(options),
        recommended=recommended,
        safe_default=safe_default,
        deferrable=deferrable,
        resolution=None,
    )
    write_json(harness_root(root) / "decisions" / (decision_id + ".json"), record)
    state = dict(task["state"])
    state.update({"task_status": "needs_decision", "decision_id": decision_id})
    _replace_record(task_record_path(root, task_id), task, state=state)
    _bump_generation(root)
    return record


def read_decision(root: Path, decision_id: str) -> dict[str, Any]:
    """Read and validate one decision record."""
    if not TASK_ID.fullmatch(decision_id):
        raise HarnessError("invalid decision id")
    payload = read_json(harness_root(root) / "decisions" / (decision_id + ".json"))
    validate_record(payload, "decision")
    return payload


def render_decision(root: Path, decision_id: str) -> str:
    """Render a decision request with recommendation and impacts."""
    decision = read_decision(root, decision_id)
    lines = [
        "# Decision " + decision_id,
        "",
        "- Task: " + decision["task_id"],
        "- Status: " + decision["status"],
        "- Can defer: " + str(decision["deferrable"]).lower(),
        "- Safe default: " + str(decision.get("safe_default") or "none"),
        "",
        "## Decision",
        "",
        decision["title"],
        "",
        "## Why It Is Needed",
        "",
        decision["reason"],
        "",
        "## Options",
        "",
    ]
    for item in decision["options"]:
        marker = " (recommended)" if item["id"] == decision["recommended"] else ""
        lines.append(
            "- **" + item["id"] + marker + "** — " + item["label"] + ": " + item["impact"]
        )
    if decision.get("resolution"):
        lines.extend(["", "## Resolution", "", json.dumps(decision["resolution"], ensure_ascii=False)])
    return "\n".join(lines).rstrip() + "\n"


@canonical_mutation
def resolve_decision(
    root: Path,
    decision_id: str,
    choice: str,
    actor: str,
    note: str,
) -> dict[str, Any]:
    """Resolve one pending decision and resume only its Task."""
    require_v2(root)
    decision = read_decision(root, decision_id)
    if decision["status"] != "pending":
        raise HarnessError("decision is already resolved")
    if choice not in {item["id"] for item in decision["options"]}:
        raise HarnessError("unknown decision choice")
    path = harness_root(root) / "decisions" / (decision_id + ".json")
    decision = _replace_record(
        path,
        decision,
        status="resolved",
        resolution={"choice": choice, "actor": actor, "note": note, "resolved_at": utc_now()},
    )
    task = read_task(root, decision["task_id"])
    state = dict(task["state"])
    state.pop("decision_id", None)
    state["task_status"] = "blocked" if choice == "stop" else "active"
    state["last_decision_id"] = decision_id
    _replace_record(task_record_path(root, task["id"]), task, state=state)
    _bump_generation(root)
    return decision


def _result_index_path(root: Path) -> Path:
    return harness_root(root) / "results/index.json"


def _result_entry(record: dict[str, Any]) -> dict[str, Any]:
    """Return one compact Result index entry."""
    return {
        "id": record["id"],
        "kind": record["kind"],
        "summary": record["summary"],
        "verification_status": record["verification_status"],
        "reusable": record["reusable"],
        "supersedes": record.get("supersedes"),
        "digest": record["content_digest"],
    }


def _result_records(root: Path) -> list[dict[str, Any]]:
    """Read all non-index Result records in stable id order."""
    records = []
    for path in sorted((harness_root(root) / "results").glob("*.json")):
        if path.name == "index.json":
            continue
        payload = read_json(path)
        validate_record(payload, "result")
        records.append(payload)
    return sorted(records, key=lambda item: str(item["id"]))


def _write_result_index(root: Path) -> dict[str, Any]:
    """Rebuild the compact Result index from canonical Result records."""
    entries = [_result_entry(record) for record in _result_records(root)]
    index_path = _result_index_path(root)
    if index_path.is_file():
        index = read_json(index_path)
        validate_record(index, "result")
        return _replace_record(index_path, index, entries=entries)
    index = _new_record("result", "result-index", kind="index", entries=entries)
    write_json(index_path, index)
    return index


@canonical_mutation
def add_result(
    root: Path,
    result_id: str,
    kind: str,
    summary: str,
    source_refs: Sequence[str],
    artifact_refs: Sequence[str],
    verification_status: str,
    reusable: bool,
    supersedes: str | None,
    reviewed_by: str | None = None,
    verification_note: str = "",
) -> dict[str, Any]:
    """Add one provenance-bearing Result and rebuild the compact index."""
    require_v2(root)
    if not TASK_ID.fullmatch(result_id):
        raise HarnessError("result id must use lowercase kebab-case")
    if kind not in {"experiment", "failure", "review", "decision", "asset"}:
        raise HarnessError("unsupported result kind")
    if verification_status not in {"unverified", "reviewed", "verified", "rejected"}:
        raise HarnessError("invalid result verification status")
    if verification_status in {"reviewed", "verified"} and not reviewed_by:
        raise HarnessError("reviewed or verified Result requires --reviewed-by")
    if verification_status in {"reviewed", "verified"} and not (source_refs or artifact_refs):
        raise HarnessError("reviewed or verified Result requires source or artifact evidence")
    path = harness_root(root) / "results" / (result_id + ".json")
    if path.exists():
        raise HarnessError("result already exists")
    artifacts = []
    for raw in artifact_refs:
        source = contained_path(root, raw, must_exist=True)
        data = source.read_bytes()
        artifacts.append(
            {
                "path": safe_relative(raw).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    if supersedes and not (harness_root(root) / "results" / (supersedes + ".json")).is_file():
        raise HarnessError("superseded Result does not exist")
    record = _new_record(
        "result",
        result_id,
        kind=kind,
        summary=summary,
        source_refs=list(source_refs),
        artifact_refs=list(artifact_refs),
        artifacts=artifacts,
        verification_status=verification_status,
        reviewed_by=reviewed_by,
        verification_note=verification_note,
        reusable=reusable,
        supersedes=supersedes,
    )
    try:
        write_json(path, record)
        _write_result_index(root)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    _bump_generation(root)
    return record


@canonical_mutation
def rebuild_result_index(root: Path) -> dict[str, Any]:
    """Repair the compact Result index from canonical Result records."""
    require_v2(root)
    index = _write_result_index(root)
    _bump_generation(root)
    return index


def list_results(
    root: Path,
    kind: str | None = None,
    verification_status: str | None = None,
    reusable: bool | None = None,
    text: str | None = None,
) -> list[dict[str, Any]]:
    """Return filtered compact Result-index entries."""
    path = _result_index_path(root)
    if not path.is_file():
        return []
    index = read_json(path)
    validate_record(index, "result")
    entries = list(index.get("entries", []))
    if kind is not None:
        entries = [item for item in entries if item.get("kind") == kind]
    if verification_status is not None:
        entries = [
            item for item in entries if item.get("verification_status") == verification_status
        ]
    if reusable is not None:
        entries = [item for item in entries if bool(item.get("reusable")) == reusable]
    if text:
        needle = text.casefold()
        entries = [
            item for item in entries
            if needle in (str(item.get("id", "")) + " " + str(item.get("summary", ""))).casefold()
        ]
    return entries


def render_result(root: Path, result_id: str) -> str:
    """Render one reusable result for human review."""
    result = read_json(harness_root(root) / "results" / (result_id + ".json"))
    validate_record(result, "result")
    lines = [
        "# Result " + result_id,
        "",
        "- Kind: " + result["kind"],
        "- Verification: " + result["verification_status"],
        "- Reviewed by: " + str(result.get("reviewed_by") or "not recorded"),
        "- Reusable: " + str(result["reusable"]).lower(),
        "- Supersedes: " + str(result.get("supersedes") or "none"),
        "",
        "## Summary",
        "",
        result["summary"],
        "",
        "## Source References",
        "",
    ]
    lines.extend("- `" + item + "`" for item in result.get("source_refs", []))
    lines.extend(["", "## Artifacts", ""])
    artifacts = result.get("artifacts", [])
    if artifacts:
        for item in artifacts:
            lines.append(
                "- `" + str(item["path"]) + "` (" + str(item["bytes"])
                + " bytes, SHA-256 `" + str(item["sha256"]) + "`)"
            )
    else:
        lines.extend("- `" + item + "`" for item in result.get("artifact_refs", []))
    lines.extend(["", "## Verification Note", "", str(result.get("verification_note") or "None")])
    return "\n".join(lines).rstrip() + "\n"
