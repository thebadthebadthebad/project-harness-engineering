# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

Task human View에 bounded input의 경로, byte 크기와 SHA-256 digest를 표시하는 최소 보정을 완료했다.

## Final Goal and Result

사용자가 JSON authority를 직접 열지 않고도 Task에 고정된 입력을 `task show`에서 검토할 수 있다. 입력이 없는 Task도 `None`으로 명시된다.

## Findings

- Canonical Task record과 Codex prompt/run evidence의 input 구조는 변경하지 않았다.
- 기존 `content_digest`를 유지하면서 경로·크기·digest만 보여 주므로 input content를 View에 복제하지 않는다.

## Work and Validation

Task 산출물로 코드와 테스트 후보를 격리한 뒤 overlay에서 집중 3건과 전체 47건 회귀를 통과했다. Engineering root와 배포 Project check, Task audit도 통과했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| `scripts/project_harness/v2.py` | Code candidate | Task input human View 렌더링 |
| `scripts/tests/test_bounded_inputs.py` | Test candidate | Input/빈 input View 회귀 |
| `output/validation.md` | Evidence | 집중·전체 회귀와 check 결과 |

## Limitations

View는 input content 자체를 표시하지 않으며 내용 검토는 원본 경로를 통해 수행해야 한다.

## Project Follow-up

후보 두 파일을 공식 `project/` 템플릿과 root test에 반영하고 동일 회귀를 재확인한다.
