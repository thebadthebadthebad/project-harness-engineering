# Stage D Final Pilot Report

## Outcome

Stage D passed its two real-project vertical slices. The legacy Project migration preserved Project-owned documents, proved semantic parity, switched authority under a full check, and rolled back. A separately created Project then ran two bounded-input Codex review Tasks concurrently; both produced valid structured handoffs without changing the reviewed source.

## Legacy migration pilot

- Applied bundle version `2.0.0-final-pilot` to a clean clone of an existing legacy Project.
- Preserved `PROJECT.md`, `STATE.md`, and `AGENTS.md` byte-for-byte.
- Converted the Project record, promoted-history record, Task contract, and handoff record.
- Legacy and converted semantic digests were identical: `4afbe19a...f55f01`.
- The new authority passed the full Project check.
- Rollback restored legacy authority while retaining reversible migration evidence.
- The source Project repository was not modified.

## Parallel Codex pilot

Two independent reader Tasks reviewed bounded copies of real harness modules. Their execution contract used read-only sandboxing, approval `never`, network disabled, web disabled, shell-only tools, low reasoning effort, 300-second timeout, and 150,000-token limit.

- Both jobs started at `2026-08-02T12:27:49Z` and completed in the same 18.8-second worker window.
- Both queue jobs reached `succeeded`; both Task validations exited 0.
- No capability fallback, decision request, permission expansion, external change, or source mutation occurred.
- Each isolated worktree changed only its generated `.harness-agent-handoff.json` transport file.
- Parent review rendered both handoffs, indexed them as reusable reviewed Results, and created a follow-up Task referencing both Results.
- With no candidates returned, Promotion preparation rejected the empty selection.

## Findings

1. `harness_experiment.py` may undercount Markdown reads for valid `rg -e/-f` forms because its positional-path extraction drops the first remaining path.
2. A coordinator restart can mark a job interrupted while a surviving Task subprocess continues, allowing overlap after manual resume because Stage C intentionally does not persist or adopt PIDs.

The first finding is a normal follow-up defect. The second identifies the exact risk addressed by optional Stage E, but it is source-review evidence rather than an observed crash-recovery incident. Stage E remains deferred until a reproducible incident or operating metric justifies its complexity.

## Exit judgment

- Stage A: passed through real bundle apply, migration, authority switch, and rollback.
- Stage B: passed through actual Codex execution, structured handoff, validation, parent review, decision-safe contract, and result reuse.
- Stage C: passed through a two-job background queue run with real concurrent execution and isolation.
- Stage D: passed through the final real-project pilots and recorded measurements.
- Stage E: optional and deferred.

One presentation defect was observed: Task inputs are authoritative and injected into Codex correctly, but `task show` does not yet display their path, byte size, and digest. This is a small human-view gap, not a failed execution primitive, and must be corrected before the overall implementation handoff.
