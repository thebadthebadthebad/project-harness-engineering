# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- 검토 종합 판정의 지적과 부가기능 후보를 책임 중복, workflow 영향과 context noise 기준으로 재평가한다.
- v2 canonical check, 파일 경로 containment, Promotion freshness·review, 동시 canonical write와 실행 계약 표현을 우선 개선한다.
- Task·handoff·Decision·Promotion·Result의 human View와 검증·재사용 흐름을 개선한다.
- `project/`의 규칙·가이드·구조·template·skill을 사람과 Agent 관점에서 검토하고 필요한 문서를 개선한다.
- Harness Engineering 저장소의 목적·구조·개발·배포·검증 흐름을 설명하는 root `README.md`를 작성한다.

범위 밖: 중앙 Project registry, lease·heartbeat·PID adoption, orphan 자동 복구, 범용 evidence graph, 외부 provider·binary의 필수 설치

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
feature responsibility review → core safety fixes → human workflow views → template/document review → regression and bundle verification
```

## Outputs

- 안정성·사용성 코드와 회귀 테스트
- 개선된 공용 Project template 문서와 필요한 scoped skill
- Harness Engineering root `README.md`
- `output/feature-selection.md`
- `output/document-review.md`

## Completion Criteria

- 검토 지적 중 채택·통합·보류 기능과 그 이유가 중복·workflow 영향·noise 기준으로 기록된다.
- canonical 상태 손상, symlink escape, Promotion base drift와 동시 write에 대한 결정론적 검증이 존재한다.
- 사람이 원본 JSON 없이 Task·handoff·Decision·Promotion·Result와 effective Codex 계약을 검토할 수 있다.
- 공용 template 문서가 new/apply/update, Task, queue, Decision, Promotion, Result, migration과 복구 경계를 일관되게 설명한다.
- root `README.md`가 본 저장소의 목적, 구조, 개발·배포·검증과 적용 Project와의 경계를 설명한다.
- 전체 test suite, Task validation, audit와 bundle verification이 통과한다.
