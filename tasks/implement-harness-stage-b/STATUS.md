# STATUS

## Status


doing

허용값은 `todo`, `doing`, `completed`, `stopped`다.

## Final Goal


Codex adapter, 구조화 실행 계약, Task-local decision request/resolve, 최소 result index와 Agent handoff 회수를 구현하고 검증한다.

## Work Plan


| Work | Status |
| --- | --- |
| Execution contract와 capability probe | doing |
| Codex argv·schema·context adapter | todo |
| Structured run evidence와 handoff 회수 | todo |
| Decision request/resolve | todo |
| Minimal result index | todo |
| Agent 책임 문서와 candidate tests | todo |
| REPORT와 Promotion 후보 정리 | todo |

Work Status는 `todo`, `doing`, `completed` 중 하나를 사용한다.

## Current Work

Execution contract와 capability probe

Task가 `completed` 또는 `stopped`이면 `None`으로 작성한다.
