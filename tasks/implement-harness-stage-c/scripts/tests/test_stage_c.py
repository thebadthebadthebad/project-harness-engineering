"""Stage C queue, parallel worker, cancellation, and interruption tests."""

from __future__ import annotations

import json
import os
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[4]
CANDIDATE = REPOSITORY / "tasks/implement-harness-stage-c/scripts"
PUBLIC_TEMPLATE = REPOSITORY / "project"
HARNESSCTL = REPOSITORY / "tools/harnessctl.py"


class StageCTest(unittest.TestCase):
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
    print('[]')
    raise SystemExit(0)
prompt = sys.stdin.read()
context = json.loads(prompt[prompt.index('{'):])
task_id = context['task_id']
time.sleep(float(os.environ.get('FAKE_SLEEP', '0.7')))
output = pathlib.Path(args[args.index('-o') + 1])
workspace = pathlib.Path(args[args.index('-C') + 1])
(workspace / 'task-output').mkdir(exist_ok=True)
(workspace / 'task-output/result.txt').write_text(task_id + '\\n')
if task_id.startswith('decision'):
    payload = {
      'status':'needs_decision','summary':'Needs choice','findings':[],'limitations':[],
      'candidates':[],'blocked_reason':None,
      'decision_request':{
        'title':'Choose scope','reason':'Scope expansion requested','recommended':'keep',
        'safe_default':'keep','deferrable':True,
        'options':[{'id':'keep','label':'Keep scope','impact':'No expansion'},
                   {'id':'expand','label':'Expand','impact':'Broader work'}]
      }
    }
else:
    payload = {
      'status':'completed','summary':'Done','findings':[],'limitations':[],
      'candidates':[{'id':'result','source':'task-output/result.txt',
                     'target':'src/' + task_id + '.txt','rationale':'verified'}],
      'decision_request':None,'blocked_reason':None
    }
output.write_text(json.dumps(payload))
print(json.dumps({'type':'thread.started','thread_id':'thread-' + task_id}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':2,'reasoning_output_tokens':1}}))
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

    def project(self, name: str = "demo") -> Path:
        template = self.base / ("template-" + name)
        shutil.copytree(PUBLIC_TEMPLATE, template)
        shutil.copy2(CANDIDATE / "projectctl.py", template / "tools/projectctl.py")
        for source in (CANDIDATE / "project_harness").glob("*.py"):
            shutil.copy2(source, template / "tools/project_harness" / source.name)
        bundle = self.base / ("bundle-" + name)
        self.command(
            "python3", str(HARNESSCTL), "package", "--template", str(template),
            "--version", "2.0.0-c1", "--output", str(bundle),
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

    def create_task(self, root: Path, name: str, dependency: str | None = None) -> None:
        argv = [
            "task", "create", name, "--goal", "Run " + name, "--scope", "One file",
            "--output", "src/" + name + ".txt", "--acceptance", "Verified",
            "--owned-path", "task-output", "--validation-command", "python3 -c pass",
            "--codex", "--reasoning-effort", "medium", "--sandbox", "workspace-write",
            "--approval-policy", "never", "--web-mode", "disabled", "--no-network-access",
            "--allowed-tool", "shell", "--time-limit", "10",
        ]
        if dependency:
            argv.extend(("--dependency", dependency))
        self.ctl(root, *argv)

    def commit_state(self, root: Path, message: str) -> None:
        self.git(root, "add", ".harness")
        self.git(root, "commit", "-m", message)

    def enqueue(self, root: Path, *names: str) -> None:
        for name in names:
            self.ctl(root, "queue", "enqueue", name)

    def worker(self, root: Path, *extra: str, env=None, ok: bool = True):
        return self.ctl(
            root, "worker", "run", "--once", "--codex-bin", str(self.fake_codex),
            "--poll-seconds", "0.05", *extra, env=env, ok=ok,
        )

    def test_parallel_limit_allows_two_writers_only_when_configured(self) -> None:
        parallel = self.project("parallel")
        self.create_task(parallel, "task-one")
        self.create_task(parallel, "task-two")
        self.commit_state(parallel, "create parallel tasks")
        self.enqueue(parallel, "task-one", "task-two")
        environment = os.environ.copy()
        environment["FAKE_SLEEP"] = "0.8"
        started = time.monotonic()
        self.worker(parallel, "--max-parallel", "2", "--max-writers", "2", env=environment)
        parallel_elapsed = time.monotonic() - started
        states = {item["task_id"]: item["state"] for item in json.loads(self.ctl(parallel, "queue", "list").stdout)}
        self.assertEqual({"task-one": "succeeded", "task-two": "succeeded"}, states)

        serial = self.project("serial")
        self.create_task(serial, "task-one")
        self.create_task(serial, "task-two")
        self.commit_state(serial, "create serial tasks")
        self.enqueue(serial, "task-one", "task-two")
        started = time.monotonic()
        self.worker(serial, "--max-parallel", "2", env=environment)
        serial_elapsed = time.monotonic() - started
        self.assertLess(parallel_elapsed, 1.6)
        self.assertGreater(serial_elapsed, parallel_elapsed + 0.45)

    def test_decision_and_unmet_dependency_do_not_stop_independent_work(self) -> None:
        root = self.project()
        self.create_task(root, "decision-one")
        self.create_task(root, "independent")
        self.create_task(root, "blocker")
        self.create_task(root, "dependent", dependency="blocker")
        self.commit_state(root, "create tasks")
        self.enqueue(root, "decision-one", "independent", "dependent")
        self.worker(root, "--max-parallel", "2", "--max-writers", "2")
        states = {item["task_id"]: item["state"] for item in json.loads(self.ctl(root, "queue", "list").stdout)}
        self.assertEqual("needs_decision", states["decision-one"])
        self.assertEqual("succeeded", states["independent"])
        self.assertEqual("queued", states["dependent"])

    def test_running_cancel_and_singleton_worker_lock(self) -> None:
        root = self.project()
        self.create_task(root, "slow-task")
        self.commit_state(root, "create slow task")
        self.enqueue(root, "slow-task")
        environment = os.environ.copy()
        environment["FAKE_SLEEP"] = "5"
        process = subprocess.Popen(
            (
                "python3", str(root / "tools/projectctl.py"), "--root", str(root),
                "worker", "run", "--once", "--codex-bin", str(self.fake_codex),
                "--poll-seconds", "0.05",
            ),
            cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if json.loads(self.ctl(root, "queue", "status", "slow-task").stdout)["state"] == "running":
                break
            time.sleep(0.05)
        second = self.worker(root, ok=False)
        self.assertIn("another worker coordinator", second.stderr)
        requested = json.loads(self.ctl(root, "queue", "cancel", "slow-task").stdout)
        self.assertTrue(requested["cancel_requested"])
        stdout, stderr = process.communicate(timeout=8)
        self.assertEqual(0, process.returncode, stderr)
        self.assertEqual("cancelled", json.loads(self.ctl(root, "queue", "status", "slow-task").stdout)["state"])

    def test_stale_running_requires_explicit_resume(self) -> None:
        root = self.project()
        self.create_task(root, "stale-task")
        self.commit_state(root, "create task")
        self.enqueue(root, "stale-task")
        self.ctl(root, "task", "start", "stale-task")
        database = sqlite3.connect(root / ".git/harness/v2/queue.sqlite3")
        database.execute("UPDATE jobs SET state='running' WHERE task_id='stale-task'")
        database.commit()
        database.close()
        result = json.loads(self.worker(root).stdout)
        self.assertEqual(1, result["interrupted"])
        self.assertEqual("interrupted", json.loads(self.ctl(root, "queue", "status", "stale-task").stdout)["state"])
        resumed = json.loads(self.ctl(root, "queue", "resume", "stale-task").stdout)
        self.assertEqual("queued", resumed["state"])
        self.assertEqual(2, resumed["attempt"])

    def test_detached_worker_stops_through_queue_flag_without_pid_adoption(self) -> None:
        root = self.project()
        started = json.loads(
            self.ctl(
                root, "worker", "start", "--codex-bin", str(self.fake_codex),
                "--max-parallel", "2", "--max-writers", "1",
            ).stdout
        )
        self.assertFalse(started["pid_persisted"])
        time.sleep(0.3)
        self.ctl(root, "worker", "stop")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            probe = self.worker(root, ok=False)
            if probe.returncode == 0:
                break
            time.sleep(0.1)
        else:
            os.kill(started["pid"], signal.SIGTERM)
            self.fail("detached worker did not stop")


if __name__ == "__main__":
    unittest.main()
