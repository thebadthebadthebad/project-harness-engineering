# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- `origin/main...HEAD` PR diff의 위생·범위·검증 상태를 확인한다.
- 검증을 막는 기존 Markdown EOF 공백 4건만 정리한다.
- 별도 원격 branch를 push하고 구조화된 PR을 생성한다.

범위 밖: 기능 코드 변경, history 삭제, commit squash/rewrite, `main` direct push

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
readiness → diff hygiene → check → branch push → GitHub PR
```

## Outputs

- PR readiness 검증 기록
- GitHub PR URL

## Completion Criteria

- `git diff --check origin/main...HEAD` 통과
- 47개 회귀 근거와 두 Project check 근거가 PR에 포함된다.
- `main`이 아닌 별도 branch가 push되고 `main`을 base로 하는 PR이 생성된다.
