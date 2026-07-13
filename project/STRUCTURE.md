# STRUCTURE

이 문서는 Project와 Task의 관계, 디렉터리 책임, Task 생성·완료·Promotion 절차를 설명한다.

## Document Roles

- `PROJECT.md`: 프로젝트의 안정적인 Goal과 Scope
- `STATE.md`: Current Goal과 현재 Goal에서 관리 중인 Task
- `AGENTS.md`: 저장소 전체에 지속적으로 적용할 규칙
- `STRUCTURE.md`: Project/Task 운영 구조와 결정적 도구 사용법
- Task `TASK.md`: Scope, 입력, 절차, 산출물, 완료 조건
- Task `STATUS.md`: Final Goal, Work Plan, Current Work, 현재 Status
- Task `REPORT.md`: 종료된 Task의 최종 handoff

## Directory Responsibilities

- `src/`: 공식 제품·라이브러리·런타임 코드
- `tools/`: Project에서 반복 사용하는 공용 도구
- `data/`: 공식 데이터
- `docs/`: 공식 문서, ADR, Project 사건 기록
- `tasks/`: Project Goal을 위한 서브 작업, 실험, 리서치 공간

Task 내부 디렉터리는 다음 책임을 가진다.

- `scripts/`: Project에서 복사한 코드 snapshot과 Task 실행·실험 코드
- `data/`: Project 공식 데이터에 대한 symlink
- `docs/research/`: 외부 조사 근거
- `docs/notes/`: Task 수행 메모
- `output/`: Task 결과 파일

## Execution Model

- 사용자가 Project 세션과 Task 세션을 직접 전환한다.
- Task Agent는 Project Agent가 호출하거나 자동으로 오케스트레이션하지 않는다.
- Task 세션은 `danger-full-access`, network 허용, approval 없음으로 실행한다.
- 현재 환경에서는 Project write를 sandbox로 막지 않는다.
- Task 시작 전 Git 기준점과 linked data checksum을 저장하고 종료 후 예상 외 변경을 감사한다.
- 감사는 우발적 변경 감지 장치이며 악의적 변경을 막는 보안 경계가 아니다.

Task 세션은 Task 디렉터리에서 다음 명령으로 시작한다.

```bash
codex -C tasks/<task-name> --strict-config
```

Task의 `.codex/config.toml`은 `sandbox_mode = "danger-full-access"`, `approval_policy = "never"`를 적용한다.

## State

Project STATE Status는 `todo`, `doing`, `completed`만 사용한다.

- `todo`: Task가 생성되어 사용자 확인을 기다린다.
- `doing`: Task 생성 결과가 확인되고 기준점이 준비됐다.
- `completed`: Task STATUS가 completed이고 변경 감사까지 통과했다.

Task STATUS는 `todo`, `doing`, `completed`, `stopped`를 사용한다. STATUS와 STATE는 로그가 아니며 현재 내용만 유지한다.

## Task Creation

```text
사용자와 Project Agent가 Final Goal, 코드, 데이터를 결정
    ↓
projectctl task create로 Task 생성
    ↓
Project Agent가 TASK의 Scope, Workflow, Outputs, Completion Criteria 작성
    ↓
사용자가 생성 결과 확인
    ↓
projectctl task activate 실행
    ↓
생성·활성화 변경을 Git commit
    ↓
projectctl task baseline 실행
    ↓
사용자가 Task 세션으로 전환
```

코드는 `src/` 또는 `tools/`에서 선택해 Task `scripts/`로 복사한다. 공식 데이터는 Task `data/`에 상대 symlink로 연결한다.

## Completion

```text
Task Agent가 REPORT 작성 및 STATUS completed
    ↓
사용자가 Project 세션으로 복귀
    ↓
projectctl task status로 completed 알림 확인
    ↓
projectctl task audit로 Task 외 Git 변경과 data checksum 검사
    ↓
감사 통과 시 projectctl task acknowledge
    ↓
STATE completed 및 completed History 기록
```

예상 외 변경은 자동 복구하지 않는다. Project Agent는 diff를 사용자에게 보여주고 수정 지시를 기다린다.

Task completed는 Promotion 시작 조건이 아니다. Promotion은 사용자의 명시적 요청이 있을 때만 수행한다.

## Promotion

```text
사용자가 Promotion 요청
    ↓
Project Agent가 REPORT와 Relevant Files 검토
    ↓
적용 계획과 공식 변경 경로를 사용자에게 제시
    ↓
사용자 사전 확인
    ↓
Project Agent가 src/tools/data/docs에 필요한 내용 반영
    ↓
diff와 검증 결과를 사용자에게 제시
    ↓
사용자 사후 확인
    ↓
promoted 또는 not-promoted History 기록
```

Promotion 가치 판단, 결과 해석, ADR 필요성 판단은 자동화하지 않는다.
