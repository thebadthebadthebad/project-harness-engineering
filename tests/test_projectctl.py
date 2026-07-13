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

    def ctl(self, *args, ok=True):
        result = subprocess.run(
            ("python3", str(self.tool), "--root", str(self.root), "task", *args),
            text=True, capture_output=True,
        )
        if ok and result.returncode:
            self.fail(result.stderr)
        return result

    def replace(self, path, old, new):
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def make_ready(self, name):
        task = self.root / "tasks" / name
        doc = task / "TASK.md"
        text = doc.read_text()
        text = text.replace("## Scope\n\nTBD", "## Scope\n\nDefined scope")
        text = text.replace("TBD\n" + chr(96) * 3, "Run the work\n" + chr(96) * 3)
        text = text.replace("## Outputs\n\nTBD", "## Outputs\n\noutput/result.txt")
        text = text.replace("## Completion Criteria\n\nTBD", "## Completion Criteria\n\nResult is verified")
        doc.write_text(text)
        status = task / "STATUS.md"
        text = status.read_text().replace("| TBD | todo |", "| Execute work | todo |")
        text = text.replace("## Current Work\n\nTBD", "## Current Work\n\nExecute work")
        status.write_text(text)

    def test_create_populates_goal_and_full_access_config(self):
        self.ctl(
            "create", "research-one", "--goal", "Answer the question",
            "--copy-code", "src/example.py", "example.py",
            "--link-data", "data/example.txt", "example.txt",
        )
        task = self.root / "tasks/research-one"
        self.assertIn("Answer the question", (task / "STATUS.md").read_text())
        config = (task / ".codex/config.toml").read_text()
        self.assertIn('sandbox_mode = "danger-full-access"', config)
        self.assertIn('approval_policy = "never"', config)
        self.assertEqual("VALUE = 1\n", (task / "scripts/example.py").read_text())
        self.assertTrue((task / "data/example.txt").is_symlink())
        self.ctl("validate", "research-one", "--phase", "created")

    def test_baseline_detects_project_change(self):
        self.ctl("create", "research-one", "--goal", "Answer the question")
        self.make_ready("research-one")
        self.ctl("activate", "research-one")
        self.git("add", ".")
        self.git("commit", "-m", "activate task")
        self.ctl("baseline", "research-one")
        (self.root / "PROJECT.md").write_text("# changed\n")
        result = self.ctl("audit", "research-one", ok=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unexpected Project change: PROJECT.md", result.stderr)

    def test_status_reports_completed_task(self):
        self.ctl("create", "research-one", "--goal", "Answer the question")
        self.make_ready("research-one")
        self.ctl("activate", "research-one")
        status = self.root / "tasks/research-one/STATUS.md"
        status.write_text(status.read_text().replace("\ndoing\n", "\ncompleted\n", 1))
        result = self.ctl("status")
        self.assertIn("return to Project session", result.stdout)


if __name__ == "__main__":
    unittest.main()
