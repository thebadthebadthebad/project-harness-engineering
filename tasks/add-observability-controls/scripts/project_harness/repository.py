"""Project discovery, path validation, and Git command helpers."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Sequence

from .errors import HarnessError


TASK_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


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
    if path.is_absolute() or ".." in path.parts:
        raise HarnessError("invalid Task destination: " + raw)
    return path
