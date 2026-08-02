#!/usr/bin/env python3
"""Build and install versioned, Project-local harness bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
MANIFEST = "HARNESS-MANIFEST.json"
INSTALL = ".harness/install.json"
IGNORED_PARTS = {".git", ".harness", "__pycache__"}
MANAGED_PREFIXES = ("tools/", ".codex/", ".agents/", "tasks/_template/")
MANAGED_FILES = {"GUIDE.md", "STRUCTURE.md"}
INTEGRATION_FILES = {"AGENTS.md", "data/AGENTS.md", "docs/AGENTS.md"}


class DistributionError(RuntimeError):
    """One recoverable packaging or installation failure."""


def utc_now() -> str:
    """Return a compact UTC timestamp suitable for metadata and paths."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def digest(path: Path) -> str:
    """Return one file's SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write deterministic JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object with a user-facing error."""
    if not path.is_file():
        raise DistributionError("missing JSON file: " + str(path))
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise DistributionError("JSON file must contain an object: " + str(path))
    return payload


def safe_relative(raw: str) -> Path:
    """Return a path that cannot escape its bundle or Project root."""
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise DistributionError("unsafe bundle path: " + raw)
    return path


def template_files(template: Path) -> Iterable[Path]:
    """Yield distributable template files in stable order."""
    for path in sorted(template.rglob("*")):
        relative = path.relative_to(template)
        if path.is_file() and not any(part in IGNORED_PARTS for part in relative.parts):
            if path.suffix != ".pyc" and relative.as_posix() != MANIFEST:
                yield path


def ownership(relative: str) -> str:
    """Classify one template path by update ownership."""
    if relative in INTEGRATION_FILES:
        return "integration"
    if relative in MANAGED_FILES or relative.startswith(MANAGED_PREFIXES):
        return "managed"
    return "bootstrap"


def build_manifest(template: Path, version: str) -> dict[str, Any]:
    """Build the complete, checksummed bundle manifest."""
    if not version.strip():
        raise DistributionError("bundle version cannot be empty")
    if not (template / "tools/projectctl.py").is_file():
        raise DistributionError("template does not contain tools/projectctl.py")
    files = []
    for path in template_files(template):
        relative = path.relative_to(template).as_posix()
        files.append(
            {
                "path": relative,
                "sha256": digest(path),
                "ownership": ownership(relative),
                "mode": path.stat().st_mode & 0o777,
            }
        )
    return {
        "manifest_version": SCHEMA_VERSION,
        "harness_version": version,
        "created_at": utc_now(),
        "files": files,
    }


def load_bundle(bundle: Path) -> tuple[Path, dict[str, Any]]:
    """Resolve and validate one unpacked bundle directory."""
    bundle = bundle.resolve()
    manifest = read_json(bundle / MANIFEST)
    if manifest.get("manifest_version") != SCHEMA_VERSION:
        raise DistributionError("unsupported bundle manifest version")
    seen: set[str] = set()
    for item in manifest.get("files", []):
        if not isinstance(item, dict):
            raise DistributionError("invalid bundle file entry")
        relative = safe_relative(str(item.get("path", ""))).as_posix()
        if relative in seen:
            raise DistributionError("duplicate bundle path: " + relative)
        seen.add(relative)
        source = bundle / relative
        if not source.is_file() or digest(source) != item.get("sha256"):
            raise DistributionError("bundle checksum mismatch: " + relative)
        if item.get("ownership") not in {"managed", "bootstrap", "integration"}:
            raise DistributionError("invalid ownership: " + relative)
    return bundle, manifest


def copy_file(source: Path, target: Path, mode: int) -> None:
    """Copy one bundle file and its portable permission bits."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(mode)


def package(template: Path, version: str, output: Path) -> Path:
    """Create a new immutable-once-published bundle directory."""
    template = template.resolve()
    output = output.resolve()
    if output.exists():
        raise DistributionError("bundle output already exists: " + str(output))
    manifest = build_manifest(template, version)
    stage = Path(tempfile.mkdtemp(prefix="." + output.name + "-", dir=output.parent))
    try:
        for item in manifest["files"]:
            relative = safe_relative(item["path"])
            copy_file(template / relative, stage / relative, int(item["mode"]))
        write_json(stage / MANIFEST, manifest)
        stage.rename(output)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return output


def _plan_install(root: Path, manifest: dict[str, Any], update: bool) -> dict[str, Any]:
    """Return an install/update plan without changing the Project."""
    installed = read_json(root / INSTALL) if (root / INSTALL).is_file() else {}
    old_checksums = installed.get("managed_checksums", {})
    if not isinstance(old_checksums, dict):
        old_checksums = {}
    actions = []
    conflicts = []
    for item in manifest["files"]:
        relative = item["path"]
        target = root / safe_relative(relative)
        current = digest(target) if target.is_file() else None
        wanted = item["sha256"]
        owner = item["ownership"]
        action = "unchanged"
        reason = "already matches bundle"
        if owner in {"bootstrap", "integration"}:
            if current is None:
                action, reason = "create", owner + " file is missing"
            elif current != wanted:
                action, reason = "preserve", "Project-owned or integrated file differs"
        elif current is None:
            action, reason = "create", "managed file is missing"
        elif current == wanted:
            pass
        elif not update:
            action, reason = "replace", "managed file will be installed"
        else:
            old = old_checksums.get(relative)
            if old is None:
                action, reason = "conflict", "no installed checksum proves ownership"
            elif current == old:
                action, reason = "replace", "only the bundle changed"
            elif wanted == old:
                action, reason = "preserve", "only the Project copy changed"
            else:
                action, reason = "conflict", "bundle and Project copy both changed"
        record = {"path": relative, "ownership": owner, "action": action, "reason": reason}
        actions.append(record)
        if action == "conflict":
            conflicts.append(relative)
    return {
        "from_version": installed.get("harness_version"),
        "to_version": manifest["harness_version"],
        "actions": actions,
        "conflicts": conflicts,
    }


def _run_check(root: Path) -> None:
    """Run the installed Project's deterministic structural check."""
    result = subprocess.run(
        (sys.executable, "tools/projectctl.py", "--root", str(root), "check"),
        cwd=root,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise DistributionError(result.stderr.strip() or result.stdout.strip())


def _install_metadata(
    root: Path,
    manifest: dict[str, Any],
    previous: dict[str, Any],
    initial_authority: str,
) -> dict[str, Any]:
    """Build installation metadata while preserving state authority fields."""
    managed = {
        item["path"]: item["sha256"]
        for item in manifest["files"]
        if item["ownership"] == "managed"
    }
    return {
        **previous,
        "schema_version": 2,
        "harness_version": manifest["harness_version"],
        "authority": previous.get("authority", initial_authority),
        "generation": int(previous.get("generation", 0)),
        "managed_checksums": managed,
        "updated_at": utc_now(),
    }


def install(
    bundle: Path,
    root: Path,
    update: bool,
    apply: bool,
    initial_authority: str = "legacy",
) -> dict[str, Any]:
    """Plan or atomically apply a bundle to an existing Project."""
    bundle, manifest = load_bundle(bundle)
    root = root.resolve()
    if not root.is_dir():
        raise DistributionError("Project root does not exist: " + str(root))
    plan = _plan_install(root, manifest, update)
    plan["applied"] = False
    if not apply:
        return plan
    if plan["conflicts"]:
        raise DistributionError("managed file conflicts: " + ", ".join(plan["conflicts"]))
    previous_install = read_json(root / INSTALL) if (root / INSTALL).is_file() else {}
    backup_root = Path(tempfile.mkdtemp(prefix="harness-update-"))
    touched = [item for item in plan["actions"] if item["action"] in {"create", "replace"}]
    existing: set[str] = set()
    try:
        for item in touched:
            relative = safe_relative(item["path"])
            target = root / relative
            if target.is_file():
                existing.add(relative.as_posix())
                copy_file(target, backup_root / relative, target.stat().st_mode & 0o777)
            manifest_item = next(value for value in manifest["files"] if value["path"] == item["path"])
            copy_file(bundle / relative, target, int(manifest_item["mode"]))
        install_target = root / INSTALL
        if install_target.is_file():
            existing.add(INSTALL)
            copy_file(install_target, backup_root / INSTALL, install_target.stat().st_mode & 0o777)
        write_json(
            install_target,
            _install_metadata(root, manifest, previous_install, initial_authority),
        )
        _run_check(root)
    except Exception:
        for item in touched:
            relative = safe_relative(item["path"])
            target = root / relative
            if relative.as_posix() in existing:
                copy_file(backup_root / relative, target, (backup_root / relative).stat().st_mode & 0o777)
            else:
                target.unlink(missing_ok=True)
        if INSTALL in existing:
            copy_file(backup_root / INSTALL, root / INSTALL, (backup_root / INSTALL).stat().st_mode & 0o777)
        else:
            (root / INSTALL).unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)
    plan["applied"] = True
    return plan


def new_project(
    bundle: Path,
    destination: Path,
    project_id: str,
    goal: str,
    scope: list[str],
) -> Path:
    """Create and validate one new Git Project from a bundle."""
    bundle, manifest = load_bundle(bundle)
    destination = destination.resolve()
    if destination.exists():
        raise DistributionError("destination already exists: " + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="." + destination.name + "-", dir=destination.parent))
    try:
        result = install(
            bundle,
            stage,
            update=False,
            apply=True,
            initial_authority="uninitialized",
        )
        if not result["applied"]:
            raise DistributionError("bundle was not applied")
        subprocess.run(("git", "init"), cwd=stage, check=True, capture_output=True, text=True)
        initialized = subprocess.run(
            (
                sys.executable,
                "tools/projectctl.py",
                "--root",
                str(stage),
                "init",
                "--project-id",
                project_id,
                "--goal",
                goal,
                "--harness-version",
                str(manifest["harness_version"]),
                *(part for item in scope for part in ("--scope", item)),
            ),
            cwd=stage,
            text=True,
            capture_output=True,
        )
        if initialized.returncode:
            raise DistributionError(initialized.stderr.strip() or initialized.stdout.strip())
        _run_check(stage)
        stage.rename(destination)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return destination


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    """Build the distribution CLI."""
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    package_parser = commands.add_parser("package")
    package_parser.add_argument("--template", type=Path, required=True)
    package_parser.add_argument("--version", required=True)
    package_parser.add_argument("--output", type=Path, required=True)
    new_parser = commands.add_parser("new")
    new_parser.add_argument("destination", type=Path)
    new_parser.add_argument("--source", type=Path, required=True)
    new_parser.add_argument("--project-id", required=True)
    new_parser.add_argument("--goal", required=True)
    new_parser.add_argument("--scope", action="append", required=True)
    for name in ("apply", "update"):
        command = commands.add_parser(name)
        command.add_argument("project", type=Path)
        command.add_argument("--source", type=Path, required=True)
        command.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one distribution command."""
    try:
        args = build_parser().parse_args(argv)
        if args.command == "package":
            print(package(args.template, args.version, args.output))
        elif args.command == "new":
            print(new_project(args.source, args.destination, args.project_id, args.goal, args.scope))
        else:
            _print(install(args.source, args.project, args.command == "update", args.apply))
        return 0
    except (DistributionError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
