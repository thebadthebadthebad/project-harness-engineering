# STATUS

## Status


doing

허용값은 `todo`, `doing`, `completed`, `stopped`다.

## Final Goal


Engineering Project와 공용 Project의 책임 구조를 구분해 projectctl check가 두 루트를 모두 정확히 검증하도록 한다.

## Work Plan


| Work | Status |
| --- | --- |
| Engineering과 공용 Project 식별 규칙 정의 | doing |
| check candidate 설계와 테스트 작성 | todo |
| Task-local 검증 | todo |
| REPORT handoff 완성 | todo |

Work Status는 `todo`, `doing`, `completed` 중 하나를 사용한다.

## Current Work

Engineering과 공용 Project 식별 규칙 정의

Task가 `completed` 또는 `stopped`이면 `None`으로 작성한다.
