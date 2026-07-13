# Observability Contract

## Purpose

The observer makes Project/Task harness behavior reviewable after a session without using logs as model instructions or workflow gates.

## Stored Metadata

- run, session, turn, role, Task, time, model, permission mode
- Hook event and coarse tool category
- Markdown paths visible in supported shell Hook input
- classified `projectctl` action without arguments or the full command
- context source paths and explicitly marked Skill name
- compaction and subagent lifecycle identifiers

## Excluded Content

- user prompt text
- tool response and stdout/stderr
- patch body
- full shell command and arguments
- transcript contents

The Hook never reads the unstable transcript path. It returns exit 0 with no output on valid input, malformed input, missing Git metadata, or write failure. It does not return Hook decision fields, warnings, or additional context.

## Storage and Reporting

Raw events live under `.git/harness/observability/<run-id>/events.jsonl`, outside the worktree. `projectctl observe report` writes a derived `REPORT.md` and `summary.json` below `.harness/observability/<run-id>/` by default. The report shows coverage rather than pretending unsupported events were observed; current Codex Hook interception does not cover every unified shell execution.

## Human Boundaries

Hook events do not trigger lifecycle commands. Skills are explicit-only. Custom agents are optional read-only roles, inherit the full-access environment because bubblewrap is unavailable, and therefore depend on instructions rather than a security sandbox. A user reviews Hook trust and approves any subagent delegation in normal operation.
