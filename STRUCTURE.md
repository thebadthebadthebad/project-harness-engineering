# STRUCTURE

이 문서는 Harness Engineering Project의 구조와 공용 `project/` 템플릿을 관리하는 절차를 설명한다.

## Repository Structure

```text
project-harness-engineering/
├── README.md
├── PROJECT.md
├── STRUCTURE.md
├── AGENTS.md
├── STATE.md
├── docs/
│   ├── AGENTS.md
│   ├── adr/
│   └── history/
├── tasks/
│   ├── _template/
│   └── <task-name>/
└── project/
    ├── README.md
    ├── PROJECT.md
    ├── STRUCTURE.md
    ├── AGENTS.md
    ├── STATE.md
    ├── src/
    ├── tools/
    ├── data/
    ├── docs/
    └── tasks/
```

## Responsibilities

### Engineering Project Root

- `PROJECT.md`는 공용 하네스 개발 목표와 범위를 관리한다.
- `STATE.md`는 현재 Engineering 목표와 현재 Task만 관리한다.
- `docs/adr/`은 하네스에 장기 영향을 주는 결정을 관리한다.
- `docs/history/`는 Engineering Task 종료와 공용 템플릿 Promotion 사건만 짧게 기록한다.
- `tasks/`는 공용 템플릿을 위한 조사, 설계, 실험, 검증 작업 공간이다.

### Public Template

- `project/`는 검토된 공용 배포 템플릿이다.
- 다른 프로젝트에 복사할 대상은 `project/` 아래 내용이다.
- `project/`의 PROJECT와 STATE는 실제 Engineering 상태가 아니라 새 프로젝트가 작성할 placeholder를 제공한다.
- `project/`는 Engineering Task가 직접 수정하지 않고 Project 세션의 Promotion 단계에서만 수정한다.

## Task Names and State

- Task 이름은 숫자 ID 없이 영문 kebab-case를 사용한다.
- Project STATE는 `todo`, `doing`, `review`, `completed`만 사용한다.
- Task STATUS는 `todo`, `doing`, `completed`, `stopped`만 사용한다.
- blocker는 새로운 상태값이 아니라 STATE Note 또는 Task STATUS Blocker에 현재 내용만 기록한다.
- 완료 Task는 Current Goal이 바뀔 때 STATE에서 제거한다.

## Engineering Task Workflow

```text
Project Agent가 필요한 Engineering Task 결정
    ↓
tasks/_template을 tasks/<task-name>/으로 복사
    ↓
TASK, STATUS, STATE 작성
    ↓
사용자가 생성 결과와 Task 계약 확인
    ↓
사용자가 독립 Task 세션으로 전환
    ↓
Task Agent가 Task 내부에서 조사·실험·검증
    ↓
Task Agent가 REPORT 작성 후 종료
    ↓
사용자가 Project 세션으로 복귀
```

Project Agent는 Task를 생성하지만 Task Agent를 호출하거나 Task 수행을 자동으로 오케스트레이션하지 않는다.

## Public Template Promotion

```text
Project Agent가 Engineering Task REPORT와 Relevant Files 확인
    ↓
project/ 반영 계획과 변경 경로 작성
    ↓
사용자가 적용 전 계획 확인
    ↓
Project Agent가 project/에 필요한 내용 반영
    ↓
문서 참조, 구조, diff 검증
    ↓
사용자가 적용 후 결과 확인
    ↓
필요한 수정 후 History와 STATE 갱신
```

- Task 결과를 그대로 복사하는 것을 기본값으로 삼지 않는다.
- Project Agent는 공식 템플릿에 필요한 내용을 판단해 직접 작성·수정한다.
- Promotion 가치 판단, ADR 필요성 판단, 문서 내용 판단은 자동화하지 않는다.
- Promotion하지 않은 결과는 Engineering Task 내부에 보존한다.

## Records

- ADR 파일명은 날짜 없이 `<decision-name>.md` 형식의 영문 kebab-case를 사용한다.
- History 파일명은 `YYYY-MM-DD-HHMM-<action>-<task-name>.md`를 사용한다.
- History는 REPORT를 요약하지 않고 사건, Task 경로, 공식 반영 경로만 기록한다.

## Automation

이번 구조에는 Task 생성 도구, validator, Skill, Hook을 포함하지 않는다. 실제 수동 운영을 반복해 문서 형식이 안정된 뒤 결정적 작업만 별도 Task로 검토한다.
