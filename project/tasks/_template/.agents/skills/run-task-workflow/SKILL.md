---
name: run-task-workflow
description: Explicit-only execution of the current Task contract and preparation of its REPORT handoff. Use when the user invokes $run-task-workflow inside a Task session; never use it to change Project state, select Promotion targets, or broaden the Task scope.
---

# Run Task Workflow

Execute the current Task contract without assuming shared Project-session context.

1. Attempt `python3 ../../tools/projectctl.py observe mark skill run-task-workflow`. If no run is active, continue without inventing a log.
2. Run `python3 ../../tools/projectctl.py context` once. Treat its contract, Final Goal, Work Plan, and Current Work as the session handoff; do not immediately reread the same Markdown files.
3. Perform the current Work Plan item within `TASK.md` Scope. Keep research, experiments, code, and temporary outputs in the Task locations named by the contract. Apply only the relevant quality lens:
   - Code: ownership, compatibility, focused test/build evidence, and regression risk.
   - Document: intended reader, authoritative sources, required structure, unsupported claims, and link/readability review.
   - Research: question and source policy, query/retrieval conditions, inclusion/exclusion, claim evidence, contradictions, and uncertainty.
   Do not create extra profile documents when the Task contract already expresses these requirements.
   If the canonical goal, scope, ownership, validation, or execution contract is wrong, stop the affected work and request a Project-session amendment. Do not edit canonical JSON or silently broaden the contract inside the Task session.
4. Update `STATUS.md` only when the current Work item changes. Keep exactly one `doing` item while active.
5. Validate changed code or evidence in proportion to the work. Record reproducible commands and distinguish deterministic checks from Agent or user judgment. Do not treat format checks as a substitute for result interpretation.
6. When all completion criteria are met, complete `REPORT.md`, set every Work Plan item to `completed`, set Current Work to `None`, and set Status to `completed`. Use `stopped` only when the work cannot or should not continue, with no `doing` item.
7. Run `python3 ../../tools/projectctl.py task validate <task-name> --phase completed|stopped`, report the handoff, and stop for the user's Project-session switch.
