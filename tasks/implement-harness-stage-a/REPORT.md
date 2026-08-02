# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

Stage A의 배포·적용·업데이트, JSON authority/View, 실제 legacy 변환, 수동 worktree Task와 exact-diff Promotion 후보를 구현하고 fault 검증을 완료했다.

## Final Goal and Result

Versioned bundle을 새 Project와 기존 저장소에 안전하게 적용하고, Task를 공식 worktree와 분리해 수행한 뒤 typed handoff와 선택된 exact diff만 승인·반영하는 최소 흐름이 동작한다. Legacy Markdown은 side-by-side candidate로 실제 변환되며 normalized semantic parity가 일치할 때만 v2 authority로 전환된다.

## Findings

- 배포 파일을 `managed`, `bootstrap`, `integration`으로 나누면 Project-owned 문서와 규칙을 보존하면서 공용 도구만 갱신할 수 있다.
- `.harness`가 canonical JSON을 소유하므로 전체 디렉터리를 ignore할 수 없고, Git-local runtime 및 observability만 추적 대상에서 제외해야 한다.
- v2 authority 전환 뒤 legacy writer를 차단해야 split-brain을 피할 수 있다.
- Task worktree와 Promotion integration worktree를 분리하면 후보 선택과 exact-diff 승인을 실제 파일 경계로 검증할 수 있다.
- 실패 validation과 승인 후 diff 변경은 Promotion을 차단하며 worktree는 자동 삭제하지 않는다.

## Work and Validation

`harnessctl package|new|apply|update`, v2 record/view/migration CLI, worktree Task/handoff/Promotion을 구현했다. 후보 acceptance 5건과 기존 회귀 29건이 통과했고, conflict·rollback·validation failure·stale approval fault를 검증했다. 세부 명령과 결과는 `output/validation.md`에 기록했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| scripts/harnessctl.py | code | Versioned bundle package/new/apply/update와 ownership·checksum·rollback |
| scripts/create_project.py | code | harnessctl 기반 호환 생성 wrapper |
| scripts/project_harness/v2.py | code | JSON authority, migration, worktree, handoff와 Promotion core |
| scripts/project_harness/cli.py | code | Stage A public CLI 연결과 legacy writer guard |
| scripts/project_harness/lifecycle.py | code | canonical `.harness` 추적을 반영한 구조 검사 |
| scripts/template/.gitignore | template | canonical state는 추적하고 observability만 제외 |
| scripts/tests/test_stage_a.py | test | Stage A E2E와 fault acceptance suite |
| output/validation.md | evidence | 실행한 검증과 결과 |

## Limitations

Stage B의 Codex adapter·Decision·Result index와 Stage C의 queue·worker·parallel 실행은 범위 밖이다. Legacy rollback은 v2 mutation 전까지만 허용하고, worktree 정리는 provenance 확인 전 자동화하지 않았다. Migration 후 legacy 파일 제거는 파일럿과 보존 기간을 통과할 때까지 수행하지 않는다.

## Project Follow-up

후보를 공식 `project/tools`, root `tools`, public `.gitignore`, tests와 운영 문서에 Promotion하고 전체 회귀를 다시 실행한다. 그 다음 별도 Engineering Task로 Stage B를 구현한다.
