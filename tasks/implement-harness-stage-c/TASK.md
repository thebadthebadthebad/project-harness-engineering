# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- Git-local SQLite에 `queued|running|succeeded|needs_decision|blocked|cancelled|interrupted` 현재 상태를 저장하는 simple queue를 구현한다.
- 한 Project에 하나의 worker coordinator만 실행하고 기본 total parallel 2, writer parallel 1로 독립 Task를 병렬 실행한다.
- queue enqueue/list/status/cancel/resume과 worker run/start/stop CLI를 제공한다.
- 의존 Task가 review 상태가 될 때까지 dependent job만 대기시키고 다른 runnable job은 계속한다.
- 실행 중 cancel request와 시간 제한을 Codex subprocess 종료로 연결한다.
- worker 시작 시 남아 있는 running job은 interrupted로 표시하며 자동 재시도·adoption하지 않는다.
- Task canonical mutation은 짧은 Project-local file lock으로 직렬화하고 Codex 실행 자체는 병렬화한다.

범위 밖:

- lease, heartbeat, PID adoption, orphan 자동 복구, mutation 자동 retry
- append-only runtime ledger와 distributed/multi-writer scheduler
- worker가 사용자 Decision 또는 Promotion을 대신 승인하는 기능

## Inputs


| Project Source | Task Snapshot |
| --- | --- |
| project/tools/project_harness | scripts/project_harness |
| project/tools/projectctl.py | scripts/projectctl.py |

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
queue schema/CLI → cancellable adapter → worker concurrency/dependency/state isolation → detached start/stop → race/fault acceptance
```

## Outputs

- `scripts/project_harness/queueing.py` simple SQLite queue와 worker 후보
- `scripts/project_harness/adapter.py`, `v2.py`, `cli.py` Stage C integration 후보
- `scripts/tests/test_stage_c.py` parallel/background/cancel/interruption suite
- 운영 문서 후보, `output/validation.md`, REPORT

## Completion Criteria

- SQLite는 Git-local 단일 queue와 현재 job 상태만 저장하며 event ledger가 아니다.
- 동시에 2개 read-only Task가 실행되고 elapsed time으로 실제 병렬성이 검증된다.
- writer Task 2개는 기본 writer limit 1을 넘지 않는다.
- 하나의 Task가 needs_decision/blocked여도 다른 독립 Task가 succeeded로 완료된다.
- dependency가 미충족이면 해당 Task만 queued를 유지한다.
- queued cancel과 running cancel request가 Task-local 결과로 반영된다.
- worker 재시작의 stale running은 interrupted이며 explicit resume 전 실행되지 않는다.
- 두 번째 worker coordinator는 singleton lock으로 거부된다.
- background start/stop이 동작하며 PID adoption이나 kill 기반 복구를 사용하지 않는다.
- 기존 Stage A/B와 전체 회귀, Project check와 Task audit이 통과한다.
