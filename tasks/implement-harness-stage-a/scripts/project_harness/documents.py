"""Small Markdown and durable-file helpers used by the harness."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

from .errors import HarnessError


def section(text: str, name: str) -> str:
    """Return the body of a level-two Markdown section named ``name``."""
    match = re.search(r"(?ms)^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)", text)
    if not match:
        raise HarnessError("missing section: " + name)
    return match.group(1).strip()


def replace_section(text: str, name: str, body: str) -> str:
    """Return ``text`` with one existing level-two section body replaced."""
    pattern = re.compile(r"(?ms)(^## " + re.escape(name) + r"\s*\n).*?(?=^## |\Z)")
    if not pattern.search(text):
        raise HarnessError("missing section: " + name)
    replaced = pattern.sub(
        lambda match: match.group(1) + "\n" + body.strip() + "\n\n", text
    )
    return replaced.rstrip() + "\n"


def scalar(text: str, name: str) -> str:
    """Return the first non-guidance line from a Markdown section."""
    lines = [
        line.strip()
        for line in section(text, name).splitlines()
        if line.strip() and not line.startswith("허용값")
    ]
    if not lines:
        raise HarnessError("empty section: " + name)
    return lines[0]


def markdown_table(body: str) -> list[list[str]]:
    """Parse a simple pipe table body and return data rows without the header."""
    rows: list[list[str]] = []
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            rows.append(cells)
    return rows[1:] if rows else []


def format_table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """Render headers and rows as a simple Markdown pipe table."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def clean_value(raw: str) -> str:
    """Remove surrounding whitespace and Markdown code ticks from a scalar."""
    return raw.strip().strip("`")


def file_digest(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Atomically replace ``path`` with UTF-8 ``text`` on the same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        if path.exists():
            os.fchmod(descriptor, path.stat().st_mode & 0o777)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
