# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- 최종 공용 `project/` 템플릿으로 실제 Codex Project 세션 하나를 실행한다.
- 교정 Hook이 실제 content read와 non-read Markdown path를 구분하고 metadata-only event를 남기는지 검증한다.
- 전체 구조 검사, 테스트, Skill validation과 기존 두 통제 실험을 함께 최종 분석한다.

## Inputs

- 공식 `project/` 템플릿
- `tools/harness_experiment.py`
- `experiments/RESULTS.md`와 커밋된 세 결과 summary
- 현재 전체 test suite와 Skills

## Data

별도 Project 데이터는 없다. raw 실행 로그는 `.harness/`에만 보관한다.

## Workflow

```text
최소 actual Hook scenario 작성
→ 독립 Codex session 실행
→ acceptance와 Hook event 직접 분석
→ 전체 회귀·구조·Skill 재검증
→ content-free 결과와 최종 분석 작성
→ REPORT handoff
```

## Outputs

- `output/scenarios/hook-observability-smoke.json`: 최소 actual Hook 시나리오
- `output/results/hook-observability-smoke/`: raw 내용을 제외한 manifest, summary, report
- `docs/notes/final-analysis.md`: 전체 구현·실험·한계의 최종 분석

## Completion Criteria

- actual Codex session이 exit 0이고 hard acceptance를 통과한다.
- 교정 Hook에서 `README.md` content read는 한 번 집계되고 `git diff -- README.md`는 document visit으로 집계되지 않는다.
- Hook event에 prompt, tool input/response, 전체 command, transcript path가 없다.
- root와 public 구조 검사, 전체 unittest, 두 Skill validation이 통과한다.
- raw 로그는 ignored `.harness/` 밖으로 Promotion하지 않고 content-free evidence만 handoff한다.
