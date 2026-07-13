"""Integration tests for metadata-only observability and conservative controls."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


TASK = Path(__file__).resolve().parents[2]
REPOSITORY = TASK.parents[1]
PUBLIC_TEMPLATE = REPOSITORY / "project"
CANDIDATE = TASK / "scripts"
PUBLIC_CONFIG = TASK / "output/public-config"
TASK_CONFIG = TASK / "output/task-config"
HOOK_EVENTS = {
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PreCompact", "PostCompact", "SubagentStart", "SubagentStop", "Stop",
}


class ObservabilityControlsTest(unittest.TestCase):
    """Exercise Hook events and projectctl reports in a copied Git Project."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project"
        shutil.copytree(PUBLIC_TEMPLATE, self.root)
        shutil.copy2(CANDIDATE / "projectctl.py", self.root / "tools/projectctl.py")
        shutil.copytree(
            CANDIDATE / "project_harness",
            self.root / "tools/project_harness",
            dirs_exist_ok=True,
        )
        shutil.copytree(PUBLIC_CONFIG / ".codex", self.root / ".codex")
        shutil.copytree(PUBLIC_CONFIG / ".agents", self.root / ".agents")
        shutil.copy2(PUBLIC_CONFIG / ".gitignore", self.root / ".gitignore")
        self.tool = self.root / "tools/projectctl.py"
        self.hook = self.root / ".codex/hooks/observe.py"
        subprocess.run(("git", "init"), cwd=self.root, check=True, capture_output=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def environment(self) -> dict[str, str]:
        """Return launcher metadata shared by projectctl and Hook subprocesses."""
        environment = os.environ.copy()
        environment.update(
            {
                "HARNESS_RUN_ID": "test-run",
                "HARNESS_SESSION_ROLE": "project",
            }
        )
        return environment

    def command(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run candidate projectctl in the fixture Project."""
        result = subprocess.run(
            ("python3", str(self.tool), "--root", str(self.root), *args),
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return result

    def hook_event(self, payload: dict[str, object] | str) -> subprocess.CompletedProcess[str]:
        """Send one JSON or raw input payload to the candidate Hook."""
        input_value = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            ("python3", str(self.hook)),
            cwd=self.root,
            env=self.environment(),
            input=input_value,
            text=True,
            capture_output=True,
        )

    def test_context_hook_skill_and_report_share_one_run(self) -> None:
        self.command("context", "--json")
        secret = "PROMPT-AND-OUTPUT-MUST-NOT-BE-LOGGED"
        prompt = self.hook_event(
            {
                "session_id": "session-one",
                "cwd": str(self.root),
                "hook_event_name": "UserPromptSubmit",
                "prompt": secret,
            }
        )
        self.assertEqual(0, prompt.returncode, prompt.stderr)
        tool = self.hook_event(
            {
                "session_id": "session-one",
                "turn_id": "turn-one",
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {
                    "command": "cat PROJECT.md && echo " + secret
                    + "; python3 tools/projectctl.py task status"
                },
            }
        )
        self.assertEqual(0, tool.returncode, tool.stderr)
        self.command("observe", "mark", "skill", "manage-project-workflow")
        destination = self.root / ".harness/report"
        self.command("observe", "report", "--latest", "--output", str(destination))
        summary = json.loads((destination / "summary.json").read_text())
        self.assertEqual("test-run", summary["run_id"])
        self.assertGreaterEqual(summary["document_visits"]["PROJECT.md"], 2)
        self.assertEqual(1, summary["skills"]["manage-project-workflow"])
        self.assertEqual(1, summary["lifecycle_actions"]["task.status"])
        self.assertIn("UserPromptSubmit", summary["hook_events"])
        log = (self.root / ".git/harness/observability/test-run/events.jsonl").read_text()
        self.assertNotIn(secret, log)
        self.assertNotIn("tool_input", log)
        self.assertNotIn("prompt", log)

    def test_hook_is_fail_open_for_invalid_input(self) -> None:
        result = self.hook_event("not json")
        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_hook_config_skills_and_agents_are_conservative(self) -> None:
        hooks = json.loads((PUBLIC_CONFIG / ".codex/hooks.json").read_text())["hooks"]
        self.assertEqual(HOOK_EVENTS, set(hooks))
        commands = {
            handler["command"]
            for groups in hooks.values()
            for group in groups
            for handler in group["hooks"]
        }
        self.assertEqual(1, len(commands))
        self.assertIn(".codex/hooks/observe.py", next(iter(commands)))
        for directory in (
            PUBLIC_CONFIG / ".agents/skills/manage-project-workflow",
            TASK_CONFIG / ".agents/skills/run-task-workflow",
        ):
            self.assertNotIn("TODO", (directory / "SKILL.md").read_text())
            metadata = (directory / "agents/openai.yaml").read_text()
            self.assertIn("allow_implicit_invocation: false", metadata)
        for path in (PUBLIC_CONFIG / ".codex/agents").glob("*.toml"):
            text = path.read_text()
            self.assertIn("developer_instructions", text)
            self.assertIn("Do not edit files", text)
            self.assertNotIn("sandbox_mode", text)
        config = (PUBLIC_CONFIG / ".codex/config.toml").read_text()
        self.assertIn("hooks = true", config)
        self.assertIn("max_threads = 3", config)
        self.assertIn("max_depth = 1", config)

    def test_project_check_rejects_damaged_hook_config(self) -> None:
        self.command("check")
        hooks_path = self.root / ".codex/hooks.json"
        hooks = json.loads(hooks_path.read_text())
        del hooks["hooks"]["Stop"]
        hooks_path.write_text(json.dumps(hooks))
        result = subprocess.run(
            ("python3", str(self.tool), "--root", str(self.root), "check"),
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing events: Stop", result.stderr)


if __name__ == "__main__":
    unittest.main()
