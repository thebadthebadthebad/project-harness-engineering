# Hook Observability Smoke Result

## Result

최종 공용 템플릿의 실제 Codex Project 세션 1개가 exit 0으로 종료됐고 8개 hard acceptance를 모두 통과했다. 실행 전 runner가 exact Hook event set, command, timeout, config·script SHA-256을 검증한 경우에만 Hook trust를 우회했다.

## Actions

| Metric | Value |
| --- | ---: |
| Commands | 3 |
| Failed commands | 0 |
| File changes | 0 |
| Context calls | 1 |
| Markdown content reads | 1 |
| Input tokens | 52,178 |
| Output tokens | 304 |

Agent는 context, `sed` content read, `git diff -- README.md`를 각각 한 번 실행했다. Codex action analyzer와 public `observe report` 모두 README content visit을 1회로 집계했다. diff tool-use의 Pre/Post Hook event에는 `documents`가 없어서 교정된 non-read 제외가 실제 Hook 프로세스에서 확인됐다.

## Observability

- Events: 10, malformed: 0
- Observed: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop
- Not triggered: PreCompact, PostCompact, SubagentStart, SubagentStop
- Document visits after `tool_use_id` deduplication: PROJECT 1, STATE 1, README 1
- Lifecycle actions: context 1
- Skills: 0, scenario에서 명시적으로 사용하지 않음

원본 Hook event에서 README는 동일 `tool_use_id`의 Pre/Post 두 줄로 기록됐고 public report가 한 visit으로 중복 제거했다. forbidden field 검사에서 `prompt`, `tool_input`, `tool_response`, `command`, `transcript_path`는 0건이었다.

## Evidence Policy

raw Codex JSONL과 Hook JSONL은 ignored `.harness/`에만 보존한다. 이 디렉터리에는 prompt 원문이나 absolute 실행 경로를 제외한 manifest, summary와 report만 둔다.

