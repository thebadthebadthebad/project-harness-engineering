# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

Git-local simple SQLite queue, cancellable Codex adapter, 단일 coordinator 기반 background worker와 제한된 병렬 Task 실행 후보를 구현하고 race/fault 검증했다.

## Final Goal and Result

단계 C의 기능 구현 완료 조건을 충족했다. 적용 Project는 여러 Codex Task를 enqueue하고 기본 total 2/writer 1 제한으로 백그라운드 실행할 수 있다. Task별 decision·blocked·cancelled·dependency 상태가 독립적으로 유지되며 stale running은 자동 복구되지 않고 interrupted로 전환된다.

## Findings

- 단일 coordinator가 여러 Codex subprocess를 병렬 실행하고 canonical state mutation만 짧은 file lock으로 직렬화하면 multi-writer scheduler 없이 안전한 균형안을 만들 수 있다.
- Queue에는 현재 job 상태만 필요하며 append-only event ledger는 단계 C 요구를 해결하는 데 필요하지 않았다.
- writer 기본 1은 충돌 위험을 줄이고, 파일 격리와 테스트가 확보된 경우 명시적으로 2까지 올려 실제 병렬성을 얻을 수 있다.
- permission/decision/blocked는 job-local terminal state여서 다른 runnable Task의 scheduling을 막지 않는다.
- 프로세스가 비정상 종료된 stale running은 interrupted로 표시하고 명시적 resume만 허용해야 자동 mutation retry를 피할 수 있다.
- PID를 저장·adopt하지 않아 구현은 단순하지만, 비정상 종료 뒤 남은 orphan subprocess 확인은 운영자 책임이며 Stage E의 근거 후보다.

## Work and Validation

queue schema/CLI, cancellable adapter, coordinator, dependency/writer scheduling, detached start/stop과 5개 acceptance test를 구현했다. Stage C suite 5건, 기존 회귀 38건, Task audit이 모두 통과했다. 상세 결과는 `output/validation.md`에 기록했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| scripts/project_harness/queueing.py | code | SQLite current-state queue, singleton coordinator, concurrency/dependency/cancel/resume와 detached worker |
| scripts/project_harness/adapter.py | code | Polling subprocess cancellation, wall-clock timeout과 canonical mutation lock |
| scripts/project_harness/v2.py | code | Worker의 직렬화된 multi-Task worktree 시작과 dependencies |
| scripts/project_harness/cli.py | code | queue와 worker public CLI |
| scripts/tests/test_stage_c.py | test | Parallel, writer limit, decision, dependency, cancel, singleton, interruption와 background acceptance |
| output/validation.md | evidence | 실행한 검증과 정량 결과 |

## Limitations

SQLite는 distributed scheduler나 history ledger가 아니며 한 Project·한 coordinator만 지원한다. Worker crash 시 살아남은 orphan Codex를 adopt하거나 kill하지 않는다. Token budget은 최종 usage에서 위반을 판정하며 선제 중단은 현재 event가 중간 usage를 제공하지 않아 제한적이다. Mutation 자동 retry, lease, heartbeat와 PID 복구는 Stage E로 연기했다.

## Project Follow-up

후보를 public template과 tests에 Promotion하고 전체 회귀를 재실행한다. 그 다음 Stage D에서 실제 Project 파일럿으로 A–C 사용 흐름과 운영 지표를 검증해야 전체 프로젝트 요구사항이 완료된다.
