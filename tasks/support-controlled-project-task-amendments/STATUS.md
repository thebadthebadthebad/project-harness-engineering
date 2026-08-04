# STATUS

## Status


doing

허용값은 `todo`, `doing`, `completed`, `stopped`다.

## Final Goal


생성 후 Project와 Task 계약을 revision·digest·사용자 의사결정 근거와 함께 안전하게 개정하고 사람이 제안한 Markdown 변경을 검토 가능한 방식으로 canonical authority에 반영할 수 있게 한다.

## Work Plan


| Work | Status |
| --- | --- |
| 현재 mutation·schema와 사용자 편집 경로 분석 | completed |
| amendment 계약과 상태 규칙 설계 | completed |
| Project·Task preview/apply 구현 | completed |
| Markdown proposal import와 human View 구현 | completed |
| 문서·회귀·bundle 검증 및 handoff | doing |

Work Status는 `todo`, `doing`, `completed` 중 하나를 사용한다.

## Current Work

문서·회귀·bundle 검증 및 handoff

Task가 `completed` 또는 `stopped`이면 `None`으로 작성한다.
