# Workflow Core Design

## Compatibility

`projectctl.py` remains the executable entry point. Existing `context`, `session`, and `task create|validate|activate|baseline|audit|close|status` command names and lifecycle meanings remain available.

## Module Responsibilities

- `documents.py`: level-two Markdown sections, pipe tables, digests, atomic text replacement
- `repository.py`: Project discovery, safe paths, Git subprocesses
- `lifecycle.py`: Task creation, validation, state transitions, baseline, audit, close, handoff, Promotion record, integrity check
- `context.py`: dynamic Project and Task context payloads
- `observability.py`: best-effort metadata-only JSONL events below `.git/`
- `cli.py`: arguments, output, and launcher-declared Task role guard

The package uses only the Python standard library. Public functions state their input and output in signatures and docstrings. Atomic replacement is used where an interrupted write could corrupt lifecycle state.

## New Commands

- `check [--json]`: validates established structure, headings, state rows, and ADR/History naming.
- `task handoff <name> [--json]`: validates a finished Task and emits its REPORT contract.
- `promotion record <name> --decision promoted|not-promoted [--path ...]`: records a decision already made by a person; it never selects or copies files.
- `observe mark skill <name>`: records explicit Skill use when a launcher run id exists.

## Session Guard

The launcher exports `HARNESS_SESSION_ROLE`, `HARNESS_TASK_NAME`, and `HARNESS_RUN_ID`. A declared Task session can request its context, validate its own Task, and mark a Skill. Project lifecycle mutations are rejected. A shell without these variables remains compatible with direct human operation.

## Context Rule

Project context includes REPORT handoff fields only when Project STATE is `doing` and Task STATUS is `completed` or `stopped`. A closed completed Task remains as one current-state row but its REPORT body is no longer reinjected. Static command documentation stays in human documentation rather than every context payload.
