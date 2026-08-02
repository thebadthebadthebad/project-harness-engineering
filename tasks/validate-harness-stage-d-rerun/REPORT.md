# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

stopped

허용값은 `completed` 또는 `stopped`다.

## Summary

Legacy 재파일럿은 통과했다. 실제 Codex 병렬 run은 token budget 차단과 read-only sandbox 실패 decision을 올바르게 처리했지만, Task `inputs`가 bounded prompt context로 전달되지 않는 계약 누락을 발견해 최종 exit 판정을 보류한다.

## Final Goal and Result

Stage D 전체 완료 조건은 아직 미충족이다. Legacy apply/migration은 0.612초, parity 100%, Project-owned byte parity, switch/full check/rollback을 통과했다. 두 실제 Codex reader는 동시에 시작됐고 각각 blocked와 needs_decision으로 독립 종료했다.

## Findings

- Token limit은 실제 usage 92,635 input tokens를 탐지해 유효한 handoff도 공식 review로 승격하지 않았다.
- 이 실행 환경의 read-only bwrap 실패는 권한 자동 확대 없이 Task-local decision으로 전환됐다.
- Task JSON에는 inputs 필드가 있지만 v2 create CLI가 항상 빈 값으로 만들고 adapter가 실제 source 내용을 bounded context로 주입하지 않아, shell sandbox 장애 시 제공된 입력으로 작업할 수 없었다.
- 새 Task에서 더 높은 budget을 사전 계약하되 sandbox 권한은 확대하지 않고 explicit input context를 제공하는 것이 안전한 수정이다.

## Work and Validation

실제 legacy clone과 신규 Project를 임시 독립 저장소에서 운영했다. 두 실제 Codex run은 같은 시각에 시작되어 queue 병렬성·상태 격리를 확인했다. Source 원본 저장소는 clean을 유지했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| output/.gitkeep | placeholder | 임시 파일럿의 근거는 REPORT에 요약하고 적용 Project는 등록하지 않음 |

## Limitations

실제 Codex 입력 토큰은 작은 source review에도 repository instructions 때문에 35k–92k였다. 파일럿 budget 50k는 한 Task에 부족했다. Sandbox 기능 probe는 help flag만으로 runtime bwrap 가능성을 증명하지 못한다.

## Project Follow-up

`--input` 계약과 bounded source context를 별도 repair Task로 구현·검증한다. Pending decision을 자동 resolve하지 않고 새 사전 승인 계약의 Task로 Stage D를 다시 실행한다.
