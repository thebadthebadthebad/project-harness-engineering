# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- Harness installation integrity check를 legacy semantic check와 분리해 migration 도구를 먼저 안전하게 설치할 수 있게 한다.
- 실제 파일럿의 3열 이상 STATE row와 기존 promoted History를 supported legacy variant로 normalize한다.
- Unsupported/ambiguous row는 계속 명시적으로 거부하고 semantic parity 100% gate는 유지한다.
- Apply validation failure rollback과 Project-owned 파일 preserve를 유지한다.

범위 밖: 새 queue/adapter 기능, legacy 파일 자동 삭제, 실제 원본 Project 변경

## Inputs


| Project Source | Task Snapshot |
| --- | --- |
| tools/harnessctl.py | scripts/harnessctl.py |
| project/tools/project_harness | scripts/project_harness |
| project/tools/projectctl.py | scripts/projectctl.py |

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
failure fixture → installation-only gate → legacy variant normalization → parity/switch/rollback → full regression
```

## Outputs

- `scripts/harnessctl.py`, `scripts/project_harness/{cli,lifecycle,v2}.py` repair 후보
- 실제 legacy variant 회귀 test와 validation evidence
- REPORT와 Promotion 후보

## Completion Criteria

- 파일럿 구버전 fixture에 bundle apply가 성공하고 Project-owned 문서가 byte-identical이다.
- installation-only check가 손상된 managed tool/config는 거부하지만 pre-migration legacy 의미 차이는 허용한다.
- 3열 이상 STATE에서 Task와 Status를 정확히 추출한다.
- promoted History를 lossless legacy-history item으로 보존한다.
- migration plan/verify parity 100%, switch와 rollback이 통과한다.
- 기존 43개 회귀와 Project check, Task audit이 통과한다.
