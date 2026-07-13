"""Regression and boundary tests for the modular projectctl candidate."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
CANDIDATE = REPOSITORY / "project/tools"
PUBLIC_TEMPLATE = REPOSITORY / "project"
sys.path.insert(0, str(CANDIDATE))

from project_harness.documents import atomic_write_text  # noqa: E402


class WorkflowCoreTest(unittest.TestCase):
    """Exercise public commands against a copied Project template."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project"
        shutil.copytree(PUBLIC_TEMPLATE, self.root)
        (self.root / "src/example.py").write_text("VALUE = 1\n")
        (self.root / "data/example.txt").write_text("data\n")
        self.tool = self.root / "tools/projectctl.py"
        self.git("init")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Harness Test")
        self.git("add", ".")
        self.git("commit", "-m", "initial")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run one successful Git command in the fixture Project."""
        return subprocess.run(
            ("git", *args), cwd=self.root, text=True, capture_output=True, check=True
        )

    def command(
        self,
        *args: str,
        ok: bool = True,
        cwd: Path | None = None,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run candidate projectctl and optionally require success."""
        env = os.environ.copy()
        env.update(environment or {})
        result = subprocess.run(
            ("python3", str(self.tool), "--root", str(self.root), *args),
            cwd=cwd or self.root,
            env=env,
            text=True,
            capture_output=True,
        )
        if ok and result.returncode:
            self.fail(result.stderr)
        return result

    def create_ready(self, name: str = "research-one") -> Path:
        """Create and fill the deterministic ready-state fixture."""
        self.command("task", "create", name, "--goal", "Answer the question")
        task = self.root / "tasks" / name
        contract = task / "TASK.md"
        text = contract.read_text()
        text = text.replace("## Scope\n\nTBD", "## Scope\n\nDefined scope")
        text = text.replace("TBD\n```", "Run the work\n```")
        text = text.replace("## Outputs\n\nTBD", "## Outputs\n\noutput/result.txt")
        text = text.replace("## Completion Criteria\n\nTBD", "## Completion Criteria\n\nResult is verified")
        contract.write_text(text)
        status = task / "STATUS.md"
        text = status.read_text().replace("| TBD | todo |", "| Execute work | todo |")
        status.write_text(text.replace("## Current Work\n\nTBD", "## Current Work\n\nExecute work"))
        return task

    def activate_and_baseline(self, name: str = "research-one") -> Path:
        """Create, activate, commit, and baseline one fixture Task."""
        task = self.create_ready(name)
        self.command("task", "validate", name, "--phase", "ready")
        self.command("task", "activate", name)
        self.git("add", ".")
        self.git("commit", "-m", "activate")
        self.command("task", "baseline", name)
        return task

    def finish(self, task: Path, outcome: str = "completed") -> None:
        """Write a complete Task STATUS, output, and REPORT fixture."""
        status = task / "STATUS.md"
        text = status.read_text().replace("\ndoing\n", "\n" + outcome + "\n", 1)
        text = text.replace("| Execute work | doing |", "| Execute work | completed |")
        status.write_text(text.replace("## Current Work\n\nExecute work", "## Current Work\n\nNone"))
        (task / "output/result.txt").write_text("verified\n")
        report = task / "REPORT.md"
        text = report.read_text().replace("## Outcome\n\nTBD", "## Outcome\n\n" + outcome)
        for heading, body in {
            "Summary": "Reviewable result.",
            "Final Goal and Result": "Goal reached.",
            "Findings": "One deterministic finding.",
            "Work and Validation": "Checked output/result.txt.",
            "Limitations": "Synthetic fixture.",
            "Project Follow-up": "Review the candidate.",
        }.items():
            text = text.replace("## " + heading + "\n\nTBD", "## " + heading + "\n\n" + body)
        text = text.replace("| TBD | TBD | TBD |", "| output/result.txt | output | Verified result |")
        report.write_text(text)

    def test_existing_lifecycle_and_dynamic_handoff(self) -> None:
        task = self.activate_and_baseline()
        self.finish(task)
        before = json.loads(self.command("context", "--json").stdout)
        self.assertIn("research-one", before["handoffs"])
        self.assertNotIn("lifecycle_commands", before)
        handoff = json.loads(self.command("task", "handoff", "research-one", "--json").stdout)
        self.assertEqual("completed", handoff["outcome"])
        self.command("task", "close", "research-one")
        after = json.loads(self.command("context", "--json").stdout)
        self.assertEqual({}, after["handoffs"])
        self.assertEqual({"PROJECT.md", "STATE.md"}, set(after["sources"]))
        self.command(
            "promotion", "record", "research-one", "--decision", "promoted",
            "--path", "tools/result.py",
        )
        history = next((self.root / "docs/history").glob("*-completed-research-one.md"))
        self.assertIn("Promotion: promoted", history.read_text())
        self.assertIn("tools/result.py", history.read_text())

    def test_task_role_allows_own_context_and_validate_only(self) -> None:
        task = self.create_ready()
        environment = {
            "HARNESS_SESSION_ROLE": "task",
            "HARNESS_TASK_NAME": "research-one",
            "HARNESS_RUN_ID": "test-run",
        }
        self.command("context", "--json", cwd=task, environment=environment)
        self.command(
            "task", "validate", "research-one", "--phase", "ready",
            cwd=task, environment=environment,
        )
        denied = self.command(
            "task", "activate", "research-one", ok=False, cwd=task, environment=environment
        )
        self.assertIn("unavailable in a Task session", denied.stderr)
        other = self.command(
            "task", "validate", "other-task", ok=False, cwd=task, environment=environment
        )
        self.assertIn("validate only research-one", other.stderr)
        events = self.root / ".git/harness/observability/test-run/events.jsonl"
        self.assertTrue(events.is_file())
        self.assertEqual("context", json.loads(events.read_text().splitlines()[0])["event"])

    def test_check_and_nested_linked_data_keys(self) -> None:
        collection = self.root / "data/collection"
        (collection / "a").mkdir(parents=True)
        (collection / "b").mkdir()
        (collection / "a/same.txt").write_text("a\n")
        (collection / "b/same.txt").write_text("b\n")
        self.git("add", ".")
        self.git("commit", "-m", "data")
        task = self.create_ready()
        shutil.rmtree(task / "data")
        (task / "data").mkdir()
        (task / "data/collection").symlink_to(collection)
        self.command("task", "activate", "research-one")
        self.git("add", ".")
        self.git("commit", "-m", "activate")
        self.command("task", "baseline", "research-one")
        metadata = json.loads(
            (self.root / ".git/harness/tasks/research-one.json").read_text()
        )
        keys = set(metadata["linked_data"])
        self.assertIn("data/collection:a/same.txt", keys)
        self.assertIn("data/collection:b/same.txt", keys)
        self.command("check")
        (self.root / "docs/adr/2026-bad.md").write_text("# bad\n")
        invalid = self.command("check", ok=False)
        self.assertIn("invalid ADR filename", invalid.stderr)

    def test_atomic_write_preserves_original_on_replace_failure(self) -> None:
        path = self.root / "atomic.txt"
        path.write_text("original\n")
        with mock.patch("project_harness.documents.os.replace", side_effect=OSError("failure")):
            with self.assertRaises(OSError):
                atomic_write_text(path, "changed\n")
        self.assertEqual("original\n", path.read_text())

    def test_create_project_refuses_existing_destination(self) -> None:
        destination = Path(self.temporary.name) / "created"
        result = subprocess.run(
            (
                "python3", str(REPOSITORY / "tools/create_project.py"), str(destination),
                "--template", str(self.root),
            ),
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((destination / ".git").is_dir())
        again = subprocess.run(
            (
                "python3", str(REPOSITORY / "tools/create_project.py"), str(destination),
                "--template", str(self.root),
            ),
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(0, again.returncode)
        self.assertIn("already exists", again.stderr)


if __name__ == "__main__":
    unittest.main()
