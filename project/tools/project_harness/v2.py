"""Stage A JSON authority, migration, worktree, and Promotion operations."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from .context import report_condition
from .documents import atomic_write_text, markdown_table, scalar, section
from .errors import HarnessError
from .lifecycle import report_handoff
from .repository import git_dir, run_command, safe_relative


SCHEMA_VERSION = 2
TASK_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RECORD_TYPES = {"project", "task", "handoff", "decision", "result", "promotion"}


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
    """Revision one canonical record using compare-and-reseal semantics."""
    validate_record(payload)
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
    return "\n".join(lines).rstrip() + "\n"


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
    return {
        "authority": authority_mode(root),
        "tasks": len(model["tasks"]),
        "handoffs": sum(item["handoff"] is not None for item in model["tasks"]),
        "histories": len(model["histories"]),
        "supported": True,
    }


def migration_plan(root: Path) -> dict[str, Any]:
    """Return conversion paths and semantic parity without writing files."""
    records = legacy_records(root)
    legacy = legacy_semantic_model(root)
    converted = semantic_model_from_records(records)
    return {
        "records": sorted(records),
        "semantic_parity": legacy == converted,
        "legacy_digest": hashlib.sha256(canonical_bytes(legacy)).hexdigest(),
        "converted_digest": hashlib.sha256(canonical_bytes(converted)).hexdigest(),
    }


def migration_apply(root: Path, migration_id: str) -> Path:
    """Write side-by-side candidate records without switching authority."""
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
    legacy = legacy_semantic_model(root)
    converted = semantic_model_from_records(_candidate_records(root, migration_id))
    return {
        "semantic_parity": legacy == converted,
        "legacy_digest": hashlib.sha256(canonical_bytes(legacy)).hexdigest(),
        "converted_digest": hashlib.sha256(canonical_bytes(converted)).hexdigest(),
    }


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
    for raw in owned_write_paths:
        safe_relative(raw)
    input_records = []
    total_input_bytes = 0
    for raw in inputs:
        relative = safe_relative(raw)
        source = root / relative
        if not source.is_file():
            raise HarnessError("Task input file does not exist: " + raw)
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
    owned_paths = list(owned_write_paths)
    if execution is not None and ".harness-agent-handoff.json" not in owned_paths:
        owned_paths.append(".harness-agent-handoff.json")
    record = _new_record(
        "task",
        task_id,
        objective_id="current",
        goal=goal,
        scope=scope,
        inputs=input_records,
        outputs=list(outputs),
        acceptance=list(acceptance),
        dependencies=list(dependencies),
        context_refs=list(context_refs),
        owned_write_paths=owned_paths,
        validation_commands=[list(item) for item in validation_commands],
        execution=execution,
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


def render_task(root: Path, task_id: str) -> str:
    """Render one Task contract and current state as Markdown."""
    task = read_task(root, task_id)
    lines = [
        "# Task " + task_id,
        "",
        "> Generated view. Source digest: `" + task["content_digest"] + "`",
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
    lines.extend([
        "",
        "## Owned Write Paths",
        "",
    ])
    lines.extend("- `" + item + "`" for item in task.get("owned_write_paths", []))
    lines.extend(["", "## Acceptance", ""])
    lines.extend("- " + item for item in task.get("acceptance", []))
    lines.extend(["", "## Context References", ""])
    lines.extend("- `" + item + "`" for item in task.get("context_refs", []))
    if task.get("execution") is not None:
        lines.extend(["", "## Codex Execution Contract", "", "```json"])
        lines.append(json.dumps(task["execution"], ensure_ascii=False, indent=2, sort_keys=True))
        lines.extend(["```", ""])
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


def run_validations(workspace: Path, commands: Sequence[Sequence[str]]) -> list[dict[str, Any]]:
    """Run deterministic validation argv lists without shell interpretation."""
    results = []
    for command in commands:
        if not command:
            raise HarnessError("validation command cannot be empty")
        process = subprocess.run(command, cwd=workspace, text=True, capture_output=True)
        results.append(
            {
                "argv": list(command),
                "exit_code": process.returncode,
                "stdout": process.stdout[-4000:],
                "stderr": process.stderr[-4000:],
            }
        )
    return results


def submit_handoff(root: Path, task_id: str, source: Path) -> dict[str, Any]:
    """Validate actual Task changes and import one typed handoff."""
    require_v2(root)
    task = read_task(root, task_id)
    workspace = read_workspace(root, task_id)
    if workspace.get("state") != "active":
        raise HarnessError("Task workspace is not active")
    worktree = Path(workspace["workspace"])
    source_path = safe_relative(source.as_posix())
    payload = read_json(worktree / source_path)
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
        safe_relative(str(candidate.get("target", "")))
        if not (worktree / source_path).is_file():
            raise HarnessError("candidate source does not exist: " + str(source_path))
    validation = run_validations(worktree, task.get("validation_commands", []))
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
    write_json(harness_root(root) / "tasks" / task_id / "handoff.json", handoff)
    state = dict(task["state"])
    state["task_status"] = "review"
    _replace_record(task_record_path(root, task_id), task, state=state)
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
        "",
        "## Validation",
        "",
    ]
    for item in handoff["validation"]:
        lines.append("- `" + " ".join(item["argv"]) + "`: exit " + str(item["exit_code"]))
    lines.extend(["", "## Promotion Candidates", ""])
    for item in handoff["candidates"]:
        lines.append(
            "- **" + item["id"] + "**: `" + item["source"] + "` → `" + item["target"] + "` — " + str(item.get("rationale", ""))
        )
    lines.extend(["", "## Changed Paths", ""])
    lines.extend("- `" + item + "`" for item in handoff["changed_paths"])
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
        source = task_workspace / safe_relative(item["source"])
        target = integration / safe_relative(item["target"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        targets.append(safe_relative(item["target"]).as_posix())
    run_command(integration, ("git", "add", "-N", "--", *targets))
    task = read_task(root, task_id)
    validation = run_validations(integration, task.get("validation_commands", []))
    diff = _promotion_diff(integration)
    payload = {
        "promotion_id": promotion_id,
        "task_id": task_id,
        "candidate_ids": list(candidate_ids),
        "base_commit": base,
        "branch": branch,
        "workspace": str(integration),
        "targets": targets,
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
        "validation": validation,
        "validation_digest": hashlib.sha256(canonical_bytes(validation)).hexdigest(),
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


def approve_promotion(root: Path, promotion_id: str, actor: str) -> dict[str, Any]:
    """Record one exact-diff packet approval in Git-local runtime state."""
    path = _promotion_runtime_path(root, promotion_id)
    payload = _refresh_promotion(read_json(path))
    if payload["current_diff_sha256"] != payload["diff_sha256"]:
        raise HarnessError("staged Promotion diff changed")
    if any(item["exit_code"] for item in payload["validation"]):
        raise HarnessError("Promotion validation failed")
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
    if payload["current_diff_sha256"] != payload["diff_sha256"]:
        raise HarnessError("approved Promotion diff changed")
    if payload["approval"]["subject_digest"] != promotion_subject(payload):
        raise HarnessError("Promotion approval is stale")
    if run_command(root, ("git", "status", "--porcelain")):
        raise HarnessError("official worktree must be clean")
    integration = Path(payload["workspace"])
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
        validation=payload["validation"],
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
        "",
        "## Candidates",
        "",
    ]
    lines.extend("- `" + item + "`" for item in payload["candidate_ids"])
    lines.extend(["", "## Validation", ""])
    for item in payload["validation"]:
        lines.append("- `" + " ".join(item["argv"]) + "`: exit " + str(item["exit_code"]))
    return "\n".join(lines).rstrip() + "\n"


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
) -> dict[str, Any]:
    """Add one discoverable result and update the small canonical index."""
    require_v2(root)
    if not TASK_ID.fullmatch(result_id):
        raise HarnessError("result id must use lowercase kebab-case")
    if kind not in {"experiment", "failure", "review", "decision", "asset"}:
        raise HarnessError("unsupported result kind")
    if verification_status not in {"unverified", "reviewed", "verified", "rejected"}:
        raise HarnessError("invalid result verification status")
    path = harness_root(root) / "results" / (result_id + ".json")
    if path.exists():
        raise HarnessError("result already exists")
    for raw in artifact_refs:
        safe_relative(raw)
    record = _new_record(
        "result",
        result_id,
        kind=kind,
        summary=summary,
        source_refs=list(source_refs),
        artifact_refs=list(artifact_refs),
        verification_status=verification_status,
        reusable=reusable,
        supersedes=supersedes,
    )
    write_json(path, record)
    index_path = _result_index_path(root)
    if index_path.is_file():
        index = read_json(index_path)
        validate_record(index, "result")
        entries = list(index.get("entries", []))
        entries.append(
            {
                "id": result_id,
                "kind": kind,
                "summary": summary,
                "verification_status": verification_status,
                "reusable": reusable,
                "supersedes": supersedes,
                "digest": record["content_digest"],
            }
        )
        _replace_record(index_path, index, entries=entries)
    else:
        write_json(
            index_path,
            _new_record(
                "result",
                "result-index",
                kind="index",
                entries=[
                    {
                        "id": result_id,
                        "kind": kind,
                        "summary": summary,
                        "verification_status": verification_status,
                        "reusable": reusable,
                        "supersedes": supersedes,
                        "digest": record["content_digest"],
                    }
                ],
            ),
        )
    _bump_generation(root)
    return record


def list_results(root: Path) -> list[dict[str, Any]]:
    """Return compact result-index entries."""
    path = _result_index_path(root)
    if not path.is_file():
        return []
    index = read_json(path)
    validate_record(index, "result")
    return list(index.get("entries", []))


def render_result(root: Path, result_id: str) -> str:
    """Render one reusable result for human review."""
    result = read_json(harness_root(root) / "results" / (result_id + ".json"))
    validate_record(result, "result")
    lines = [
        "# Result " + result_id,
        "",
        "- Kind: " + result["kind"],
        "- Verification: " + result["verification_status"],
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
    lines.extend("- `" + item + "`" for item in result.get("artifact_refs", []))
    return "\n".join(lines).rstrip() + "\n"
