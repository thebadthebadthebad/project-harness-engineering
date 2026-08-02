# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- 실제 legacy Project clone에서 최종 bundle apply, preserve, parity, switch/check/rollback을 검증한다.
- 신규 Project와 실제 Python source 두 파일에 bounded `--input` review Task를 만든다.
- 실제 Codex 두 Task를 read-only, network/web disabled, approval never 계약으로 병렬 실행한다.
- typed handoff, validation, worktree/상태 격리, result index와 parent review 경계를 확인한다.
- 운영 지표와 Stage A–D exit, Stage E 필요성 근거를 기록한다.

범위 밖: 원본 저장소 변경, 외부 배포, Stage E 구현

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
final package → legacy pilot → new real-code Project → two bounded-input Codex Tasks → queue/handoff/result → metrics/exit
```

## Outputs

- output/pilot-report.md, pilot-metrics.json, validation.md와 REPORT

## Completion Criteria

- Legacy preserve/parity/switch/check/rollback 통과
- 두 실제 Codex Task가 같은 worker window에서 실행되고 review handoff·validation 통과
- Source 원본과 공식 Project가 변경되지 않음
- Result index와 human Views 검토 가능
- 전체 46개 이상 회귀와 check/audit 통과
- 전체 프로젝트 요구사항 완료 및 Stage E 보류/진입 판정
