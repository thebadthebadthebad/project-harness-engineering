# AGENTS

## Rules

- 새 Project 세션을 시작하거나 컨텍스트가 압축된 뒤 `python3 tools/projectctl.py context`를 한 번 실행한다.
- 같은 세션에서는 context의 source 문서가 외부에서 변경됐거나 lifecycle 명령 후 현재 상태가 달라졌을 때만 context를 다시 실행한다.
- context가 제공한 PROJECT, STATE, pending Task handoff를 별도로 다시 읽지 않는다. 문서를 수정할 때만 필요한 부분을 확인한다.
- 문서 전체의 TBD·상태를 반복 탐색하지 않고 `projectctl check`와 `projectctl task validate` 결과를 사용한다.
- Task lifecycle은 `python3 tools/projectctl.py task ...`로, 이미 결정된 Promotion 기록은 `python3 tools/projectctl.py promotion record ...`로 수행한다.
- 함수는 역할·입력·출력이 드러나게 작성하고 재사용 가능한 작은 경계를 사용한다. 이해하기 쉬운 단순 구현을 우선하고 변경한 코드는 관련 검증을 수행한다.
- 새 문서나 디렉터리는 기존 책임으로 표현할 수 없을 때만 추가한다.
- Skill은 사용자가 `$manage-project-workflow`로 명시 호출했을 때만 사용한다.
- subagent는 사용자가 요청하고 서로 독립적인 읽기 작업을 병렬화하는 이점이 분명할 때만 사용한다. 호출 전에 역할, 범위, 예상 추가 비용을 알리고 사용자 확인을 받는다.
- Project와 Task 세션의 전환은 사용자가 수행한다. Agent는 다른 역할의 세션을 자동으로 시작하지 않는다.
