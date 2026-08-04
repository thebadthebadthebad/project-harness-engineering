"""Stage B Codex adapter, decisions, and result-index acceptance tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PUBLIC_TEMPLATE = REPOSITORY / "project"
HARNESSCTL = REPOSITORY / "tools/harnessctl.py"


class StageBTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.fake_codex = self.base / "fake-codex"
        self.fake_codex.write_text(
            """#!/usr/bin/env python3
import json, os, pathlib, sys, time
args = sys.argv[1:]
if args == ['--version']:
    print('codex-cli 0.test')
    raise SystemExit(0)
if args[:2] == ['exec', '--help']:
    print('--json --output-schema --output-last-message --sandbox --model --config --cd')
    raise SystemExit(0)
if args[:3] == ['mcp', 'list', '--json']:
    print('[{"name":"docs"}]')
    raise SystemExit(0)
if not args or args[0] != 'exec':
    raise SystemExit(2)
prompt = sys.stdin.read()
capture = os.environ.get('FAKE_CAPTURE')
if capture:
    pathlib.Path(capture).write_text(json.dumps({'argv': sys.argv, 'prompt': prompt}))
mode = os.environ.get('FAKE_CODEX_MODE', 'completed')
if mode == 'permission':
    print(json.dumps({'type':'thread.started','thread_id':'thread-permission'}))
    print(json.dumps({'type':'turn.failed','error':'approval required for external change'}))
    print('sandbox approval required', file=sys.stderr)
    raise SystemExit(1)
if mode == 'timeout':
    time.sleep(3)
output = pathlib.Path(args[args.index('-o') + 1])
workspace = pathlib.Path(args[args.index('-C') + 1])
(workspace / 'task-output').mkdir(exist_ok=True)
(workspace / 'task-output/result.txt').write_text('agent result\\n')
decision = None
status = 'completed'
blocked = None
if mode == 'decision':
    status = 'needs_decision'
    decision = {
        'title':'External publication', 'reason':'Publishing changes external state',
        'recommended':'keep-local', 'safe_default':'keep-local', 'deferrable':True,
        'options':[
            {'id':'keep-local','label':'Keep local','impact':'No external change.'},
            {'id':'publish','label':'Publish','impact':'Changes an external system.'}
        ]
    }
payload = {
    'status': status, 'summary':'Agent result', 'findings':['checked'], 'limitations':[],
    'candidates': [] if status != 'completed' else [{
        'id':'result','source':'task-output/result.txt','target':'src/result.txt','rationale':'verified'
    }],
    'decision_request': decision, 'blocked_reason': blocked,
}
output.write_text('{broken') if mode == 'malformed' else output.write_text(json.dumps(payload))
print(json.dumps({'type':'thread.started','thread_id':'thread-test'}))
tokens = 999 if mode == 'tokens' else 12
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':tokens,'output_tokens':3,'reasoning_output_tokens':2}}))
"""
        )
        self.fake_codex.chmod(0o755)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(self, *argv: str, cwd: Path | None = None, ok: bool = True, env=None):
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, env=env)
        if ok and result.returncode:
            self.fail("command failed: " + " ".join(argv) + "\n" + result.stderr + result.stdout)
        return result

    def git(self, root: Path, *argv: str):
        return self.command("git", *argv, cwd=root)

    def template(self, name: str = "template") -> Path:
        target = self.base / name
        shutil.copytree(PUBLIC_TEMPLATE, target)
        return target

    def project(self, name: str = "demo") -> Path:
        template = self.template("template-" + name)
        bundle = self.base / ("bundle-" + name)
        self.command(
            "python3", str(HARNESSCTL), "package", "--template", str(template),
            "--version", "2.0.0-b1", "--output", str(bundle),
        )
        root = self.base / name
        self.command(
            "python3", str(HARNESSCTL), "new", str(root), "--source", str(bundle),
            "--project-id", name, "--goal", "Goal", "--scope", "Scope",
        )
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Test")
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", "initial")
        return root

    def ctl(self, root: Path, *argv: str, ok: bool = True, env=None):
        return self.command(
            "python3", str(root / "tools/projectctl.py"), "--root", str(root),
            *argv, cwd=root, ok=ok, env=env,
        )

    def create_codex_task(
        self,
        root: Path,
        name: str,
        reasoning: str = "ultra",
        token_limit: int | None = None,
        context_ref: str | None = None,
    ) -> None:
        argv = [
            "task", "create", name, "--goal", "Agent task", "--scope", "One file",
            "--output", "src/result.txt", "--acceptance", "Verified",
            "--owned-path", "task-output", "--validation-command", "python3 -c pass",
            "--codex", "--reasoning-effort", reasoning, "--reasoning-fallback", "high",
            "--sandbox", "workspace-write", "--approval-policy", "never",
            "--web-mode", "disabled", "--no-network-access", "--allowed-tool", "shell",
            "--allowed-mcp", "missing", "--allow-missing-mcp", "--time-limit", "2",
            "--agent-role", "implementation",
        ]
        if token_limit is not None:
            argv.extend(("--token-limit", str(token_limit)))
        if context_ref:
            argv.extend(("--context-ref", context_ref))
        self.ctl(root, *argv)

    def commit_state(self, root: Path, message: str) -> None:
        self.git(root, "add", ".harness")
        self.git(root, "commit", "-m", message)

    def start(self, root: Path, name: str) -> None:
        self.ctl(root, "task", "start", name)

    def test_project_amendment_previews_markdown_and_context_uses_canonical_state(self) -> None:
        root = self.project()
        proposal = root / "docs/project-amendment.md"
        proposal.write_text(
            self.ctl(root, "show", "project").stdout
            .replace("\nGoal\n", "\nRevised goal\n", 1)
            .replace("- Scope", "- Revised scope", 1)
            .replace("\nGoal\n\n## Canonical Roots", "\nRevised objective\n\n## Canonical Roots", 1)
        )
        preview = json.loads(
            self.ctl(
                root, "project", "amend", "--from-markdown", "docs/project-amendment.md",
                "--reason", "User refined the project", "--actor", "user",
            ).stdout
        )
        self.assertFalse(preview["applied"])
        self.assertEqual(1, preview["expected_revision"])
        self.assertEqual("Goal", json.loads((root / ".harness/project.json").read_text())["goal"])
        before = json.loads(self.ctl(root, "context", "--json").stdout)
        self.assertEqual("Goal", before["goal"])

        applied = json.loads(
            self.ctl(
                root, "project", "amend", "--from-markdown", "docs/project-amendment.md",
                "--reason", "User refined the project", "--actor", "user",
                "--expected-revision", "1", "--apply",
            ).stdout
        )
        self.assertTrue(applied["applied"])
        self.assertEqual(2, applied["new_revision"])
        context = json.loads(self.ctl(root, "context", "--json").stdout)
        self.assertEqual("v2", context["authority"])
        self.assertEqual("Revised goal", context["goal"])
        self.assertEqual("Revised objective", context["current_goal"])
        self.assertIn(".harness/project.json", context["sources"])
        self.assertIn("User refined the project", self.ctl(root, "show", "project").stdout)
        self.ctl(root, "check")

        stale = self.ctl(
            root, "project", "amend", "--goal", "Another goal",
            "--reason", "Stale update", "--actor", "user",
            "--expected-revision", "1", "--apply", ok=False,
        )
        self.assertIn("stale Project revision", stale.stderr)
        missing_approval = self.ctl(
            root, "project", "amend", "--goal", "Agent goal",
            "--reason", "Agent proposal", "--actor", "agent", ok=False,
        )
        self.assertIn("user approval reference", missing_approval.stderr)

    def test_task_amendment_updates_ready_contract_and_rejects_active_change(self) -> None:
        root = self.project()
        self.ctl(
            root, "task", "create", "draft-one", "--goal", "Draft goal",
            "--scope", "Draft scope", "--output", "src/old.txt",
            "--acceptance", "Old acceptance", "--owned-path", "task-output",
            "--validation-command", "python3 -c pass",
        )
        proposal = root / "docs/task-amendment.md"
        proposal.write_text(
            self.ctl(root, "task", "show", "draft-one").stdout
            .replace("\nDraft goal\n", "\nRevised Task goal\n", 1)
            .replace("`src/old.txt`", "`src/new.txt`", 1)
            .replace("- Old acceptance", "- New acceptance", 1)
        )
        preview = json.loads(
            self.ctl(
                root, "task", "amend", "draft-one", "--from-markdown",
                "docs/task-amendment.md", "--model", "gpt-test",
                "--reason", "Approved contract refinement", "--actor", "agent",
                "--approval-ref", "user-message:42",
            ).stdout
        )
        self.assertFalse(preview["applied"])
        self.assertIn("execution", preview["changes"])
        applied = json.loads(
            self.ctl(
                root, "task", "amend", "draft-one", "--from-markdown",
                "docs/task-amendment.md", "--model", "gpt-test",
                "--reason", "Approved contract refinement", "--actor", "agent",
                "--approval-ref", "user-message:42", "--expected-revision", "1", "--apply",
            ).stdout
        )
        self.assertEqual(2, applied["new_revision"])
        task = json.loads((root / ".harness/tasks/draft-one/task.json").read_text())
        self.assertEqual("Revised Task goal", task["goal"])
        self.assertEqual(["src/new.txt"], task["outputs"])
        self.assertEqual("gpt-test", task["execution"]["model"])
        self.assertIn("task-output", task["owned_write_paths"])
        self.assertIn(".harness-agent-handoff.json", task["owned_write_paths"])
        task_context = json.loads(self.ctl(root, "context", "--task", "draft-one", "--json").stdout)
        self.assertEqual("Revised Task goal", task_context["final_goal"])
        self.assertEqual(2, task_context["revision"])
        self.ctl(root, "check")

        self.commit_state(root, "amend task")
        self.start(root, "draft-one")
        rejected = self.ctl(
            root, "task", "amend", "draft-one", "--goal", "Mid-run change",
            "--reason", "Unsafe", "--actor", "user", ok=False,
        )
        self.assertIn("can only be amended while ready", rejected.stderr)

    def test_capability_fallback_is_applied_to_real_argv_and_handoff(self) -> None:
        root = self.project()
        self.create_codex_task(root, "agent-one")
        task_view = self.ctl(root, "task", "show", "agent-one").stdout
        self.assertIn("## Outputs", task_view)
        self.assertIn("## Validation Commands", task_view)
        self.assertIn("Post-run token ceiling", task_view)
        self.commit_state(root, "create agent task")
        self.start(root, "agent-one")
        capture = self.base / "capture.json"
        environment = os.environ.copy()
        environment["FAKE_CAPTURE"] = str(capture)
        result = json.loads(
            self.ctl(
                root, "task", "run", "agent-one", "--codex-bin", str(self.fake_codex),
                env=environment,
            ).stdout
        )
        self.assertEqual("review", result["status"])
        handoff = result["handoff"]
        self.assertEqual("thread-test", handoff["agent_run"]["thread_id"])
        self.assertEqual("high", handoff["agent_run"]["effective_contract"]["reasoning_effort"])
        self.assertEqual(["missing"], handoff["agent_run"]["fallbacks"][1]["removed"])
        captured = json.loads(capture.read_text())
        self.assertIn('model_reasoning_effort="high"', captured["argv"])
        self.assertIn('web_search="disabled"', captured["argv"])
        self.assertIn("Agent task", captured["prompt"])
        self.assertIn("parent Agent reviews", captured["prompt"])
        review = self.ctl(root, "task", "review", "agent-one").stdout
        self.assertIn("## Findings", review)
        self.assertIn("## Limitations", review)
        self.assertIn("## Codex Execution Contract", review)

    def test_decision_pauses_only_its_task_and_explicit_resolution_resumes_it(self) -> None:
        root = self.project()
        self.create_codex_task(root, "agent-one", "medium")
        self.create_codex_task(root, "agent-two", "medium")
        self.commit_state(root, "create tasks")
        self.start(root, "agent-one")
        self.commit_state(root, "start one")
        self.start(root, "agent-two")
        self.commit_state(root, "start two")
        environment = os.environ.copy()
        environment["FAKE_CODEX_MODE"] = "decision"
        outcome = json.loads(
            self.ctl(root, "task", "run", "agent-one", "--codex-bin", str(self.fake_codex), env=environment).stdout
        )
        self.assertEqual("needs_decision", outcome["status"])
        one = json.loads((root / ".harness/tasks/agent-one/task.json").read_text())
        two = json.loads((root / ".harness/tasks/agent-two/task.json").read_text())
        self.assertEqual("needs_decision", one["state"]["task_status"])
        self.assertEqual("active", two["state"]["task_status"])
        view = self.ctl(root, "decision", "show", outcome["decision_id"]).stdout
        self.assertIn("recommended", view)
        self.assertIn("Safe default: keep-local", view)
        self.ctl(
            root, "decision", "resolve", outcome["decision_id"], "--choice", "keep-local",
            "--actor", "user", "--note", "Keep this local",
        )
        one = json.loads((root / ".harness/tasks/agent-one/task.json").read_text())
        self.assertEqual("active", one["state"]["task_status"])

    def test_permission_timeout_and_token_limit_become_task_local_states(self) -> None:
        for index, mode in enumerate(("permission", "timeout", "tokens", "malformed"), 1):
            root = self.project("case-" + str(index))
            self.create_codex_task(root, "agent-one", "medium", token_limit=100 if mode == "tokens" else None)
            self.commit_state(root, "create")
            self.start(root, "agent-one")
            environment = os.environ.copy()
            environment["FAKE_CODEX_MODE"] = mode
            outcome = json.loads(
                self.ctl(root, "task", "run", "agent-one", "--codex-bin", str(self.fake_codex), env=environment).stdout
            )
            expected = "needs_decision" if mode == "permission" else "blocked"
            self.assertEqual(expected, outcome["status"])
            task = json.loads((root / ".harness/tasks/agent-one/task.json").read_text())
            self.assertEqual(expected, task["state"]["task_status"])

    def test_result_index_is_readable_and_injected_by_stable_reference(self) -> None:
        root = self.project()
        (root / "docs/result.md").write_text("# Parser result\n")
        self.ctl(
            root, "result", "add", "experiment-one", "--kind", "experiment",
            "--summary", "Prior parser experiment passed", "--source-ref", "task:old-task",
            "--artifact-ref", "docs/result.md", "--verification-status", "verified",
            "--reviewed-by", "parent-agent", "--verification-note", "Reviewed result",
            "--reusable",
        )
        indexed = json.loads(self.ctl(root, "result", "list").stdout)
        self.assertEqual("experiment-one", indexed[0]["id"])
        filtered = json.loads(
            self.ctl(root, "result", "list", "--kind", "experiment", "--reusable").stdout
        )
        self.assertEqual(["experiment-one"], [item["id"] for item in filtered])
        view = self.ctl(root, "result", "show", "experiment-one").stdout
        self.assertIn("Prior parser experiment passed", view)
        self.assertIn("Reviewed by: parent-agent", view)
        self.assertIn("SHA-256", view)
        artifact = root / "docs/result.md"
        original_artifact = artifact.read_text()
        artifact.write_text("changed after review\n")
        damaged = self.ctl(root, "check", ok=False)
        self.assertIn("artifact digest mismatch", damaged.stderr)
        artifact.write_text(original_artifact)
        self.ctl(root, "check")
        self.create_codex_task(root, "agent-one", "medium", context_ref="result:experiment-one")
        self.commit_state(root, "result and task")
        self.start(root, "agent-one")
        capture = self.base / "result-context.json"
        environment = os.environ.copy()
        environment["FAKE_CAPTURE"] = str(capture)
        self.ctl(root, "task", "run", "agent-one", "--codex-bin", str(self.fake_codex), env=environment)
        prompt = json.loads(capture.read_text())["prompt"]
        self.assertIn("result:experiment-one", prompt)
        self.assertIn("Prior parser experiment passed", prompt)

    def test_concurrent_result_add_is_serialized_and_index_is_rebuildable(self) -> None:
        root = self.project()
        commands = []
        for index in (1, 2):
            artifact = root / "docs" / ("result-" + str(index) + ".md")
            artifact.write_text("result " + str(index) + "\n")
            commands.append(
                [
                    "python3", str(root / "tools/projectctl.py"), "--root", str(root),
                    "result", "add", "result-" + str(index), "--kind", "experiment",
                    "--summary", "Concurrent result " + str(index),
                    "--artifact-ref", artifact.relative_to(root).as_posix(),
                    "--verification-status", "unverified",
                ]
            )
        processes = [
            subprocess.Popen(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for command in commands
        ]
        outcomes = [process.communicate(timeout=10) + (process.returncode,) for process in processes]
        self.assertEqual([0, 0], [item[2] for item in outcomes], outcomes)
        indexed = json.loads(self.ctl(root, "result", "list").stdout)
        self.assertEqual(["result-1", "result-2"], [item["id"] for item in indexed])
        (root / ".harness/results/index.json").unlink()
        self.ctl(root, "result", "rebuild")
        self.ctl(root, "check")

    def test_misleading_full_access_network_contract_is_rejected(self) -> None:
        root = self.project()
        self.ctl(
            root, "task", "create", "unsafe-agent", "--goal", "Unsafe", "--scope", "One file",
            "--codex", "--sandbox", "danger-full-access", "--approval-policy", "never",
            "--web-mode", "disabled", "--no-network-access", "--allowed-tool", "shell",
        )
        self.commit_state(root, "create unsafe task")
        self.start(root, "unsafe-agent")
        rejected = self.ctl(
            root, "task", "run", "unsafe-agent", "--codex-bin", str(self.fake_codex), ok=False,
        )
        self.assertIn("cannot promise network isolation", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
