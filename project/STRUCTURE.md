# STRUCTURE

이 문서는 Project와 Task의 관계, 디렉터리 책임, Task 생성·완료·Promotion 절차를 설명한다.

## Authority and Distribution

- 각 적용 Project는 자신의 `.harness` 상태와 Git 이력을 독립적으로 소유한다. Harness Engineering 저장소는 bundle 원본·버전만 배포하며 적용 Project를 검색하거나 등록하지 않는다.
- `.harness/install.json`의 `authority`가 `legacy`이면 기존 Markdown lifecycle이 원본이다. `v2`이면 sealed JSON record가 원본이고 `projectctl show`, `task show/review`, `decision show`, `promotion show`, `result show`가 읽기 쉬운 Markdown View를 생성한다. `projectctl check`는 v2 record의 schema, digest, internal reference, Result index와 artifact provenance를 전수 검사한다.
- 공용 bundle의 `managed` 파일은 checksum 기반으로 갱신한다. `bootstrap` 파일은 없을 때만 만들고, `integration` 파일은 기존 사용자 내용을 보존한다.
- root distribution의 `harnessctl`은 `package|new|apply|update`를 담당한다. 적용 뒤 각 Project의 로컬 `tools/projectctl.py`가 상태와 Task를 담당하므로 중앙 설치에 실행 의존하지 않는다.

## Responsibility Boundaries

- Rules와 `AGENTS.md`: Project 전체의 지속 제약, authority와 역할 경계를 정의한다.
- Skills: 사용자가 명시 호출하는 반복 절차를 설명하며 상태 원본이나 보안 경계가 아니다.
- Hooks: 실행 관찰과 빠른 형식 신호를 제공하되 fail-open이며 lifecycle 결정을 대신하지 않는다.
- Workflow와 `projectctl`: Task·Decision·Result·Promotion 상태 전이와 검증을 결정론적으로 수행한다.
- Codex adapter: Task context와 실행 계약을 실제 CLI argv로 변환하고 JSONL·structured handoff를 회수한다.
- Task Agent와 subagent: 명시된 scope와 file ownership 안에서 산출물과 근거를 만든다. Subagent는 objective, inputs, context refs, owned paths, typed outputs 계약이 필요하다.
- Parent Agent: handoff 주장·validation·diff를 검토하고 후보를 선택·통합한다. Agent 결과를 자동으로 공식 사실로 승격하지 않는다.
- User: 목표·범위·가치 판단, 추가 권한, 외부 변경과 exact-diff Promotion을 승인한다.
- Deterministic scripts: bundle checksum, resolved path containment, schema/digest/reference, worktree, bounded validation, diff, index와 상태 전이를 담당한다.

이 책임들은 versioned bundle의 `AGENTS.md`, `.agents/`, `.codex/`, `tools/`, `tasks/_template/`, `GUIDE.md`, `STRUCTURE.md`에 각각 포함된다. 인증 정보, 적용 Project 목록과 Git-local run evidence는 bundle에 포함하지 않는다.

## Document Roles

- `PROJECT.md`: 프로젝트의 안정적인 Goal과 Scope
- `STATE.md`: Current Goal과 현재 Goal에서 관리 중인 Task
- `AGENTS.md`: 저장소 전체에 지속적으로 적용할 규칙
- `STRUCTURE.md`: Project/Task 운영 구조와 결정적 도구 사용법
- `GUIDE.md`: 사용자가 따라 하는 생성·세션 전환·장애 대응 절차
- Task `TASK.md`: Scope, 입력, 절차, 산출물, 완료 조건
- Task `STATUS.md`: Final Goal, Work Plan, Current Work, 현재 Status
- Task `REPORT.md`: 종료된 Task의 최종 handoff

Agent는 새 세션 또는 컨텍스트 압축 후 `projectctl context`를 한 번 실행해 이 문서들의 현재 운영 정보를 함께 확인한다. 같은 세션의 매 요청마다 문서를 다시 읽지 않는다.

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

- Legacy/manual session에서는 사용자가 Project 세션과 Task 세션을 직접 전환한다. Interactive `projectctl session`은 신뢰한 저장소에서 사용하는 full-access launcher다.
- v2 Task는 별도 worktree에서 사람이 수행하거나 Codex adapter가 non-interactive로 실행한다. Adapter 기본은 `workspace-write`, approval `never`, web/network disabled이며 execution contract가 우선한다.
- Stage C queue는 독립 Codex Task를 병렬 실행하지만 긴 Codex turn과 validation은 canonical writer lock 밖에서 수행한다. 마지막 짧은 JSON compare-and-write만 직렬화한다.
- Task 시작 전 Git 기준점을 고정하고 input digest, owned path와 validation을 계약에 기록한다.
- worktree, ownership과 Git 감사는 우발적 경계 이탈 감지 장치이며 hostile code를 막는 완전한 보안 sandbox가 아니다.

v2의 수동 Stage A 흐름은 다음과 같다.

```text
Task JSON 생성·commit
  → task start가 Task branch/worktree 생성
  → owned path 안에서 작업하고 typed handoff 작성
  → task submit이 ownership과 validation 검사
  → parent Agent가 handoff/candidate 검토
  → promotion prepare가 선택 후보만 integration worktree에 배치
  → 사용자가 actual exact diff·base·validation packet 승인
  → current HEAD·Task·diff·approval이 같고 apply 직전 validation이 통과할 때만 official branch에 반영
```

Task worktree와 integration worktree는 자동 삭제하지 않는다. Validation 실패, 후보 밖 변경, 승인 후 diff 변경, dirty official worktree는 반영을 차단한다.

Stage B에서는 active Task를 `task run`으로 Codex adapter에 넘길 수 있다. Adapter는 Project goal, Task contract, 검증된 context references와 Agent 역할만 bounded prompt로 구성한다. 최종 출력은 `completed`, `needs_decision`, `blocked` 중 하나이며, completed handoff도 parent review 뒤에만 Promotion 후보가 된다.

Stage C의 queue는 `.git/harness/v2/queue.sqlite3`에 현재 job 상태만 저장한다. 한 Project에 하나의 coordinator가 기본 total 2, writer 1로 Task를 scheduling한다. Codex subprocess와 validation은 병렬이지만 canonical JSON mutation은 짧은 re-entrant local file lock과 revision compare-and-swap으로 보호한다. SQLite는 공식 Project 지식, 중앙 registry, append-only ledger 또는 distributed scheduler가 아니다.

```text
ready Task + committed contract
  → queue enqueue
  → worker가 dependency와 reader/writer capacity 확인
  → worktree 생성 후 Codex adapter 병렬 실행
  → succeeded | needs_decision | blocked | cancelled
  → parent review와 canonical state commit
  → 선택 후보의 exact-diff Promotion
```

Queued job은 즉시 취소할 수 있고 running job은 cooperative cancel request로 Codex subprocess를 종료한다. Worker 재시작 시 남은 running row는 interrupted가 되며 자동 retry하지 않는다. `queue resume`은 사용자가 pending Decision, 잔존 프로세스와 worktree 상태를 확인한 뒤에만 사용한다. Lease, heartbeat, PID adoption, orphan 자동 복구와 mutation retry는 필요성이 입증될 때의 Stage E 후보다.

권한·외부 변경·범위 확대가 필요하면 해당 Task에 pending Decision record를 만들고 `needs_decision`으로 바꾼다. Decision View는 이유, 선택지, 권고, 각 영향, safe default와 보류 가능성을 보여준다. Explicit resolve는 그 Task만 active 또는 blocked로 전환한다.

Result index는 범용 graph가 아니다. `experiment|failure|review|decision|asset`의 짧은 요약, source refs, artifact path·byte·digest, reviewer·검증 상태, 재사용 여부와 supersedes만 보존하며 후속 Task는 `result:<id>`처럼 참조한다. Index는 kind/status/reusable/text로 단순 filter하고 canonical Result record에서 rebuild할 수 있다.

Project와 Task 세션은 사용자 shell에서 다음 명령으로 시작한다.

```bash
python3 tools/projectctl.py session project
python3 tools/projectctl.py session task <task-name>
```

런처는 신규 저장소의 config trust에 의존하지 않고 명시적으로 full-access와 approval 없음 옵션을 전달한다. 이 명령은 사용자가 세션을 여는 용도이며 Agent 자동 오케스트레이션 기능이 아니다.

일반 세션은 repository Hook trust를 우회하지 않는다. 사용자는 처음 실행할 때 `.codex/hooks.json`의 명령과 script를 검토하고 `/hooks`에서 상태를 확인한다.

Project/Task Skills는 `allow_implicit_invocation: false`인 명시 호출형이다. subagent는 사용자가 허용한 독립 읽기 작업에만 보수적으로 사용하며, full-access 환경의 지시상 제한을 sandbox 보안 경계로 취급하지 않는다.

## State

Project STATE Status는 `todo`, `doing`, `completed`만 사용한다.

- `todo`: Task가 생성되어 사용자 확인을 기다린다.
- `doing`: Task 생성 결과가 확인되고 기준점이 준비됐다.
- `completed`: Task STATUS가 completed이고 변경 감사까지 통과했다.

Task STATUS는 `todo`, `doing`, `completed`, `stopped`를 사용한다. STATUS와 STATE는 로그가 아니며 현재 내용만 유지한다.

STATE의 Current Tasks 표는 Task 이름과 Project 상태만 기록한다. Task 경로는 이름으로 결정하며 중지 Task는 Project가 종료를 확인하면 표에서 제거한다.

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
Task Agent가 작업을 멈춤(audit/close 실행 안 함)
    ↓
사용자가 Project 세션으로 복귀
    ↓
projectctl task status로 completed 또는 stopped 알림 확인
    ↓
projectctl task handoff로 REPORT 계약 확인
    ↓
projectctl task audit로 Task 외 Git 변경과 data checksum 검사
    ↓
REPORT와 상태 검증 및 감사 통과 시 projectctl task close
    ↓
completed는 STATE completed와 History 기록
stopped는 STATE에서 제거하고 stopped History 기록
```

예상 외 변경은 자동 복구하지 않는다. Project Agent는 diff를 사용자에게 보여주고 수정 지시를 기다린다.

Task completed는 handoff 검토 가능 시점을 결정한다. Promotion 시작 조건은 아니며 Promotion은 사용자가 결과 가치를 판단한 뒤 수행한다.

## Promotion

이 절의 기존 `promotion record` 흐름은 legacy authority에 적용된다. v2에서는 `promotion prepare|show|approve|apply`가 선택 후보, base commit, diff digest와 validation digest를 하나의 승인 대상으로 묶는다. 안전하고 위임된 여러 변경은 한 packet에 묶을 수 있지만 packet 밖 파일이나 승인 후 변경은 새 승인이 필요하다.

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
projectctl promotion record로 promoted 또는 not-promoted History 기록
```

`promotion record`는 이미 내린 결정을 기록할 뿐 파일을 복사하거나 가치를 판단하지 않는다. Promotion 가치 판단, 결과 해석, ADR 필요성 판단은 자동화하지 않는다.

## Deterministic Controls

- `projectctl context`: 새 세션에 현재 계약과 종료 대기 handoff를 한 번 제공한다.
- `projectctl check`: 필수 구조와 문서 section, legacy STATE 또는 v2 canonical schema·digest·reference·Result artifact/index, ADR·History 이름, Hook·Skill·agent 설정을 검사한다.
- `task validate`: lifecycle 단계별 STATUS, Work Plan, REPORT 형식을 검사한다.
- `task baseline|audit`: clean Git 기준점, linked data checksum, Task 밖 변경을 검사한다.
- `task status|handoff|close`: 종료 상태 탐지, 정규화 handoff, STATE와 History 반영을 수행한다.
- `observe list|report`: Git-local Hook metadata를 내용 없는 집계 보고서로 만든다.

Hook은 fail-open이고 관찰 coverage는 완전한 보안 감사를 의미하지 않는다. 형식 검사도 목표·결과의 품질 판단을 대신하지 않는다. 상세 실행 예제는 `GUIDE.md`가 담당한다.
