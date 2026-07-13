# Harness Experiment Action Report

이 보고서는 Codex JSONL에 노출된 액션만 집계한다. 내부 AGENTS 주입과 shell 내부의 간접 파일 접근은 포함하지 않는다.

## Acceptance

- PASS: no_parent_reads
- PASS: no_projectctl_source_reads
- PASS: no_unchanged_repeated_markdown_reads
- PASS: no_task_project_lifecycle_commands
- PASS: context_used_in_each_session
- PASS: no_malformed_jsonl
- PASS: observability_no_malformed_jsonl
- PASS: session_prompt_stop_hooks_observed

## Totals

| Metric | Value |
| --- | ---: |
| commands | 42 |
| context_calls | 3 |
| failed_commands | 3 |
| file_changes | 9 |
| malformed | 0 |
| markdown_read_commands | 9 |
| markdown_reads | 9 |
| parent_reads | 0 |
| projectctl_source_reads | 0 |
| task_project_lifecycle_commands | 0 |

## Sessions

### project-close

- Thread: 019f5bd0-d885-7ae0-9233-f5f61ecc71c7
- Commands: 13
- Failed commands: 1
- Markdown reads: 0
- Markdown read commands: 0
- Context calls: 1
- Task Project-lifecycle commands: 0
- Parent reads: []
- Unchanged repeated reads: {}
- Usage: {"cached_input_tokens": 120576, "input_tokens": 131737, "output_tokens": 2142, "reasoning_output_tokens": 683}

### project-setup

- Thread: 019f5bce-04c3-7831-98a2-a0fcccedefd0
- Commands: 21
- Failed commands: 1
- Markdown reads: 6
- Markdown read commands: 6
- Context calls: 1
- Task Project-lifecycle commands: 0
- Parent reads: []
- Unchanged repeated reads: {}
- Usage: {"cached_input_tokens": 125696, "input_tokens": 142101, "output_tokens": 4709, "reasoning_output_tokens": 1771}

### task-work

- Thread: 019f5bcf-a199-7e70-9033-f6f01bc16ce3
- Commands: 8
- Failed commands: 1
- Markdown reads: 3
- Markdown read commands: 3
- Context calls: 1
- Task Project-lifecycle commands: 0
- Parent reads: []
- Unchanged repeated reads: {}
- Usage: {"cached_input_tokens": 185088, "input_tokens": 203772, "output_tokens": 2726, "reasoning_output_tokens": 700}

## Markdown Reads by Path

- .agents/skills/run-task-workflow/SKILL.md: 1
- PROJECT.md: 1
- REPORT.md: 1
- STATE.md: 1
- STATUS.md: 1
- tasks/_template/STATUS.md: 1
- tasks/_template/TASK.md: 1
- tasks/harness-loop-check/STATUS.md: 1
- tasks/harness-loop-check/TASK.md: 1

## Hook and Context Observability

- Observed Hook events: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop
- Missing Hook events: PreCompact, PostCompact, SubagentStart, SubagentStop

### project-close metadata

- Events: 31
- Hook events: {"PostToolUse": 13, "PreToolUse": 13, "SessionStart": 1, "Stop": 1, "UserPromptSubmit": 1}
- Document visits: {"PROJECT.md": 1, "STATE.md": 1, "tasks/harness-loop-check/REPORT.md": 1, "tasks/harness-loop-check/STATUS.md": 1}
- Skills: {"manage-project-workflow": 1}
- Lifecycle actions: {"check": 2, "context": 1, "observe.mark": 1, "task.audit": 2, "task.close": 1, "task.handoff": 1, "task.status": 3, "task.validate": 2}

### project-setup metadata

- Events: 51
- Hook events: {"PostToolUse": 23, "PreToolUse": 23, "SessionStart": 1, "Stop": 1, "UserPromptSubmit": 1}
- Document visits: {"PROJECT.md": 3, "STATE.md": 3, "STATUS.md": 1, "TASK.md": 1, "tasks/_template/STATUS.md": 1, "tasks/_template/TASK.md": 1, "tasks/harness-loop-check/STATUS.md": 2, "tasks/harness-loop-check/TASK.md": 2}
- Skills: {"manage-project-workflow": 1}
- Lifecycle actions: {"check": 1, "context": 1, "observe.mark": 1, "task.create": 2, "task.status": 3, "task.validate": 2}

### task-work metadata

- Events: 29
- Hook events: {"PostToolUse": 12, "PreToolUse": 12, "SessionStart": 1, "Stop": 1, "UserPromptSubmit": 1}
- Document visits: {".agents/skills/run-task-workflow/SKILL.md": 1, "REPORT.md": 2, "STATUS.md": 2, "TASK.md": 1}
- Skills: {"run-task-workflow": 1}
- Lifecycle actions: {"context": 1, "observe.mark": 1, "task.validate": 2}

