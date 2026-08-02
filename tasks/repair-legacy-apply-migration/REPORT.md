# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

실제 Stage D failure를 재현해 installation-only gate와 구버전 STATE/History normalization을 구현하고 검증했다.

## Final Goal and Result

구버전 Project에 새 migration 도구를 먼저 설치한 뒤 3열 이상 STATE와 promoted History를 lossless candidate로 변환하고 semantic parity 100%, authority switch, v2 full check와 rollback을 통과했다.

## Findings

- 설치 도구 무결성과 legacy 의미 유효성은 authority switch 전에 별도 gate여야 한다.
- STATE 첫 두 열은 Task/Status이고 추가 열은 legacy semantic payload로 보존할 수 있다.
- v2 authority에서는 보존된 legacy STATE/History naming을 canonical validation 대상으로 다시 검사하면 안 된다.

## Work and Validation

실제 clone과 최소 고정 fixture에서 apply, preserve hash, plan/apply/verify/switch/check/rollback을 검증했다. Focused 1건과 기존 43건 회귀가 통과했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| scripts/harnessctl.py | code | Legacy authority apply/update의 installation-only check |
| scripts/project_harness/lifecycle.py | code | Installation gate와 authority-aware full check |
| scripts/project_harness/cli.py | code | check --installation-only |
| scripts/project_harness/v2.py | code | Multi-column legacy STATE lossless normalization |
| scripts/tests/test_legacy_compatibility.py | test | Actual failure variant regression |
| output/validation.md | evidence | 검증 요약 |

## Limitations

지원되지 않는 임의 legacy schema를 추측 변환하지 않는다. Legacy 제거는 여전히 파일럿·보존 기간·복구 검증 뒤의 별도 조건이다.

## Project Follow-up

공식 도구와 회귀에 Promotion한 뒤 Stage D 파일럿을 새 Task로 처음부터 재실행한다.
