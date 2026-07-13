# AGENTS

## Rules

- 새 Task 세션을 시작하거나 컨텍스트가 압축된 뒤 `python3 ../../tools/projectctl.py context`를 한 번 실행한다.
- 같은 세션에서는 `TASK.md`나 `STATUS.md`가 변경된 뒤에만 context를 다시 실행한다.
- context가 제공한 TASK, STATUS, REPORT 계약을 작업 시작 전에 별도로 다시 읽지 않는다.
- REPORT와 STATUS 형식은 한 번 작성한 뒤 Task 산출물 검증과 `projectctl task validate <task-name> --phase completed|stopped` 한 번으로 확인한다.
- `TASK.md`의 범위, 입력, 절차, 산출물, 완료 조건에 따라 작업한다.
- 기본 탐색 범위는 현재 Task와 `TASK.md`에 명시된 입력이다. 상위 또는 형제 경로를 탐색해야 하면 먼저 사용자에게 이유와 대상을 제시한다.
- Task 결과와 수행 기록은 이 Task 디렉터리에 작성한다.
- `STATUS.md`에는 현재 Final Goal, Work Plan, Current Work만 유지한다.
- Scope 변경이 필요하면 작업을 계속하지 않고 사용자에게 확인한다.
- 종료 시 `REPORT.md`를 완성하고 Work Plan과 Current Work를 정리한 뒤 Status를 `completed` 또는 `stopped`로 갱신한다.
- Task 세션은 `activate`, `baseline`, `audit`, `close`를 실행하지 않는다. 종료 상태를 작성한 뒤 멈추고 사용자가 Project 세션으로 전환한다.

## Task-specific Rules

이 Task에만 필요한 규칙이 있다면 여기에 추가한다.
