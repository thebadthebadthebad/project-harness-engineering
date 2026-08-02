# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- 기존 clean Project의 임시 clone에 versioned bundle을 apply하고 legacy 실데이터를 v2로 변환·검증·switch·rollback한다.
- 신규 독립 Project를 bundle로 만들고 실제 repository code snapshot을 제품 코드로 사용한다.
- 신규 Project에서 두 read-only review Task를 실제 Codex CLI로 queue/background 병렬 실행한다.
- handoff·Decision 격리·result index·exact-diff 검토 경계를 운영자 관점에서 확인한다.
- 준비 시간, 실행 시간, 사용자 개입 지점, 병렬성, 실패/복구, result 재사용과 검증 통과율을 측정한다.
- 원본 적용 Project를 수정하거나 Harness Engineering이 파일럿 Project를 등록·관리하지 않는다.

범위 밖:

- 파일럿 원본 저장소 변경, 외부 배포와 공개
- Stage E lease/heartbeat/PID/orphan 복구 구현
- 파일럿 결과를 근거로 하지 않은 추가 기능 구현

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
bundle package → legacy clone apply/migrate/rollback → new Project → real code snapshot → two real Codex Tasks → queue parallel run → parent review/result reuse → metric/exit judgment
```

## Outputs

- `output/pilot-report.md` 익명화한 단계·측정값·판정
- `output/pilot-metrics.json` 관측 가능한 지표
- `output/validation.md` 명령과 검증 결과
- REPORT와 Stage E 근거 판정

## Completion Criteria

- 원본 Project와 Harness Engineering 밖의 파일럿 source가 변경되지 않는다.
- 기존 Project apply가 Project-owned 파일을 보존하고 migration parity 100%, switch와 mutation 전 rollback을 통과한다.
- 신규 Project bundle/init/check가 통과한다.
- 실제 Codex CLI 두 Task가 독립 worktree에서 concurrent queue 실행되고 typed handoff를 회수한다.
- 한 Task의 결과·상태가 다른 Task를 덮어쓰지 않고 parent가 두 handoff를 읽을 수 있다.
- 최소 result index에 검토 결과를 등록하고 후속 context reference로 조회 가능하다.
- Stage A–C 전체 회귀와 Project check가 통과한다.
- 단계 D exit criteria와 전체 프로젝트 요구사항 충족 여부를 명시적으로 판정한다.
- Stage E 기능은 관찰된 실제 필요성이 없으면 계속 보류한다.
