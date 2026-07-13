# AGENTS

## Rules

- 새 Task 세션을 시작하거나 컨텍스트가 압축된 뒤 `python3 ../../project/tools/projectctl.py --root ../.. context`를 한 번 실행한다.
- 같은 세션에서는 context의 source 문서가 외부에서 변경됐을 때만 context를 다시 실행한다.
- context가 제공한 TASK, STATUS, REPORT 계약을 별도로 다시 읽지 않는다. 문서를 수정할 때만 필요한 부분을 확인한다.
- `TASK.md`의 범위, 입력, 절차, 산출물, 완료 조건에 따라 작업한다.
- Task 결과와 수행 기록은 이 Task 디렉터리에 작성하고 `STATUS.md`에는 현재 Final Goal, Work Plan, Current Work만 유지한다.
- 함수는 역할·입력·출력이 드러나게 작성하고 재사용 가능한 작은 경계를 사용한다. 이해하기 쉬운 단순 구현을 우선하고 변경한 코드는 관련 검증을 수행한다.
- Scope 변경이 필요하면 작업을 계속하지 않고 사용자에게 확인한다.
- 종료 시 `REPORT.md`를 완성하고 Work Plan과 Current Work를 정리한 뒤 Status를 `completed` 또는 `stopped`로 갱신한다.
- Project와 Task 세션의 전환은 사용자가 수행한다.
- subagent는 사용자가 요청하고 독립적인 읽기 작업을 병렬화하는 이점이 분명할 때만 사용한다. 호출 전에 역할, 범위, 예상 추가 비용을 알리고 사용자 확인을 받는다.

## Task-specific Rules

이 Task에만 필요한 규칙이 있다면 여기에 추가한다.
