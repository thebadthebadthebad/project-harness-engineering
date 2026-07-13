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
| commands | 64 |
| context_calls | 3 |
| failed_commands | 4 |
| file_changes | 16 |
| malformed | 0 |
| markdown_read_commands | 10 |
| markdown_reads | 11 |
| parent_reads | 0 |
| projectctl_source_reads | 0 |
| task_project_lifecycle_commands | 0 |

## Sessions

### project-research-close

- Thread: 019f5bd9-4d3a-79e3-af30-57a29da52c70
- Commands: 21
- Failed commands: 1
- Markdown reads: 1
- Markdown read commands: 1
- Context calls: 1
- Task Project-lifecycle commands: 0
- Parent reads: []
- Unchanged repeated reads: {}
- Usage: {"cached_input_tokens": 257280, "input_tokens": 280846, "output_tokens": 3848, "reasoning_output_tokens": 1661}

### project-research-setup

- Thread: 019f5bd2-dd14-7bd2-927d-b5a2cdd26ca6
- Commands: 29
- Failed commands: 3
- Markdown reads: 5
- Markdown read commands: 4
- Context calls: 1
- Task Project-lifecycle commands: 0
- Parent reads: []
- Unchanged repeated reads: {}
- Usage: {"cached_input_tokens": 373760, "input_tokens": 405388, "output_tokens": 6537, "reasoning_output_tokens": 2646}

### task-research-code

- Thread: 019f5bd5-5086-7e70-81ea-fcbcd09f4c1b
- Commands: 14
- Failed commands: 0
- Markdown reads: 5
- Markdown read commands: 5
- Context calls: 1
- Task Project-lifecycle commands: 0
- Parent reads: []
- Unchanged repeated reads: {}
- Usage: {"cached_input_tokens": 498944, "input_tokens": 538739, "output_tokens": 11468, "reasoning_output_tokens": 4916}

## Markdown Reads by Path

- .agents/skills/run-task-workflow/SKILL.md: 1
- PROJECT.md: 1
- REPORT.md: 2
- STATE.md: 1
- STATUS.md: 1
- docs/research/python-csv.md: 1
- tasks/csv-normalization-research/AGENTS.md: 1
- tasks/csv-normalization-research/STATUS.md: 1
- tasks/csv-normalization-research/TASK.md: 1
- tasks/csv-normalization-research/docs/research/python-csv.md: 1

## Hook and Context Observability

- Observed Hook events: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop
- Missing Hook events: PreCompact, PostCompact, SubagentStart, SubagentStop

### project-research-close metadata

- Events: 47
- Hook events: {"PostToolUse": 21, "PreToolUse": 21, "SessionStart": 1, "Stop": 1, "UserPromptSubmit": 1}
- Document visits: {"PROJECT.md": 1, "STATE.md": 1, "tasks/csv-normalization-research/REPORT.md": 1, "tasks/csv-normalization-research/STATUS.md": 1, "tasks/csv-normalization-research/docs/research/python-csv.md": 1}
- Skills: {"manage-project-workflow": 1}
- Lifecycle actions: {"check": 3, "context": 1, "observe.mark": 1, "task.audit": 2, "task.close": 2, "task.status": 3, "task.validate": 2}

### project-research-setup metadata

- Events: 75
- Hook events: {"PostToolUse": 35, "PreToolUse": 35, "SessionStart": 1, "Stop": 1, "UserPromptSubmit": 1}
- Document visits: {"PROJECT.md": 2, "STATE.md": 2, "tasks/csv-normalization-research/AGENTS.md": 1, "tasks/csv-normalization-research/STATUS.md": 1, "tasks/csv-normalization-research/TASK.md": 1}
- Skills: {"manage-project-workflow": 1}
- Lifecycle actions: {"check": 3, "context": 1, "observe.mark": 1, "task.create": 2, "task.status": 3, "task.validate": 4}

### task-research-code metadata

- Events: 51
- Hook events: {"PostToolUse": 23, "PreToolUse": 23, "SessionStart": 1, "Stop": 1, "UserPromptSubmit": 1}
- Document visits: {".agents/skills/run-task-workflow/SKILL.md": 1, "REPORT.md": 4, "STATUS.md": 3, "TASK.md": 2, "docs/research/python-csv.md": 1}
- Skills: {"run-task-workflow": 1}
- Lifecycle actions: {"context": 1, "observe.mark": 1, "task.validate": 1}

