# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

공용 Project의 디렉터리 계약을 완화하지 않으면서 Harness Engineering root의 고유 책임을 식별하고, 내장 `project/` 템플릿까지 재귀 검사하는 최소 설계를 작성했다. 적용 전 정확히 실패하는 세 개의 회귀 test candidate로 기대 동작을 고정했다.

## Final Goal and Result

최종 목표에 필요한 구현 handoff를 완성했다. Engineering marker를 재사용 가능한 작은 함수로 분리하고, root 필수 디렉터리 선택과 nested template 검사에 같은 결과를 사용한다. class hierarchy나 범용 schema 계층 없이 기존 `check_project()`를 유지하는 단순 변경이다.

## Findings

- 현재 실패는 Engineering root에 `missing src/`, `missing data/`를 잘못 반환하는 구조 분류 부재다.
- 빈 `src/`, `data/`를 추가하면 검사만 통과하고 디렉터리 책임은 모호해진다.
- `tools/create_project.py`와 `tools/harness_experiment.py`는 공용 템플릿에 없는 Engineering 전용 marker다.
- Engineering 검사가 root만 통과하고 내장 공용 템플릿 손상을 놓치지 않도록 동일 검사기를 한 번 재귀 호출해야 한다.
- 일반 공용 Project의 `src/` 제거 test는 현재도 통과해 기존 계약을 guard한다.

## Work and Validation

- `python3 -m py_compile scripts/test_engineering_structure_check.py`: 통과.
- 적용 전 candidate test 결과: 3개 중 공용 guard 1개 통과, Engineering 기대 동작 2개 예상 실패.
- 첫 fixture는 실제 STATE의 완료 Task를 복사해 불필요한 missing Task 오류가 발생했다. STATE를 빈 Current Tasks fixture로 교정한 뒤 실패 원인을 `missing src/`, `missing data/`로 고립했다.
- Promotion 후 같은 3개 test와 기존 26개 test, root/public `projectctl check`를 모두 실행해야 한다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| output/design.md | design | marker, 필수 구조, nested 검사와 실패 동작의 최소 변경 설계 |
| scripts/test_engineering_structure_check.py | test | Engineering root, nested public 오류, 일반 public guard 회귀 candidate |

## Limitations

- candidate는 red regression을 고정한 handoff이며 공식 `lifecycle.py`에 아직 적용되지 않았다.
- 현재 두 Engineering test의 실패는 결함 재현이므로 Promotion 후 green 결과가 필요하다.

## Project Follow-up

Project가 `managed_public_template()`과 conditional directory/nested 검사를 `lifecycle.py`에 적용하고 candidate test를 공식 suite에 반영한다. 두 root 검사와 전체 회귀 테스트를 통과한 뒤 Promotion을 기록한다.
