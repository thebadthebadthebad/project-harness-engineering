# STATUS

## Status


doing

허용값은 `todo`, `doing`, `completed`, `stopped`다.

## Final Goal


Simple SQLite queue, background worker와 제한된 병렬 Codex Task 실행을 구현하고 검증한다.

## Work Plan


| Work | Status |
| --- | --- |
| SQLite queue schema와 CLI | doing |
| Cancellable Codex adapter | todo |
| Worker concurrency와 writer limit | todo |
| Dependency·decision·cancel·interruption | todo |
| Background start/stop | todo |
| Candidate race/fault tests | todo |
| REPORT와 Promotion 후보 정리 | todo |

Work Status는 `todo`, `doing`, `completed` 중 하나를 사용한다.

## Current Work

SQLite queue schema와 CLI

Task가 `completed` 또는 `stopped`이면 `None`으로 작성한다.
