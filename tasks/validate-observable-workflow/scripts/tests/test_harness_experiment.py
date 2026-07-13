"""Tests for the observable harness experiment runner and analyzer."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


TASK = Path(__file__).resolve().parents[2]
REPOSITORY = TASK.parents[1]
TOOL = TASK / "scripts/harness_experiment.py"
SPEC = importlib.util.spec_from_file_location("candidate_harness_experiment", TOOL)
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)
HOOK_SPEC = importlib.util.spec_from_file_location("candidate_hook", TASK / "output/hook-observe.py")
HOOK = importlib.util.module_from_spec(HOOK_SPEC)
HOOK_SPEC.loader.exec_module(HOOK)


def write_log(path: Path, items: list[dict[str, object]]) -> None:
    """Write a minimal Codex JSONL fixture around item.completed payloads."""
    events = [{"type": "thread.started", "thread_id": "thread-one"}]
    events.extend({"type": "item.completed", "item": item} for item in items)
    events.append({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 2}})
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")


class HarnessExperimentTest(unittest.TestCase):
    """Exercise parser precision, generation semantics, trust checks, and comparison."""

    def test_shell_parser_ignores_globs_and_find_name_predicates(self) -> None:
        reads, parents = HARNESS.command_reads(
            "sed -n '1,80p' AGENTS.md; rg --files -g '!TASK.md'; find .. -name REPORT.md"
        )
        self.assertEqual(["AGENTS.md"], reads)
        self.assertEqual([".."], parents)
        reads, _ = HARNESS.command_reads("rg -n 'Goal' PROJECT.md STATE.md")
        self.assertEqual(["PROJECT.md", "STATE.md"], reads)
        reads, _ = HARNESS.command_reads("/bin/bash -lc \"sed -n '1,80p' STATUS.md\"")
        self.assertEqual(["STATUS.md"], reads)

    def test_unchanged_reread_fails_but_post_change_read_is_new_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repeated_log = root / "task-repeat.jsonl"
            write_log(
                repeated_log,
                [
                    {"type": "command_execution", "command": "sed -n '1,80p' STATUS.md"},
                    {"type": "command_execution", "command": "sed -n '1,80p' STATUS.md"},
                ],
            )
            repeated = HARNESS.analyze([repeated_log], root / "repeated")
            self.assertFalse(repeated["acceptance"]["no_unchanged_repeated_markdown_reads"])

            changed_log = root / "task-changed.jsonl"
            write_log(
                changed_log,
                [
                    {"type": "command_execution", "command": "sed -n '1,80p' STATUS.md"},
                    {"type": "file_change", "changes": [{"path": "STATUS.md", "kind": "update"}]},
                    {"type": "command_execution", "command": "sed -n '1,80p' STATUS.md"},
                ],
            )
            changed = HARNESS.analyze([changed_log], root / "changed")
            self.assertTrue(changed["acceptance"]["no_unchanged_repeated_markdown_reads"])

    def test_hook_bundle_verification_rejects_changed_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            template = Path(temporary) / "project"
            shutil.copytree(REPOSITORY / "project", template)
            verified = HARNESS.verify_hook_bundle(template)
            self.assertEqual(9, verified["handlers"])
            path = template / ".codex/hooks.json"
            payload = json.loads(path.read_text())
            payload["hooks"]["Stop"][0]["hooks"][0]["command"] = "python3 /tmp/other.py"
            path.write_text(json.dumps(payload))
            with self.assertRaises(HARNESS.Error):
                HARNESS.verify_hook_bundle(template)

    def test_dry_run_records_roles_run_ids_and_verified_hook_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dry"
            result = subprocess.run(
                (
                    "python3", str(TOOL), "run",
                    "--template", str(REPOSITORY / "project"),
                    "--scenario", str(REPOSITORY / "experiments/scenarios/project-task-loop.json"),
                    "--output", str(output), "--dry-run",
                ),
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual("bypassed-after-local-verification", manifest["hook_trust"])
            self.assertEqual("project", manifest["sessions"][0]["role"])
            self.assertEqual("task", manifest["sessions"][1]["role"])
            self.assertTrue(all(session["run_id"] for session in manifest["sessions"]))
            self.assertTrue(
                all(
                    "--dangerously-bypass-hook-trust" in session["command"]
                    for session in manifest["sessions"]
                )
            )

    def test_compare_reports_metric_delta(self) -> None:
        before = {"totals": {"commands": 5}, "usage": {"input_tokens": 20}, "acceptance": {"check": False}}
        after = {"totals": {"commands": 3}, "usage": {"input_tokens": 10}, "acceptance": {"check": True}}
        comparison = HARNESS.compare_summaries(before, after)
        self.assertEqual(-2, comparison["metrics"]["totals.commands"]["delta"])
        self.assertEqual(True, comparison["acceptance"]["check"]["after"])

    def test_hook_document_paths_ignore_non_reads_and_globs(self) -> None:
        self.assertEqual(["PROJECT.md"], HOOK.document_paths("sed -n '1p' PROJECT.md"))
        self.assertEqual([], HOOK.document_paths("git diff -- PROJECT.md STATE.md"))
        self.assertEqual([], HOOK.document_paths("rg --files -g '!TASK.md'"))
        self.assertEqual(
            ["PROJECT.md", "STATE.md"],
            HOOK.document_paths("rg -n Goal PROJECT.md STATE.md"),
        )

    def test_observability_deduplicates_pre_and_post_document_visit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run.jsonl"
            rows = [
                {
                    "event": "hook", "hook_event": hook, "tool_use_id": "tool-one",
                    "documents": ["PROJECT.md"], "projectctl_action": "context",
                }
                for hook in ("PreToolUse", "PostToolUse")
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            summary = HARNESS.summarize_observability({"project": path})
            session = summary["sessions"][0]
            self.assertEqual(1, session["document_visits"]["PROJECT.md"])
            self.assertEqual(1, session["lifecycle_actions"]["context"])


if __name__ == "__main__":
    unittest.main()
