# 현 구조 비의존 Greenfield 설계

## 제안: Capsule–Promotion Harness

핵심은 공식 Project, 상태·승인 control plane, Task work plane을 분리하고 양방향 전달을 작은 typed capsule로 제한하는 것이다.

## 설계 불변조건

1. Canonical plane에는 승인된 코드, 결정, 관찰, interface만 둔다.
2. Control plane에는 목표, Task registry, 승인, Promotion ledger와 audit event만 둔다.
3. Work plane에는 Task 대화, 실험, 초안, 로그와 전체 산출물을 두며 기본 Project context에서 제외한다.
4. Task는 고정 base revision과 입력 capsule로 시작하고 Project 공식 경로를 직접 수정하지 않는다.
5. Task 완료와 Promotion은 독립이다. 한 Task에서 후보 일부만 채택하거나 아무것도 채택하지 않을 수 있다.
6. 공유 대화가 아니라 versioned decision, observation, interface가 Task 간 계약이다.
7. 목표·분해·해석·승계 가치는 사용자와 Agent가 판단하고 schema/hash/dependency/path/test/event만 자동화한다.
8. 승인 대상은 digest로 고정하며 내용이 바뀌면 승인을 무효화한다.

## End-to-end workflow

```text
Intent interview
  → Objective와 Task DAG 초안
  → G0 사용자 목표·범위·분해 승인
  → Task brief와 context capsule 생성
  → G1 사용자 계약·위임 envelope 승인
  → 독립 workspace에서 사용자–Task Agent 작업
  → 범위 변경 시 G2 brief revision 승인
  → HANDOFF와 typed Promotion candidates 제출
  → 독립 verification
  → G3 사용자 accepted / stopped / rework 판정
  → 선택 후보로 Promotion packet 작성
  → G4 사용자 unit·대상·검증 계획 승인
  → integration workspace에서 적용·검증
  → exact diff와 provenance 제시
  → G5 사용자 공식 commit 승인
  → canonical 반영과 ledger 기록
  → Task archive 또는 보존기간 후 승인 삭제
```

Task와 Promotion은 별도 상태 머신을 가진다.

```text
Task: draft → ready → active ↔ blocked → review_ready
                                      ├→ accepted → closed
                                      ├→ rework → active
                                      └→ stopped → closed

Promotion: candidate → reviewed → selected → staged → verified
                                                  ├→ committed
                                                  ├→ rejected
                                                  └→ failed
```

## 제안 directory tree

```text
<project-repo>/
├── README.md
├── <domain-owned canonical roots...>
├── knowledge/
│   ├── decisions/
│   ├── observations/
│   └── interfaces/
└── .harness/
    ├── project.yaml
    ├── policy.yaml
    ├── objectives/
    ├── registry/tasks/
    ├── registry/promotions/
    ├── records/tasks/          # 종료 후 1-page record
    ├── approvals/
    ├── events/
    ├── schemas/
    ├── context/
    ├── roles/
    ├── skills/
    └── hooks/

<project-work-root>/            # repo 밖 또는 ignored
├── tasks/<task>/
│   ├── BRIEF.yaml
│   ├── CHECKPOINT.yaml
│   ├── HANDOFF.yaml
│   ├── journal/
│   ├── evidence/
│   ├── results/
│   ├── scratch/
│   └── candidates/
├── integration/<promotion>/
└── archive/
```

공식 source/data/docs 이름은 하네스가 강제하지 않고 `canonical_roots`로 Project가 선언한다.

## 핵심 schema

- Project: mission, canonical roots, current objective, context budget.
- Objective: outcome, success measures, constraints, Task DAG.
- Task registry: state, revision, base ref, scope, acceptance, dependencies, selected context refs, delegation envelope, checkpoint digest.
- Brief: 사용자 승인 목표, 질문, 입출력, 완료조건, 금지사항과 위임 범위.
- Checkpoint: completed/current/next/open questions/working refs만 가진 재개 capsule.
- Handoff: outcome, goal result, key findings, limitations, validation refs, candidate unit index, non-promoted results.
- Decision: context, choice, alternatives, consequences, evidence, supersedes.
- Observation: 검증 가능한 claim, 조건, evidence, confidence, freshness, supersedes.
- Interface: producer/consumer, schema 또는 API, invariant, version, compatibility policy.
- Promotion unit: kind, source Task, base ref, payload hash, targets, rationale, provenance, compatibility, validation, risk.
- Approval: gate, subject digest, decision, condition, actor, timestamp.
- compact Task record: 목표, 결과, 선택/거부 unit, limitation, archive pointer.

Promotion unit은 decision, observation, code patch, canonical documentation update로 나누며 독립 승인·revert·supersede할 수 있어야 한다. 분리 불가능한 후보만 atomic group으로 묶는다.

## Context budget과 노이즈 통제

- 파일 트리 탐색이 아니라 Task의 `context_refs` allowlist로 capsule을 조립한다.
- journal, raw log, closed handoff, archive는 자동 로드하지 않는다.
- capsule에 source digest를 포함하고 변경 시 stale로 처리한다.
- active Task는 Project context에 짧은 summary만 넣고 상세는 요청 시 연다.
- decision/observation은 `supersedes`로 이전 항목을 기본 context에서 제거한다.
- budget 초과 시 조용히 자르지 않고 가장 큰 기여자와 제거 후보를 보여주며 실패한다.
- 초기 제안치는 Project 6,000 tokens, Task 9,000 tokens이지만 실제 사례 benchmark로 조정해야 한다.

## 승계 기준

기본 승계 대상은 다음 네 종류다.

1. 장기 구조 Decision
2. 다른 Task가 재사용할 수 있는 검증된 Observation
3. 공식 대상, 테스트와 compatibility가 명확한 Reusable Code
4. 사용자·운영·interface를 설명하는 최소 Canonical Documentation update

Task journal, 사고 과정, raw research dump, 탐색용 fixture, 중간 생성물, 실패 로그, 중복 요약과 일회성 코드는 기본적으로 승계하지 않는다.

판단 기준은 두 번째 소비자 존재 가능성, provenance, 공식 owner/target, 검증 가능성, interface 충돌, 유지비 대비 재사용 가치다.

## 자동화와 사용자 경계

자동화:

- ID/scaffold/schema, DAG cycle, dependency version
- base pin, path boundary, candidate hash
- context capsule과 budget 검사
- 상태 전이 전제조건과 append-only event
- Promotion preview, conflict 검사, integration workspace
- 선언된 validation과 결과 hash
- compact record와 stale evidence 알림

사용자 판단:

- 목표 우선순위와 Task 분해의 최종 선택
- 근거 해석과 신뢰도 확정
- scope 확대와 interface 정책 충돌 해결
- 승계 unit 선택
- 공식 commit, 외부 배포, archive 삭제

Agent는 acceptance가 모호하거나, 새 canonical interface가 필요하거나, 비용·외부 영향이 승인 범위를 넘거나, 근거가 부족하면 사용자에게 질문한다.

## Failure와 recovery

- compaction/중단은 CHECKPOINT에서 재개한다.
- scope creep은 blocked 후 brief revision 승인을 받는다.
- 공식 변경은 가능하면 read-only mount로 막고, 불가능하면 quarantine와 diff audit을 사용한다.
- Promotion은 integration workspace에서 실패분을 폐기·재생성한다.
- 검증 뒤 diff가 바뀌면 승인 digest를 무효화한다.
- 잘못된 공식 반영은 revert하고 append-only superseding event를 남긴다.
- state view 손상은 event ledger에서 재구축한다.
- archive 삭제는 retention 이후 사용자 승인을 요구한다.

## 현 하네스에서 유지/대체할 것

유지:

- Project/Task 책임 분리
- 안정 목표와 현재 상태의 분리
- Task 계약, checkpoint, handoff
- 완료와 Promotion 분리
- 사용자 가치 판단과 위임 통제
- baseline/checksum/audit와 digest context
- reader/verifier 역할
- Hook을 metadata 관찰로만 보는 원칙

대체:

- authoritative Markdown table → schema registry + human view
- in-repo 전체 Task 보존 → 외부 work plane + compact record
- snapshot copy/mutable symlink → immutable revision/content-addressed input
- 자유형 REPORT → typed HANDOFF + Promotion units
- 사후 audit 중심 공식 경로 보호 → canonical write 금지 + integration transaction
- completed Task의 Current Tasks 유지 → registry query
- 수동 파일 반영 후 기록 → preview/approval/stage/verify/commit transaction
- 고정 canonical directory 이름 → Project 선언형 roots
- 문서 방문 Hook 중심 통제 → context compiler budget/digest

## 단계적 도입

1. 기존 구조 옆에 typed handoff와 context compiler를 추가한다.
2. 신규 Task부터 외부/ignored work plane과 immutable base를 시험한다.
3. integration worktree와 digest 기반 transactional Promotion을 도입한다.
4. 고위험 Project에 권한 격리와 retention/archive를 추가한다.
5. 검증 후 legacy Markdown state와 in-repo Task 전체 보존을 제거한다.

schema는 일관성을 높이지만 직접 편집성이 낮고, 외부 workspace는 노이즈를 줄이지만 발견·백업 비용이 있다. 따라서 greenfield 전체 전환은 독립 실험 결과 없이 즉시 적용하지 않는다.

## 근거

- `project/STRUCTURE.md`
- `project/GUIDE.md`
- `project/tasks/_template/REPORT.md`
- `experiments/RESULTS.md`
- `tasks/stabilize-workflow-core/REPORT.md`
- `tasks/validate-observable-workflow/REPORT.md`

