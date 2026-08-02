# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- 실제 clean legacy Project의 임시 clone에서 bundle apply, Project-owned preserve, migration parity, switch/full check/rollback을 재검증한다.
- 신규 독립 Project에 실제 Harness Engineering Python code snapshot을 넣고 두 read-only review Task를 실제 Codex CLI로 병렬 실행한다.
- Handoff, Task 격리, queue 상태, result index와 parent review 경계를 확인한다.
- 준비/실행 시간, 개입 횟수, 병렬성, 검증 통과와 복구 결과를 기록한다.
- 원본 Project를 변경하거나 적용 Project를 중앙 등록하지 않는다.

범위 밖: 외부 배포, Stage E 기능 구현, 원본 저장소 mutation

## Inputs


| Project Source | Task Snapshot |
| --- | --- |
| None | None |

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
package → legacy clone apply/migrate/switch/check/rollback → new Project+real code → two Codex Tasks queue → parent review/result index → metrics/exit decision
```

## Outputs

- `output/pilot-report.md`, `output/pilot-metrics.json`, `output/validation.md`
- Stage D exit 판정과 REPORT

## Completion Criteria

- 원본 source 두 저장소가 clean 상태를 유지한다.
- Legacy apply와 migration parity 100%, switch/full check/rollback이 통과한다.
- New Project check와 실제 Codex 2개 병렬 Task typed handoff가 통과한다.
- 두 Task의 상태·worktree·handoff가 독립적이고 result index로 재사용 가능하다.
- 단계 A–C 기능의 실제 운영 흐름과 사용자 개입 경계를 평가한다.
- 전체 44개 이상 회귀와 Project check가 통과한다.
- 전체 프로젝트 요구사항 충족 여부와 Stage E 보류/진입 근거를 명시한다.
