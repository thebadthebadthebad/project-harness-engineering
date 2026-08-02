"""Bounded v2 Task input contract tests."""

from __future__ import annotations

import hashlib
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


class BoundedInputsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        template = self.base / "template"
        shutil.copytree(PUBLIC_TEMPLATE, template)
        bundle = self.base / "bundle"
        self.command(
            "python3", str(HARNESSCTL), "package", "--template", str(template),
            "--version", "2.0.0-input", "--output", str(bundle),
        )
        self.root = self.base / "project"
        self.command(
            "python3", str(HARNESSCTL), "new", str(self.root), "--source", str(bundle),
            "--project-id", "input-pilot", "--goal", "Goal", "--scope", "Scope",
        )
        self.command("git", "config", "user.email", "test@example.com", cwd=self.root)
        self.command("git", "config", "user.name", "Test", cwd=self.root)
        (self.root / "src/input.py").write_text("VALUE = 42\n")
        self.command("git", "add", ".", cwd=self.root)
        self.command("git", "commit", "-m", "initial", cwd=self.root)
        self.fake = self.base / "fake-codex"
        self.fake.write_text(
            """#!/usr/bin/env python3
import json, os, pathlib, sys
a=sys.argv[1:]
if a==['--version']: print('codex-cli test'); raise SystemExit
if a[:2]==['exec','--help']: print('--json --output-schema --output-last-message --sandbox --model --config --cd'); raise SystemExit
if a[:3]==['mcp','list','--json']: print('[]'); raise SystemExit
p=sys.stdin.read(); pathlib.Path(os.environ['CAPTURE']).write_text(p)
o=pathlib.Path(a[a.index('-o')+1]); o.write_text(json.dumps({'status':'completed','summary':'ok','findings':[],'limitations':[],'candidates':[],'decision_request':None,'blocked_reason':None}))
print(json.dumps({'type':'thread.started','thread_id':'input-thread'})); print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':1,'reasoning_output_tokens':0}}))
"""
        )
        self.fake.chmod(0o755)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(self, *argv: str, cwd: Path | None = None, ok: bool = True, env=None):
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, env=env)
        if ok and result.returncode:
            self.fail(result.stderr + result.stdout)
        return result

    def ctl(self, *argv: str, ok: bool = True, env=None):
        return self.command(
            "python3", str(self.root / "tools/projectctl.py"), "--root", str(self.root),
            *argv, cwd=self.root, ok=ok, env=env,
        )

    def create(self, name: str, input_path: str = "src/input.py") -> None:
        self.ctl(
            "task", "create", name, "--goal", "Review input", "--scope", "Input only",
            "--input", input_path, "--output", "Review", "--acceptance", "Grounded",
            "--codex", "--reasoning-effort", "low", "--sandbox", "read-only",
            "--approval-policy", "never", "--web-mode", "disabled", "--no-network-access",
            "--allowed-tool", "shell", "--time-limit", "10",
        )

    def test_input_content_digest_and_size_are_in_prompt_and_run_evidence(self) -> None:
        self.create("input-task")
        self.command("git", "add", ".harness", cwd=self.root)
        self.command("git", "commit", "-m", "create task", cwd=self.root)
        started = json.loads(self.ctl("task", "start", "input-task").stdout)
        capture = self.base / "prompt.txt"
        environment = os.environ.copy()
        environment["CAPTURE"] = str(capture)
        outcome = json.loads(
            self.ctl("task", "run", "input-task", "--codex-bin", str(self.fake), env=environment).stdout
        )
        self.assertEqual("review", outcome["status"])
        prompt = capture.read_text()
        expected = hashlib.sha256(b"VALUE = 42\n").hexdigest()
        self.assertIn("VALUE = 42", prompt)
        self.assertIn(expected, prompt)
        run = json.loads(Path(outcome["evidence"]).read_text())
        self.assertEqual(
            [{"path": "src/input.py", "sha256": expected, "bytes": 11}], run["inputs"]
        )

    def test_task_view_lists_bounded_input_metadata_and_empty_state(self) -> None:
        expected = hashlib.sha256(b"VALUE = 42\n").hexdigest()
        self.create("input-view")
        view = self.ctl("task", "show", "input-view").stdout
        self.assertIn("## Inputs", view)
        self.assertIn("`src/input.py` (11 bytes, SHA-256 `" + expected + "`)", view)

        self.ctl("task", "create", "empty-view", "--goal", "No input", "--scope", "View only")
        empty_view = self.ctl("task", "show", "empty-view").stdout
        self.assertIn("## Inputs\n\n- None", empty_view)

    def test_unsafe_binary_oversize_and_post_contract_drift_are_blocked(self) -> None:
        unsafe = self.ctl(
            "task", "create", "unsafe", "--goal", "x", "--scope", "x", "--input", "../x",
            "--codex", ok=False,
        )
        self.assertIn("invalid Task destination", unsafe.stderr)
        (self.root / "src/binary.bin").write_bytes(b"\x00x")
        binary = self.ctl(
            "task", "create", "binary", "--goal", "x", "--scope", "x",
            "--input", "src/binary.bin", "--codex", ok=False,
        )
        self.assertIn("binary Task input", binary.stderr)
        (self.root / "src/large.txt").write_text("x" * 131073)
        large = self.ctl(
            "task", "create", "large", "--goal", "x", "--scope", "x",
            "--input", "src/large.txt", "--codex", ok=False,
        )
        self.assertIn("default file limit", large.stderr)

        self.create("drift")
        self.command("git", "add", ".harness", cwd=self.root)
        self.command("git", "commit", "-m", "create drift", cwd=self.root)
        started = json.loads(self.ctl("task", "start", "drift").stdout)
        (Path(started["workspace"]) / "src/input.py").write_text("VALUE = 99\n")
        outcome = json.loads(
            self.ctl("task", "run", "drift", "--codex-bin", str(self.fake)).stdout
        )
        self.assertEqual("blocked", outcome["status"])
        self.assertIn("changed after contract creation", outcome["reason"])


if __name__ == "__main__":
    unittest.main()
