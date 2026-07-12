# STRUCTURE

이 문서는 Project와 Task의 관계, 디렉터리 책임, Task 생성·종료·Promotion 절차를 설명한다. 현재 프로젝트 내용은 `PROJECT.md`, 현재 상태는 `STATE.md`가 관리한다.

## Document Roles

### `README.md`

- 사람을 위한 프로젝트 소개와 시작 안내다.
- Agent의 기본 작업 컨텍스트가 아니다.

### `PROJECT.md`

- 프로젝트의 안정적인 목표, 범위, 주요 정보를 관리한다.
- 프로젝트 특성에 따라 필요한 안정적 섹션을 추가할 수 있다.

### `STRUCTURE.md`

- Project와 Task의 관계와 책임 분담을 설명한다.
- 디렉터리 역할과 Project 수준 운영 절차를 관리한다.

### `AGENTS.md`

- Project와 모든 Task가 계승하는 공통 Agent 규칙을 관리한다.
- 프로젝트 지식이나 현재 상태를 누적하지 않는다.

### `STATE.md`

- Current Goal과 현재 Goal에서 관리 중인 Task만 기록한다.
- 과거 작업 로그와 Task의 세부 실행 기록은 관리하지 않는다.

## Directory Structure

```text
project/
├── README.md
├── PROJECT.md
├── STRUCTURE.md
├── AGENTS.md
├── STATE.md
├── data/
│   └── AGENTS.md
├── src/
├── tools/
├── docs/
│   ├── AGENTS.md
│   ├── history/
│   └── adr/
└── tasks/
    └── _template/
        ├── AGENTS.md
        ├── TASK.md
        ├── STATUS.md
        ├── REPORT.md
        ├── data/
        ├── docs/
        │   ├── research/
        │   └── notes/
        ├── scripts/
        └── output/
```

## Project and Task Relationship

- Project는 공식 코드, 데이터, 도구, 문서와 현재 Project 상태를 관리한다.
- Task는 Project 목표를 달성하기 위한 하나의 서브 작업, 실험 또는 별도 리서치다.
- Task는 수행 과정과 임시 결과를 공식 Project 자산과 섞지 않기 위해 독립 작업 공간을 사용한다.
- Project 세션은 Task 목표를 정의하고 Task 공간을 생성하지만 Task 수행 과정을 직접 관리하거나 Task Agent를 호출하지 않는다.
- 사용자가 Project 세션과 Task 세션 사이를 직접 전환한다.
- Task 세션은 조사, 구현, 실험, 분석을 수행하고 REPORT를 작성하는 데 집중한다.
- Project 세션은 종료된 Task의 REPORT와 관련 파일을 새로 읽고 필요한 결과만 공식 자산으로 Promotion한다.

## Project Directories

### `src/`

- 프로젝트의 공식 라이브러리, 제품, 런타임 코드를 관리한다.

### `tools/`

- 여러 Task 또는 Project 운영에서 반복해서 사용할 공용 도구를 관리한다.
- 특정 Task에서만 필요한 실험 스크립트는 Task 내부에 남긴다.

### `data/`

- 프로젝트가 공식적으로 사용하는 데이터를 관리한다.
- 데이터셋은 `data/<data-name>/` 단위로 관리하고 해당 디렉터리에 README를 둔다.
- 원본 데이터는 가능한 경우 `raw/`에 두고 수정하거나 덮어쓰지 않는다.

### `docs/`

- 프로젝트의 공식 문서를 관리한다.
- `docs/adr/`은 프로젝트에 장기 영향을 주는 결정을 관리한다.
- `docs/history/`는 Task 종료와 Promotion 같은 Project 사건을 짧게 기록한다.
- Task의 실험 로그와 자유 메모는 공식 문서로 Promotion하지 않는 한 Task 내부에 남긴다.

### `tasks/`

- Project 목표를 위한 Task 작업 공간을 관리한다.
- Task 이름은 숫자 ID 대신 고유한 영문 kebab-case를 사용한다.
- 종료 Task는 경로를 유지하고 Project 후속 검토가 끝난 뒤에는 수정하지 않는다.

## Task Directories

- `data/`: Task 수행에만 사용하는 입력·중간 데이터다. 공식 Project 데이터가 아니다.
- `docs/research/`: 외부 자료, 출처, 조사 근거를 관리한다.
- `docs/notes/`: Task 내부 메모, 관찰, 실행 과정의 필요한 기록을 관리한다.
- `scripts/`: Task 수행, 실험, 분석, 재현을 위한 Task 전용 코드를 관리한다.
- `output/`: Task가 생성한 최종 결과 파일을 관리한다. 공식 Project 경로를 모방하는 Promotion staging 구조로 사용하지 않는다.

Task의 모든 관련 파일은 REPORT의 `Relevant Files`에서 경로와 의미를 설명한다.

## Current State

Project `STATE.md`의 Task 상태는 다음 네 개만 사용한다.

- `todo`: 생성되었지만 Task 수행을 시작하지 않았다.
- `doing`: 사용자가 Task 세션에서 수행 중이다.
- `review`: Task REPORT가 준비되어 Project 검토 또는 Promotion 판단을 기다린다.
- `completed`: Project 수준 후속 검토까지 끝났다.

Task `STATUS.md`는 `todo`, `doing`, `completed`, `stopped`만 사용한다. blocker는 새로운 상태값이 아니라 현재 blocker 항목으로 기록한다.

STATE는 로그가 아니다. 완료 Task는 Current Goal이 유지되는 동안만 남기고 Goal 전환 시 제거한다.

## Task Generation Workflow

```text
Project Agent가 Current Goal에 필요한 Task를 결정
    ↓
영문 kebab-case Task 이름 결정
    ↓
tasks/_template을 tasks/<task-name>/으로 복사
    ↓
TASK.md 작성 및 STATUS.md를 todo로 초기화
    ↓
STATE.md에 todo Task 등록
    ↓
사용자가 생성 결과와 TASK 계약 확인
    ↓
필요한 수정 후 STATUS와 STATE를 doing으로 변경
    ↓
사용자가 Task 세션으로 전환
```

Task 생성은 Project Agent가 실제 파일 작업까지 수행한다. 전용 자동화 도구가 없더라도 사용자에게 생성 결과를 확인받기 전에는 Task 수행을 시작하지 않는다.

## Task Completion Workflow

```text
Task Agent가 TASK.md에 따라 수행
    ↓
STATUS.md에는 현재 작업, blocker, 다음 행동만 유지
    ↓
REPORT.md 작성 및 Relevant Files 정리
    ↓
STATUS.md를 completed 또는 stopped로 변경
    ↓
사용자가 Project 세션으로 복귀
    ↓
Project Agent가 REPORT를 확인
    ↓
완료 Task는 STATE에서 review로 갱신
```

중지 Task에 수행 결과가 있으면 REPORT에 종료 이유와 남은 결과를 기록한다. 더 이상 현재 Goal의 작업이 아니면 STATE에서 제거한다.

## Promotion Workflow

Promotion은 Task 결과를 자동 복사하는 작업이 아니라 Project Agent가 공식 Project 자산으로 필요한 내용을 판단하고 반영하는 단계다.

```text
Project Agent가 REPORT와 Relevant Files 확인
    ↓
공식 반영 대상과 변경 경로를 판단
    ↓
사용자에게 적용 전 계획 제시
    ↓
사용자 승인 또는 수정
    ↓
Project Agent가 공식 경로에 직접 반영
    ↓
관련 검증 수행
    ↓
사용자에게 diff와 검증 결과 제시
    ↓
사용자 사후 확인 및 필요한 수정
    ↓
History 기록 및 STATE를 completed로 갱신
```

공식 반영 위치는 다음 기준으로 판단한다.

- 제품, 라이브러리, 런타임 코드: `src/`
- 반복 사용하는 Project 도구: `tools/`
- 공식 데이터: `data/`
- 장기 유지할 공식 문서: `docs/`
- 장기 영향을 주는 결정: 필요한 경우 `docs/adr/`
- Task 종료와 Promotion 사건: `docs/history/`

Promotion 가치가 없는 결과는 Task 내부에 그대로 두고 `not-promoted` History만 기록한다. ADR 필요성, 결과의 가치, 공식 반영 내용은 자동화하지 않는다.
