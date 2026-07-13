# Project/Task 하네스 운영 가이드

이 가이드는 공용 템플릿으로 새 Project를 만들고, 사람이 Project 세션과 Task 세션을 전환하면서 독립 작업 결과를 공식 Project로 Promotion하는 전체 운영 절차를 설명한다.

## 1. 운영 모델

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

## 2. 사람 판단과 결정적 도구의 경계

사람과 Agent가 판단할 항목:

- Project 목표와 Current Goal
- Task의 Final Goal, Scope, Workflow, 완료 기준
- 조사·실험 설계와 결과 해석
- 완료 결과의 가치, Promotion 여부와 공식 반영 위치
- ADR 작성 필요성
- Project/Task 세션 전환과 subagent 사용 허용

`projectctl`이 결정적으로 처리할 항목:

- Project 구조와 정해진 파일 형식 검사
- Task 템플릿 생성, 선택 코드 snapshot, 공식 데이터 symlink
- 상태 전이 형식과 REPORT 완성도 검사
- Git 기준점과 linked data checksum 저장
- Task 경계 밖 변경 감사
- 완료·중지 History와 이미 내려진 Promotion 결정 기록
- 내용 없는 Hook 메타데이터의 목록과 보고서 생성

형식 검사를 통과해도 목표의 타당성, 결과 해석 또는 Promotion 가치는 증명되지 않는다.

## 3. 실행 전 조건과 보안 모델

필요한 실행 환경은 Python 3, Git, Codex CLI다. Project는 Git 저장소여야 하며 Task 기준점을 만들기 전에 적어도 하나의 commit과 깨끗한 worktree가 필요하다.

이 하네스의 세션 런처는 현재 환경에 맞춰 network를 허용하고 `--dangerously-bypass-approvals-and-sandbox`로 Codex를 실행한다. bubblewrap sandbox나 자동 승인 검토에 의존하지 않는다. 따라서 다음 특성을 이해해야 한다.

- full-access는 신뢰한 저장소에서만 사용한다.
- Task 경계는 Git diff와 checksum으로 사후 감사하며 쓰기 보안 경계가 아니다.
- custom agent의 비수정 지시는 행동 규칙이지 시스템 권한 제한이 아니다.
- Hook은 작업을 차단하지 않는 관찰 장치이며 보안 감사의 완전성을 보장하지 않는다.

## 4. 새 Project 만들기

Harness Engineering 저장소에서 공용 템플릿을 복사한다.

```bash
python3 tools/create_project.py /absolute/path/to/new-project
cd /absolute/path/to/new-project
```

생성 도구는 목적지 부재를 확인하고 숨김 설정을 포함한 템플릿을 복사한 뒤 Git을 초기화하고 `projectctl check`를 실행한다. 기존 목적지는 덮어쓰지 않는다.

다음 순서로 초기 내용을 확정한다.

1. `PROJECT.md`의 Goal과 Scope를 작성한다.
2. `STATE.md`의 Current Goal을 작성한다. Current Tasks는 아직 비워 둔다.
3. 사람용 소개가 필요하면 `README.md`의 Project Introduction을 작성한다.
4. 구조를 검사하고 최초 commit을 만든다.

```bash
python3 tools/projectctl.py check
git add .
git commit -m "chore: initialize project"
```

`PROJECT.md`는 안정적인 프로젝트 정의이고 `STATE.md`는 현재 Goal과 현재 Task만 보관한다. 두 파일을 진행 로그로 사용하지 않는다.

## 5. Hook을 검토하고 Project 세션 열기

공용 템플릿은 `.codex/hooks.json`에서 내용 없는 관찰 Hook을 등록한다. 처음 저장소를 신뢰할 때 Hook 명령과 `.codex/hooks/observe.py`를 직접 검토하고 Codex의 `/hooks` 화면에서 상태를 확인한다. 일반 세션 런처는 Hook trust를 우회하지 않는다.

Project 세션은 사람이 다음 명령으로 연다.

```bash
python3 tools/projectctl.py session project
```

런처는 Project 역할과 관찰 run ID를 환경 변수로 전달한다. 새 세션 또는 컨텍스트 압축 뒤에는 한 번만 실행한다.

```bash
python3 tools/projectctl.py context
```

출력에는 Project Goal, Scope, Current Goal, 현재 Task 상태, 종료 대기 handoff와 source digest가 포함된다. 같은 세션에서 source가 바뀌지 않았다면 같은 문서를 다시 읽을 필요가 없다.

## 6. Task 설계와 생성

Task 이름은 숫자 ID 대신 의미가 드러나는 lowercase kebab-case를 사용한다. 예: `compare-parser-strategies`, `normalize-csv-input`.

Final Goal이 정해지면 Project 세션에서 Task를 생성한다.

```bash
python3 tools/projectctl.py task create normalize-csv-input \
  --goal "CSV 입력을 정규화하는 구현과 검증 근거를 작성한다."
```

필요한 공식 코드는 생성 시 Task `scripts/`로 복사하고, 공식 데이터는 Task `data/`에 symlink로 연결할 수 있다. 옵션은 여러 번 사용할 수 있다.

```bash
python3 tools/projectctl.py task create evaluate-model \
  --goal "기존 평가 코드를 기준 데이터로 검증한다." \
  --copy-code src/evaluate.py evaluate.py \
  --copy-code tools/report.py report.py \
  --link-data data/benchmark benchmark
```

코드 원본은 `src/` 또는 `tools/`, 데이터 원본은 `data/` 안에 있어야 한다. 복사한 코드는 Task snapshot이고 symlink 데이터는 공식 원본이므로 Task가 수정하지 않는다.

생성 직후 `tasks/<task-name>/TASK.md`를 작성한다.

- Scope: 이 Task가 다루는 범위
- Inputs/Data: 사용할 snapshot, link, 문서 또는 근거
- Workflow: 수행 순서
- Outputs: Task 내부에 생성할 결과
- Completion Criteria: 종료를 판단할 검증 가능한 조건

`STATUS.md`에는 Final Goal, Work Plan, Current Work와 현재 Status만 둔다. 상태 로그나 장문의 결과를 쌓지 않는다.

계약을 작성한 뒤 Project 세션에서 확인·활성화·기준점 생성을 수행한다.

```bash
python3 tools/projectctl.py context --task normalize-csv-input
python3 tools/projectctl.py task validate normalize-csv-input --phase ready
python3 tools/projectctl.py task activate normalize-csv-input
git add STATE.md tasks/normalize-csv-input
git commit -m "chore: activate normalize csv task"
python3 tools/projectctl.py task baseline normalize-csv-input
```

`baseline`은 worktree가 깨끗할 때만 성공한다. Git commit과 linked data checksum은 `.git/harness/`에 저장되므로 Project 공식 산출물이 아니다.

## 7. Task 세션 수행

Project 세션을 종료한 뒤 사람이 Task 세션을 연다.

```bash
python3 tools/projectctl.py session task normalize-csv-input
```

Task 작업 디렉터리에서 새 세션 또는 컨텍스트 압축 뒤 한 번 실행한다.

```bash
python3 ../../tools/projectctl.py context
```

Task Agent는 context의 Final Goal, Work Plan, Current Work, 계약과 REPORT 형식을 세션 handoff로 사용한다. 조사, 구현, 실험, 메모와 임시 산출물은 Task 계약이 지정한 위치에 둔다.

- `scripts/`: snapshot과 Task 실행·실험 코드
- `data/`: 공식 데이터 symlink
- `docs/research/`: 외부 조사 근거
- `docs/notes/`: 수행 메모
- `output/`: Task 결과

진행 중에는 현재 Work가 바뀔 때만 `STATUS.md`를 갱신한다. doing Task에는 정확히 하나의 doing Work가 있어야 하며 Current Work가 그 이름과 같아야 한다.

완료할 때는 다음을 한 번에 정리한다.

1. 산출물과 관련 검증을 완료한다.
2. `REPORT.md`에 Outcome, 목표 대비 결과, 핵심 발견, 검증, Project가 볼 Relevant Files, 한계와 후속 검토를 작성한다.
3. Work Plan을 모두 completed로, Current Work를 `None`으로, Task Status를 completed로 바꾼다.
4. 종료 형식을 검사하고 Task 세션을 멈춘다.

```bash
python3 ../../tools/projectctl.py task validate normalize-csv-input --phase completed
```

계속하지 않기로 한 Task는 REPORT에 중지 결과와 재사용 가능한 근거를 남기고 Status를 stopped로 바꾼다. doing Work를 남기지 않고 Current Work를 `None`으로 만든 뒤 `--phase stopped`로 검증한다.

Task Agent는 Project close나 Promotion을 실행하지 않는다.

## 8. Project handoff 검토와 Task 종료

사람이 Task 세션을 종료하고 Project 세션으로 돌아온다.

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

`audit`은 기준점 이후 Task 밖 변경과 linked data 변경을 검사한다. 실패하면 자동 복구하지 말고 `git diff`와 원본 데이터를 확인해 원인을 판단한다.

completed Task는 Current Goal이 유지되는 동안 STATE에 completed로 남는다. stopped Task는 STATE에서 제거되고 History에만 남는다. Task 디렉터리와 REPORT는 어느 경우에도 증거로 보존한다. 재시도가 필요하면 기존 Task를 되살리기보다 새 목표가 드러나는 새 이름의 Task를 만든다.

## 9. Promotion

Task close와 Promotion은 별도 단계다. completed는 검토 가능 상태일 뿐 자동 Promotion 신호가 아니다.

사람이 `REPORT.md`와 Relevant Files를 바탕으로 다음을 결정한다.

- 어떤 결과가 공식 Project에 필요한가
- `src/`, `tools/`, `data/`, `docs/` 중 어디에 반영할 것인가
- 어떤 Project 검증을 실행할 것인가
- 장기 결정으로 ADR을 남길 필요가 있는가

공식 위치의 기준은 다음과 같다.

| 결과 | 공식 위치 |
| --- | --- |
| 제품·라이브러리·런타임 코드 | `src/` |
| 반복 사용하는 개발·운영 도구 | `tools/` |
| 검증된 공식 데이터와 데이터 README | `data/` |
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

가치가 없거나 Task 근거만 보존할 결과는 공식 파일을 만들지 않고 다음처럼 기록한다.

```bash
python3 tools/projectctl.py promotion record normalize-csv-input \
  --decision not-promoted
```

`promotion record`는 파일을 복사하거나 가치를 판단하지 않는다. completed History의 `not evaluated`를 한 번만 변경한다. ADR 파일명에는 날짜를 넣지 않는다.

## 10. 명시적 Skills

공용 Skills는 자연어 요청에 자동 호출되지 않는다.

- `$manage-project-workflow`: 사용자가 선택한 Project lifecycle checkpoint만 실행
- `$run-task-workflow`: 현재 Task 계약 수행과 REPORT handoff 준비

두 Skill의 `allow_implicit_invocation`은 false다. 반복 명령을 줄이는 보조 절차이며 Goal, 해석, Promotion 판단 또는 세션 전환을 대신하지 않는다. 호출 여부는 관찰 로그의 skill marker로 확인할 수 있다.

## 11. 보수적 subagent 사용

기본은 단일 Agent다. 다음 조건을 모두 만족할 때만 사용자가 subagent 사용을 허용한다.

- 서로 독립적인 읽기 작업이라 병렬 실행 이점이 분명하다.
- 부모 Agent의 현재 판단 컨텍스트를 불필요한 세부 정보로 오염시킬 가능성이 낮다.
- 역할, 범위, 예상 추가 비용을 호출 전에 확인했다.

제공된 `research_reader`와 `verification_reader`는 각각 하나의 제한된 근거 수집과 독립 검증을 위한 설정이다. 파일 수정, lifecycle 명령, 범위 확장, 재위임을 지시상 금지한다. full-access 환경에서는 이 지시가 권한 차단이 아님을 전제로 결과를 검토한다.

## 12. 관찰 보고서

`projectctl session`으로 시작한 각 세션은 Git-local run ID를 가진다. Hook과 context, 명시적 Skill marker는 다음 위치에 내용 없는 JSONL 메타데이터로 누적된다.

```text
.git/harness/observability/<run-id>/events.jsonl
```

사용자는 Project 세션에서 run을 확인하고 보고서를 만든다.

```bash
python3 tools/projectctl.py observe list
python3 tools/projectctl.py observe report --latest
```

기본 보고서는 `.harness/observability/<run-id>/REPORT.md`와 `summary.json`에 생성된다. 다음 항목을 확인할 수 있다.

- Hook event coverage와 malformed line
- 관찰된 Markdown path별 방문 횟수
- context와 lifecycle action
- 명시적 Skill marker
- compaction과 subagent start/stop
- 역할별 이벤트 수와 시간 순서

Hook은 사용자 프롬프트, 도구 출력, patch 본문, 전체 shell 명령을 기록하지 않는다. 그러나 모든 도구 실행을 완전히 관찰할 수 없으며 누락 event는 “동작이 없었다”는 증거가 아니다. 실험 runner의 raw Codex JSONL은 프롬프트와 Agent 메시지를 포함할 수 있으므로 `.harness/` 밖으로 자동 공개하지 않는다.

## 13. 사용자가 결과를 검토하는 순서

Project 수행 내역을 직접 볼 때는 다음 순서가 가장 적은 컨텍스트로 판단하기 좋다.

1. `PROJECT.md`: 안정적인 Goal과 Scope
2. `STATE.md`: Current Goal과 현재 Task
3. 종료 대기 또는 검토 대상 Task의 `REPORT.md`
4. REPORT의 Relevant Files와 실제 테스트 결과
5. 공식 영역의 `git diff`와 관련 테스트
6. `docs/history/`의 종료·Promotion 기록
7. 필요할 때만 `docs/adr/`의 장기 결정
8. `.harness/observability/.../REPORT.md`의 행동·coverage 집계
9. 문제 조사에 꼭 필요할 때만 Git-local event JSONL이나 실험 raw JSONL

Task의 `docs/notes/`나 전체 수행 과정을 기본 검토 대상으로 삼지 않는다. REPORT와 Relevant Files만으로 판단이 부족할 때 제한적으로 확인한다.

## 14. 자주 만나는 실패

### baseline이 실패한다

Task 활성화 변경을 commit하지 않았거나 worktree가 더럽다. `git status --short`로 확인하고 의도한 변경만 commit한 뒤 다시 실행한다.

### audit이 Project 변경을 보고한다

기준점 뒤 Task 밖 파일이 바뀌었다. 자동으로 되돌리지 말고 변경 주체와 필요성을 확인한다. Task 결과의 공식 반영은 close 이후 Promotion 단계에서 수행한다.

### Task status와 Project status가 다르다

정상적인 handoff 구간일 수 있다. Task가 completed/stopped이고 Project가 doing이면 Project 세션에서 handoff, audit, close할 차례다.

### Hook event가 없다

세션을 `projectctl session`으로 열었는지, repository Hook을 신뢰했는지, `/hooks`에서 활성 상태인지 확인한다. Hook 실패는 본 작업을 막지 않도록 fail-open이다.

### observe report가 실행되지 않는다

먼저 `observe list`로 run 존재를 확인한다. `--latest` 또는 정확한 run ID 하나를 제공해야 한다.

### Task 세션에서 lifecycle 명령이 거부된다

런처가 Task 역할을 선언했기 때문이다. Task는 자기 context와 종료 형식 검증만 수행하고 Project lifecycle은 사람이 Project 세션으로 돌아간 뒤 실행한다.

## 15. 최소 운영 체크리스트

Project 시작:

- `PROJECT.md`, `STATE.md` 작성
- `projectctl check` 통과
- 최초 commit
- Hook 명령 검토와 trust

Task 시작:

- 의미 있는 Task 이름과 Final Goal
- TASK 계약과 STATUS Work Plan 완성
- `validate --phase ready`
- activate → commit → baseline
- 사람이 Task 세션으로 전환

Task 종료:

- 결과 검증과 REPORT 완성
- STATUS completed 또는 stopped
- `validate --phase completed|stopped`
- 사람이 Project 세션으로 복귀
- handoff → audit → close → commit

Promotion:

- 사람이 가치와 공식 경로 결정
- 필요한 결과만 반영
- 관련 검증과 `projectctl check`
- `promotion record`와 commit

