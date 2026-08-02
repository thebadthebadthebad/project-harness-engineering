"""Regression for pre-v2 Project installation and semantic migration."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PUBLIC_TEMPLATE = REPOSITORY / "project"
HARNESSCTL = REPOSITORY / "tools/harnessctl.py"


class LegacyCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.template = self.base / "template"
        shutil.copytree(PUBLIC_TEMPLATE, self.template)
        self.bundle = self.base / "bundle"
        self.command(
            "python3", str(HARNESSCTL), "package",
            "--template", str(self.template), "--version", "2.0.0-repair",
            "--output", str(self.bundle),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(self, *argv: str, cwd: Path | None = None, ok: bool = True):
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
        if ok and result.returncode:
            self.fail("command failed: " + " ".join(argv) + "\n" + result.stderr + result.stdout)
        return result

    def ctl(self, root: Path, *argv: str, ok: bool = True):
        return self.command(
            "python3", str(root / "tools/projectctl.py"), "--root", str(root),
            *argv, cwd=root, ok=ok,
        )

    def digest(self, root: Path, relative: str) -> str:
        return hashlib.sha256((root / relative).read_bytes()).hexdigest()

    def test_install_precedes_semantic_migration_and_preserves_legacy_meaning(self) -> None:
        root = self.base / "legacy"
        shutil.copytree(self.template, root)
        shutil.rmtree(root / "tools/project_harness")
        old_tool = root / "tools/projectctl.py"
        old_tool.write_text("#!/usr/bin/env python3\nraise SystemExit('old tool')\n")
        task = root / "tasks/legacy-task"
        shutil.copytree(root / "tasks/_template", task)
        task_file = task / "TASK.md"
        task_file.write_text(
            task_file.read_text().replace("## Scope\n\nTBD", "## Scope\n\nLegacy scope")
            .replace("TBD\n```", "Perform legacy work\n```")
            .replace("## Outputs\n\nTBD", "## Outputs\n\noutput/result.txt")
            .replace("## Completion Criteria\n\nTBD", "## Completion Criteria\n\nVerified")
        )
        status = task / "STATUS.md"
        status.write_text(
            status.read_text().replace("## Final Goal\n\nTBD", "## Final Goal\n\nLegacy goal")
            .replace("| TBD | todo |", "| Work | todo |")
            .replace("## Current Work\n\nTBD", "## Current Work\n\nWork")
        )
        state = root / "STATE.md"
        state.write_text(
            state.read_text().replace(
                "| Task | Status |\n| --- | --- |",
                "| Task | Status | Path | Note |\n| --- | --- | --- | --- |\n"
                "| legacy-task | todo | tasks/legacy-task | preserved note |",
            )
        )
        (root / "docs/history/2026-01-01-0101-promoted-legacy-task.md").write_text(
            "# Legacy Promotion\n\nPreserve exactly.\n"
        )
        (root / "AGENTS.md").write_text("# Project-specific rules\n")
        subprocess.run(("git", "init"), cwd=root, check=True, capture_output=True)
        self.command("git", "config", "user.email", "test@example.com", cwd=root)
        self.command("git", "config", "user.name", "Test", cwd=root)
        self.command("git", "add", ".", cwd=root)
        self.command("git", "commit", "-m", "legacy baseline", cwd=root)
        protected = {
            name: self.digest(root, name) for name in ("PROJECT.md", "STATE.md", "AGENTS.md")
        }

        applied = self.command(
            "python3", str(HARNESSCTL), "apply", str(root),
            "--source", str(self.bundle), "--apply",
        )
        self.assertTrue(json.loads(applied.stdout)["applied"])
        self.assertEqual(
            protected,
            {name: self.digest(root, name) for name in protected},
        )
        self.ctl(root, "check", "--installation-only")
        self.command("git", "add", ".", cwd=root)
        self.command("git", "commit", "-m", "install migration tools", cwd=root)
        plan = json.loads(self.ctl(root, "migrate", "plan").stdout)
        self.assertTrue(plan["semantic_parity"])
        self.ctl(root, "migrate", "apply", "compatibility")
        self.assertTrue(
            json.loads(self.ctl(root, "migrate", "verify", "compatibility").stdout)["semantic_parity"]
        )
        candidate = json.loads(
            (root / ".harness/migrations/compatibility/candidate/tasks/legacy-task/task.json").read_text()
        )
        self.assertEqual(
            ["tasks/legacy-task", "preserved note"],
            candidate["state"]["legacy_state_extra"],
        )
        history = json.loads(
            (root / ".harness/migrations/compatibility/candidate/legacy-history.json").read_text()
        )
        self.assertIn("Preserve exactly.", history["items"][0]["text"])
        self.ctl(root, "migrate", "switch", "compatibility", "--harness-version", "2.0.0-repair")
        self.ctl(root, "check")
        self.ctl(root, "migrate", "rollback", "compatibility")


if __name__ == "__main__":
    unittest.main()
