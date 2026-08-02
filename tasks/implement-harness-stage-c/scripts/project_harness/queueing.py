"""Simple Git-local SQLite queue and single-process parallel worker."""

from __future__ import annotations

import fcntl
import json
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .adapter import canonical_state_lock, execute_task
from .errors import HarnessError
from .repository import git_dir
from .v2 import (
    _bump_generation,
    _replace_record,
    authority_mode,
    read_task,
    read_workspace,
    start_v2_task,
    task_record_path,
)


JOB_STATES = {
    "queued", "running", "succeeded", "needs_decision", "blocked",
    "cancelled", "interrupted",
}
TERMINAL_STATES = {"succeeded", "needs_decision", "blocked", "cancelled", "interrupted"}


def utc_now() -> str:
    """Return a stable UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def queue_path(root: Path) -> Path:
    """Return the Git-local SQLite queue path."""
    return git_dir(root) / "harness/v2/queue.sqlite3"


def connect(root: Path) -> sqlite3.Connection:
    """Open and initialize the Project-local queue database."""
    path = queue_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(path, timeout=10, isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA journal_mode=WAL")
    database.execute("PRAGMA busy_timeout=10000")
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            task_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            job_class TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 1,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            enqueued_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            result_json TEXT
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    return database


def _job(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one queue row to public JSON."""
    value = dict(row)
    value["cancel_requested"] = bool(value["cancel_requested"])
    if value.get("result_json"):
        value["result"] = json.loads(value.pop("result_json"))
    else:
        value.pop("result_json", None)
        value["result"] = None
    return value


def _task_class(task: dict[str, Any]) -> str:
    """Classify a Task for the conservative writer concurrency limit."""
    execution = task.get("execution") or {}
    if execution.get("sandbox", "workspace-write") == "read-only":
        return "reader"
    return "writer"


def enqueue(root: Path, task_id: str) -> dict[str, Any]:
    """Add one ready Codex Task without mutating canonical state."""
    if authority_mode(root) != "v2":
        raise HarnessError("queue requires v2 authority")
    task = read_task(root, task_id)
    if task.get("execution") is None:
        raise HarnessError("queued Task requires a Codex execution contract")
    if task["state"].get("task_status") != "ready":
        raise HarnessError("new queue job requires a ready Task")
    database = connect(root)
    try:
        database.execute(
            "INSERT INTO jobs(task_id,state,job_class,enqueued_at) VALUES(?,?,?,?)",
            (task_id, "queued", _task_class(task), utc_now()),
        )
        row = database.execute("SELECT * FROM jobs WHERE task_id=?", (task_id,)).fetchone()
        return _job(row)
    except sqlite3.IntegrityError as error:
        raise HarnessError("Task already has a queue job") from error
    finally:
        database.close()


def list_jobs(root: Path, state: str | None = None) -> list[dict[str, Any]]:
    """List queue state newest first."""
    if state is not None and state not in JOB_STATES:
        raise HarnessError("invalid queue state")
    database = connect(root)
    try:
        if state:
            rows = database.execute(
                "SELECT * FROM jobs WHERE state=? ORDER BY enqueued_at,task_id", (state,)
            ).fetchall()
        else:
            rows = database.execute("SELECT * FROM jobs ORDER BY enqueued_at,task_id").fetchall()
        return [_job(row) for row in rows]
    finally:
        database.close()


def get_job(root: Path, task_id: str) -> dict[str, Any]:
    """Return one queue job."""
    database = connect(root)
    try:
        row = database.execute("SELECT * FROM jobs WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise HarnessError("queue job does not exist")
        return _job(row)
    finally:
        database.close()


def cancel_job(root: Path, task_id: str) -> dict[str, Any]:
    """Cancel queued work or request cooperative cancellation of a running turn."""
    database = connect(root)
    try:
        database.execute("BEGIN IMMEDIATE")
        row = database.execute("SELECT * FROM jobs WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise HarnessError("queue job does not exist")
        if row["state"] == "queued":
            database.execute(
                "UPDATE jobs SET state='cancelled',finished_at=? WHERE task_id=?",
                (utc_now(), task_id),
            )
        elif row["state"] == "running":
            database.execute(
                "UPDATE jobs SET cancel_requested=1 WHERE task_id=?", (task_id,)
            )
        else:
            raise HarnessError("only queued or running jobs can be cancelled")
        database.execute("COMMIT")
        return get_job(root, task_id)
    except Exception:
        if database.in_transaction:
            database.execute("ROLLBACK")
        raise
    finally:
        database.close()


def _set_canonical_active(root: Path, task_id: str) -> None:
    """Explicitly resume one existing workspace after operator review."""
    task = read_task(root, task_id)
    workspace = read_workspace(root, task_id)
    if workspace.get("state") not in {"active", "review"}:
        raise HarnessError("Task workspace cannot be resumed")
    if task["state"].get("task_status") == "needs_decision":
        raise HarnessError("resolve the pending decision before queue resume")
    state = dict(task["state"])
    state["task_status"] = "active"
    state.pop("blocked_reason", None)
    _replace_record(task_record_path(root, task_id), task, state=state)
    workspace["state"] = "active"
    from .v2 import write_json, _workspace_metadata_path
    write_json(_workspace_metadata_path(root, task_id), workspace)
    _bump_generation(root)


def resume_job(root: Path, task_id: str) -> dict[str, Any]:
    """Explicitly requeue one stopped job; never called automatically."""
    database = connect(root)
    try:
        database.execute("BEGIN IMMEDIATE")
        row = database.execute("SELECT * FROM jobs WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise HarnessError("queue job does not exist")
        if row["state"] not in {"interrupted", "blocked", "cancelled", "needs_decision"}:
            raise HarnessError("job state is not resumable")
        task = read_task(root, task_id)
        if task["state"].get("task_status") != "ready":
            with canonical_state_lock(root):
                _set_canonical_active(root, task_id)
        database.execute(
            """UPDATE jobs SET state='queued',attempt=attempt+1,cancel_requested=0,
               started_at=NULL,finished_at=NULL,result_json=NULL WHERE task_id=?""",
            (task_id,),
        )
        database.execute("COMMIT")
        return get_job(root, task_id)
    except Exception:
        if database.in_transaction:
            database.execute("ROLLBACK")
        raise
    finally:
        database.close()


def _cancel_requested(root: Path, task_id: str) -> bool:
    database = connect(root)
    try:
        row = database.execute(
            "SELECT cancel_requested FROM jobs WHERE task_id=?", (task_id,)
        ).fetchone()
        return bool(row and row[0])
    finally:
        database.close()


def _claim(root: Path, task_id: str) -> bool:
    """Atomically claim one queued job."""
    database = connect(root)
    try:
        cursor = database.execute(
            """UPDATE jobs SET state='running',started_at=?,finished_at=NULL
               WHERE task_id=? AND state='queued'""",
            (utc_now(), task_id),
        )
        return cursor.rowcount == 1
    finally:
        database.close()


def _finish(root: Path, task_id: str, outcome: dict[str, Any]) -> None:
    """Store one current job outcome without an event ledger."""
    state = {
        "review": "succeeded",
        "needs_decision": "needs_decision",
        "blocked": "blocked",
        "cancelled": "cancelled",
    }.get(str(outcome.get("status")), "blocked")
    database = connect(root)
    try:
        database.execute(
            """UPDATE jobs SET state=?,finished_at=?,result_json=?,cancel_requested=0
               WHERE task_id=?""",
            (state, utc_now(), json.dumps(outcome, ensure_ascii=False), task_id),
        )
    finally:
        database.close()


def _dependencies_satisfied(root: Path, task: dict[str, Any]) -> bool:
    """Return whether every declared predecessor has a reviewable handoff."""
    for dependency in task.get("dependencies", []):
        try:
            predecessor = read_task(root, dependency)
        except HarnessError:
            return False
        if predecessor["state"].get("task_status") != "review":
            return False
    return True


def _prepare_task(root: Path, task_id: str) -> None:
    """Create a workspace for a new job or reuse an explicitly resumed one."""
    task = read_task(root, task_id)
    status = task["state"].get("task_status")
    if status == "ready":
        with canonical_state_lock(root):
            start_v2_task(root, task_id, allow_dirty_harness=True)
    elif status != "active":
        raise HarnessError("queued Task is neither ready nor explicitly resumed")


def _run_job(root: Path, task_id: str, codex_bin: str) -> dict[str, Any]:
    """Prepare and execute one queue job."""
    try:
        _prepare_task(root, task_id)
        return execute_task(
            root,
            task_id,
            codex_bin,
            cancel_check=lambda: _cancel_requested(root, task_id),
        )
    except Exception as error:
        with canonical_state_lock(root):
            try:
                task = read_task(root, task_id)
                state = dict(task["state"])
                state.update({"task_status": "blocked", "blocked_reason": str(error)})
                _replace_record(task_record_path(root, task_id), task, state=state)
                _bump_generation(root)
            except Exception:
                pass
        return {"status": "blocked", "reason": str(error)}


@contextmanager
def _worker_singleton(root: Path) -> Iterator[None]:
    """Allow one coordinator process without a lease or PID adoption."""
    path = git_dir(root) / "harness/v2/worker.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise HarnessError("another worker coordinator is already running") from error
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _interrupt_stale_jobs(root: Path) -> int:
    """Mark pre-existing running rows interrupted; do not retry them."""
    database = connect(root)
    try:
        rows = database.execute("SELECT task_id FROM jobs WHERE state='running'").fetchall()
        database.execute(
            "UPDATE jobs SET state='interrupted',finished_at=?,cancel_requested=0 WHERE state='running'",
            (utc_now(),),
        )
    finally:
        database.close()
    for row in rows:
        with canonical_state_lock(root):
            try:
                task = read_task(root, row["task_id"])
                state = dict(task["state"])
                state.update({"task_status": "blocked", "blocked_reason": "worker restart interrupted run"})
                _replace_record(task_record_path(root, task["id"]), task, state=state)
                _bump_generation(root)
            except HarnessError:
                pass
    return len(rows)


def _set_meta(root: Path, key: str, value: str) -> None:
    database = connect(root)
    try:
        database.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
    finally:
        database.close()


def _get_meta(root: Path, key: str, default: str) -> str:
    database = connect(root)
    try:
        row = database.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return str(row[0]) if row else default
    finally:
        database.close()


def request_worker_stop(root: Path) -> None:
    """Request graceful coordinator shutdown through queue state."""
    _set_meta(root, "shutdown_requested", "1")


def run_worker(
    root: Path,
    codex_bin: str = "codex",
    max_parallel: int = 2,
    max_writers: int = 1,
    once: bool = False,
    poll_seconds: float = 0.25,
) -> dict[str, Any]:
    """Run one local coordinator with bounded parallel Codex turns."""
    if max_parallel < 1 or max_writers < 0 or max_writers > max_parallel:
        raise HarnessError("invalid worker concurrency limits")
    completed = 0
    with _worker_singleton(root):
        interrupted = _interrupt_stale_jobs(root)
        _set_meta(root, "shutdown_requested", "0")
        _set_meta(root, "worker_state", "running")
        futures: dict[Future[dict[str, Any]], tuple[str, str]] = {}
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            while True:
                for future in list(futures):
                    if not future.done():
                        continue
                    task_id, _ = futures.pop(future)
                    try:
                        outcome = future.result()
                    except Exception as error:
                        outcome = {"status": "blocked", "reason": str(error)}
                    _finish(root, task_id, outcome)
                    completed += 1
                shutdown = _get_meta(root, "shutdown_requested", "0") == "1"
                if not shutdown:
                    active_writers = sum(job_class == "writer" for _, job_class in futures.values())
                    capacity = max_parallel - len(futures)
                    if capacity:
                        for job in list_jobs(root, "queued"):
                            if capacity <= 0:
                                break
                            task = read_task(root, job["task_id"])
                            if not _dependencies_satisfied(root, task):
                                continue
                            if job["job_class"] == "writer" and active_writers >= max_writers:
                                continue
                            if not _claim(root, job["task_id"]):
                                continue
                            future = executor.submit(_run_job, root, job["task_id"], codex_bin)
                            futures[future] = (job["task_id"], job["job_class"])
                            capacity -= 1
                            if job["job_class"] == "writer":
                                active_writers += 1
                queued = bool(list_jobs(root, "queued"))
                if not futures and (shutdown or (once and not queued)):
                    break
                if once and not futures and queued:
                    # Remaining jobs are dependency- or concurrency-blocked, so a later run may retry.
                    break
                time.sleep(poll_seconds)
        _set_meta(root, "worker_state", "stopped")
        return {"completed": completed, "interrupted": interrupted, "jobs": list_jobs(root)}


def start_background_worker(
    root: Path,
    projectctl: Path,
    codex_bin: str,
    max_parallel: int,
    max_writers: int,
) -> dict[str, Any]:
    """Detach one coordinator without persisting or adopting its PID."""
    runtime = git_dir(root) / "harness/v2"
    runtime.mkdir(parents=True, exist_ok=True)
    log_path = runtime / "worker.log"
    _set_meta(root, "worker_state", "starting")
    log = log_path.open("a")
    argv = [
        sys.executable,
        str(projectctl),
        "--root",
        str(root),
        "worker",
        "run",
        "--codex-bin",
        codex_bin,
        "--max-parallel",
        str(max_parallel),
        "--max-writers",
        str(max_writers),
    ]
    process = subprocess.Popen(
        argv,
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    log.close()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise HarnessError("background worker exited during startup; inspect " + str(log_path))
        if _get_meta(root, "worker_state", "") == "running":
            return {
                "started": True,
                "pid": process.pid,
                "log": str(log_path),
                "pid_persisted": False,
            }
        time.sleep(0.05)
    raise HarnessError("background worker did not report ready; inspect " + str(log_path))
