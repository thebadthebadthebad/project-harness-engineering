# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- v2 canonical Project의 goal, scope, current objective 개정
- v2 canonical Task의 목적, 범위, 산출물, 완료 조건, 의존성, 소유 경로, validation, context reference와 실행 계약 개정
- CLI flag 또는 사람이 편집한 제한된 Markdown proposal에서 변경안을 읽는 preview/apply 흐름
- expected revision, 상태별 변경 제한, 변경 이유와 승인 근거 기록
- 기존 Decision, Promotion, Result 책임과의 경계 정리
- 공용 Project 문서, human View와 회귀 테스트 갱신

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
현재 canonical schema와 mutation 경계 분석
→ 최소 amendment 계약과 상태별 허용 규칙 설계
→ Project/Task preview·apply 및 Markdown proposal import 구현
→ stale revision·승인 근거·검증과 human View 구현
→ 문서·회귀·bundle smoke 검증
→ Task audit와 handoff
```

## Outputs

- Project와 Task의 공식 amendment CLI
- 직접 편집 proposal을 canonical authority로 검토·반영하는 preview/apply 절차
- revision CAS, 변경 이유·승인 근거와 상태별 안전 규칙
- 갱신된 공용 문서와 회귀 테스트

## Completion Criteria

- 생성 후 Project goal, scope와 current objective를 JSON 직접 편집 없이 공식 개정할 수 있다.
- 생성 후 Task 계약을 허용된 lifecycle 상태에서 공식 개정할 수 있다.
- 사람이 편집한 Project/Task Markdown proposal을 preview하고 명시적 apply로 반영할 수 있다.
- apply는 expected revision과 변경 이유를 요구하며 stale writer와 무변경 적용을 거부한다.
- agent가 반영할 때 사용자 승인 근거를 기록할 수 있고 사용자 직접 적용과 구분된다.
- 기존 Decision·Promotion 책임과 중복되지 않고 전체 회귀와 Project check가 통과한다.
