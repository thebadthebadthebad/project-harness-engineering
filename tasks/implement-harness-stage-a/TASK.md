# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- Project별 versioned bundle manifest와 공용 `harnessctl package|new|apply|update` 후보를 구현한다.
- JSON을 canonical state로 사용하는 `projectctl init|show|migrate` 후보를 구현한다.
- 현재 Project/Task Markdown을 실제 JSON으로 변환하고 semantic parity, authority switch와 rollback을 검증한다.
- scheduler 없이 Task branch/worktree를 만들고 typed handoff, validation, exact-diff Promotion을 수행하는 수동 흐름을 구현한다.
- 기존 Markdown lifecycle과 public template 검증을 깨지 않는 호환 경계를 유지한다.

범위 밖:

- Codex adapter, Decision/Result index, background queue와 worker
- lease, heartbeat, PID/orphan 복구, 자동 retry, runtime event ledger
- 실제 적용 Project의 authority 전환과 legacy 제거

## Inputs


| Project Source | Task Snapshot |
| --- | --- |
| project/tools/project_harness | scripts/project_harness |
| project/tools/projectctl.py | scripts/projectctl.py |
| tools/create_project.py | scripts/create_project.py |

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
bundle ownership·update
  → JSON state와 human View
  → legacy conversion·parity·switch·rollback
  → manual Task worktree·handoff·validation
  → exact-diff Promotion
  → candidate 회귀·fault 검증
```

## Outputs

- `scripts/harnessctl.py`와 versioned bundle manifest 후보
- `scripts/project_harness/`의 Stage A core 후보
- `scripts/projectctl.py`의 Stage A CLI 후보
- `scripts/tests/`의 신규·기존 적용, migration, worktree와 Promotion 검증
- `output/`의 fixture 결과와 검증 기록
- 완료 REPORT와 Project Promotion 대상 목록

## Completion Criteria

- 신규 Project `new`와 기존 저장소 `apply`가 Project-owned 파일을 덮어쓰지 않는다.
- update dry-run, managed checksum, conflict 중단과 검증 실패 rollback이 동작한다.
- JSON canonical record와 Markdown CLI View의 의미가 일치한다.
- current-format PROJECT/STATE/TASK/STATUS/REPORT/History가 실제 변환된다.
- legacy와 v2 normalized semantic parity가 100%가 아니면 authority switch가 차단된다.
- switch 전 rollback과 switch 후 v2 writer guard가 검증된다.
- 수동 Task가 별도 Git worktree에서 실행되고 main worktree를 직접 변경하지 않는다.
- validation 실패 시 Promotion apply가 차단된다.
- 선택한 후보만 integration worktree에 stage되고 exact diff digest 변경 시 승인 실패한다.
- dirty 또는 provenance가 불명확한 worktree를 자동 삭제하지 않는다.
- 기존 전체 회귀와 `projectctl check`가 통과한다.
