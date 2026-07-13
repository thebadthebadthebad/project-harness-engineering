# Harness Experiments

이 디렉터리는 공용 `project/` 템플릿의 Project/Task 세션 전환을 독립 Codex 실행으로 재현하고 분석한다. 실험 runner는 Engineering 전용이며 공용 Project 템플릿에 포함되지 않는다.

## Scenarios

- `scenarios/project-task-loop.json`: 작은 결정적 산출물로 lifecycle과 handoff를 검증한다.
- `scenarios/research-code-loop.json`: 공식 자료 조사, 코드, fixture, unittest, REPORT를 포함한 대표 작업을 검증한다.
- `scenarios/hook-observability-smoke.json`: content read와 같은 Markdown 경로의 non-read diff를 실제 Hook에서 구분한다.

각 시나리오는 Project setup → Task work → Project close의 서로 독립된 세션 세 개로 구성된다. runner의 자동 세션 연결은 사람이 같은 경계에서 전환하는 정상 운영을 재현하기 위한 실험 장치이지 공용 자동 오케스트레이션 기능이 아니다.

## Dry Run

```bash
python3 tools/harness_experiment.py run \
  --template project \
  --scenario experiments/scenarios/project-task-loop.json \
  --output .harness/runs/project-task-loop-dry \
  --dry-run
```

Dry run은 workspace와 manifest만 만들고 Codex 또는 시나리오의 준비 명령을 실행하지 않는다. Acceptance도 평가하지 않는다.

## Controlled Run

```bash
python3 tools/harness_experiment.py run \
  --template project \
  --scenario experiments/scenarios/project-task-loop.json \
  --output .harness/runs/project-task-loop-v3

python3 tools/harness_experiment.py run \
  --template project \
  --scenario experiments/scenarios/research-code-loop.json \
  --output .harness/runs/research-code-loop
```

각 세션은 독립된 `codex exec --json` 호출이며 full-access, network 허용, approval 없음 옵션을 사용한다. `before`는 Agent 세션 사이에서 사람이 수행했을 결정적 lifecycle 명령을 argv 배열로 표현한다.

runner는 `.codex/hooks.json`의 exact event set, command, timeout과 template 내부 Hook script를 확인하고 config·script SHA-256을 manifest에 남긴 뒤에만 실험 프로세스의 Hook trust를 우회한다. 검증이 실패하면 Codex를 시작하지 않는다. 일반 interactive session은 이 우회를 사용하지 않는다.

결과는 다음 위치에 생성된다.

- `manifest.json`: 템플릿 commit, Codex 버전, 실행 옵션, 세션 종료 상태
- `sessions/*.jsonl`: 원본 Codex 이벤트
- `sessions/*.stderr`: 세션 표준 오류
- `sessions/*.last.md`: 마지막 Agent 메시지
- `actions/*.jsonl`: 명령, Markdown 확인, 상위 경로 탐색, 파일 변경의 정규화 로그
- `observability/<session>/events.jsonl`: 실험 workspace의 Git-local Hook event 복사본
- `summary.json`: 세션별 집계와 acceptance
- `REPORT.md`: 사람이 검토하는 결과 요약

원본 Codex JSONL에는 프롬프트와 Agent 출력이 포함될 수 있다. `.harness/`는 Git에서 제외하며 외부 공유 전에 원본 내용을 직접 확인한다. 커밋된 `experiments/results/`에는 content-free summary와 comparison만 둔다.

## Existing Logs

```bash
python3 tools/harness_experiment.py analyze \
  path/to/project-session.jsonl \
  path/to/task-session.jsonl \
  --output .harness/analysis
```

두 summary를 같은 metric으로 비교한다.

```bash
python3 tools/harness_experiment.py compare \
  .harness/analysis-before/summary.json \
  .harness/analysis-after/summary.json \
  --output .harness/comparison
```

분석기는 JSONL에 노출된 액션만 관찰한다. AGENTS의 내부 주입, unified shell 내부의 간접 접근, 모든 Hook interception을 완전히 증명하는 보안 감사 도구는 아니다.

## Acceptance

현재 hard acceptance는 다음 결정적 경계를 검사한다.

- 각 독립 세션의 context 호출
- 상위 경로 탐색 없음
- Agent의 `projectctl` source 읽기 없음
- Task 세션의 Project lifecycle 명령 없음
- 변경 없는 같은 Markdown path 반복 읽기 없음
- malformed Codex·observability JSONL 없음
- SessionStart, UserPromptSubmit, Stop Hook event 관찰

실패 후 복구된 command 수와 token 사용량은 관찰 metric이며 hard gate가 아니다. 리서치 결과 품질과 Promotion 가치는 사람이 별도로 판단한다.

실제 결과와 해석은 `RESULTS.md`, 공유 가능한 수치는 `results/`에서 확인한다.

## Scenario Contract

- `name`: 실험 이름
- `sessions[].name`: lowercase kebab-case 세션 이름
- `sessions[].role`: `project` 또는 `task`
- `sessions[].cwd`: 실험 workspace 내부 상대 경로
- `sessions[].prompt`: Agent에게 전달할 전체 프롬프트
- `sessions[].before`: 선택적인 결정적 준비 명령의 argv 배열 목록
- `sessions[].resume`: 선택적으로 이어갈 이전 세션 이름
- `sessions[].continue_on_error`: 실패 후 다음 세션 진행 여부
