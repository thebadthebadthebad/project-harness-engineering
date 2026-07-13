---
name: manage-project-workflow
description: Explicit-only execution of a user-selected Project lifecycle checkpoint with projectctl. Use when the user invokes $manage-project-workflow to create, inspect, activate, baseline, close, check, or record an already-made Promotion decision; never use it to choose goals, interpret results, decide Promotion value, or switch into a Task session.
---

# Manage Project Workflow

Run only the Project checkpoint the user explicitly requested.

1. Attempt `python3 tools/projectctl.py observe mark skill manage-project-workflow`. If no run is active, continue without inventing a log.
2. Run `python3 tools/projectctl.py context` once. Do not reread documents already included in its `sources` unless editing a specific section.
3. Use `projectctl check`, `task validate`, `task status`, or `task handoff` for deterministic checks instead of manually scanning every Markdown file.
   - Status: `python3 tools/projectctl.py task status [--json]` takes no Task name.
   - Create: `python3 tools/projectctl.py task create <name> --goal <final-goal>`.
   - Inspect a created Task: `python3 tools/projectctl.py context --task <name>`.
   - Validate: `python3 tools/projectctl.py task validate <name> --phase ready|doing|completed|stopped`.
   - Transition: `task activate <name>`, `task baseline <name>`, `task audit <name>`, then `task close <name>` at their defined Project checkpoints.
   - Review: `python3 tools/projectctl.py task handoff <name> --json` applies only before close.
4. Execute only the requested lifecycle command. Do not infer a Final Goal, Scope, experiment design, result meaning, Promotion value, or ADR need.
5. After a lifecycle mutation, report the new state and the next human-controlled session boundary. Do not launch or impersonate the Task session.
6. For Promotion, modify official files only after the user has selected the result and destinations. Run relevant verification, then use `promotion record` solely to record the decision already made.
