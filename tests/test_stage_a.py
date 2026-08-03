"""Stage A distribution, migration, isolation, and Promotion acceptance tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PUBLIC_TEMPLATE = REPOSITORY / "project"
HARNESSCTL = REPOSITORY / "tools/harnessctl.py"


class StageATest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def command(self, *argv: str, cwd: Path | None = None, ok: bool = True):
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
        if ok and result.returncode:
            self.fail("command failed: " + " ".join(argv) + "\n" + result.stderr + result.stdout)
        return result

    def git(self, root: Path, *argv: str, ok: bool = True):
        return self.command("git", *argv, cwd=root, ok=ok)

    def candidate_template(self, name: str = "template") -> Path:
        target = self.base / name
        shutil.copytree(PUBLIC_TEMPLATE, target)
        return target

    def package(self, template: Path, version: str, name: str) -> Path:
        bundle = self.base / name
        self.command(
            "python3", str(HARNESSCTL), "package", "--template", str(template),
            "--version", version, "--output", str(bundle)
        )
        return bundle

    def new_project(self, bundle: Path, name: str = "demo") -> Path:
        root = self.base / name
        self.command(
            "python3", str(HARNESSCTL), "new", str(root), "--source", str(bundle),
            "--project-id", name, "--goal", "Goal " + name, "--scope", "Scope " + name,
        )
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Test")
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", "initial")
        return root

    def ctl(self, root: Path, *argv: str, ok: bool = True):
        return self.command(
            "python3", str(root / "tools/projectctl.py"), "--root", str(root),
            *argv, cwd=root, ok=ok,
        )

    def test_new_initializes_v2_and_human_view_matches_json(self) -> None:
        bundle = self.package(self.candidate_template(), "2.0.0-a1", "bundle")
        root = self.new_project(bundle)
        install = json.loads((root / ".harness/install.json").read_text())
        project = json.loads((root / ".harness/project.json").read_text())
        view = self.ctl(root, "show", "project").stdout
        self.assertEqual("v2", install["authority"])
        self.assertEqual("Goal demo", project["goal"])
        self.assertIn(project["content_digest"], view)
        self.assertIn("Goal demo", view)
        self.assertFalse(self.git(root, "status", "--porcelain").stdout)

    def test_apply_preserves_project_files_and_update_conflict_or_rollback(self) -> None:
        first_template = self.candidate_template("template-one")
        first = self.package(first_template, "2.0.0-a1", "bundle-one")
        root = self.new_project(first)
        (root / "README.md").write_text("Project-specific README\n")
        (root / "AGENTS.md").write_text("Project-specific rules\n")

        second_template = self.candidate_template("template-two")
        (second_template / "GUIDE.md").write_text("Harness guide v2\n")
        second = self.package(second_template, "2.0.0-a2", "bundle-two")
        dry_run = json.loads(
            self.command(
                "python3", str(HARNESSCTL), "update", str(root), "--source", str(second)
            ).stdout
        )
        guide_action = next(item for item in dry_run["actions"] if item["path"] == "GUIDE.md")
        self.assertEqual("replace", guide_action["action"])
        self.assertEqual("Project-specific README\n", (root / "README.md").read_text())
        self.assertEqual("Project-specific rules\n", (root / "AGENTS.md").read_text())

        (root / "GUIDE.md").write_text("Local guide edit\n")
        conflict = self.command(
            "python3", str(HARNESSCTL), "update", str(root), "--source", str(second),
            "--apply", ok=False,
        )
        self.assertIn("managed file conflicts: GUIDE.md", conflict.stderr)
        self.assertEqual("Local guide edit\n", (root / "GUIDE.md").read_text())

        rollback_root = self.new_project(first, "rollback")
        old_hooks = (rollback_root / ".codex/hooks.json").read_text()
        bad_template = self.candidate_template("template-bad")
        (bad_template / ".codex/hooks.json").write_text("{ invalid json\n")
        bad = self.package(bad_template, "2.0.0-bad", "bundle-bad")
        failed = self.command(
            "python3", str(HARNESSCTL), "update", str(rollback_root),
            "--source", str(bad), "--apply", ok=False,
        )
        self.assertNotEqual(0, failed.returncode)
        self.assertEqual(old_hooks, (rollback_root / ".codex/hooks.json").read_text())
        self.assertEqual(
            "2.0.0-a1",
            json.loads((rollback_root / ".harness/install.json").read_text())["harness_version"],
        )

    def test_first_apply_requires_replace_ack_and_managed_paths_reject_symlinks(self) -> None:
        bundle = self.package(self.candidate_template("source"), "2.0.0-a1", "bundle")
        root = self.candidate_template("existing")
        (root / "GUIDE.md").write_text("Existing local guide\n")
        refused = self.command(
            "python3", str(HARNESSCTL), "apply", str(root), "--source", str(bundle),
            "--apply", ok=False,
        )
        self.assertIn("--accept-managed-replace", refused.stderr)
        self.command(
            "python3", str(HARNESSCTL), "apply", str(root), "--source", str(bundle),
            "--apply", "--accept-managed-replace",
        )

        unsafe = self.candidate_template("unsafe")
        shutil.rmtree(unsafe / ".codex")
        outside = self.base / "outside"
        outside.mkdir()
        (unsafe / ".codex").symlink_to(outside, target_is_directory=True)
        rejected = self.command(
            "python3", str(HARNESSCTL), "apply", str(unsafe), "--source", str(bundle),
            ok=False,
        )
        self.assertIn("symlink is not allowed", rejected.stderr)

        unsafe_template = self.candidate_template("unsafe-template")
        (unsafe_template / "GUIDE.md").unlink()
        (unsafe_template / "GUIDE.md").symlink_to(self.base / "external-guide.md")
        packaged = self.command(
            "python3", str(HARNESSCTL), "package", "--template", str(unsafe_template),
            "--version", "unsafe", "--output", str(self.base / "unsafe-bundle"), ok=False,
        )
        self.assertIn("symlink is not allowed in template", packaged.stderr)

    def test_legacy_conversion_parity_switch_guard_and_rollback(self) -> None:
        root = self.candidate_template("legacy")
        self.git(root, "init")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Test")
        self.ctl(root, "task", "create", "legacy-task", "--goal", "Legacy goal")
        task = root / "tasks/legacy-task"
        task_file = task / "TASK.md"
        text = task_file.read_text().replace("## Scope\n\nTBD", "## Scope\n\nLegacy scope")
        text = text.replace("TBD\n```", "Perform legacy work\n```")
        text = text.replace("## Outputs\n\nTBD", "## Outputs\n\noutput/result.txt")
        text = text.replace("## Completion Criteria\n\nTBD", "## Completion Criteria\n\nVerified")
        task_file.write_text(text)
        status = task / "STATUS.md"
        status.write_text(
            status.read_text().replace("| TBD | todo |", "| Work | todo |")
            .replace("## Current Work\n\nTBD", "## Current Work\n\nWork")
        )
        (root / "docs/history/2026-01-01-fixture.md").write_text("# retained history\n")
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", "legacy baseline")

        plan = json.loads(self.ctl(root, "migrate", "plan").stdout)
        self.assertTrue(plan["semantic_parity"])
        self.assertIn("tasks/legacy-task/task.json", plan["records"])
        self.ctl(root, "migrate", "apply", "legacy-to-v2")
        verification = json.loads(self.ctl(root, "migrate", "verify", "legacy-to-v2").stdout)
        self.assertTrue(verification["semantic_parity"])
        self.ctl(root, "migrate", "switch", "legacy-to-v2", "--harness-version", "2.0.0-a1")
        blocked = self.ctl(root, "task", "activate", "legacy-task", ok=False)
        self.assertIn("legacy lifecycle writer is disabled", blocked.stderr)
        self.ctl(root, "migrate", "rollback", "legacy-to-v2")
        self.assertEqual("legacy", json.loads((root / ".harness/install.json").read_text())["authority"])

    def test_legacy_inventory_blocks_partial_task_omission(self) -> None:
        root = self.candidate_template("partial-legacy")
        self.git(root, "init")
        partial = root / "tasks/partial-task"
        partial.mkdir()
        shutil.copy2(root / "tasks/_template/TASK.md", partial / "TASK.md")
        inspected = json.loads(self.ctl(root, "migrate", "inspect").stdout)
        self.assertFalse(inspected["supported"])
        self.assertEqual(["STATUS.md", "REPORT.md"], inspected["source_inventory"]["partial_tasks"]["partial-task"])
        blocked = self.ctl(root, "migrate", "plan", ok=False)
        self.assertIn("partial Tasks", blocked.stderr)

    def create_started_task(self, root: Path, validation: str = "python3 -c pass") -> tuple[Path, str]:
        self.ctl(
            root, "task", "create", "build-one", "--goal", "Build one", "--scope", "One file",
            "--output", "src/result.txt", "--acceptance", "Verified",
            "--owned-path", "task-output", "--owned-path", "handoff.json",
            "--validation-command", validation,
        )
        self.git(root, "add", ".harness")
        self.git(root, "commit", "-m", "create task")
        started = json.loads(self.ctl(root, "task", "start", "build-one").stdout)
        workspace = Path(started["workspace"])
        (workspace / "task-output").mkdir()
        (workspace / "task-output/result.txt").write_text("verified\n")
        handoff = {
            "status": "completed", "summary": "Built", "findings": [], "limitations": [],
            "candidates": [{
                "id": "result", "source": "task-output/result.txt",
                "target": "src/result.txt", "rationale": "verified",
            }],
        }
        (workspace / "handoff.json").write_text(json.dumps(handoff))
        return workspace, started["run_id"]

    def test_manual_worktree_validation_and_exact_diff_promotion(self) -> None:
        root = self.new_project(self.package(self.candidate_template(), "2.0.0-a1", "bundle"))
        workspace, _ = self.create_started_task(root)
        self.assertNotEqual(root, workspace)
        self.assertFalse((root / "task-output/result.txt").exists())
        self.ctl(root, "task", "submit", "build-one", "--handoff", "handoff.json")
        self.git(root, "add", ".harness")
        self.git(root, "commit", "-m", "review task")
        packet = json.loads(
            self.ctl(root, "promotion", "prepare", "--task", "build-one", "--candidate", "result").stdout
        )
        review = self.ctl(root, "promotion", "show", packet["promotion_id"]).stdout
        self.assertIn("## Exact Diff", review)
        self.assertIn("+verified", review)
        self.assertIn("full log", review)
        self.ctl(root, "promotion", "approve", packet["promotion_id"], "--actor", "test-user")
        self.ctl(root, "promotion", "apply", packet["promotion_id"])
        self.assertEqual("verified\n", (root / "src/result.txt").read_text())
        self.assertTrue((root / ".harness/promotions" / (packet["promotion_id"] + ".json")).is_file())
        self.assertTrue(workspace.is_dir(), "Task workspace must not be auto-deleted")

    def test_failed_validation_and_stale_diff_block_promotion(self) -> None:
        root = self.new_project(self.package(self.candidate_template(), "2.0.0-a1", "bundle"))
        workspace, _ = self.create_started_task(root, "python3 -c 'raise SystemExit(4)'")
        handoff = json.loads(self.ctl(root, "task", "submit", "build-one", "--handoff", "handoff.json").stdout)
        self.assertEqual(4, handoff["validation"][0]["exit_code"])
        blocked = self.ctl(
            root, "promotion", "prepare", "--task", "build-one", "--candidate", "result", ok=False
        )
        self.assertIn("Task validation failed", blocked.stderr)
        self.assertTrue(workspace.is_dir())

        other = self.new_project(self.package(self.candidate_template("template-two"), "2.0.0-a1", "bundle-two"), "stale")
        self.create_started_task(other)
        self.ctl(other, "task", "submit", "build-one", "--handoff", "handoff.json")
        self.git(other, "add", ".harness")
        self.git(other, "commit", "-m", "review task")
        packet = json.loads(
            self.ctl(other, "promotion", "prepare", "--task", "build-one", "--candidate", "result").stdout
        )
        self.ctl(other, "promotion", "approve", packet["promotion_id"], "--actor", "test-user")
        (Path(packet["workspace"]) / "src/result.txt").write_text("changed after approval\n")
        stale = self.ctl(other, "promotion", "apply", packet["promotion_id"], ok=False)
        self.assertIn("approved Promotion diff changed", stale.stderr)

    def test_v2_check_detects_canonical_damage_and_promotion_base_drift(self) -> None:
        root = self.new_project(self.package(self.candidate_template(), "2.0.0-a1", "bundle"))
        project_path = root / ".harness/project.json"
        original = project_path.read_text()
        payload = json.loads(original)
        payload["goal"] = "tampered without resealing"
        project_path.write_text(json.dumps(payload))
        damaged = self.ctl(root, "check", ok=False)
        self.assertIn("digest mismatch", damaged.stderr)
        project_path.write_text(original)

        self.create_started_task(root)
        self.ctl(root, "task", "submit", "build-one", "--handoff", "handoff.json")
        self.git(root, "add", ".harness")
        self.git(root, "commit", "-m", "review task")
        packet = json.loads(
            self.ctl(root, "promotion", "prepare", "--task", "build-one", "--candidate", "result").stdout
        )
        self.git(root, "commit", "--allow-empty", "-m", "advance official base")
        stale = self.ctl(
            root, "promotion", "approve", packet["promotion_id"], "--actor", "test-user", ok=False,
        )
        self.assertIn("official HEAD changed", stale.stderr)

    def test_task_handoff_rejects_symlink_candidate_source(self) -> None:
        root = self.new_project(self.package(self.candidate_template(), "2.0.0-a1", "bundle"))
        workspace, _ = self.create_started_task(root)
        external = self.base / "external.txt"
        external.write_text("outside\n")
        source = workspace / "task-output/result.txt"
        source.unlink()
        source.symlink_to(external)
        rejected = self.ctl(
            root, "task", "submit", "build-one", "--handoff", "handoff.json", ok=False,
        )
        self.assertIn("symlink", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
