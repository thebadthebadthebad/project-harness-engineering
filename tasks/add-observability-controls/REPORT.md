# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

Project/Task context, Skill marker, Codex Hook 이벤트를 하나의 Git-local run 로그로 합치고 Markdown·JSON 보고서로 집계하는 candidate를 구현했다. Hook은 내용 없는 metadata만 기록하며 항상 fail-open이다. 명시 호출형 Project/Task Skill과 동시성 3·깊이 1의 읽기 전용 custom agent 설정도 함께 검증했다.

## Final Goal and Result

최종 목표를 달성했다. 사용자는 `observe list|report`로 문서 방문, Skill, Hook, compaction, subagent, lifecycle 분류와 event coverage를 확인할 수 있다. 설정은 full-access·network 허용 환경을 바꾸지 않으며 Hook이나 Skill이 lifecycle 판단을 대신하지 않는다.

## Findings

- Codex Hook은 저장소 `.codex/hooks.json`과 `.codex/hooks/observe.py`로 관리하는 것이 현재 공식 구조와 일치한다.
- Hook trust는 script hash 단위이므로 일반 사용자는 `/hooks`에서 직접 검토해야 하고, 통제 실험만 검증된 digest에 대해 일회 우회할 수 있다.
- Hook이 모든 unified shell 실행을 가로채지는 않으므로 보고서는 누락 이벤트를 coverage로 명시해야 한다.
- 원본 transcript는 형식이 안정적이지 않고 프롬프트를 포함하므로 읽지 않는 편이 현재 관찰 목적에 맞다.
- bubblewrap가 없는 full-access 환경에서 custom agent `sandbox_mode`를 선언하면 실행 호환성이 떨어진다. 따라서 파일 비수정 지시만 제공하며 보안 경계라고 주장하지 않는다.
- Skill은 `allow_implicit_invocation: false`로 두어 사용자가 세션에서 직접 호출하는 운영 모델을 보존한다.

## Work and Validation

- `python3 -m unittest discover -s scripts/tests -v`: 4개 테스트 통과.
- context, UserPromptSubmit, PreToolUse, Skill marker를 같은 run에 기록하고 `observe report --latest`가 REPORT와 summary를 생성하는지 확인했다.
- 프롬프트와 shell에 삽입한 비밀 문자열, `tool_input`, 전체 command가 event JSONL에 없는지 확인했다.
- 손상 JSON 입력에서도 Hook exit 0·무출력, Hook event 누락 시 `projectctl check` 실패를 확인했다.
- 공식 `quick_validate.py`로 `manage-project-workflow`, `run-task-workflow` 두 Skill 검증 통과. validator용 PyYAML은 저장소 밖 `/tmp` 가상환경에만 설치했다.
- Hook JSON 파싱 및 Python compileall 성공.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| scripts/project_harness/observability.py | code | run 목록, 집계, Markdown·JSON 보고서 candidate |
| scripts/project_harness/cli.py | code | observe list and report CLI candidate |
| scripts/project_harness/lifecycle.py | code | Hook·Skill·agent 설정 무결성 검사 candidate |
| output/public-config | config | Project Hook, config, agents, Skill, AGENTS, gitignore candidate |
| output/task-config | config | Task Skill과 AGENTS candidate |
| scripts/tests/test_observability_controls.py | test | privacy, fail-open, report, config 손상 통합 테스트 |
| docs/notes/observability.md | documentation | event schema, 제외 내용, 저장과 사람 경계 |

## Limitations

- Hook이 지원하지 않는 unified shell·WebSearch 호출은 누락될 수 있으며 coverage가 이를 표시한다.
- custom agent는 instructions-only 읽기 제한이라 악의적 또는 잘못된 실행을 시스템 sandbox처럼 막지 못한다.
- Skill forward test와 실제 Hook event coverage는 공식 템플릿 Promotion 이후 독립 Codex 실험에서 추가 확인해야 한다.

## Project Follow-up

Project가 관찰 모듈·CLI·구조 검사와 공용 config를 공식 템플릿에 Promotion한다. 이후 실험 runner가 Hook script/config digest를 확인한 경우에만 `--dangerously-bypass-hook-trust`를 전달하도록 개선하고, 결정적·리서치+코드 시나리오에서 coverage와 문서 재방문을 비교한다.
