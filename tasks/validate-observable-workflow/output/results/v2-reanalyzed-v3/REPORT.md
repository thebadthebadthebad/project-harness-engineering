# Harness Experiment Comparison

## Metrics

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| totals.commands | 32 | 42 | 10 |
| totals.failed_commands | 1 | 3 | 2 |
| totals.file_changes | 10 | 9 | -1 |
| totals.markdown_reads | 22 | 9 | -13 |
| totals.markdown_read_commands | 8 | 9 | 1 |
| totals.parent_reads | 0 | 0 | 0 |
| totals.context_calls | 4 | 3 | -1 |
| totals.projectctl_source_reads | 0 | 0 | 0 |
| totals.task_project_lifecycle_commands | 0 | 0 | 0 |
| usage.input_tokens | 539273 | 477610 | -61663 |
| usage.output_tokens | 15195 | 9577 | -5618 |

## Acceptance

| Check | Before | After |
| --- | --- | --- |
| context_used_in_each_session | True | True |
| no_malformed_jsonl | True | True |
| no_parent_reads | True | True |
| no_projectctl_source_reads | True | True |
| no_task_project_lifecycle_commands | True | True |
| no_unchanged_repeated_markdown_reads | False | True |
| observability_no_malformed_jsonl | None | True |
| session_prompt_stop_hooks_observed | None | True |
