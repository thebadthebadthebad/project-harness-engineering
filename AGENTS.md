# AGENTS

## Rules

- 새 Project 세션을 시작하거나 컨텍스트가 압축된 뒤 `python3 project/tools/projectctl.py --root . context`를 한 번 실행한다.
- 같은 세션에서는 문서가 외부에서 변경됐거나 lifecycle 명령을 실행한 뒤에만 context를 다시 실행한다.
- context가 제공한 PROJECT, STATE, Task handoff를 별도로 다시 읽지 않는다. 문서를 수정할 때만 해당 문서의 필요한 부분을 확인한다.
- 문서 전체의 TBD·상태를 수동 `rg`·`sed`로 반복 확인하지 않고 `projectctl task validate` 결과를 따른다.
- Task 생성, 활성화, 상태 확인, 종료는 `python3 project/tools/projectctl.py --root . task ...` 명령을 사용한다.
- 생성한 Task 계약은 `python3 project/tools/projectctl.py --root . context --task <task-name>`으로 확인한다.
- 도구 자체를 수정하거나 디버깅하는 작업이 아니면 `project/tools/projectctl.py` 원문을 읽지 않는다.
- `project/`는 공용 배포 템플릿이다. Task 결과를 반영하기 전 계획을, 반영한 뒤 diff와 검증 결과를 사용자에게 확인받는다.
- 함수는 역할·입력·출력이 드러나게 작성하고 재사용 가능한 작은 경계를 사용한다. 이해하기 쉬운 단순 구현을 우선하고 변경한 코드는 관련 검증을 수행한다.
- subagent는 사용자가 요청하고 독립적인 읽기 작업을 병렬화하는 이점이 분명할 때만 사용한다. 호출 전에 역할, 범위, 예상 추가 비용을 알리고 사용자 확인을 받는다.
- 이 저장소에만 필요한 공통 코딩·문서 규칙이 생기면 이 문서에 추가한다.
