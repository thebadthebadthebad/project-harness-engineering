# PROJECT

## Goal

Project 단위의 공식 자산 관리, 독립 Task 수행, 사용자 확인을 포함한 Promotion을 안정적으로 운영할 수 있는 공용 Project 템플릿을 설계하고 관리한다.

## Scope

- Project와 Task의 관계와 책임 분담 설계
- Project 및 Task 문서 템플릿 관리
- Agent 규칙과 세션 간 handoff 방식 관리
- Task 생성·종료·Promotion 운영 방식 검증
- 검토된 공용 템플릿을 `project/`에 유지
- 반복적이고 결정적인 작업의 후속 자동화 가능성 검토

## Information

- `project/`는 다른 프로젝트에 복사해 사용할 공식 배포 템플릿이다.
- 조사, 실험, 설계 과정은 루트 `tasks/`에서 수행한다.
- Task 결과는 Project Agent와 사용자의 검토를 거친 뒤에만 `project/`에 반영한다.
- 현재 단계에서는 Skills, 자동화 도구, Hooks를 구현하지 않는다.
