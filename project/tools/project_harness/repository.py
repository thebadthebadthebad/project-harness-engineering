"""Project discovery, path validation, and Git command helpers."""

from __future__ import annotations

import fcntl
import re
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from .errors import HarnessError


TASK_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_CANONICAL_THREAD_LOCK = threading.RLock()
_CANONICAL_LOCK_STATE = threading.local()


def run_command(root: Path, argv: Sequence[str]) -> str:
    """Run ``argv`` in ``root`` and return stripped stdout or raise HarnessError."""
    result = subprocess.run(argv, cwd=root, text=True, capture_output=True)
    if result.returncode:
        raise HarnessError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def is_project_root(path: Path) -> bool:
    """Return whether ``path`` has the two stable Project root markers."""
    return (path / "STATE.md").is_file() and (path / "tasks/_template").is_dir()


def find_project_root(raw: str | None = None, cwd: Path | None = None) -> Path:
    """Resolve an explicit root or discover the nearest Project root from ``cwd``."""
    if raw:
        root = Path(raw).resolve()
        if not is_project_root(root):
            raise HarnessError("not a Project root")
        return root
    current = (cwd or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if is_project_root(candidate):
            return candidate
    raise HarnessError("not inside a Project")


def task_path(root: Path, name: str) -> Path:
    """Validate a Task name and return its path below ``root/tasks``."""
    if not TASK_NAME.fullmatch(name):
        raise HarnessError("Task name must use lowercase kebab-case")
    return root / "tasks" / name


def git_dir(root: Path) -> Path:
    """Return the absolute Git metadata directory for ``root``."""
    value = Path(run_command(root, ("git", "rev-parse", "--git-dir")))
    return value if value.is_absolute() else root / value


def relative_source(root: Path, raw: str, allowed: Sequence[str]) -> Path:
    """Resolve an existing Project input constrained to one of ``allowed`` roots."""
    path = (root / raw).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise HarnessError("source is outside Project: " + raw) from error
    if not any(relative == Path(base) or Path(base) in relative.parents for base in allowed):
        raise HarnessError("source is outside allowed roots: " + raw)
    if not path.exists():
        raise HarnessError("source does not exist: " + raw)
    return path


def safe_relative(raw: str) -> Path:
    """Return a relative destination path that cannot traverse its base directory."""
    path = Path(raw)
    if not raw or path.is_absolute() or ".." in path.parts:
        raise HarnessError("invalid Task destination: " + raw)
    return path


def contained_path(base: Path, raw: str, must_exist: bool = False) -> Path:
    """Return a non-symlink path contained by ``base``.

    Lexical relative-path checks alone are insufficient because an existing
    parent symlink can redirect a later read or copy outside the Project.
    """
    relative = safe_relative(raw)
    resolved_base = base.resolve()
    candidate = resolved_base / relative
    cursor = resolved_base
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise HarnessError("Task path contains a symlink: " + raw)
    try:
        candidate.resolve(strict=False).relative_to(resolved_base)
    except ValueError as error:
        raise HarnessError("Task path escapes its root: " + raw) from error
    if must_exist and not candidate.is_file():
        raise HarnessError("Task file does not exist: " + raw)
    return candidate


@contextmanager
def canonical_state_lock(root: Path) -> Iterator[None]:
    """Serialize canonical-state mutation across threads and local processes.

    The lock is re-entrant in one thread so high-level mutations can safely
    call smaller mutation helpers without deadlocking on a second ``flock``.
    """
    with _CANONICAL_THREAD_LOCK:
        path = git_dir(root) / "harness/v2/canonical.lock"
        key = str(path.resolve())
        held = dict(getattr(_CANONICAL_LOCK_STATE, "held", {}))
        if key in held:
            held[key] += 1
            _CANONICAL_LOCK_STATE.held = held
            try:
                yield
            finally:
                held = dict(getattr(_CANONICAL_LOCK_STATE, "held", {}))
                held[key] -= 1
                if not held[key]:
                    held.pop(key)
                _CANONICAL_LOCK_STATE.held = held
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            held[key] = 1
            _CANONICAL_LOCK_STATE.held = held
            try:
                yield
            finally:
                held = dict(getattr(_CANONICAL_LOCK_STATE, "held", {}))
                held.pop(key, None)
                _CANONICAL_LOCK_STATE.held = held
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
