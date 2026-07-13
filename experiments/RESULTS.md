# Observable Workflow Experiment Analysis

## Result

Both controlled workflows completed all three independent Project/Task/Project sessions with exit code 0. Every hard acceptance check passed: one context call per session, no parent traversal, no `projectctl` source read, no Project lifecycle command from a Task session, no unchanged repeated Markdown read, and no malformed Codex or observability JSONL.

## Comparable Lifecycle Result

The v2 raw Codex logs were reanalyzed with the same v3 parser before comparison.

| Metric | v2 reanalyzed | v3 | Delta |
| --- | ---: | ---: | ---: |
| Commands | 32 | 42 | +10 |
| Failed commands later recovered | 1 | 3 | +2 |
| Markdown paths read | 22 | 9 | -13 |
| Markdown read commands | 8 | 9 | +1 |
| Context calls | 4 | 3 | -1 |
| Input tokens | 539,273 | 477,610 | -61,663 (-11.4%) |
| Output tokens | 15,195 | 9,577 | -5,618 (-37.0%) |

The lower path count is meaningful: v2 bundled repeated reads of `PROJECT.md`, `STATE.md`, and the created `TASK.md` before changes; v3 read no Markdown path twice within the same unchanged generation. The command count increased because explicit Skills were marked and the Project agent queried CLI help. Two of the three recovered v3 failures came from incorrectly trying `task status <name>`, although status takes no Task name. The refined Project Skill therefore includes exact compact command forms.

## Research and Code Result

The representative workflow researched official Python CSV behavior, wrote an evidence note, implemented a standard-library normalizer, created fixtures, and completed two unittests. Independent post-run checks confirmed `projectctl check`, completed Project/Task state, clean diff formatting, History creation, and both tests passing.

| Metric | Result |
| --- | ---: |
| Sessions with exit 0 | 3/3 |
| Commands | 64 |
| Failed commands later recovered | 4 |
| Markdown paths read | 11 |
| Unchanged repeated reads | 0 |
| Input tokens | 1,224,973 |
| Output tokens | 21,853 |

This larger token count is an observation, not an acceptance target. It reflects real research, implementation, fixture generation, validation, and handoff rather than only lifecycle mechanics.

## Skills, Hooks, and Agents

- Each Project session recorded one explicit `manage-project-workflow` marker; each Task session recorded one explicit `run-task-workflow` marker.
- Each session observed `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`.
- `PreCompact`/`PostCompact` were absent because no session compacted. `SubagentStart`/`SubagentStop` were absent because both scenarios were small and sequential and deliberately did not delegate.
- Lifecycle and research runs produced 111 and 173 metadata events respectively, with zero malformed lines.
- The runner verified the exact local Hook event set, command, timeout, in-template script resolution, and config/script SHA-256 before adding `--dangerously-bypass-hook-trust`. Normal interactive use still requires human `/hooks` review.

## Observability Defect and Correction

The first report counted a document once in `PreToolUse` and again in `PostToolUse`, and the Hook extracted `.md` paths from non-read commands such as `git diff`. Raw events remain unchanged as evidence. The report candidate now deduplicates document and lifecycle observations by `tool_use_id`. The Hook candidate restricts document extraction to content-read commands and removes glob arguments and `rg --files` listings.

The corrected Hook must be tested in a future real session after Promotion; current raw events were produced by the pre-correction Hook. This limitation is explicit rather than retroactively rewriting evidence.

## Content Review

No Hook event contained `prompt`, `tool_input`, `tool_response`, full `command`, or `transcript_path` fields. A boundary-aware heuristic found no API key, private-key header, or password assignment pattern in either run. Raw Codex JSONL can still contain prompts and agent messages by design, remains ignored under `.harness/`, and must not be published without manual review.

## Remaining Risks

- Hook interception is incomplete for some unified shell and non-shell tools; coverage reports missing events but cannot prove an action did not occur.
- Custom agents inherit full access because bubblewrap is unavailable. Instructions limit them to reading, but this is not a security boundary.
- Recovered CLI/validation failures add commands and tokens. Exact Skill command examples address the repeated status syntax error; validation-driven correction remains expected for research-shaped work.
- The experiment automates session launches to reproduce a user-controlled boundary. It does not change the public operating rule that a person switches between normal Project and Task sessions.
