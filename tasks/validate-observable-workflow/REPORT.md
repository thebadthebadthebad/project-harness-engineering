# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

실험 analyzer의 shell 오탐·변경 generation·acceptance를 교정하고, exact Hook bundle digest 검증 뒤에만 trust를 우회하는 runner를 구현했다. 결정적 lifecycle과 리서치+코드 두 시나리오의 Project/Task/Project 독립 세션 6개를 실제 실행해 모두 exit 0 및 hard acceptance 통과를 확인했다.

## Final Goal and Result

최종 목표를 달성했다. v2 원본을 같은 parser로 재분석한 공정 비교에서 lifecycle v3의 Markdown path 읽기는 22에서 9로, input token은 539,273에서 477,610으로 줄었고 변경 없는 반복 읽기는 제거됐다. 리서치+코드 시나리오는 공식 근거, 구현, fixture, 2개 unittest, REPORT, close까지 완결했다.

## Findings

- `rg --files -g '!TASK.md'`와 `find .. -name REPORT.md`는 문서 내용 읽기가 아니며 구조적으로 제외해야 한다.
- `bash -lc` wrapper 내부 명령을 재귀적으로 풀어야 현재 Codex JSONL의 실제 read command를 집계할 수 있다.
- 절대 읽기 명령 임계값보다 상위 탐색, Project lifecycle 경계, context 누락, 변경 없는 같은 path 재읽기가 더 안정적인 hard acceptance다.
- 명시 호출형 Skill marker는 6개 세션 모두 역할에 맞게 관찰됐고, 작은 순차 작업에서는 subagent가 호출되지 않았다.
- Hook은 Pre/Post를 각각 기록하므로 visit 집계는 `tool_use_id`로 중복 제거해야 한다.
- Hook의 단순 `.md` 정규식은 `git diff`와 glob을 방문으로 오인했다. content-read command와 실제 path argument로 범위를 좁힌 candidate를 만들었다.
- Project Agent가 `task status <name>`을 반복 오용했다. explicit Skill에 정확한 명령 형태를 넣는 것이 CLI help 재탐색보다 저비용이다.

## Work and Validation

- `python3 -m unittest discover -s scripts/tests -v`: parser, generation, trust 거부, dry-run metadata, compare, Hook path, Pre/Post dedup 7개 테스트 통과.
- lifecycle run: 3/3 session exit 0, 8개 hard acceptance 전부 PASS, 42 commands, 9 Markdown paths, 0 unchanged repeats.
- research+code run: 3/3 session exit 0, 8개 hard acceptance 전부 PASS, 64 commands, 11 Markdown paths, 0 unchanged repeats.
- 독립 재검증: 두 workspace의 `projectctl check`, status, diff check, History 확인 성공. CSV normalizer unittest 2개 통과.
- Hook metadata: lifecycle 111 events, research 173 events, malformed 0. 각 session에서 SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop 관찰.
- PreCompact, PostCompact, SubagentStart, SubagentStop은 해당 동작이 없어서 관찰되지 않았으며 coverage에 missing으로 유지된다.
- boundary-aware secret heuristic 결과 0건. Hook event에 prompt, tool input/response, full command, transcript path 필드가 없음을 확인했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| scripts/harness_experiment.py | code | 정밀 parser, Hook 검증, 관찰 추출, compare를 포함한 runner candidate |
| scripts/tests/test_harness_experiment.py | test | analyzer와 trust, Hook 교정 회귀 테스트 |
| output/scenarios | scenario | lifecycle v3와 research plus code 통제 시나리오 |
| output/results | evidence | raw 내용을 제외한 두 run summary, report, manifest와 v2 comparison |
| output/hook-observe.py | code | content-read 문서 path만 기록하는 Hook candidate |
| output/project-observability.py | code | tool use별 visit과 lifecycle 중복을 제거하는 report candidate |
| output/manage-project-workflow-SKILL.md | skill | 정확한 projectctl 형태를 포함한 explicit Skill candidate |
| docs/notes/final-analysis.md | documentation | 비교 수치, 해석, privacy 검토, 남은 위험 |

## Limitations

- 현재 실제 run의 raw Hook events는 교정 전 Hook으로 생성됐다. 교정 Hook의 실제 coverage는 Promotion 후 재확인이 필요하다.
- Codex raw JSONL은 prompt와 Agent message를 포함할 수 있어 `.harness/` 밖으로 자동 공개하지 않는다.
- Hook은 unified shell과 일부 도구를 완전히 가로채지 못하며, absence를 보안 증명으로 사용할 수 없다.
- 리서치 시나리오 token은 1,224,973으로 높다. 이는 비용 관찰값이며 hard acceptance가 아니다.
- full-access custom agent는 instruction 제한일 뿐 sandbox 보안 경계가 아니다.

## Project Follow-up

Project가 analyzer·시나리오와 세 교정 candidate를 공식 위치에 Promotion한다. Promotion 후 단위·통합 테스트와 최소 Hook fixture를 다시 실행하고, 사용자 가이드에 Hook trust, observability report, explicit Skill, session switch, raw log 주의를 설명한다.
