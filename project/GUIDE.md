# Project Harness Operations Guide

이 문서는 공용 하네스를 설치·갱신하고, 적용 Project에서 Task를 생성·실행·검토·반영하는 실제 절차를 설명한다. 새 Project의 기본 authority는 v2다. Legacy Markdown lifecycle은 migration 전 Project에만 사용하며 마지막 부록으로 분리한다.

## 1. 운영 모델

```text
Project goal과 current objective
  → Task contract: goal, scope, input, output, ownership, acceptance, validation
  → worktree 격리
  → 사람 또는 Codex adapter가 Task 수행
  → structured handoff와 validation
  → 부모 Agent review
  → 필요한 Task만 Decision 대기
  → 사용자가 selected candidate의 exact diff 승인
  → Promotion apply
  → 재사용 가치가 있는 결과만 Result index에 기록
```

`.harness/*.json`이 v2의 기계 상태 원본이고 `show`, `task show/review`, `decision show`, `promotion show`, `result show`가 사람용 Markdown View를 생성한다. JSON을 직접 편집하지 않는다.

각 Project는 자신의 `.harness`, Git history, queue와 Git-local runtime을 소유한다. Harness Engineering 저장소는 bundle을 제공할 뿐 적용 Project를 등록·검색·원격 관리하지 않는다.

## 2. 필요한 환경과 지원 범위

- Python 3
- Git과 최초 commit
- Codex Task를 실행할 경우 Codex CLI
- local Linux 또는 WSL filesystem

현재 native Windows, NFS, distributed worker와 중앙 dashboard는 지원 범위가 아니다. Task/integration worktree를 만들 수 있도록 Project parent directory에도 쓰기 권한이 필요하다.

## 3. Bundle 만들기와 새 Project 생성

Harness Engineering 저장소 root에서 versioned bundle을 만든다.

```bash
python3 tools/harnessctl.py package \
  --template project \
  --version 2.0.0-local \
  --output /tmp/project-harness-2.0.0-local
```

새 Project 생성은 destination을 새로 만들고 Git과 v2 authority를 초기화한다.

```bash
python3 tools/harnessctl.py new /absolute/path/to/my-project \
  --source /tmp/project-harness-2.0.0-local \
  --project-id my-project \
  --goal "Project goal" \
  --scope "Initial scope"

cd /absolute/path/to/my-project
git add .
git commit -m "chore: initialize project"
python3 tools/projectctl.py check
python3 tools/projectctl.py show project
```

`check`는 template 구조뿐 아니라 v2 canonical record의 schema, digest, internal reference, Result index와 artifact provenance를 검사한다. 형식 통과가 목표 타당성이나 결과 품질을 증명하지는 않는다.

## 4. 기존 Project에 최초 적용

`apply`는 기본 dry-run이다. 대상 Project를 중앙에 등록하지 않으며 명시된 경로만 검사한다.

```bash
python3 tools/harnessctl.py apply /absolute/path/to/existing-project \
  --source /tmp/project-harness-2.0.0-local
```

결과의 `actions`를 검토한다.

- `create`: 없는 파일을 추가한다.
- `preserve`: Project 소유 또는 integration 파일이 달라 유지한다.
- `replace`: managed 파일을 bundle 버전으로 교체한다.
- `conflict`: 자동 반영하지 않는다.

최초 apply에서 기존 `.codex/`, `.agents/`, `tools/`, `tasks/_template/`, `GUIDE.md`, `STRUCTURE.md`가 replace될 수 있다. 별도 backup과 dry-run review 뒤에만 명시적으로 확인한다.

```bash
python3 tools/harnessctl.py apply /absolute/path/to/existing-project \
  --source /tmp/project-harness-2.0.0-local \
  --apply --accept-managed-replace
```

managed source/target과 parent에 symlink가 있으면 적용을 거부한다. Bundle checksum은 내용 일치를 확인하지만 출처를 인증하지 않으므로 신뢰된 commit에서 만든 bundle만 사용한다.

## 5. 설치된 Project 업데이트

```bash
python3 tools/harnessctl.py update /absolute/path/to/project \
  --source /tmp/project-harness-next
python3 tools/harnessctl.py update /absolute/path/to/project \
  --source /tmp/project-harness-next --apply
```

update는 설치 당시 checksum, 현재 Project 파일과 새 bundle을 비교한다. Project와 bundle 양쪽이 바뀐 managed 파일은 conflict로 중단한다. 적용 뒤 Project-local `check`가 실패하면 같은 프로세스가 건드린 파일과 install metadata를 backup에서 복구한다. SIGKILL·host 장애를 넘는 journal이나 임의 과거 version rollback 명령은 제공하지 않으므로 중요한 Project는 Git과 외부 backup을 함께 사용한다.

## 6. Session과 현재 상태 확인

사람이 interactive Project session을 열 때 다음 launcher를 사용할 수 있다.

```bash
python3 tools/projectctl.py session project
```

이 launcher는 현재 구현상 full-access/no-approval Codex를 실행한다. 신뢰한 저장소에서만 사용하며 Task adapter의 `workspace-write`와 같은 보안 경계로 오해하지 않는다.

새 세션 또는 컨텍스트 압축 뒤 한 번 현재 상태를 확인한다.

```bash
python3 tools/projectctl.py context
```

이 출력의 Project Goal, current objective, Current Tasks와 pending handoff를 운영 상태로 사용한다. lifecycle mutation 뒤 상태가 바뀌었을 때만 다시 실행한다.

## 7. 생성 후 Project와 Task 계약 개정

v2의 `.harness/project.json`과 `.harness/tasks/*/task.json`은 canonical이므로 직접 편집하지 않는다. 생성 뒤 의미를 고정하는 것이 목적이지 영구 불변으로 만드는 것이 아니다. 공식 amendment는 항상 before/after preview를 먼저 보여주고, apply에서 현재 revision·변경 이유·actor를 기록한다.

Project 목표를 사람이 직접 고칠 때는 읽기 쉬운 View를 Project 안에 저장해 편집한다.

```bash
python3 tools/projectctl.py show project > docs/project-amendment.md
# Goal, Scope, Current Objective section을 편집
python3 tools/projectctl.py project amend \
  --from-markdown docs/project-amendment.md \
  --reason "사용자가 범위와 성공 방향을 구체화함" \
  --actor user
```

Preview의 `changes`와 `expected_revision`을 검토한 뒤 같은 proposal을 적용한다.

```bash
python3 tools/projectctl.py project amend \
  --from-markdown docs/project-amendment.md \
  --reason "사용자가 범위와 성공 방향을 구체화함" \
  --actor user \
  --expected-revision 1 \
  --apply
python3 tools/projectctl.py show project
git diff -- .harness/project.json
```

한두 필드만 바꿀 때는 `--goal`, 반복 가능한 `--scope`, `--current-objective`를 직접 사용할 수 있다. Scope option은 기존 목록에 추가하는 것이 아니라 전체 목록을 교체한다.

Task도 같은 방식으로 `task show` View를 편집한다. Markdown import가 다루는 필드는 Goal, Scope, Outputs, Dependencies, Owned Write Paths, Acceptance, Validation Commands와 Context References다.

```bash
python3 tools/projectctl.py task show improve-parser > docs/improve-parser-amendment.md
# 계약 section 편집
python3 tools/projectctl.py task amend improve-parser \
  --from-markdown docs/improve-parser-amendment.md \
  --reason "검증 조건을 사용자 피드백에 맞춤" \
  --actor user
# preview의 expected_revision이 2인 경우
python3 tools/projectctl.py task amend improve-parser \
  --from-markdown docs/improve-parser-amendment.md \
  --reason "검증 조건을 사용자 피드백에 맞춤" \
  --actor user --expected-revision 2 --apply
```

Input은 `--input`, Codex 실행 계약은 `--model`, `--reasoning-effort`, sandbox·approval·web/network·tool·MCP·Skill·limit option으로 별도 개정한다. 실행 계약 전체 제거는 `--clear-execution`을 사용한다. Task amendment는 `ready`, `needs_decision`, `blocked`에서만 허용한다. `active`, `review`, `completed`, `stopped` Task의 의미는 중간에 바꾸지 않고 follow-up 또는 replacement Task를 만든다.

Agent가 사용자의 요청을 대신 적용할 때는 `--actor agent --approval-ref <실제-승인-참조>`가 필수다. Approval reference는 인증이나 전자서명이 아니라 대화·Decision·issue와 Git diff를 연결하는 provenance다. Agent는 preview를 사용자에게 보여주고 승인받은 범위만 apply한다. `expected_revision`이 달라졌으면 최신 View로 preview를 다시 만들며 JSON을 수동 병합하지 않는다.

일반 코드·README·설계 문서는 해당 Project의 Git 규칙 안에서 직접 편집할 수 있다. Amendment는 Project/Task canonical 계약 전용이다. Decision은 실행 중 선택, Promotion은 Task 산출물의 공식 반영을 담당하므로 amendment가 두 기능을 대신하지 않는다.

## 8. Task 계약 작성

Task 이름은 의미가 드러나는 lowercase kebab-case를 사용한다. 큰 writer Task에는 최소한 scope, output, acceptance, owned path와 validation을 작성한다. 작은 read-only Task는 필요한 필드만 사용한다.

```bash
python3 tools/projectctl.py task create improve-parser \
  --goal "Parser 오류 처리를 개선한다" \
  --scope "src/parser.py와 관련 test만 변경" \
  --input src/parser.py \
  --output src/parser.py \
  --acceptance "관련 test가 통과한다" \
  --owned-path task-output \
  --validation-command "python3 -m unittest tests.test_parser"

git add .harness
git commit -m "task: create improve-parser"
python3 tools/projectctl.py task show improve-parser
```

`--input`은 Project-relative UTF-8 file만 받는다. 기본 한도는 파일당 128 KiB, Task 전체 256 KiB다. path, byte와 SHA-256이 계약에 고정되며 start 뒤 파일이 달라지면 Codex 실행을 차단한다. Directory, binary, traversal과 symlink input은 거부한다.

`task show`에서 다음을 확인한다.

- Goal·Scope와 current state
- input path·size·digest
- outputs, dependencies와 context references
- owned write paths와 acceptance
- validation argv
- 요청한 model, reasoning, sandbox, web/network, tools·MCP·skills와 budget

Task 유형별 공통 원칙:

| 유형 | 계약에서 명확해야 할 것 | 부모 review |
| --- | --- | --- |
| 코드 | 수정 경로, compatibility, test/build | diff, regression, scope, validation log |
| 문서 | 독자, authority source, 필수 section | 주장 근거, link·구조, 읽기 흐름 |
| 연구 | 질문, source policy, recency, 포함/제외 | source 품질, claim 근거, 모순과 한계 |

별도 generic profile을 강제하지 않는다. 같은 계약이 여러 Project에서 반복될 때만 Project-local scoped Skill로 승격한다.

## 9. 수동 worktree Task

Task contract를 commit한 뒤 격리 worktree를 만든다.

```bash
python3 tools/projectctl.py task start improve-parser
```

출력된 worktree에서 작업한다. Handoff JSON은 다음 필드를 가진다.

```json
{
  "status": "completed",
  "summary": "What changed and why",
  "findings": ["Important observation"],
  "limitations": ["Known limitation"],
  "candidates": [
    {
      "id": "parser-change",
      "source": "task-output/parser.py",
      "target": "src/parser.py",
      "rationale": "Acceptance evidence"
    }
  ]
}
```

Candidate source와 target은 worktree/repository 안의 non-symlink relative path여야 한다. 제출은 전체 changed path ownership을 검사하고 validation을 실행한다.

```bash
python3 tools/projectctl.py task submit improve-parser --handoff handoff.json
python3 tools/projectctl.py task review improve-parser
git add .harness
git commit -m "task: review improve-parser"
```

`task review`에서 summary, findings, limitations, acceptance, changed paths, candidates와 validation full-log 경로를 확인한다. Validation은 shell string이 아니라 argv로 실행되고 명령별 기본 300초 timeout을 가진다. Full log는 Git-local이고 canonical handoff에는 tail, digest와 경로만 남는다.

## 10. Codex adapter Task

실행 전 capability를 확인한다.

```bash
python3 tools/projectctl.py doctor codex
```

```bash
python3 tools/projectctl.py task create agent-parser \
  --goal "Implement parser change" \
  --scope "Only parser and tests" \
  --input src/parser.py \
  --output src/parser.py \
  --acceptance "Parser tests pass" \
  --owned-path task-output \
  --validation-command "python3 -m unittest tests.test_parser" \
  --codex \
  --model gpt-5.6 \
  --reasoning-effort high \
  --reasoning-fallback medium \
  --sandbox workspace-write \
  --approval-policy never \
  --web-mode disabled \
  --no-network-access \
  --allowed-tool shell \
  --allowed-tool apply_patch \
  --time-limit 3600 \
  --token-limit 200000 \
  --agent-role implementation

git add .harness
git commit -m "task: create agent-parser"
python3 tools/projectctl.py task start agent-parser
python3 tools/projectctl.py task run agent-parser
```

Adapter는 reasoning effort를 prompt 문구가 아니라 Codex CLI config로 전달한다. requested/effective contract, fallback, argv, thread, JSONL events와 usage를 Git-local run evidence에 기록한다.

실제 enforcement를 구분한다.

- hard: Codex sandbox, wall-time, structured output
- CLI config: approval, web mode, workspace-write network, MCP, Project skill, view image, multi-agent
- Agent policy/audit: shell과 apply_patch 선언
- post-run: token ceiling

`danger-full-access + network_access=false`는 network 격리를 약속할 수 없어 adapter가 거부한다. Timeout/cancel은 Codex process group을 종료한다. 부모 environment는 현재 상속하므로 secret-bearing host에서는 별도 container 또는 최소 환경으로 실행한다.

추가 권한, 외부 변경이나 scope 확대가 필요하면 Task는 `needs_decision`을 반환해야 한다. Adapter가 permission 계열 실패를 감지해도 자동 권한 상승하지 않는다.

## 11. Decision

```bash
python3 tools/projectctl.py decision show <decision-id>
python3 tools/projectctl.py decision resolve <decision-id> \
  --choice <option-id> --actor <user-id> --note "Reason"
```

View는 이유, option별 영향, 권고, safe default와 보류 가능성을 보여준다. Resolve는 canonical Task를 active 또는 blocked로 바꾸지만 queue job은 자동 재실행하지 않는다. Queue에서 실행하던 Task는 상태·worktree를 확인한 뒤 별도로 `queue resume`한다. 다른 독립 Task는 계속 진행한다.

## 12. Queue와 background worker

Codex execution contract가 있는 ready Task를 commit한 뒤 enqueue한다.

```bash
python3 tools/projectctl.py queue enqueue reader-one
python3 tools/projectctl.py queue enqueue reader-two
python3 tools/projectctl.py queue list
```

처음에는 foreground worker로 상태를 관찰한다.

```bash
python3 tools/projectctl.py worker run --max-parallel 2 --max-writers 1
```

안정된 Project에서는 detached coordinator를 시작할 수 있다.

```bash
python3 tools/projectctl.py worker start --max-parallel 2 --max-writers 1
python3 tools/projectctl.py queue status reader-one
python3 tools/projectctl.py queue cancel reader-one
python3 tools/projectctl.py worker stop
```

Queue는 `.git/harness/v2/queue.sqlite3`에 current job state만 보존한다. Codex subprocess와 validation은 병렬 실행할 수 있지만 canonical JSON의 짧은 mutation만 Project-local lock과 revision compare-and-swap으로 직렬화한다.

Worker 재시작은 남은 running job을 `interrupted`로 표시할 뿐 PID를 adopt하거나 자동 retry하지 않는다. 다음을 확인하기 전 resume하지 않는다.

1. 이전 worker와 Codex descendant가 살아 있지 않은가.
2. Task worktree의 `git status`와 diff는 무엇인가.
3. pending Decision과 최신 run evidence가 있는가.
4. 같은 workspace에 새 attempt가 겹치지 않는가.

```bash
python3 tools/projectctl.py queue resume <task-id>
```

Queue `succeeded`는 review 가능한 handoff가 생겼다는 뜻이지 Promotion 승인이 아니다.

## 13. Result 기록과 재사용

Result는 범용 evidence graph가 아니다. 후속 Task가 발견할 가치가 있는 실험·실패·review·결정·asset만 기록한다.

```bash
python3 tools/projectctl.py result add parser-experiment \
  --kind experiment \
  --summary "Parser fixture passed" \
  --source-ref task:parser-research \
  --artifact-ref docs/parser-result.md \
  --verification-status verified \
  --reviewed-by parent-agent \
  --verification-note "Fixture and report reviewed" \
  --reusable
```

`reviewed` 또는 `verified` Result는 reviewer와 source 또는 artifact evidence가 필요하다. Artifact는 존재하는 Project-relative non-symlink file이어야 하며 path, byte와 SHA-256을 기록한다.

```bash
python3 tools/projectctl.py result list --kind experiment --reusable
python3 tools/projectctl.py result list --verification-status verified --text parser
python3 tools/projectctl.py result show parser-experiment
```

Index가 손상되거나 record와 어긋나면 canonical Result records에서 재생성한다.

```bash
python3 tools/projectctl.py result rebuild
python3 tools/projectctl.py check
```

후속 Task는 `--context-ref result:parser-experiment`를 사용한다. Adapter는 digest, summary, verification과 artifact path metadata만 주입하며 artifact 전체 내용은 명시 input으로 별도 선택해야 한다. Superseded, rejected 또는 Project에 맞지 않는 Result를 관성적으로 재사용하지 않는다.

## 14. Promotion

Parent Agent가 handoff와 candidate를 검토하고 사용자가 공식 반영할 candidate를 선택한 뒤 packet을 만든다. Official worktree와 `.harness`는 clean해야 한다.

```bash
python3 tools/projectctl.py promotion prepare \
  --task improve-parser --candidate parser-change
python3 tools/projectctl.py promotion show <promotion-id>
```

`promotion show`에서 반드시 확인한다.

- Task와 selected candidate
- exact base commit
- diff와 validation digest
- validation exit와 full-log 경로
- 실제 exact diff 본문

안전하고 위임된 여러 candidate는 한 packet으로 묶을 수 있다. 다른 가치 판단이나 서로 독립된 위험을 가진 변경은 별도 packet을 사용한다.

```bash
python3 tools/projectctl.py promotion approve <promotion-id> --actor <user-id>
python3 tools/projectctl.py promotion show <promotion-id>
python3 tools/projectctl.py promotion apply <promotion-id>
```

Approve는 current base·Task·diff를 확인하고 validation을 새로 실행해 승인 subject에 결속한다. Apply도 official HEAD가 같은 base인지 확인하고 즉시 validation을 다시 통과한 경우에만 cherry-pick한다. Base, Task contract, diff나 approval subject가 바뀌면 기존 packet을 재사용하지 말고 새로 prepare한다.

Apply 중 cherry-pick 또는 두 번째 canonical record commit이 실패하면 자동 rollback journal은 없다. `git status`, cherry-pick 상태, candidate commit과 `.harness/promotions`를 확인해 forward repair하고, 불명확하면 Project를 변경하지 말고 중단한다.

## 15. Observability와 Hooks

`.codex/hooks.json`과 `.codex/hooks/observe.py`를 신뢰하기 전에 직접 검토한다. Hook은 항상 성공을 반환하는 fail-open 관찰 장치다.

```bash
python3 tools/projectctl.py observe list
python3 tools/projectctl.py observe report --latest
```

Git-local event는 prompt·tool output·patch 전체가 아닌 최소 metadata를 기록한다. Coverage 누락은 “행동이 없었다”는 증거가 아니다. Raw Codex JSONL은 prompt와 Agent message를 포함할 수 있으므로 자동 공개하지 않는다.

## 16. Legacy Project migration

기존 Markdown lifecycle Project에 bundle을 먼저 설치한 뒤 authority를 side-by-side로 변환한다. 표준 `PROJECT.md`, `STATE.md`, 완전한 Task `TASK/STATUS/REPORT`와 History가 지원 범위다. Custom/partial Task와 표준 밖 파일은 사람이 별도 inventory로 대조한다.

```bash
python3 tools/projectctl.py migrate inspect
python3 tools/projectctl.py migrate plan
python3 tools/projectctl.py migrate apply legacy-to-v2
python3 tools/projectctl.py migrate verify legacy-to-v2
python3 tools/projectctl.py migrate switch legacy-to-v2 --harness-version 2.0.0-local
python3 tools/projectctl.py check
python3 tools/projectctl.py show project
```

`apply`는 candidate만 만들고 `verify`는 candidate record schema/digest와 normalized semantic parity를 검사한다. Source file·Task·History 수를 별도 inventory와 대조한다. v2 mutation 전에는 다음 rollback이 가능하다.

```bash
python3 tools/projectctl.py migrate rollback legacy-to-v2
```

v2 mutation 뒤에는 legacy authority로 되돌리지 않고 forward repair한다. 보존 기간과 복구 훈련이 끝나고, 실제 Project pilot에서 semantic parity와 새 workflow가 확인되기 전에는 legacy 원본을 삭제하지 않는다.

Migration 전 legacy Task lifecycle이 필요한 경우에만 `task activate|baseline|validate|handoff|audit|close`와 `promotion record`를 사용한다. V2 switch 뒤 legacy writer는 split-brain 방지를 위해 거부된다.

## 17. 문제 진단 순서

1. `python3 tools/projectctl.py check`
2. `python3 tools/projectctl.py show project`
3. 해당 `task show`와 `task review`
4. pending `decision show` 또는 `queue status`
5. `promotion show`의 base·diff·validation
6. 공식 worktree와 Task/integration worktree의 `git status`·diff
7. Git-local validation/run log
8. 필요할 때만 Hook raw event

대표 오류:

- `canonical record changed concurrently`: stale writer가 감지됐다. 최신 View를 다시 읽고 작업을 재시도한다.
- `stale Project revision` 또는 `stale Task revision`: preview 뒤 다른 amendment가 먼저 반영됐다. 새 View와 diff를 검토해 새 expected revision으로 다시 승인한다.
- `Task contract can only be amended`: 이미 실행 또는 review 단계다. 현재 결과를 보존하고 follow-up/replacement Task를 만든다.
- `official HEAD changed`: 기존 Promotion packet을 버리고 최신 HEAD에서 prepare한다.
- `managed replacements require`: dry-run replace와 backup을 검토한 뒤 최초 apply에 확인 flag를 사용한다.
- `symlink is not allowed` 또는 `Task path contains a symlink`: 실제 파일을 Project 안의 정상 경로로 옮긴다.
- `token limit exceeded`: 이미 사용량이 발생한 뒤의 ceiling 판정이다. 다음 Task scope/input/model을 줄인다.
- `interrupted`: 자동 resume하지 말고 process와 worktree부터 확인한다.

## 18. 최소 운영 체크리스트

Project 시작:

- trusted bundle과 dry-run 확인
- `check`, Project View와 최초 commit
- Hook 명령·trust 확인

Task 시작:

- bounded goal/scope/input/output/acceptance
- writer면 owned path와 validation
- Task contract commit 뒤 start 또는 enqueue
- Task View에서 requested contract 확인

계약 개정:

- Markdown proposal 또는 명시적 field로 preview
- before/after, reason, actor와 expected revision 확인
- Agent apply이면 실제 사용자 approval reference 기록
- apply 뒤 View·Git diff·`check`와 commit

Task 검토:

- summary, findings, limitations와 acceptance 연결
- changed paths·candidate·validation full log
- effective Codex contract와 fallback
- 필요한 Decision만 해당 Task에서 해결

Promotion:

- clean official base
- actual exact diff와 fresh validation
- candidate 선택 범위와 rollback/forward-repair 계획
- apply 뒤 official file, canonical Promotion과 `check`

Result:

- 실제 재사용 가치
- source/artifact와 reviewer
- verification·reusable·supersedes 상태
