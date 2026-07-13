#!/usr/bin/env python3
"""Create a new Git Project from the public harness template."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class CreateError(RuntimeError):
    """A user-correctable project creation error."""


def default_template() -> Path:
    """Return the public template adjacent to this repository-level tool."""
    return Path(__file__).resolve().parents[1] / "project"


def run(argv: tuple[str, ...], cwd: Path) -> None:
    """Run one required setup command or raise CreateError with its output."""
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise CreateError(result.stderr.strip() or result.stdout.strip())


def create_project(template: Path, destination: Path) -> Path:
    """Copy ``template``, initialize Git, validate it, and return ``destination``."""
    template = template.resolve()
    destination = destination.resolve()
    if not (template / "tools/projectctl.py").is_file():
        raise CreateError("template does not contain tools/projectctl.py")
    if destination.exists():
        raise CreateError("destination already exists: " + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="." + destination.name + "-", dir=destination.parent))
    try:
        shutil.rmtree(stage)
        shutil.copytree(
            template,
            stage,
            ignore=shutil.ignore_patterns(".git", ".harness", "__pycache__", "*.pyc"),
        )
        run(("git", "init"), stage)
        run(("python3", "tools/projectctl.py", "check"), stage)
        stage.rename(destination)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return destination


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--template", type=Path, default=default_template())
    return parser


def main(argv: list[str] | None = None) -> int:
    """Create one Project and return a process exit code."""
    try:
        args = build_parser().parse_args(argv)
        print(create_project(args.template, args.destination))
        return 0
    except (CreateError, OSError, subprocess.SubprocessError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
