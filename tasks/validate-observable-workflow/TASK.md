# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- shell argument를 구조적으로 분리해 `rg -g '!TASK.md'` 같은 filter를 문서 읽기로 오인하지 않도록 분석기를 수정한다.
- 파일 변경 전후 generation을 구분해 실제 변경 사이의 재확인은 허용하고, 변경 없는 반복 읽기만 집계한다.
- 절대 문서 읽기 임계값을 hard acceptance에서 제거하고 결정적 경계·문서 반복·context 사용을 판정한다.
- Hook config와 script가 template 내부에 있고 승인된 구조·digest인지 확인한 뒤에만 실험 runner가 Hook trust를 일회 우회한다.
- 세션별 run id와 역할을 전달하고 Git-local Hook events를 결과 디렉터리로 추출해 action 분석과 함께 보존한다.
- 이전/현재 summary를 비교하는 `compare` 명령과 normalized schema coverage를 추가한다.
- 결정적 lifecycle 시나리오와 외부 리서치+간단한 코드 검증 시나리오를 실행하고 결과를 분석한다.
- 실험 runner의 세션 분리는 실제 사용자의 Project/Task 세션 전환을 모사하며 자동 agent orchestration으로 해석하지 않는다.

## Inputs


| Project Source | Task Snapshot |
| --- | --- |
| tools/harness_experiment.py | scripts/harness_experiment.py |

추가 참고 입력은 `../../experiments/scenarios/project-task-loop.json`, `../../.harness/analysis-v2-final/summary.json`, `../../project/` 공식 템플릿이다.

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
기존 analyzer 오탐 fixture와 acceptance 재정의
→ shell parser, generation, compare 구현 및 단위 테스트
→ Hook digest 검증, run metadata 전달, event 추출 구현
→ 결정적 lifecycle 시나리오 dry run과 실제 실행
→ 리서치+코드 시나리오 작성과 실제 실행
→ 이전 실험 대비 결과·coverage·한계 분석
→ REPORT와 Promotion 후보 정리
```

## Outputs

- `scripts/harness_experiment.py`: 개선된 runner/analyzer candidate
- `scripts/tests/test_harness_experiment.py`: parser, Hook 검증, compare 테스트
- `output/scenarios/`: 새·수정 시나리오 candidate
- `output/results/`: raw logs를 제외한 실험 REPORT, summary, manifest, 비교 결과
- `output/hook-observe.py`: 문서 방문 오탐을 줄인 Hook candidate
- `output/project-observability.py`: Pre/Post 관찰 중복을 제거한 보고서 candidate
- `output/manage-project-workflow-SKILL.md`: 실험에서 반복된 CLI 오용을 줄이는 Skill candidate
- `docs/notes/final-analysis.md`: 실험 결과 해석과 남은 한계

## Completion Criteria

- filter/pattern 안의 Markdown 이름은 read로 집계되지 않고 실제 read command path만 집계된다.
- 변경 없는 같은 문서 반복 읽기는 실패하고 파일 변경 후 재확인은 실패하지 않는다.
- Task 세션의 activate/baseline/audit/close는 hard failure이며 context는 각 세션에서 관찰된다.
- Hook 검증 실패 시 Codex를 시작하기 전에 runner가 실패하고 trust bypass를 전달하지 않는다.
- manifest에 config/script digest, run id, role, Hook trust mode가 기록되고 raw Hook events가 결과에 복사된다.
- 두 실제 시나리오가 종료되고 hard acceptance 및 이전 기준 대비 delta가 보고된다.
- raw JSONL·Hook events의 민감 내용 검토 결과를 명시하며 저장소에는 요약 결과만 후보로 둔다.
