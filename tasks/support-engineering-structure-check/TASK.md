# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- `projectctl check`가 일반 공용 Project와 이 Harness Engineering Project의 서로 다른 필수 디렉터리를 구분하도록 수정안을 설계한다.
- Engineering 검사 시 내장 `project/` 공용 템플릿 무결성도 함께 검사한다.
- 기존 공용 Project 검사를 완화하지 않는 회귀 테스트를 작성한다.

## Inputs

- `project/tools/project_harness/lifecycle.py`
- `project/tools/project_harness/repository.py`
- `tests/test_workflow_core.py`
- 루트와 `project/`의 실제 디렉터리 구조

## Data

별도 데이터 입력은 없다.

## Workflow

```text
두 Project 구조의 안정적인 식별 조건 정의
→ 필수 디렉터리와 nested template 검사 설계
→ candidate patch와 회귀 테스트 작성
→ Task-local 검증
→ REPORT handoff 작성
```

## Outputs

- `output/design.md`: 구조 식별 규칙, 실패 메시지와 변경 candidate
- `scripts/test_engineering_structure_check.py`: 수정 전 실패와 수정 후 기대 동작을 나타내는 회귀 테스트 candidate

## Completion Criteria

- Engineering 루트는 책임 없는 빈 `src/`, `data/` 없이 검사 가능하다.
- Engineering 루트 검사에서 내장 공용 `project/` 결함을 놓치지 않는다.
- 일반 공용 Project는 계속 `src/`, `data/`를 요구한다.
- 구조 식별은 명시적이고 재사용 가능한 작은 함수로 표현된다.
- candidate 테스트와 기존 테스트의 적용 후 검증 방법이 REPORT에 명시된다.
