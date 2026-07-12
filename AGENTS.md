# AGENTS

이 파일의 규칙은 Harness Engineering Project와 모든 Engineering Task에 공통으로 적용된다. 하위 `AGENTS.md`는 이 규칙을 반복하지 않고 해당 범위의 추가 규칙만 정의한다.

## Common Rules

- `README.md`는 사람을 위한 문서이므로 기본 작업 컨텍스트로 읽지 않는다.
- 현재 작업에 필요한 문서와 파일만 읽고 관련 없는 컨텍스트를 넓히지 않는다.
- 기존 코드와 문서의 스타일을 우선하며 관련 없는 변경을 함께 수행하지 않는다.
- 비밀 정보, 인증 정보, 개인 데이터를 문서나 Git에 기록하지 않는다.
- 파일을 수정한 Agent가 가능한 범위의 검증을 수행하고 결과를 명확히 보고한다.
- 새 문서나 디렉터리를 만들기 전에 기존 위치의 책임으로 관리할 수 있는지 확인한다.

## Project Session

- 작업을 시작할 때 `PROJECT.md`와 `STATE.md`를 읽는다.
- 저장소 구조, Task 생성, Promotion 절차가 필요할 때만 `STRUCTURE.md`를 읽는다.
- 공용 템플릿 개선 작업은 루트 `tasks/_template/`을 복사해 Engineering Task로 생성한다.
- Task 생성 결과를 사용자에게 확인받은 뒤 Task 수행 상태로 전환한다.
- Task Agent를 직접 호출하거나 Task 수행 과정을 대신 관리하지 않는다.
- 종료된 Task의 REPORT와 관련 파일을 검토해 `project/` 반영 계획을 작성한다.
- `project/` 수정 전 계획과 수정 후 diff·검증 결과를 사용자에게 각각 확인받는다.

## Task Session

- 이 규칙을 계승한 뒤 Task의 `AGENTS.md`, `TASK.md`, `STATUS.md` 순서로 읽는다.
- `PROJECT.md`, `STATE.md`, 전체 `STRUCTURE.md`는 기본 컨텍스트로 읽지 않는다. 필요한 정보는 TASK가 입력으로 지정해야 한다.
- 수행 중에는 자신의 `tasks/<task-name>/` 내부만 수정한다.
- 공용 배포본 `project/`, Project 공식 문서, Project `STATE.md`를 직접 수정하지 않는다.
- 종료 시 REPORT를 완성하고 STATUS를 갱신한 뒤 사용자에게 Project 세션으로 돌아갈 수 있음을 알린다.

## Project-wide Rules

- `project/`는 공용 배포본이며 Engineering Task의 작업 공간으로 사용하지 않는다.
- `project/` 안의 문서는 배포될 템플릿의 규칙과 placeholder를 소유한다. 루트 문서의 현재 Engineering 상태를 복제하지 않는다.
- 루트 `tasks/_template/`은 이 Engineering Project가 사용하는 설치본이고, `project/tasks/_template/`은 외부 배포용 원본이다.
- 자동화는 문서 형식과 수동 운영이 안정된 뒤 별도 Task로 검토한다.
