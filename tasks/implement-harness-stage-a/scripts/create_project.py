#!/usr/bin/env python3
"""Compatibility wrapper for ``harnessctl package`` plus ``harnessctl new``."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from harnessctl import DistributionError, new_project, package


def default_template() -> Path:
    """Return the public template adjacent to this repository-level tool."""
    return Path(__file__).resolve().parents[1] / "project"


def create_project(
    template: Path,
    destination: Path,
    project_id: str | None = None,
    goal: str = "TBD",
    scope: list[str] | None = None,
) -> Path:
    """Package a development bundle and initialize one v2 Project."""
    with tempfile.TemporaryDirectory() as temporary:
        bundle = package(template, "development", Path(temporary) / "bundle")
        return new_project(
            bundle,
            destination,
            project_id or destination.name.lower().replace("_", "-"),
            goal,
            scope or ["TBD"],
        )


def build_parser() -> argparse.ArgumentParser:
    """Build the deprecated compatibility CLI."""
    parser = argparse.ArgumentParser(
        description="Compatibility wrapper; prefer tools/harnessctl.py new."
    )
    parser.add_argument("destination", type=Path)
    parser.add_argument("--template", type=Path, default=default_template())
    parser.add_argument("--project-id")
    parser.add_argument("--goal", default="TBD")
    parser.add_argument("--scope", action="append")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Create one Project and return a process exit code."""
    try:
        args = build_parser().parse_args(argv)
        print(
            create_project(
                args.template,
                args.destination,
                args.project_id,
                args.goal,
                args.scope,
            )
        )
        return 0
    except (DistributionError, OSError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
