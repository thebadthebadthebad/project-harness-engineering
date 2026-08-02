# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- v2 task create에 반복 가능한 `--input` Project-relative file을 추가하고 존재·경로 안전성을 검증한다.
- Adapter가 input digest, 크기와 UTF-8 content를 총량 제한 안에서 prompt에 포함한다.
- 파일별·총량 초과, binary와 실행 후 input 변경을 명시적으로 차단한다.
- Run evidence에 실제 input digest set을 기록해 Task 시작 계약과 provenance를 검증한다.

범위 밖: directory/archive 자동 주입, retrieval graph, sandbox 권한 확대

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
input schema/CLI → bounded loader/digest → start/run drift gate → regression → pilot handoff
```

## Outputs

- v2/CLI/adapter 후보와 focused test
- validation evidence와 REPORT

## Completion Criteria

- `--input` 파일만 context에 포함되고 traversal, missing, binary가 거부된다.
- 기본 파일 128 KiB, 총 256 KiB 제한이 적용된다.
- Task start 후 input digest 변경 시 Codex 실행이 차단된다.
- Prompt와 run evidence가 input path/digest/content를 포함한다.
- 기존 44개 회귀와 check/audit이 통과한다.
