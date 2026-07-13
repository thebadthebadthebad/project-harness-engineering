# Harness Experiments

이 디렉터리는 공용 `project/` 템플릿의 Project/Task 세션 전환을 통제된 Codex 실행으로 검증한다. 실험 도구는 공용 Project 템플릿에 포함되지 않는다.

## Dry Run

```bash
python3 tools/harness_experiment.py run \
  --template project \
  --scenario experiments/scenarios/project-task-loop.json \
  --output .harness/runs/project-task-loop-dry \
  --dry-run
```

Dry run은 workspace와 실행 manifest만 만들고 Codex 또는 시나리오의 준비 명령을 실행하지 않는다. Acceptance도 평가하지 않는다.

## Controlled Run

```bash
python3 tools/harness_experiment.py run \
  --template project \
  --scenario experiments/scenarios/project-task-loop.json \
  --output .harness/runs/project-task-loop
```

각 세션은 독립된 `codex exec --json` 호출이며 full-access와 approval 없음 옵션을 명시적으로 사용한다. `before`는 Agent 세션 사이에서 사용자 확인 뒤 수행했을 결정적 lifecycle 명령을 argv 배열로 표현한다.

결과는 다음 위치에 생성된다.

- `manifest.json`: 템플릿 commit, Codex 버전, 실행 옵션, 세션 종료 상태
- `sessions/*.jsonl`: 원본 Codex 이벤트
- `sessions/*.stderr`: 세션 표준 오류
- `sessions/*.last.md`: 마지막 Agent 메시지
- `actions/*.jsonl`: 명령, Markdown 확인, 상위 경로 탐색, 파일 변경의 정규화 로그
- `summary.json`: 세션별 집계와 acceptance
- `REPORT.md`: 사람이 검토하는 결과 요약

원본 JSONL에는 프롬프트와 Agent 출력이 포함될 수 있다. `.harness/`는 Git에서 제외하며 외부 공유 전에 원본 내용을 직접 확인한다.

## Existing Logs

```bash
python3 tools/harness_experiment.py analyze \
  path/to/project-session.jsonl \
  path/to/task-session.jsonl \
  --output .harness/analysis
```

분석기는 JSONL에 노출된 액션만 관찰한다. Codex가 내부적으로 주입한 AGENTS 내용이나 하나의 shell 프로그램 내부에서 발생한 간접 파일 접근까지 완전하게 증명하는 보안 감사 도구는 아니다.

## Scenario Contract

- `name`: 실험 이름
- `sessions[].name`: lowercase kebab-case 세션 이름
- `sessions[].cwd`: 실험 workspace 내부 상대 경로
- `sessions[].prompt`: Agent에게 전달할 전체 프롬프트
- `sessions[].before`: 선택적인 결정적 준비 명령의 argv 배열 목록
- `sessions[].resume`: 선택적으로 이어갈 이전 세션 이름
- `sessions[].continue_on_error`: 실패 후 다음 세션 진행 여부
