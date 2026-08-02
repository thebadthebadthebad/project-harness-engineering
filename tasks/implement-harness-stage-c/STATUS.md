# STATUS

## Status


completed

허용값은 `todo`, `doing`, `completed`, `stopped`다.

## Final Goal


Simple SQLite queue, background worker와 제한된 병렬 Codex Task 실행을 구현하고 검증한다.

## Work Plan


| Work | Status |
| --- | --- |
| SQLite queue schema와 CLI | completed |
| Cancellable Codex adapter | completed |
| Worker concurrency와 writer limit | completed |
| Dependency·decision·cancel·interruption | completed |
| Background start/stop | completed |
| Candidate race/fault tests | completed |
| REPORT와 Promotion 후보 정리 | completed |

Work Status는 `todo`, `doing`, `completed` 중 하나를 사용한다.

## Current Work

None

Task가 `completed` 또는 `stopped`이면 `None`으로 작성한다.
