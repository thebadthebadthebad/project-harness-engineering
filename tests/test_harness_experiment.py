import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/harness_experiment.py"
SPEC = importlib.util.spec_from_file_location("harness_experiment", TOOL)
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class HarnessExperimentTest(unittest.TestCase):
    def test_analyzer_reports_reads_traversal_source_and_usage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "task-one.jsonl"
            events = [
                {"type": "thread.started", "thread_id": "thread-1"},
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "sed -n '1,80p' AGENTS.md; find .. -name TASK.md",
                        "exit_code": 0,
                        "status": "completed",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "sed -n '1,80p' tools/projectctl.py",
                        "exit_code": 0,
                        "status": "completed",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "python3 ../../tools/projectctl.py context",
                        "exit_code": 0,
                        "status": "completed",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "python3 ../../tools/projectctl.py task audit task-one",
                        "exit_code": 0,
                        "status": "completed",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "file_change",
                        "changes": [{"path": "STATUS.md", "kind": "update"}],
                        "status": "completed",
                    },
                },
                {
                    "type": "turn.completed",
                    "usage": {"input_tokens": 10, "output_tokens": 2},
                },
            ]
            log.write_text("\n".join(json.dumps(event) for event in events) + "\n")
            summary = HARNESS.analyze([log], root / "result")
            self.assertEqual(2, summary["totals"]["markdown_reads"])
            self.assertEqual(1, summary["totals"]["parent_reads"])
            self.assertEqual(1, summary["totals"]["projectctl_source_reads"])
            self.assertEqual(1, summary["totals"]["context_calls"])
            self.assertEqual(1, summary["totals"]["task_project_lifecycle_commands"])
            self.assertEqual(10, summary["usage"]["input_tokens"])
            self.assertFalse(summary["acceptance"]["no_parent_reads"])

    def test_dry_run_does_not_execute_dynamic_session_setup(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            result = subprocess.run(
                (
                    "python3",
                    str(TOOL),
                    "run",
                    "--template",
                    str(ROOT / "project"),
                    "--scenario",
                    str(ROOT / "experiments/scenarios/project-task-loop.json"),
                    "--output",
                    str(output),
                    "--dry-run",
                ),
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("acceptance was not evaluated", (output / "REPORT.md").read_text())
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(3, len(manifest["sessions"]))
            self.assertTrue(all(item["exit_code"] == 0 for item in manifest["sessions"]))
            self.assertTrue(manifest["template_snapshot_sha256"])
            self.assertTrue(manifest["scenario_sha256"])


if __name__ == "__main__":
    unittest.main()
