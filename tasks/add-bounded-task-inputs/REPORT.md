# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

V2 Task `--input` 파일 계약, bounded UTF-8 prompt context와 digest drift gate를 구현·검증했다.

## Final Goal and Result

Task가 명시한 Project-relative source만 파일당 128 KiB·총 256 KiB 안에서 digest와 함께 Codex prompt에 전달된다. Start 후 변경, traversal, binary와 초과 입력은 실행 전에 차단된다.

## Findings

- Shell sandbox가 동작하지 않아도 명시된 input content로 bounded review를 수행할 수 있다.
- Input content는 prompt에만, path/digest/bytes는 canonical Task와 Git-local run evidence에 남겨 provenance와 민감정보 표면을 분리한다.

## Work and Validation

Focused 2건과 기존 44건 회귀, Project check와 Task audit을 통과했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| scripts/project_harness/v2.py | code | Input path/digest/size 계약과 생성 시 제한 |
| scripts/project_harness/adapter.py | code | Bounded loader, drift gate, prompt/evidence 주입 |
| scripts/project_harness/cli.py | code | task create --input |
| scripts/tests/test_bounded_inputs.py | test | Content/provenance와 rejection regression |
| output/validation.md | evidence | 검증 요약 |

## Limitations

Directory, binary와 256 KiB 초과 context는 지원하지 않는다. 더 큰 입력은 result summary나 별도 retrieval 설계가 필요하다.

## Project Follow-up

공식 template과 회귀에 Promotion한 뒤 새 Stage D Task에서 read-only 실제 Codex 파일럿을 재실행한다.
