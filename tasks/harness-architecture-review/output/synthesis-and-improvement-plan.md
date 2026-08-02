# 공용 Project 하네스 분석 종합 및 개선 계획

## Executive Summary

현재 하네스의 핵심 방향은 사용자 의도와 맞는다. 특히 Project/Task 분리, 비공유 대화 기반 문서 handoff, 사용자 통제, Task 완료와 Promotion 분리, baseline/audit는 유지해야 한다.

그러나 현재 구조는 “Task 전체를 격리한다”는 데는 성공했지만 “무엇을 작은 단위로 Project에 승계할지”와 “여러 Task가 같은 Project 규칙을 어떻게 공유할지”를 충분히 구조화하지 않았다. 대형 Project에서는 다음 네 가지가 먼저 병목이 된다.

1. 자유형 REPORT 전체가 pending handoff로 들어와 Project context가 다시 커진다.
2. Task가 따라야 할 Project 공통 불변조건, interface와 관련 결정이 작은 capsule로 전달되지 않는다.
3. shared worktree audit와 다중 active Task의 관계가 정의되지 않았다.
4. Promotion이 source/target/digest/validation/commit을 연결하는 독립 unit이 아니다.

권고는 전면 재작성보다 **현재 철학을 보존한 단계적 vNext**다. 먼저 typed handoff, Project Kernel, context queue, 명시적 동시성 정책을 구현하고, 그 결과로도 규모 문제가 남을 때 machine registry와 외부 Task work plane을 도입한다.

## 세 분석의 합의

### 유지할 핵심

- 공식 Project와 Task 작업 공간의 분리
- 사용자와 Agent의 목표·해석·Promotion 판단
- 사용자 통제의 세션 전환과 delegation 승인
- Task 완료와 공식 반영의 분리
- 계약/현재 상태/종료 handoff의 책임 분리
- Task 원문·로그를 기본 Project context에서 제외
- baseline, checksum, audit, deterministic validation
- 공식 결정은 ADR, 사건은 History, 원문은 Task에 두는 원칙
- Hook과 full-access agent를 보안 경계로 과장하지 않는 원칙

### 공통 결함

| 결함 | 영향 |
| --- | --- |
| 승계 후보가 자유형 REPORT에 묻힘 | 핵심 결정·관찰·재사용 코드만 고르기 어렵다. |
| pending REPORT 전체를 context에 포함 | Task 수와 REPORT 길이에 따라 Project context가 증가한다. |
| 작은 Project Kernel 부재 | 독립 Task가 공통 불변조건과 interface를 놓칠 수 있다. |
| Task dependency/충돌 영역 부재 | 넓은 Goal의 작업 순서와 통합 조건을 표현하기 어렵다. |
| shared worktree에서 병렬 정책 불명확 | 다른 Task 변경이 audit 경계 위반이 될 수 있다. |
| Promotion provenance 부족 | 어떤 source가 어떤 공식 결과가 됐는지 재현하기 어렵다. |
| completed Task가 active view에 잔류 | 장기 Goal에서 상태와 next action 노이즈가 쌓인다. |
| subagent 역할이 read/verify에 한정 | 사용자가 허용하려는 분해·문서 초안·질문 구체화 지원이 부족하다. |

## 양립 불가능한 선택지

### 1. 동시성

| 선택 | 장점 | 단점·우려 | 권고 |
| --- | --- | --- | --- |
| 한 branch당 active Task 하나 | 현재 audit와 가장 잘 맞고 단순하다. | 실제 병렬 Task를 수행할 수 없다. | 즉시 기본 정책으로 채택 |
| Task별 branch/worktree | 진정한 병렬성, diff와 merge base가 명확하다. | state lock, merge, integration 비용이 증가한다. | 병렬 요구 시 별도 실험 후 도입 |

### 2. 상태 저장

| 선택 | 장점 | 단점·우려 | 권고 |
| --- | --- | --- | --- |
| Markdown 계약 유지 | 사람이 읽고 수정하기 쉽고 기존 도구와 호환된다. | semantic 검증과 concurrency가 약하다. | 단기 유지 |
| YAML/JSON registry를 authoritative로 사용 | 상태·dependency·digest 검증이 쉽다. | migration과 human editing 비용이 크다. | 규모 benchmark 실패 시 도입 |

### 3. Task 보존 위치

| 선택 | 장점 | 단점·우려 | 권고 |
| --- | --- | --- | --- |
| 현재처럼 repo 내부 보존 | audit, 검색, 재현이 쉽다. | Task 수에 따라 tree와 저장소가 커진다. | 기본 유지, active view만 분리 |
| repo 밖 work plane + compact record | 공식 repo가 작고 경계가 강하다. | 백업, 발견, portability가 복잡하다. | 대용량/보안 요구 Project의 선택 모드 |

### 4. Skill과 Hook

| 선택 | 장점 | 단점·우려 | 권고 |
| --- | --- | --- | --- |
| 현재 core 유지 | 이미 검증된 관찰과 명시 절차를 보존한다. | 명령 중복과 도구 호출 비용이 있다. | 기능별 비용 측정 전 유지 |
| opt-in diagnostics/상호작용 Skill로 재편 | 일반 Project가 단순해지고 사용자 의도에 직접 기여한다. | 관찰 coverage와 기존 workflow가 바뀐다. | 별도 Task에서 A/B 검증 |

### 5. REPORT와 HANDOFF

| 선택 | 장점 | 단점·우려 | 권고 |
| --- | --- | --- | --- |
| REPORT 안에 compact capsule 추가 | 새 문서 없이 호환 가능하다. | 상세 보고와 capsule이 한 파일에 공존한다. | 1차 구현 |
| REPORT와 typed HANDOFF 분리 | context 경계가 가장 명확하다. | 파일/schema/lifecycle이 하나 늘어난다. | 1차 측정 후 필요 시 전환 |

## 권고 vNext 운영 모델

```text
사용자 의도 인터뷰
  → Agent가 Current Goal과 Task Map 초안 작성
  → 사용자: Task 경계·의존성·예상 승계 유형 승인
  → Task 계약 + 선택된 Project Kernel 생성
  → 사용자: 계약·위임 범위 승인
  → 한 branch의 독립 Task 수행
  → REPORT 상세 근거 + Handoff Capsule 작성
  → Project context에는 capsule과 pending queue만 노출
  → 사용자: 결과 accepted/rework/stopped 판단
  → Promotion Candidate unit 선택
  → Agent: source→target 적용 계획과 검증 계획 제시
  → 사용자 사전 승인
  → 공식 영역 반영·검증
  → exact diff와 결과 제시
  → 사용자 사후 승인
  → provenance가 있는 append-only Promotion 기록
```

downstream Task는 이전 Task workspace를 직접 입력으로 삼지 않는다. 필요한 결과가 공식 Project로 Promotion된 뒤 canonical reference를 사용한다. 병렬 진행상 미승계 결과가 필요하면 provisional dependency와 source digest를 사용자에게 별도 승인받는다.

## 권고 문서 구조와 내용

### `PROJECT.md`

기존 Goal/Scope에 다음 bounded section을 추가한다.

- Non-goals
- Project Invariants
- Domain Vocabulary 또는 Canonical Contracts

장문 지식을 넣지 않고 Task가 반드시 따라야 할 stable kernel만 둔다.

### `STATE.md`

기본 context에는 다음 세 queue만 유지한다.

- Active/Planned Tasks: 목적, dependency, status, expected promotion kind
- Pending Review
- Pending Promotion Decision

closed와 Promotion 결정 완료 Task는 기본 view에서 제거하고 History/on-demand query로만 본다.

### Task `TASK.md`

기존 구조를 유지하되 다음을 명시한다.

- Non-goals
- Dependencies: promoted canonical refs만 기본 허용
- Inherited Project Kernel refs
- Open Questions
- Expected Promotion Kinds
- Delegation Envelope

### Task `STATUS.md`

단기에는 유지한다. 다만 병렬 work item을 표현하지 못하므로 Work Plan은 lifecycle checkpoint이고 실제 실행 스케줄이 아님을 명시한다. 장기에는 machine phase + compact checkpoint로 축소할 수 있다.

### Task `REPORT.md`

상단에 Project가 자동 소비할 길이 제한 Handoff Capsule을 추가한다.

```text
Outcome
Goal Result
Decisions
Observations
Reusable Assets
Promotion Candidates
Excluded Task-local Material
Limitations
Evidence References
```

Promotion Candidates는 최소 다음 열을 가진다.

```text
ID | Kind | Source | Proposed Target | Rationale | Evidence | Coupling
```

상세 Work/Validation과 원문 파일은 capsule 아래에 남기되 기본 Project context에는 포함하지 않는다.

### History와 ADR

- close와 Promotion을 별도 append-only event로 기록한다.
- ADR은 장기 결정만 보유한다.
- Promotion event는 Task, candidate ID, source digest, target digest, 검증, integration commit을 연결한다.
- Task 요약을 History에 복제하지 않는다.

## Context 정책

- Project context는 Project Kernel, Current Goal, active/planned Task summary, pending review capsule, pending Promotion만 조립한다.
- closed Task REPORT, journal, research 원문, output tree와 raw logs는 자동 로드하지 않는다.
- Task context는 전체 Project가 아니라 승인된 Kernel과 `context_refs`만 포함한다.
- 각 capsule은 source digest를 가진다.
- context budget은 configurable하게 두고 실제 대형 시나리오로 상한을 결정한다. Greenfield의 6k/9k 제안은 시작 가설이지 현재 근거로 고정할 값이 아니다.
- 초과 시 silent truncation하지 않고 기여 항목과 on-demand 선택지를 보여준다.

## 자동화와 사용자 판단의 경계

### 자동화할 것

- scaffold, ID, schema와 상태 전이 검사
- Project Kernel/context capsule 조립과 digest
- dependency cycle과 canonical ref 존재 검사
- baseline과 boundary audit
- Promotion source/target/digest/commit provenance
- 적용 전 preview와 선언된 검증 실행
- active/pending/closed query와 compact view

### 자동화하지 않을 것

- Current Goal과 Task 분해의 최종 선택
- 결과 해석과 confidence 확정
- scope 확대
- Promotion 후보 선택과 target의 의미적 적합성
- 정책적 충돌 해결
- 공식 반영과 외부 배포의 최종 승인

subagent는 decomposition proposal, research, document draft, verification을 수행할 수 있다. 사용자의 질문에 대한 최종 상호작용, 범위 변경, 파일 통합과 lifecycle 책임은 부모 Agent가 가진다.

## 단계별 개선 계획

### Phase 0 — 기준 시나리오와 성공 지표

목적: 현재 순차 happy path 외에 사용자의 실제 규모를 재현한다.

- 시나리오: 8–12개 Task map, 3개 동시 pending handoff, 부분 Promotion, 충돌 후보 2개, compaction 재개.
- 지표: Project bootstrap context 크기, 자동 포함 REPORT 비율, 사용자 gate 수, lifecycle 명령/실패 수, Promotion trace completeness, unexpected audit 결과.
- 변경 대상: `experiments/`, 관련 runner/test.
- 검증: 기존 regression 유지 + 신규 scenario acceptance.

### Phase 1 — Compact handoff와 Project Kernel

목적: 사용자 의도와 가장 직접적으로 연결된 양방향 context 경계를 만든다.

- REPORT에 typed Handoff Capsule과 Promotion Candidates 추가.
- `projectctl context`는 pending REPORT 전체가 아니라 capsule만 포함.
- PROJECT/TASK 계약에 stable kernel과 selected context refs 추가.
- closed/on-demand handoff review 제공.
- 변경 대상: `project/tasks/_template/`, `project/PROJECT.md`, `project/STATE.md`, context/document validation, GUIDE/STRUCTURE, tests.
- 검증: long REPORT가 Project context에 유입되지 않음, capsule evidence link 유효, 기존 Task adapter 통과.

### Phase 2 — Lifecycle state와 동시성 명료화

목적: 대형 다중 Task에서 상태와 audit의 예측 가능성을 보장한다.

- 우선 한 branch당 active Task 하나를 activate/baseline에서 강제.
- active, pending review, pending Promotion, closed query를 분리.
- baseline overwrite를 막고 승인된 rebaseline만 별도 event로 허용.
- completed Task를 기본 Current Tasks view에서 제거.
- 변경 대상: lifecycle/context/check, STATE schema, GUIDE, tests.
- 검증: 두 번째 active Task 거부, close/review/Promotion 상태 전이, stale next action 제거.

### Phase 3 — Promotion provenance

목적: 선택적 승계를 재현 가능한 transaction으로 만든다.

- candidate ID 단위 선택과 source→target mapping.
- source/base/target digest, validation result, integration commit 기록.
- official root/path 존재와 conflict 검사.
- close event와 Promotion event를 append-only로 분리.
- 변경 대상: promotion CLI/lifecycle, History schema, docs/AGENTS, tests.
- 검증: 부분 Promotion, not-promoted, 충돌, 변경 후 승인 무효, revert/supersede scenario.

### Phase 4 — 사용자 상호작용과 보조 기능 정리

목적: 사람의 판단은 유지하고 반복 조작과 문서 중복을 줄인다.

- GUIDE에 intent interview와 Task map 승인 checkpoint 추가.
- STRUCTURE는 불변식, GUIDE는 happy path/recovery, CLI help는 명령 형식으로 책임 분리.
- planning/document subagent를 response-only부터 시험.
- Hook/Skill의 실제 비용과 기여를 측정해 core 유지 또는 opt-in 여부 결정.
- 변경 대상: 문서, Skill/agent config, observability experiments.
- 검증: 사용자 승인 gate 보존, subagent edit 없음/ownership 준수, token/command delta 비교.

### Phase 5 — 병렬/work-plane Greenfield spike

목적: 순차 기본 정책이 실제 사용을 제한할 때만 구조 전환을 검증한다.

- Task별 Git worktree/branch와 merge-base audit prototype.
- optional YAML/JSON registry와 generated Markdown view.
- repo 밖/ignored Task work plane + compact record prototype.
- 변경 대상: 별도 Engineering Task의 실험 코드와 fixture만; 공용 template 직접 교체 금지.
- 검증: 병렬 Task 충돌, state lock, archive/recovery, portability, context와 repo size 비교.

## 우선 결정이 필요한 항목

개선 구현 전에 사용자가 선택해야 할 핵심은 하나다.

- 실제 Project에서 여러 Task를 **동시에 수행해야 하는가**, 아니면 여러 Task로 분리하되 기본적으로 순차 수행해도 되는가?

순차 수행이면 Phase 1–4만으로 사용자 의도의 대부분을 낮은 위험으로 충족한다. 실제 병렬 수행이 필수라면 Phase 2의 단일 active guard는 임시 호환 모드이고, Phase 5 worktree 설계를 앞당겨야 한다.

## 최종 권고

1. 전면 greenfield 전환은 보류한다.
2. Phase 0과 Phase 1을 다음 독립 Engineering Task로 먼저 수행한다.
3. 현재 branch 기반 audit를 정직하게 순차 모델로 명시한다.
4. 병렬성이 실제 요구라면 별도 worktree spike 후 상태 registry 전환을 결정한다.
5. 모든 개선에서 “Task 원문은 내려가고, Project에는 typed capsule만 올라온다”를 핵심 acceptance criterion으로 사용한다.

