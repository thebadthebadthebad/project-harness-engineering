# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- `project/tools/project_harness/v2.py`의 Task human View 렌더링만 변경한다.
- `tests/test_bounded_inputs.py`에 입력 표시와 빈 입력 표시 회귀를 추가한다.

범위 밖: Task JSON schema 변경, 입력 주입 방식 변경, queue/adapter 동작 변경

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
View 요구 확인 → 최소 렌더링 변경 → 집중 테스트 → 전체 회귀 → 공식 반영
```

## Outputs

- Task View에 bounded input의 Project-relative path, byte size, SHA-256가 표시된다.
- 입력이 없는 Task에는 `None`이 표시된다.
- 집중 테스트와 전체 테스트가 통과한다.

## Completion Criteria

- `python3 -m unittest tests.test_bounded_inputs` 통과
- `python3 -m unittest discover -s tests -v` 통과
- 루트 및 배포 Project check 통과
- Task audit 통과
