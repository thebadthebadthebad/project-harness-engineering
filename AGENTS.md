# AGENTS

## Project Identity

- 이 Git 루트는 공용 하네스를 설계·검증·배포하는 Harness Engineering Project다.
- `project/`는 다른 저장소로 복사하는 공식 공용 Project 템플릿이며 별도 Project root로 취급한다.
- 루트 `tasks/`는 하네스 자체를 변경하는 Engineering Task이고 `project/tasks/_template/`은 배포 템플릿에 포함되는 Task template이다.
- Engineering 명령은 루트에서 `python3 project/tools/projectctl.py --root . ...` 형식을 사용한다.

## Session Bootstrap

- 새 Project 세션을 시작하거나 컨텍스트가 압축된 뒤 `python3 project/tools/projectctl.py --root . context`를 한 번 실행한다.
- context 출력의 Goal, Scope, Current Goal, Current Tasks와 pending handoff를 현재 운영 상태로 사용한다.
- Current Tasks가 비어 있으면 완료 Task를 다시 탐색하지 말고 사용자의 다음 요구를 하나의 Engineering Task로 정의하는 단계부터 시작한다.
- 완료된 구현 근거가 필요한 경우에만 `experiments/RESULTS.md`, 관련 Task `REPORT.md`, `docs/history/` 순서로 제한해서 확인한다.

## Rules

- 같은 세션에서는 context source가 외부에서 변경됐거나 lifecycle 명령으로 상태가 달라진 뒤에만 context를 다시 실행한다.
- context가 제공한 PROJECT, STATE, Task handoff를 별도로 다시 읽지 않는다. 문서를 수정할 때만 해당 문서의 필요한 부분을 확인한다.
- 루트 `.codex`는 network 가능한 full-access와 approval 없음으로 실행한다. Git baseline·audit와 Hook은 사후 관찰 장치이며 쓰기 보안 경계가 아니다.
- 문서 전체의 TBD·상태를 반복 탐색하지 않고 `projectctl check`와 `projectctl task validate` 결과를 사용한다.
- Task 생성, 활성화, 상태 확인, handoff, 감사와 종료는 `python3 project/tools/projectctl.py --root . task ...` 명령을 사용한다.
- 생성한 Task 계약은 `python3 project/tools/projectctl.py --root . context --task <task-name>`으로 확인한다.
- 도구 자체를 수정하거나 디버깅하는 작업이 아니면 `project/tools/projectctl.py` 원문을 읽지 않는다.
- Task 결과를 공식 루트 또는 `project/`에 반영하기 전 적용 대상과 이유를, 반영한 뒤 diff와 검증 결과를 사용자에게 제시한다.
- 함수는 역할·입력·출력이 드러나게 작성하고 재사용 가능한 작은 경계를 사용한다. 이해하기 쉬운 단순 구현을 우선하고 변경한 코드는 관련 검증을 수행한다.
- Project와 Task 세션의 전환은 사용자가 수행한다.
- subagent는 사용자가 요청하고 독립적인 읽기 작업을 병렬화하는 이점이 분명할 때만 사용한다. 호출 전에 역할, 범위, 예상 추가 비용을 알리고 사용자 확인을 받는다.
- 이 저장소에만 필요한 지속 규칙이 생기면 중복 문서를 만들지 않고 이 문서의 해당 책임에 추가한다.
