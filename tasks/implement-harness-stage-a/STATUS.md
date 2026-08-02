# STATUS

## Status


doing

허용값은 `todo`, `doing`, `completed`, `stopped`다.

## Final Goal


Versioned Project별 bundle, new/apply/update, JSON authority와 읽기 쉬운 View, legacy 실제 migration, 수동 worktree Task와 exact-diff Promotion 흐름을 구현하고 검증한다.

## Work Plan


| Work | Status |
| --- | --- |
| Bundle ownership과 new/apply/update | doing |
| JSON state와 human View | todo |
| Legacy migration과 semantic parity | todo |
| Manual worktree Task와 typed handoff | todo |
| Exact-diff Promotion | todo |
| Candidate 회귀와 fault 검증 | todo |
| REPORT와 Promotion 후보 정리 | todo |

Work Status는 `todo`, `doing`, `completed` 중 하나를 사용한다.

## Current Work

Bundle ownership과 new/apply/update

Task가 `completed` 또는 `stopped`이면 `None`으로 작성한다.
