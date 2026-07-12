# AGENTS

이 파일의 규칙은 Project 루트와 모든 하위 Task에 공통으로 적용된다. 하위 `AGENTS.md`는 이 규칙을 반복하지 않고 해당 범위의 추가 규칙만 정의한다.

## Common Rules

- `README.md`는 사람을 위한 문서이므로 기본 작업 컨텍스트로 읽지 않는다.
- 현재 작업에 필요한 문서와 파일만 읽고 관련 없는 컨텍스트를 넓히지 않는다.
- 기존 코드와 문서의 스타일을 우선하며 관련 없는 변경을 함께 수행하지 않는다.
- 비밀 정보, 인증 정보, 개인 데이터를 문서나 Git에 기록하지 않는다.
- 파일을 수정한 Agent가 가능한 범위의 검증을 수행하고 결과를 명확히 보고한다.
- 새 문서나 디렉터리를 만들기 전에 기존 위치의 책임으로 관리할 수 있는지 확인한다.

## Project Session

Project 목표 설정, Task 생성, Task 결과 검토, Promotion, Project 상태 갱신을 수행하는 세션이다.

- 작업을 시작할 때 `PROJECT.md`와 `STATE.md`를 읽는다.
- 구조나 운영 절차가 필요할 때만 `STRUCTURE.md`를 읽는다.
- Task 생성 시 `tasks/_template/`을 복사하고 `TASK.md`, `STATUS.md`, `STATE.md`를 함께 준비한다.
- Task Agent를 직접 호출하거나 Task 수행 과정을 대신 관리하지 않는다.
- 종료된 Task의 `REPORT.md`와 REPORT가 지목한 파일을 검토해 Promotion 계획을 작성한다.
- 사용자에게 Promotion 적용 전 계획과 적용 후 변경·검증 결과를 각각 확인받는다.

## Task Session

하나의 Task를 독립적으로 수행하는 세션이다.

- Project 루트의 이 규칙을 계승한 뒤 Task의 `AGENTS.md`, `TASK.md`, `STATUS.md` 순서로 읽는다.
- `PROJECT.md`, `STATE.md`, 전체 `STRUCTURE.md`는 기본 컨텍스트로 읽지 않는다. 필요한 Project 정보는 `TASK.md`가 입력으로 지정해야 한다.
- 수행 중에는 자신의 `tasks/<task-name>/` 내부만 수정한다.
- Project 공식 경로와 Project `STATE.md`를 수정하거나 Promotion을 수행하지 않는다.
- 종료 시 `REPORT.md`를 완성하고 `STATUS.md`를 갱신한 뒤 사용자에게 Project 세션으로 돌아갈 수 있음을 알린다.

## Project-wide Rules

프로젝트 전체에 적용할 코딩 스타일, 검증 명령, 보안·데이터 규칙이 있다면 이 절에 추가한다.
