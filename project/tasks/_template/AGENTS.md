# AGENTS

이 문서는 Project 루트 `AGENTS.md`를 계승하며 이 Task에만 적용되는 추가 규칙을 정의한다.

## Read Order

1. Project 루트 `AGENTS.md`
2. 이 Task의 `AGENTS.md`
3. `TASK.md`
4. `STATUS.md`

## Task Rules

- Task 목표, 범위, 입력, 절차, 완료 조건은 `TASK.md`를 따른다.
- 수행 중에는 이 `tasks/<task-name>/` 디렉터리 내부만 수정한다.
- Project 공식 코드, 데이터, 도구, 문서와 Project `STATE.md`를 수정하지 않는다.
- Goal 또는 Scope 변경이 필요하면 임의로 변경하지 말고 `STATUS.md`의 Blocker에 기록한 뒤 사용자에게 알린다.
- 현재 상태만 `STATUS.md`에 유지하고 과거 작업 로그를 누적하지 않는다.
- 종료 시 `REPORT.md`로 결과와 관련 파일을 정리한다.
- Promotion 대상과 공식 반영 위치는 확정하지 않고 Project가 검토할 정보만 제공한다.
- completed 또는 stopped로 종료한 뒤에는 Project 후속 검토 없이 Task 파일을 추가 수정하지 않는다.

## Task-specific Rules

이 Task에만 필요한 허용·금지·검증 규칙이 있다면 여기에 추가한다.
