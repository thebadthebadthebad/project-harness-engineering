# Project/Task 하네스 운영 가이드

## 공용 하네스 설치와 업데이트

Harness Engineering 저장소에서 versioned bundle을 만든 뒤 대상 Project에 적용한다. 대상 Project는 중앙 registry에 등록되지 않는다.

```bash
python3 tools/harnessctl.py package --template project --version 2.0.0-a1 --output /tmp/harness-2.0.0-a1
python3 tools/harnessctl.py new ../my-project --source /tmp/harness-2.0.0-a1 \
  --project-id my-project --goal "Project goal" --scope "Initial scope"
python3 tools/harnessctl.py apply ../existing-project --source /tmp/harness-2.0.0-a1
python3 tools/harnessctl.py apply ../existing-project --source /tmp/harness-2.0.0-a1 --apply
python3 tools/harnessctl.py update ../existing-project --source /tmp/harness-2.0.0-a1
python3 tools/harnessctl.py update ../existing-project --source /tmp/harness-2.0.0-a1 --apply
```

`apply`와 `update`는 기본적으로 dry-run이다. update는 설치 당시 checksum과 현재 파일, 새 bundle을 비교하며 양쪽이 바뀐 managed 파일에서는 중단한다. 반영 뒤 `projectctl check`가 실패하면 건드린 파일과 install metadata를 복구한다. Project의 제품 코드·데이터·README와 기존 AGENTS 통합 내용은 덮어쓰지 않는다.

## Legacy 상태를 v2로 전환

기존 Project는 legacy와 v2를 동시에 쓰지 않고 다음 명시적 단계로 전환한다.

```bash
python3 tools/projectctl.py migrate inspect
python3 tools/projectctl.py migrate plan
python3 tools/projectctl.py migrate apply legacy-to-v2
python3 tools/projectctl.py migrate verify legacy-to-v2
python3 tools/projectctl.py migrate switch legacy-to-v2 --harness-version 2.0.0-a1
python3 tools/projectctl.py show project
```

`apply`는 side-by-side candidate만 만들고, `verify`의 normalized semantic parity가 100%일 때만 `switch`가 가능하다. v2 mutation 전에는 `migrate rollback legacy-to-v2`로 authority를 되돌릴 수 있다. 기존 문서는 파일럿·보존 기간·복구 훈련이 끝날 때까지 삭제하지 않는다.

## 수동 v2 Task와 Promotion

```bash
python3 tools/projectctl.py task create build-one --goal "Build one" \
  --scope "One bounded change" --output src/result.py --acceptance "Tests pass" \
  --owned-path task-output --owned-path handoff.json \
  --validation-command "python3 -m unittest"
git add .harness && git commit -m "task: create build-one"
python3 tools/projectctl.py task start build-one
```

출력된 worktree에서 작업한 뒤 `handoff.json`에 `status`, `summary`, `findings`, `limitations`, 그리고 `id/source/target/rationale` 후보 목록을 작성한다. Project root에서 다음을 실행한다.

```bash
python3 tools/projectctl.py task submit build-one --handoff handoff.json
python3 tools/projectctl.py task review build-one
git add .harness && git commit -m "task: review build-one"
python3 tools/projectctl.py promotion prepare --task build-one --candidate <candidate-id>
python3 tools/projectctl.py promotion show <promotion-id>
python3 tools/projectctl.py promotion approve <promotion-id> --actor <user-id>
python3 tools/projectctl.py promotion apply <promotion-id>
```

`approve`는 표시된 exact diff와 validation evidence에만 유효하다. 승인 후 diff가 바뀌거나 official worktree가 dirty이면 `apply`가 중단된다.

## Codex adapter 실행

먼저 현재 CLI capability를 확인한다.

```bash
python3 tools/projectctl.py doctor codex
```

Codex Task 생성 시 실행 계약을 함께 기록한다.

```bash
python3 tools/projectctl.py task create agent-one --goal "Implement one change" \
  --scope "Only the named module" --output src/change.py --acceptance "Tests pass" \
  --owned-path task-output --validation-command "python3 -m unittest" --codex \
  --model gpt-5.6 --reasoning-effort high --reasoning-fallback medium \
  --sandbox workspace-write --approval-policy never --web-mode disabled \
  --no-network-access --allowed-tool shell --allowed-tool apply_patch \
  --time-limit 3600 --token-limit 200000 --agent-role implementation
git add .harness && git commit -m "task: create agent-one"
python3 tools/projectctl.py task start agent-one
python3 tools/projectctl.py task run agent-one
```

Reasoning fallback은 adapter가 지원값을 고른 뒤 실제 `-c model_reasoning_effort=...`로 전달한다. 요청값, 적용값, fallback, argv, thread id, JSONL events와 usage는 Git-local run evidence에 기록된다. Sandbox·approval·web·network와 발견된 Project skill·MCP 설정은 CLI config로 제어하지만 shell 하위 동작의 allowlist를 강한 보안 경계로 간주하지 않는다.

## Decision과 Result 재사용

Task가 `needs_decision`이면 해당 Task만 기다린다.

```bash
python3 tools/projectctl.py decision show <decision-id>
python3 tools/projectctl.py decision resolve <decision-id> \
  --choice <option-id> --actor <user-id> --note "Reason"
```

이전 결과는 검증 상태와 함께 최소 index에 추가한다.

```bash
python3 tools/projectctl.py result add parser-experiment --kind experiment \
  --summary "Parser fixture passed" --source-ref task:parser-research \
  --artifact-ref docs/parser-result.md --verification-status verified --reusable
python3 tools/projectctl.py result list
python3 tools/projectctl.py result show parser-experiment
```

후속 Task 생성 시 `--context-ref result:parser-experiment`를 사용하면 adapter가 digest와 필요한 요약만 context에 넣는다.

## Queue와 background worker

Codex 실행 계약을 가진 ready Task를 commit한 뒤 queue에 넣는다.

```bash
python3 tools/projectctl.py queue enqueue task-one
python3 tools/projectctl.py queue enqueue task-two
python3 tools/projectctl.py queue list
python3 tools/projectctl.py worker start --max-parallel 2 --max-writers 1
```

`worker start`는 detached coordinator를 시작하고 Git-local log 경로를 반환하지만 PID를 영구 상태로 저장하거나 다음 worker가 adopt하지 않는다. Foreground 또는 1회 실행은 다음과 같다.

```bash
python3 tools/projectctl.py worker run --max-parallel 2 --max-writers 1
python3 tools/projectctl.py worker run --once
python3 tools/projectctl.py worker stop
```

상태 확인과 개별 제어:

```bash
python3 tools/projectctl.py queue status task-one
python3 tools/projectctl.py queue cancel task-one
python3 tools/projectctl.py queue resume task-one
```

Running cancel은 adapter가 주기적으로 queue flag를 확인해 Codex subprocess를 종료한다. Worker가 비정상 종료되면 다음 시작에서 이전 running을 interrupted로 표시할 뿐 자동 복구하지 않는다. 잔존 Codex 프로세스, worktree diff와 Decision을 확인하기 전에는 resume하지 않는다. 한 Task가 `needs_decision` 또는 `blocked`여도 독립 Task는 계속 실행한다.

Queue 작업 후 `.harness` canonical 변경을 parent Agent가 검토하고 commit해야 한다. Queue의 `succeeded`는 handoff 회수 성공이며 Promotion 승인이 아니다.

이 가이드는 공용 템플릿으로 새 Project를 만들고, 사람이 Project 세션과 Task 세션을 전환하면서 독립 작업 결과를 공식 Project로 Promotion하는 전체 절차를 설명한다.

## 운영 모델

Project는 공식 코드·데이터·문서와 현재 목표를 관리한다. Task는 Project 목표를 수행하기 위한 하나의 서브 작업, 실험 또는 리서치를 독립 공간에서 수행한다.

```text
Project 목표와 Current Goal 설정
→ Task 계약 작성·활성화·기준점 저장
→ 사람이 Task 세션으로 전환
→ Task 수행·검증·REPORT 작성
→ 사람이 Project 세션으로 복귀
→ handoff 검토·감사·종료
→ 사람이 필요한 결과와 공식 위치를 판단
→ 선택 결과만 Promotion·검증·기록
```

Project Agent와 Task Agent는 대화 컨텍스트를 공유한다고 가정하지 않는다. `TASK.md`와 `STATUS.md`가 Task 세션의 입력 계약이고, 완료된 `REPORT.md`가 Project 세션으로 돌아오는 handoff다.

### 사람 판단과 도구의 경계

사람과 Agent가 판단한다.

- Project 목표와 Current Goal
- Task의 Final Goal, Scope, Workflow, 완료 기준
- 조사·실험 설계와 결과 해석
- 결과의 가치, Promotion 여부와 공식 반영 위치
- ADR 필요성
- Project/Task 세션 전환과 subagent 사용 허용

`projectctl`은 기계적으로 판정 가능한 절차만 수행한다.

- Project 구조와 정해진 Markdown 형식 검사
- Task scaffold, 선택 코드 snapshot, 공식 데이터 symlink
- 상태 전이와 REPORT 완성도 검사
- Git 기준점과 linked data checksum 저장
- Task 경계 밖 변경 감사
- 종료 History와 이미 내려진 Promotion 결정 기록
- 내용 없는 Hook 메타데이터 목록과 보고서 생성

형식 검사를 통과해도 목표의 타당성, 결과 해석 또는 Promotion 가치는 증명되지 않는다.

## 실행 전 조건

Python 3, Git, Codex CLI가 필요하다. Project는 Git 저장소여야 하며 Task 기준점을 만들기 전에 적어도 하나의 commit과 깨끗한 worktree가 필요하다.

세션 런처는 현재 환경에 맞춰 network를 허용하고 `--dangerously-bypass-approvals-and-sandbox`로 Codex를 실행한다. bubblewrap sandbox나 auto-review에 의존하지 않는다.

- full-access는 신뢰한 저장소에서만 사용한다.
- Task 경계는 Git diff와 checksum으로 사후 감사하며 쓰기 보안 경계가 아니다.
- custom agent의 비수정 지시는 행동 규칙이지 시스템 권한 제한이 아니다.
- Hook은 작업을 차단하지 않는 관찰 장치이며 완전한 보안 감사를 보장하지 않는다.

## 새 Project 만들기

Harness Engineering 저장소에서 공용 템플릿을 복사한다.

```bash
python3 tools/create_project.py /absolute/path/to/new-project
cd /absolute/path/to/new-project
```

생성 도구는 기존 목적지를 덮어쓰지 않는다. 숨김 설정을 포함한 템플릿을 복사하고 Git을 초기화한 뒤 구조를 검사한다.

1. `PROJECT.md`의 Goal과 Scope를 작성한다.
2. `STATE.md`의 Current Goal을 작성한다. Current Tasks는 비워 둔다.
3. 사람용 소개가 필요하면 `README.md`의 Project Introduction을 작성한다.
4. 구조를 검사하고 최초 commit을 만든다.

```bash
python3 tools/projectctl.py check
git add .
git commit -m "chore: initialize project"
```

`PROJECT.md`는 안정적인 프로젝트 정의이고 `STATE.md`는 현재 Goal과 현재 Task만 보관한다. 두 파일을 진행 로그로 사용하지 않는다.

## Hook 검토와 Project 세션

공용 템플릿은 `.codex/hooks.json`에서 관찰 Hook을 등록한다. 처음 저장소를 신뢰할 때 Hook 명령과 `.codex/hooks/observe.py`를 직접 검토하고 Codex의 `/hooks` 화면에서 상태를 확인한다. 일반 세션 런처는 Hook trust를 우회하지 않는다.

사람이 Project 세션을 연다.

```bash
python3 tools/projectctl.py session project
```

런처는 Project 역할과 관찰 run ID를 전달한다. 새 세션 또는 컨텍스트 압축 뒤에는 한 번 실행한다.

```bash
python3 tools/projectctl.py context
```

출력에는 Project Goal, Scope, Current Goal, 현재 Task 상태, 종료 대기 handoff와 source digest가 포함된다. 같은 세션에서 source가 바뀌지 않았다면 같은 문서를 다시 읽을 필요가 없다.

## Task 설계와 생성

Task 이름은 숫자 ID 대신 의미가 드러나는 lowercase kebab-case를 사용한다. 예: `compare-parser-strategies`, `normalize-csv-input`.

```bash
python3 tools/projectctl.py task create normalize-csv-input \
  --goal "CSV 입력을 정규화하는 구현과 검증 근거를 작성한다."
```

필요한 공식 코드는 생성 시 Task `scripts/`로 복사하고, 공식 데이터는 Task `data/`에 symlink로 연결할 수 있다. 옵션은 반복 가능하다.

```bash
python3 tools/projectctl.py task create evaluate-model \
  --goal "기존 평가 코드를 기준 데이터로 검증한다." \
  --copy-code src/evaluate.py evaluate.py \
  --copy-code tools/report.py report.py \
  --link-data data/benchmark benchmark
```

코드 원본은 `src/` 또는 `tools/`, 데이터 원본은 `data/` 안에 있어야 한다. 복사 코드는 Task snapshot이고 symlink 데이터는 공식 원본이므로 Task가 수정하지 않는다.

생성 직후 `tasks/<task-name>/TASK.md`를 작성한다.

- Scope: 이 Task가 다루는 범위
- Inputs/Data: 사용할 snapshot, link, 문서 또는 근거
- Workflow: 수행 순서
- Outputs: Task 내부에 생성할 결과
- Completion Criteria: 종료를 판단할 검증 가능한 조건

`STATUS.md`에는 Final Goal, Work Plan, Current Work와 현재 Status만 둔다. 상태 로그나 장문의 결과를 쌓지 않는다.

계약을 작성한 뒤 확인·활성화·기준점 저장을 수행한다.

```bash
python3 tools/projectctl.py context --task normalize-csv-input
python3 tools/projectctl.py task validate normalize-csv-input --phase ready
python3 tools/projectctl.py task activate normalize-csv-input
git add STATE.md tasks/normalize-csv-input
git commit -m "chore: activate normalize csv task"
python3 tools/projectctl.py task baseline normalize-csv-input
```

`baseline`은 worktree가 깨끗할 때만 성공한다. 기준 commit과 checksum은 `.git/harness/`에 저장되며 공식 산출물이 아니다.

## Task 세션 수행

Project 세션을 종료한 뒤 사람이 Task 세션을 연다.

```bash
python3 tools/projectctl.py session task normalize-csv-input
```

Task 작업 디렉터리에서 새 세션 또는 컨텍스트 압축 뒤 한 번 실행한다.

```bash
python3 ../../tools/projectctl.py context
```

Task Agent는 context의 Final Goal, Work Plan, Current Work, 계약과 REPORT 형식을 handoff로 사용한다. 조사, 구현, 실험, 메모와 임시 산출물은 Task 계약이 지정한 위치에 둔다.

- `scripts/`: snapshot과 Task 실행·실험 코드
- `data/`: 공식 데이터 symlink
- `docs/research/`: 외부 조사 근거
- `docs/notes/`: 수행 메모
- `output/`: Task 결과

현재 Work가 바뀔 때만 `STATUS.md`를 갱신한다. doing Task에는 정확히 하나의 doing Work가 있어야 하며 Current Work가 그 이름과 같아야 한다.

완료할 때 다음을 정리한다.

1. 산출물과 관련 검증을 완료한다.
2. `REPORT.md`에 Outcome, 목표 대비 결과, 핵심 발견, 검증, Relevant Files, 한계와 후속 검토를 작성한다.
3. Work Plan을 모두 completed로, Current Work를 `None`으로, Task Status를 completed로 바꾼다.
4. 종료 형식을 검사하고 Task 세션을 멈춘다.

```bash
python3 ../../tools/projectctl.py task validate normalize-csv-input --phase completed
```

계속하지 않기로 한 Task는 REPORT에 중지 결과와 재사용 가능한 근거를 남기고 Status를 stopped로 바꾼다. doing Work를 남기지 않고 Current Work를 `None`으로 만든 뒤 `--phase stopped`로 검증한다.

## Project handoff와 Task 종료

사람이 Project 세션으로 돌아온다.

```bash
python3 tools/projectctl.py session project
python3 tools/projectctl.py context
python3 tools/projectctl.py task status
```

완료 또는 중지 Task는 Project=`doing`, Task=`completed|stopped`로 표시된다. close 전에 정규화된 handoff와 경계를 확인한다.

```bash
python3 tools/projectctl.py task handoff normalize-csv-input --json
python3 tools/projectctl.py task audit normalize-csv-input
python3 tools/projectctl.py task close normalize-csv-input
git add STATE.md docs/history tasks/normalize-csv-input
git commit -m "chore: close normalize csv task"
```

`audit`은 기준점 이후 Task 밖 변경과 linked data 변경을 검사한다. 실패하면 자동 복구하지 말고 `git diff`와 원본 데이터를 확인한다.

completed Task는 Current Goal이 유지되는 동안 STATE에 completed로 남는다. stopped Task는 STATE에서 제거되고 History에만 남는다. Task 디렉터리와 REPORT는 증거로 보존한다. 재시도는 새 목표가 드러나는 새 이름의 Task로 만든다.

## Promotion

Task close와 Promotion은 별도 단계다. completed는 검토 가능 상태일 뿐 자동 Promotion 신호가 아니다.

사람이 REPORT와 Relevant Files를 바탕으로 결과 가치, 공식 위치, 필요한 Project 검증과 ADR 필요성을 결정한다.

| 결과 | 공식 위치 |
| --- | --- |
| 제품·라이브러리·런타임 코드 | `src/` |
| 반복 사용하는 개발·운영 도구 | `tools/` |
| 검증된 공식 데이터와 metadata README | `data/` |
| 사용자·설계·운영 문서 | `docs/` 또는 책임이 정해진 루트 문서 |
| 장기 구조 결정과 이유 | `docs/adr/<decision-name>.md` |
| Task 종료·Promotion 사건 | `docs/history/`의 도구 생성 기록 |

필요한 결과만 공식 위치에 적용하고 관련 테스트와 구조 검사를 실행한다. 그 뒤 이미 내린 결정을 기록한다.

```bash
python3 tools/projectctl.py check
python3 tools/projectctl.py promotion record normalize-csv-input \
  --decision promoted \
  --path src/csv_normalizer.py \
  --path docs/csv-normalization.md
git add src docs
git commit -m "feat: promote csv normalization result"
```

공식 반영 가치가 없는 결과는 파일을 만들지 않고 기록한다.

```bash
python3 tools/projectctl.py promotion record normalize-csv-input \
  --decision not-promoted
```

`promotion record`는 파일을 복사하거나 가치를 판단하지 않는다. completed History의 결정을 한 번만 갱신한다. ADR 파일명에는 날짜를 넣지 않는다.

## Skills와 subagent

공용 Skills는 자연어 요청에 자동 호출되지 않는다.

- `$manage-project-workflow`: 사용자가 선택한 Project lifecycle checkpoint만 실행
- `$run-task-workflow`: 현재 Task 계약 수행과 REPORT handoff 준비

두 Skill의 `allow_implicit_invocation`은 false다. 반복 명령을 줄이는 보조 절차이며 Goal, 해석, Promotion 판단 또는 세션 전환을 대신하지 않는다.

기본은 단일 Agent다. 서로 독립적인 읽기 작업이라 병렬 이점이 분명하고, 부모 컨텍스트 오염 가능성이 낮으며, 역할·범위·추가 비용을 확인한 경우에만 사용자가 subagent를 허용한다.

`research_reader`와 `verification_reader`는 각각 제한된 근거 수집과 독립 검증을 위한 설정이다. 파일 수정, lifecycle 명령, 범위 확장, 재위임을 지시상 금지하지만 full-access 환경에서 권한 차단을 제공하지 않는다.

## 관찰 보고서

`projectctl session`으로 연 세션은 Git-local run ID를 가진다. Hook, context와 명시적 Skill marker는 다음 위치에 내용 없는 JSONL metadata로 누적된다.

```text
.git/harness/observability/<run-id>/events.jsonl
```

```bash
python3 tools/projectctl.py observe list
python3 tools/projectctl.py observe report --latest
```

기본 보고서는 `.harness/observability/<run-id>/REPORT.md`와 `summary.json`에 생성된다. Hook event coverage, Markdown path 방문 횟수, context와 lifecycle, Skill marker, compaction, subagent start/stop, 역할별 이벤트와 timeline을 확인할 수 있다.

Hook은 사용자 프롬프트, 도구 출력, patch 본문, 전체 shell 명령을 기록하지 않는다. 그러나 모든 동작을 완전히 관찰할 수 없으며 누락 event는 “동작이 없었다”는 증거가 아니다. 실험 raw Codex JSONL은 프롬프트와 Agent 메시지를 포함할 수 있어 자동 공개하지 않는다.

## 결과 검토 순서

가장 적은 컨텍스트로 다음 순서대로 본다.

1. `PROJECT.md`: 안정적인 Goal과 Scope
2. `STATE.md`: Current Goal과 현재 Task
3. 검토 대상 Task의 `REPORT.md`
4. REPORT의 Relevant Files와 실제 테스트 결과
5. 공식 영역의 `git diff`와 관련 테스트
6. `docs/history/`의 종료·Promotion 기록
7. 필요할 때만 `docs/adr/`의 장기 결정
8. `.harness/observability/.../REPORT.md`의 행동·coverage 집계
9. 문제 조사에 꼭 필요할 때만 Git-local event 또는 실험 raw JSONL

Task의 전체 수행 메모는 기본 검토 대상이 아니다. REPORT와 Relevant Files만으로 판단이 부족할 때 제한적으로 확인한다.

## 장애 대응

- baseline 실패: `git status --short`로 활성화 변경이 commit됐고 worktree가 깨끗한지 확인한다.
- audit의 Project 변경: 자동으로 되돌리지 말고 변경 주체와 필요성을 확인한다.
- Project=`doing`, Task=`completed|stopped`: 정상 handoff 구간이며 Project에서 handoff, audit, close한다.
- Hook event 없음: `projectctl session` 사용, Hook trust, `/hooks` 활성 상태를 확인한다. Hook은 fail-open이다.
- observe report 실패: `observe list` 뒤 `--latest` 또는 정확한 run ID를 지정한다.
- Task 세션의 lifecycle 거부: 사람이 Project 세션으로 돌아와 실행한다.

## 최소 체크리스트

Project 시작:

- `PROJECT.md`, `STATE.md` 작성
- `projectctl check` 통과와 최초 commit
- Hook 명령 검토와 trust

Task 시작:

- 의미 있는 이름과 Final Goal
- TASK 계약과 STATUS Work Plan 완성
- validate ready → activate → commit → baseline
- 사람이 Task 세션으로 전환

Task 종료:

- 결과 검증, REPORT, completed 또는 stopped STATUS
- validate completed/stopped
- 사람이 Project 세션으로 복귀
- handoff → audit → close → commit

Promotion:

- 사람이 가치와 공식 경로 결정
- 필요한 결과만 반영
- 관련 검증과 `projectctl check`
- `promotion record`와 commit
