# STATUS

## Status


doing

허용값은 `todo`, `doing`, `completed`, `stopped`다.

## Final Goal


Project/Task 운영 의도를 유지하면서 projectctl의 구조, 동적 context, 세션 역할 가드, 구조 검사, handoff와 Promotion 기록, 새 Project 생성 기능을 단순하고 검증 가능한 코드로 안정화한다.

## Work Plan


| Work | Status |
| --- | --- |
| 기존 CLI와 호환성 계약 정리 | doing |
| 최소 모듈 경계와 공개 함수 설계 | todo |
| workflow core와 새 명령 구현 | todo |
| 회귀 및 경계 테스트 작성·실행 | todo |
| REPORT와 Promotion 후보 정리 | todo |

Work Status는 `todo`, `doing`, `completed` 중 하나를 사용한다.

## Current Work

기존 CLI와 호환성 계약 정리

Task가 `completed` 또는 `stopped`이면 `None`으로 작성한다.
