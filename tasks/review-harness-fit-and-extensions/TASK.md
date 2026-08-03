# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- 현재 `main`의 하네스를 사용자의 공용 Project 운영 의도와 비교한다.
- 두 읽기 전용 subagent의 의도 적합성·운영 위험 review를 독립적으로 판단한다.
- 코드 작성, 문서 작성, 연구 검색·취합의 편의와 품질을 높일 공통 기능을 외부 공식 자료로 조사한다.
- 현재 하네스에의 적합성, 비용, 위험과 도입 순서를 종합 보고서로 정리한다.

범위 밖: 추가 기능 구현, Stage E 구현, 적용 Project 변경

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
user intent baseline → parallel independent reviews + external research → evidence grading → adoption recommendations
```

## Outputs

- `output/final-assessment.md`
- `output/subagent-review-synthesis.md`
- `output/external-feature-research.md`

## Completion Criteria

- 사용자 의도와 현재 구현의 적합성·누락이 근거와 함께 판정된다.
- 운영 위험은 심각도, 발생 조건, 완화책과 파읿 관찰 항목으로 정리된다.
- 부가 기능은 실제 사용자 요구, 공통성, 도입 비용과 검증 방법으로 평가된다.
- 즉시 도입, 파읿 검증, 보류 대상이 구분된다.
