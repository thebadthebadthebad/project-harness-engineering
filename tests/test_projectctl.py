import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "project"


class ProjectctlTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(SOURCE, self.root)
        (self.root / "src/example.py").write_text("VALUE = 1\n")
        (self.root / "data/example.txt").write_text("source data\n")
        self.tool = self.root / "tools/projectctl.py"
        self.git("init")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("add", ".")
        self.git("commit", "-m", "initial")

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ("git", *args), cwd=self.root, text=True, capture_output=True, check=True
        )

    def command(self, *args, cwd=None, ok=True):
        result = subprocess.run(
            ("python3", str(self.tool), "--root", str(self.root), *args),
            cwd=cwd or self.root,
            text=True,
            capture_output=True,
        )
        if ok and result.returncode:
            self.fail(result.stderr)
        return result

    def ctl(self, *args, ok=True):
        return self.command("task", *args, ok=ok)

    def create_ready(self, name="research-one"):
        self.ctl("create", name, "--goal", "Answer the question")
        task = self.root / "tasks" / name
        path = task / "TASK.md"
        text = path.read_text()
        text = text.replace("## Scope\n\nTBD", "## Scope\n\nDefined scope")
        text = text.replace("TBD\n```", "Run the work\n```")
        text = text.replace("## Outputs\n\nTBD", "## Outputs\n\noutput/result.txt")
        text = text.replace(
            "## Completion Criteria\n\nTBD",
            "## Completion Criteria\n\nResult is verified",
        )
        path.write_text(text)
        path = task / "STATUS.md"
        text = path.read_text().replace("| TBD | todo |", "| Execute work | todo |")
        text = text.replace("## Current Work\n\nTBD", "## Current Work\n\nExecute work")
        path.write_text(text)
        return task

    def activate_and_baseline(self, name="research-one"):
        task = self.create_ready(name)
        self.ctl("validate", name, "--phase", "ready")
        self.ctl("activate", name)
        self.git("add", ".")
        self.git("commit", "-m", "activate task")
        self.ctl("baseline", name)
        return task

    def finish(self, task, outcome):
        status = task / "STATUS.md"
        text = status.read_text().replace("\ndoing\n", "\n" + outcome + "\n", 1)
        text = text.replace("| Execute work | doing |", "| Execute work | completed |")
        text = text.replace("## Current Work\n\nExecute work", "## Current Work\n\nNone")
        status.write_text(text)
        (task / "output/result.txt").write_text("verified result\n")
        report = task / "REPORT.md"
        text = report.read_text()
        text = text.replace("## Outcome\n\nTBD", "## Outcome\n\n" + outcome)
        replacements = {
            "Summary": "Work ended with a reviewable result.",
            "Final Goal and Result": "The final goal and result are documented.",
            "Findings": "The deterministic fixture finding.",
            "Work and Validation": "Created and checked output/result.txt.",
            "Limitations": "Synthetic test only.",
            "Project Follow-up": "Review for Promotion when requested.",
        }
        for heading, body in replacements.items():
            text = text.replace("## " + heading + "\n\nTBD", "## " + heading + "\n\n" + body)
        text = text.replace(
            "| TBD | TBD | TBD |",
            "| output/result.txt | output | Verified fixture |",
        )
        report.write_text(text)

    def test_create_uses_two_column_state_and_no_task_config(self):
        self.ctl(
            "create",
            "research-one",
            "--goal",
            "Answer the question",
            "--copy-code",
            "src/example.py",
            "example.py",
            "--link-data",
            "data/example.txt",
            "example.txt",
        )
        task = self.root / "tasks/research-one"
        self.assertIn("Answer the question", (task / "STATUS.md").read_text())
        self.assertFalse((task / ".codex/config.toml").exists())
        self.assertEqual("VALUE = 1\n", (task / "scripts/example.py").read_text())
        self.assertTrue((task / "data/example.txt").is_symlink())
        self.assertIn("| research-one | todo |", (self.root / "STATE.md").read_text())
        self.ctl("validate", "research-one", "--phase", "created")

    def test_context_combines_project_and_task_documents(self):
        project = self.command("context", "--json")
        payload = json.loads(project.stdout)
        self.assertEqual("project", payload["role"])
        self.assertEqual({"PROJECT.md", "STATE.md"}, set(payload["sources"]))
        task = self.create_ready()
        result = self.command("context", "--json", cwd=task)
        payload = json.loads(result.stdout)
        self.assertEqual("task", payload["role"])
        self.assertEqual("Answer the question", payload["final_goal"])
        self.assertEqual("Defined scope", payload["contract"]["scope"])
        self.assertEqual({"TASK.md", "STATUS.md", "REPORT.md"}, set(payload["sources"]))
        self.assertNotIn("session_boundary", payload)
        from_project = self.command("context", "--task", "research-one", "--json")
        self.assertEqual("task", json.loads(from_project.stdout)["role"])

    def test_session_print_uses_explicit_full_access(self):
        self.create_ready()
        project = self.command("session", "project", "--print")
        task = self.command("session", "task", "research-one", "--print")
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", project.stdout)
        self.assertIn(str(self.root / "tasks/research-one"), task.stdout)
        self.assertNotIn("--strict-config", task.stdout)

    def test_baseline_detects_project_change(self):
        self.activate_and_baseline()
        (self.root / "PROJECT.md").write_text("# changed\n")
        result = self.ctl("audit", "research-one", ok=False)
        self.assertIn("unexpected Project change: PROJECT.md", result.stderr)

    def test_completed_close_validates_report_and_updates_state(self):
        task = self.activate_and_baseline()
        self.finish(task, "completed")
        self.ctl("validate", "research-one", "--phase", "completed")
        context = json.loads(self.command("context", "--json").stdout)
        self.assertEqual(
            "completed", context["handoffs"]["research-one"]["outcome"]
        )
        self.assertEqual(
            "output/result.txt",
            context["handoffs"]["research-one"]["relevant_files"][0]["path"],
        )
        self.ctl("close", "research-one")
        state = (self.root / "STATE.md").read_text()
        self.assertIn("| research-one | completed |", state)
        histories = list((self.root / "docs/history").glob("*-completed-research-one.md"))
        self.assertEqual(1, len(histories))
        self.assertIn("Promotion: not evaluated", histories[0].read_text())

    def test_stopped_close_removes_current_task(self):
        task = self.activate_and_baseline()
        self.finish(task, "stopped")
        self.ctl("close", "research-one")
        self.assertNotIn("research-one", (self.root / "STATE.md").read_text())
        self.assertEqual(
            1, len(list((self.root / "docs/history").glob("*-stopped-research-one.md")))
        )

    def test_stopped_validation_rejects_doing_work(self):
        task = self.activate_and_baseline()
        self.finish(task, "stopped")
        status = task / "STATUS.md"
        status.write_text(
            status.read_text().replace(
                "| Execute work | completed |", "| Execute work | doing |"
            )
        )
        result = self.ctl(
            "validate", "research-one", "--phase", "stopped", ok=False
        )
        self.assertIn("must not have a doing Work Plan item", result.stderr)

    def test_completed_validation_rejects_inconsistent_work_and_missing_file(self):
        task = self.activate_and_baseline()
        self.finish(task, "completed")
        status = task / "STATUS.md"
        status.write_text(
            status.read_text().replace(
                "| Execute work | completed |", "| Execute work | doing |"
            )
        )
        (task / "output/result.txt").unlink()
        result = self.ctl(
            "validate", "research-one", "--phase", "completed", ok=False
        )
        self.assertIn("all Work Plan items completed", result.stderr)
        self.assertIn("Relevant Files path does not exist", result.stderr)

    def test_status_reports_finished_task(self):
        task = self.activate_and_baseline()
        self.finish(task, "completed")
        result = self.ctl("status")
        self.assertIn("return to Project session", result.stdout)


if __name__ == "__main__":
    unittest.main()
