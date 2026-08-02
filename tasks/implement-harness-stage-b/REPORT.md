# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

Codex non-interactive adapter, 구조화 실행 계약, Task-local decision request/resolve, 최소 result index와 stable context reference 후보를 구현하고 fault 검증했다.

## Final Goal and Result

Task context를 별도 worktree에서 `codex exec`로 실행하고 JSONL·output-schema 결과를 typed handoff로 회수하는 Stage B 흐름이 동작한다. Model/reasoning/sandbox/approval/web·network/tool·MCP·skill/time·token/fallback 계약은 요청값과 실제 적용값을 구분해 run evidence에 남는다.

## Findings

- 로컬 Codex 0.146.0은 Stage B가 요구하는 `--json`, `--output-schema`, `-o`, `-C`, `--sandbox`, `--model`, `-c`를 지원한다.
- reasoning effort는 공식 지원 집합을 capability로 사용하고 unsupported 요청은 명시된 fallback으로만 낮춰 실제 CLI config에 전달해야 한다.
- permission·external effect·scope expansion은 non-interactive Task가 자율 승인하지 않고 Task-local decision으로 승격할 수 있다.
- result graph 없이도 stable `kind:id` ref, verification status, supersedes, reusable 표시와 짧은 index로 후속 context 재사용이 가능하다.
- sandbox/approval/web/network와 발견된 Project skill·MCP는 config로 제어할 수 있으나 모든 shell 하위 도구와 외부/global skill의 세밀한 allowlist는 prompt contract를 보조 수단으로 사용한다. 이를 강한 보안 경계로 주장하지 않는다.

## Work and Validation

adapter core, v2 decision/result 상태, CLI와 4개 acceptance test를 구현했다. Fake Codex로 success, decision, permission, timeout, token overrun, malformed output을 재현했으며 기존 회귀 34건과 Task audit이 통과했다. 공식 근거와 검증은 `docs/research/codex-adapter-sources.md`, `output/validation.md`에 기록했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| scripts/project_harness/adapter.py | code | Capability probe, contract normalization, Codex argv/context/run evidence와 outcome import |
| scripts/project_harness/v2.py | code | Execution-bearing Task, decision request/resolve, result index와 human View |
| scripts/project_harness/cli.py | code | task run, doctor codex, decision과 result public CLI |
| scripts/tests/test_stage_b.py | test | Adapter/decision/result E2E와 fault suite |
| docs/research/codex-adapter-sources.md | evidence | Codex 공식 동작과 제어 한계 |
| output/validation.md | evidence | 실행 검증 결과 |

## Limitations

실제 모델 호출은 외부 비용과 비결정성을 피하기 위해 이번 acceptance에서 수행하지 않고 로컬 capability probe와 fake CLI 계약 테스트로 분리했다. Token limit은 완료 event의 usage로 판정하므로 turn 중간 선제 중단은 Stage C streaming worker에서 보완한다. Resume, queue와 병렬 worker는 Stage C 범위다.

## Project Follow-up

후보를 public template과 tests에 Promotion하고 전체 회귀를 재실행한다. 다음 Engineering Task에서 simple SQLite queue, background worker, parallel limits와 interrupted 복구를 구현한다.
