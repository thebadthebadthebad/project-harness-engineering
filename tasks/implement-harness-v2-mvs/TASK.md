# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- Phase 0–2 Minimal Vertical Slice를 `project/` 공용 template에 구현한다.
- tracked JSON canonical records와 local SQLite/runtime manifest의 권위 경계를 구현한다.
- 현재 Project/Task Markdown을 읽는 read-only legacy inspection/conversion plan을 구현한다.
- 한 deterministic command Task를 격리 worktree에서 실행하고 typed handoff를 제출하는 local runner를 구현한다.
- staged Promotion의 subject digest, 검증, 사용자 승인 record와 integration commit provenance를 구현한다.
- DB 삭제, interrupted Run, stale approval, dirty worktree를 포함한 fault scenario를 자동 검증한다.
- 기존 Markdown lifecycle과 29개 회귀 테스트는 migration 전 공존 경로로 유지한다.

범위 밖:

- Codex runner, multi-writer scheduling, remote/team backend, 중앙 Project registry
- arbitrary Markdown importer, embeddings, 범용 evidence graph
- legacy writer 제거 또는 현재 저장소 authority의 v2 전환
- 분석 Task 결과의 공식 Promotion

## Inputs


| Project Source | Task Snapshot |
| --- | --- |
| `project/tools/project_harness/` | 같은 저장소의 pinned base commit에서 격리 worktree로 사용 |
| `project/tests/` | 같은 저장소의 pinned base commit에서 회귀 fixture로 사용 |
| `tasks/harness-architecture-review/` | read-only 설계 근거; `9558924`가 pre-close v1 fixture 기준점 |

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
authority/schema와 legacy dry-run
  → local runtime과 durable Run intent
  → isolated worktree command run
  → typed handoff
  → staged validation과 approval digest
  → integration commit provenance
  → fault injection과 전체 회귀
```

## Outputs

- 공용 template의 v2 canonical schema/validator와 `projectctl` 명령
- read-only legacy inspect/plan/parity report
- project-local SQLite runtime, durable Run manifest와 reconcile
- safe worktree lifecycle을 사용하는 deterministic command runner
- typed handoff와 staged Promotion vertical slice
- unit/integration/fault regression tests
- Task REPORT에 변경, 검증, 제한과 후속 Phase 3–5 기록

## Completion Criteria

- 기존 Project check와 전체 회귀 테스트가 통과한다.
- legacy inspect/plan은 repository state를 변경하지 않고 현재 fixture를 구조화한다.
- canonical record에 schema version, stable ID, revision과 digest가 검증된다.
- 동일 Run intent가 중복 dispatch되지 않는다.
- command Task가 isolated worktree에서 실행되고 main tree를 직접 변경하지 않는다.
- typed handoff 없이는 Task review 또는 Promotion 준비를 통과하지 않는다.
- staged diff 또는 validation 결과 변경 시 기존 approval이 무효화된다.
- validation 실패 시 official branch가 변경되지 않는다.
- SQLite 삭제 후 canonical record와 local Run manifest에서 runtime projection을 재구축한다.
- interrupted/unknown process를 자동 kill 또는 mutation retry하지 않는다.
- dirty 또는 provenance가 불명확한 worktree를 자동 삭제하지 않는다.
- 모든 공식 변경은 적용 전 대상과 이유, 적용 후 diff와 검증을 사용자에게 제시할 수 있다.
