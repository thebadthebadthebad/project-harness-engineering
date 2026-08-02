"""Codex execution adapter for structured, policy-bound v2 Task runs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

from .errors import HarnessError
from .repository import git_dir
from .v2 import (
    content_digest,
    read_json,
    read_task,
    read_workspace,
    request_decision,
    seal_record,
    submit_handoff,
    task_record_path,
    utc_now,
    write_json,
    _bump_generation,
    _replace_record,
)


REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")
SANDBOX_MODES = ("read-only", "workspace-write", "danger-full-access")
APPROVAL_POLICIES = ("untrusted", "on-request", "never")
WEB_MODES = ("disabled", "cached", "indexed", "live")
CONTROLLABLE_TOOLS = ("web_search", "view_image", "multi_agent")
FINAL_HANDOFF_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "status": {"enum": ["completed", "needs_decision", "blocked"]},
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["id", "source", "target", "rationale"],
                "additionalProperties": False,
            },
        },
        "decision_request": {
            "type": ["object", "null"],
            "properties": {
                "title": {"type": "string"},
                "reason": {"type": "string"},
                "recommended": {"type": "string"},
                "safe_default": {"type": ["string", "null"]},
                "deferrable": {"type": "boolean"},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                            "impact": {"type": "string"},
                        },
                        "required": ["id", "label", "impact"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["title", "reason", "recommended", "safe_default", "deferrable", "options"],
            "additionalProperties": False,
        },
        "blocked_reason": {"type": ["string", "null"]},
    },
    "required": [
        "status", "summary", "findings", "limitations", "candidates",
        "decision_request", "blocked_reason",
    ],
    "additionalProperties": False,
}


def _run(argv: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run one read-only capability command."""
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True)


def capability_probe(codex_bin: str = "codex") -> dict[str, Any]:
    """Probe the installed Codex CLI without starting a model turn."""
    version = _run((codex_bin, "--version"))
    help_result = _run((codex_bin, "exec", "--help"))
    if version.returncode or help_result.returncode:
        raise HarnessError("Codex CLI capability probe failed")
    help_text = help_result.stdout + help_result.stderr
    mcp_result = _run((codex_bin, "mcp", "list", "--json"))
    mcp_servers: list[str] = []
    if not mcp_result.returncode:
        try:
            raw_mcp = json.loads(mcp_result.stdout or "[]")
            if isinstance(raw_mcp, list):
                mcp_servers = sorted(
                    str(item.get("name")) for item in raw_mcp
                    if isinstance(item, dict) and item.get("name")
                )
        except json.JSONDecodeError:
            pass
    flags = {
        name: token in help_text
        for name, token in {
            "json": "--json",
            "output_schema": "--output-schema",
            "output_last_message": "--output-last-message",
            "sandbox": "--sandbox",
            "model": "--model",
            "config": "--config",
            "working_directory": "--cd",
        }.items()
    }
    return {
        "codex_version": version.stdout.strip(),
        "flags": flags,
        "reasoning_efforts": list(REASONING_EFFORTS),
        "reasoning_source": "Codex config reference plus conservative adapter policy",
        "sandbox_modes": list(SANDBOX_MODES),
        "approval_policies": list(APPROVAL_POLICIES),
        "web_modes": list(WEB_MODES),
        "controllable_tools": list(CONTROLLABLE_TOOLS),
        "mcp_servers": mcp_servers,
        "probed_at": utc_now(),
    }


def _default_contract() -> dict[str, Any]:
    """Return conservative non-interactive execution defaults."""
    return {
        "model": None,
        "reasoning_effort": "medium",
        "reasoning_fallback": ["medium", "low"],
        "sandbox": "workspace-write",
        "approval_policy": "never",
        "web_mode": "disabled",
        "network_access": False,
        "allowed_tools": ["shell", "apply_patch"],
        "allowed_mcp": [],
        "allowed_skills": [],
        "limits": {"seconds": 3600, "tokens": None},
        "fallback": {"allow_missing_mcp": False, "allow_reasoning_downgrade": True},
        "agent": {
            "role": "implementation",
            "parent_review_required": True,
            "may_delegate": False,
            "subagent_contract": {
                "required_inputs": ["objective", "scope", "context_refs", "owned_write_paths"],
                "required_outputs": ["summary", "findings", "candidates", "limitations"],
                "file_ownership": "must be explicit and non-overlapping",
                "parent_responsibility": "review claims, validate changes, select candidates, integrate",
            },
        },
    }


def normalize_contract(
    raw: dict[str, Any] | None,
    capabilities: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate a Task contract and apply only explicit safe fallbacks."""
    contract = _default_contract()
    for key, value in (raw or {}).items():
        if key in {"limits", "fallback", "agent"} and isinstance(value, dict):
            contract[key].update(value)
        else:
            contract[key] = value
    fallbacks: list[dict[str, Any]] = []
    supported_efforts = capabilities.get("reasoning_efforts", list(REASONING_EFFORTS))
    requested_effort = str(contract["reasoning_effort"])
    if requested_effort not in supported_efforts:
        replacement = next(
            (
                item for item in contract.get("reasoning_fallback", [])
                if item in supported_efforts
            ),
            None,
        )
        if not replacement or not contract["fallback"].get("allow_reasoning_downgrade"):
            raise HarnessError("unsupported reasoning effort without safe fallback")
        contract["reasoning_effort"] = replacement
        fallbacks.append(
            {"field": "reasoning_effort", "requested": requested_effort, "applied": replacement}
        )
    if contract["sandbox"] not in capabilities.get("sandbox_modes", SANDBOX_MODES):
        raise HarnessError("unsupported sandbox mode")
    if contract["approval_policy"] not in capabilities.get(
        "approval_policies", APPROVAL_POLICIES
    ):
        raise HarnessError("unsupported approval policy")
    if contract["web_mode"] not in capabilities.get("web_modes", WEB_MODES):
        raise HarnessError("unsupported web mode")
    if not isinstance(contract["network_access"], bool):
        raise HarnessError("network_access must be boolean")
    seconds = contract["limits"].get("seconds")
    tokens = contract["limits"].get("tokens")
    if not isinstance(seconds, int) or seconds < 1:
        raise HarnessError("execution seconds limit must be a positive integer")
    if tokens is not None and (not isinstance(tokens, int) or tokens < 1):
        raise HarnessError("execution token limit must be null or a positive integer")
    if contract["agent"].get("may_delegate") and "multi_agent" not in contract["allowed_tools"]:
        raise HarnessError("delegation requires multi_agent in allowed_tools")
    installed_mcp = set(capabilities.get("mcp_servers", []))
    missing_mcp = sorted(set(contract.get("allowed_mcp", [])) - installed_mcp)
    if missing_mcp:
        if not contract["fallback"].get("allow_missing_mcp"):
            raise HarnessError("required MCP unavailable: " + ", ".join(missing_mcp))
        contract["allowed_mcp"] = [
            name for name in contract["allowed_mcp"] if name in installed_mcp
        ]
        fallbacks.append({"field": "allowed_mcp", "removed": missing_mcp})
    return contract, fallbacks


def _toml_string(value: str) -> str:
    """Return a TOML-compatible quoted string."""
    return json.dumps(value, ensure_ascii=False)


def _skill_paths(workspace: Path) -> dict[str, Path]:
    """Discover Project-local skills by their frontmatter name."""
    skills: dict[str, Path] = {}
    for path in sorted(workspace.glob(".agents/skills/*/SKILL.md")):
        match = re.search(r"(?m)^name:\s*[\"']?([^\"'\n]+)", path.read_text())
        if match:
            skills[match.group(1).strip()] = path.parent.resolve()
    return skills


def build_argv(
    codex_bin: str,
    workspace: Path,
    contract: dict[str, Any],
    capabilities: dict[str, Any],
    schema_path: Path,
    output_path: Path,
) -> list[str]:
    """Build an explicit non-interactive Codex command."""
    required_flags = ("json", "output_schema", "output_last_message", "sandbox", "config")
    missing_flags = [name for name in required_flags if not capabilities["flags"].get(name)]
    if missing_flags:
        raise HarnessError("Codex CLI lacks required flags: " + ", ".join(missing_flags))
    argv = [
        codex_bin,
        "exec",
        "--json",
        "-C",
        str(workspace),
        "--sandbox",
        contract["sandbox"],
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        "-c",
        "model_reasoning_effort=" + _toml_string(contract["reasoning_effort"]),
        "-c",
        "approval_policy=" + _toml_string(contract["approval_policy"]),
        "-c",
        "web_search=" + _toml_string(contract["web_mode"]),
        "-c",
        "sandbox_workspace_write.network_access=" + str(contract["network_access"]).lower(),
        "-c",
        "tools.view_image=" + str("view_image" in contract["allowed_tools"]).lower(),
        "-c",
        "agents.enabled=" + str("multi_agent" in contract["allowed_tools"]).lower(),
    ]
    if contract.get("model"):
        argv.extend(("--model", str(contract["model"])))
    enabled_mcp = set(contract.get("allowed_mcp", []))
    for name in capabilities.get("mcp_servers", []):
        argv.extend(("-c", "mcp_servers." + name + ".enabled=" + str(name in enabled_mcp).lower()))
    discovered_skills = _skill_paths(workspace)
    allowed_skills = set(contract.get("allowed_skills", []))
    if discovered_skills:
        entries = ",".join(
            "{path=" + _toml_string(str(path)) + ",enabled=" + str(name in allowed_skills).lower() + "}"
            for name, path in discovered_skills.items()
        )
        argv.extend(("-c", "skills.config=[" + entries + "]"))
    argv.append("-")
    return argv


def _load_context_reference(root: Path, reference: str) -> dict[str, Any]:
    """Resolve one minimal stable Task context reference."""
    kind, separator, identifier = reference.partition(":")
    if not separator or not identifier:
        raise HarnessError("context ref must use kind:id")
    paths = {
        "result": root / ".harness/results" / (identifier + ".json"),
        "decision": root / ".harness/decisions" / (identifier + ".json"),
        "task": root / ".harness/tasks" / identifier / "task.json",
    }
    if kind not in paths:
        raise HarnessError("unsupported context ref kind: " + kind)
    payload = read_json(paths[kind])
    return {
        "ref": reference,
        "digest": payload.get("content_digest"),
        "summary": payload.get("summary") or payload.get("goal") or payload.get("resolution"),
        "verification_status": payload.get("verification_status"),
        "artifact_refs": payload.get("artifact_refs", []),
    }


def build_prompt(root: Path, task: dict[str, Any], contract: dict[str, Any]) -> str:
    """Build bounded Task context and the structured handoff contract."""
    project = read_json(root / ".harness/project.json")
    references = [_load_context_reference(root, item) for item in task.get("context_refs", [])]
    payload = {
        "project_goal": project.get("goal"),
        "task_id": task["id"],
        "task_goal": task["goal"],
        "scope": task["scope"],
        "inputs": task.get("inputs", []),
        "outputs": task.get("outputs", []),
        "acceptance": task.get("acceptance", []),
        "owned_write_paths": task.get("owned_write_paths", []),
        "context_references": references,
        "agent_contract": contract["agent"],
        "allowed_tools": contract["allowed_tools"],
        "allowed_mcp": contract["allowed_mcp"],
        "allowed_skills": contract["allowed_skills"],
    }
    return (
        "Execute the following bounded Task contract. Do not write outside owned_write_paths. "
        "Do not request or perform external changes, broader scope, or additional permission "
        "without returning status needs_decision. The parent Agent reviews all handoff claims and "
        "controls integration. Return only the requested structured handoff.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    )


def _parse_events(raw: str) -> tuple[list[dict[str, Any]], str | None, dict[str, Any]]:
    """Parse JSONL events and extract thread and final usage."""
    events = []
    thread_id = None
    usage: dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            event = {"type": "adapter.unparsed", "text": line[-2000:]}
        events.append(event)
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = event["usage"]
    return events, thread_id, usage


def _permission_failure(events: Sequence[dict[str, Any]], stderr: str) -> bool:
    """Return whether a failed run appears to require user authority."""
    text = stderr.lower() + " " + " ".join(json.dumps(item).lower() for item in events[-20:])
    terms = ("permission", "approval", "sandbox", "external change", "scope expansion")
    return any(term in text for term in terms)


def _set_task_state(root: Path, task_id: str, status: str, **extra: Any) -> None:
    """Update only one canonical Task state."""
    task = read_task(root, task_id)
    state = dict(task["state"])
    state.update({"task_status": status, **extra})
    _replace_record(task_record_path(root, task_id), task, state=state)
    _bump_generation(root)


def execute_task(root: Path, task_id: str, codex_bin: str = "codex") -> dict[str, Any]:
    """Run Codex once and import its structured Task outcome."""
    task = read_task(root, task_id)
    workspace = read_workspace(root, task_id)
    if task["state"].get("task_status") != "active" or workspace.get("state") != "active":
        raise HarnessError("Task must have an active workspace")
    capabilities = capability_probe(codex_bin)
    contract, fallbacks = normalize_contract(task.get("execution"), capabilities)
    runtime = git_dir(root) / "harness/v2/runs" / task_id / workspace["run_id"]
    runtime.mkdir(parents=True, exist_ok=True)
    schema_path = runtime / "handoff.schema.json"
    final_path = runtime / "final.json"
    write_json(schema_path, FINAL_HANDOFF_SCHEMA)
    argv = build_argv(
        codex_bin,
        Path(workspace["workspace"]),
        contract,
        capabilities,
        schema_path,
        final_path,
    )
    prompt = build_prompt(root, task, contract)
    try:
        process = subprocess.run(
            argv,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=contract["limits"]["seconds"],
            env=os.environ.copy(),
        )
        timed_out = False
    except subprocess.TimeoutExpired as error:
        process = subprocess.CompletedProcess(
            argv,
            124,
            error.stdout if isinstance(error.stdout, str) else "",
            error.stderr if isinstance(error.stderr, str) else "",
        )
        timed_out = True
    events, thread_id, usage = _parse_events(process.stdout)
    token_total = sum(
        int(usage.get(key, 0) or 0)
        for key in ("input_tokens", "output_tokens", "reasoning_output_tokens")
    )
    token_limit = contract["limits"].get("tokens")
    evidence = {
        "task_id": task_id,
        "run_id": workspace["run_id"],
        "thread_id": thread_id,
        "started_contract_digest": content_digest(seal_record({
            "schema_version": 2, "record_type": "result", "id": "execution-contract",
            "revision": 1, "contract": contract,
        })),
        "requested_contract": task.get("execution"),
        "effective_contract": contract,
        "fallbacks": fallbacks,
        "capabilities": capabilities,
        "argv": argv,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "usage": usage,
        "token_limit_exceeded": token_limit is not None and token_total > token_limit,
        "events": events,
        "stderr": process.stderr[-8000:],
        "finished_at": utc_now(),
    }
    write_json(runtime / "run.json", evidence)
    if timed_out:
        _set_task_state(root, task_id, "blocked", blocked_reason="execution timeout")
        return {"status": "blocked", "reason": "execution timeout", "evidence": str(runtime / "run.json")}
    if process.returncode:
        if _permission_failure(events, process.stderr):
            decision = request_decision(
                root,
                task_id,
                "Codex execution needs additional authority",
                "The non-interactive run reported a permission, approval, external-change, or scope boundary.",
                [
                    {"id": "revise-contract", "label": "Revise contract", "impact": "Grant only reviewed scope or permission."},
                    {"id": "stop", "label": "Stop Task", "impact": "Keep current evidence without further execution."},
                ],
                "revise-contract",
                None,
                True,
            )
            return {"status": "needs_decision", "decision_id": decision["id"], "evidence": str(runtime / "run.json")}
        _set_task_state(root, task_id, "blocked", blocked_reason="Codex execution failed")
        return {"status": "blocked", "reason": "Codex execution failed", "evidence": str(runtime / "run.json")}
    if not final_path.is_file():
        _set_task_state(root, task_id, "blocked", blocked_reason="missing structured final output")
        return {"status": "blocked", "reason": "missing structured final output", "evidence": str(runtime / "run.json")}
    try:
        final = read_json(final_path)
    except (HarnessError, json.JSONDecodeError, OSError):
        _set_task_state(root, task_id, "blocked", blocked_reason="malformed structured final output")
        return {
            "status": "blocked",
            "reason": "malformed structured final output",
            "evidence": str(runtime / "run.json"),
        }
    if final.get("status") == "needs_decision":
        request = final.get("decision_request") or {}
        decision = request_decision(
            root,
            task_id,
            str(request.get("title", "Task decision required")),
            str(request.get("reason", final.get("summary", ""))),
            list(request.get("options", [])),
            str(request.get("recommended", "")),
            request.get("safe_default"),
            bool(request.get("deferrable", True)),
        )
        return {"status": "needs_decision", "decision_id": decision["id"], "evidence": str(runtime / "run.json")}
    if final.get("status") == "blocked" or evidence["token_limit_exceeded"]:
        reason = "token limit exceeded" if evidence["token_limit_exceeded"] else str(final.get("blocked_reason") or "Agent blocked")
        _set_task_state(root, task_id, "blocked", blocked_reason=reason)
        return {"status": "blocked", "reason": reason, "evidence": str(runtime / "run.json")}
    handoff_source = Path(workspace["workspace"]) / ".harness-agent-handoff.json"
    write_json(handoff_source, final)
    handoff = submit_handoff(root, task_id, Path(".harness-agent-handoff.json"))
    handoff_path = root / ".harness/tasks" / task_id / "handoff.json"
    handoff = _replace_record(
        handoff_path,
        handoff,
        agent_run={
            "thread_id": thread_id,
            "run_id": workspace["run_id"],
            "evidence": str((runtime / "run.json").relative_to(git_dir(root))),
            "effective_contract": contract,
            "fallbacks": fallbacks,
            "usage": usage,
        },
    )
    return {"status": "review", "handoff": handoff, "evidence": str(runtime / "run.json")}
