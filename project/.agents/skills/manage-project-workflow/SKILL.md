---
name: manage-project-workflow
description: Explicit-only execution of a user-selected legacy or v2 Project lifecycle checkpoint with projectctl. Use when the user invokes $manage-project-workflow to inspect state, operate a Task, check, or execute an already-made Promotion decision; never use it to choose goals, interpret results, decide Promotion value, or broaden a Task.
---

# Manage Project Workflow

Run only the Project checkpoint the user explicitly requested.

1. Attempt `python3 tools/projectctl.py observe mark skill manage-project-workflow`. If no run is active, continue without inventing a log.
2. Run `python3 tools/projectctl.py context` once. Do not reread documents already included in its `sources` unless editing a specific section.
3. Check `.harness/install.json` authority. Use the following v2 commands when authority is `v2`; do not invoke a legacy writer.
   - View: `show project`, `task show <name>`, `task review <name>`.
   - Contract amendment: use `project amend|task amend` only for fields the user directly changed or explicitly approved. Show the preview first. Apply with its current revision and reason; when acting as Agent, include the concrete user approval reference. Never edit canonical JSON directly or amend active/review/completed/stopped Tasks.
   - Task: `task create|start|run|submit` with the explicit contract and worktree handoff.
   - Decisions and reusable results: `decision show|resolve`, `result add|list|show|rebuild` only for an explicit user choice or reviewed result. `reviewed|verified` results require reviewer and real source/artifact evidence.
   - Background work: `queue enqueue|list|status|cancel|resume` and `worker run|start|stop`; never auto-resume `interrupted` work.
   - Promotion: `promotion prepare|show|approve|apply`; review the actual diff, current base, validation and log before approval. A changed HEAD, Task, diff, or stale validation requires a new packet.
4. Under legacy authority, use `projectctl check`, `task validate`, `task status`, or `task handoff` for deterministic checks instead of manually scanning every Markdown file.
   - Status: `python3 tools/projectctl.py task status [--json]` takes no Task name.
   - Create: `python3 tools/projectctl.py task create <name> --goal <final-goal>`.
   - Inspect a created Task: `python3 tools/projectctl.py context --task <name>`.
   - Validate: `python3 tools/projectctl.py task validate <name> --phase ready|doing|completed|stopped`.
   - Transition: `task activate <name>`, `task baseline <name>`, `task audit <name>`, then `task close <name>` at their defined Project checkpoints.
   - Review: `python3 tools/projectctl.py task handoff <name> --json` applies only before close.
5. Execute only the requested lifecycle command. Do not infer a Final Goal, Scope, experiment design, result meaning, Promotion value, or ADR need.
6. After a lifecycle mutation, report the new state and the next human-controlled session boundary. In Stage A, do not launch or impersonate the Task session.
7. For legacy Promotion, modify official files only after the user has selected the result and destinations. Run relevant verification, then use `promotion record` solely to record the decision already made.
