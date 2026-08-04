# Project

이 저장소에는 큰 목표를 독립 Task로 나누고, 사용자·부모 Agent·Codex Task가 함께 수행하며, 검토된 결과만 공식 자산으로 반영하기 위한 로컬 Project 하네스가 설치돼 있다.

이 README는 사람을 위한 입문 문서다. Agent는 새 세션이나 컨텍스트 압축 뒤 `python3 tools/projectctl.py context`의 bounded output을 운영 상태로 사용한다.

## 이 Project에서 관리하는 것

- `PROJECT.md`: 쉽게 바뀌지 않는 Project Goal과 Scope
- `.harness/project.json`: v2 authority에서의 canonical Project 목표와 현재 objective
- `.harness/tasks/`: Task 계약과 현재 상태
- `.harness/decisions/`: 사용자 선택이 필요한 Task-local 요청과 해결 결과
- `.harness/results/`: 검토된 실험·실패·review·결정·재사용 asset의 최소 index
- `.harness/promotions/`: 공식 반영된 Promotion 근거
- `src/`, `tools/`, `data/`, `docs/`: 검토를 통과한 공식 Project 자산

queue, Codex run, validation full log와 승인 전 Promotion packet은 Git-local runtime이다. 다른 중앙 하네스 저장소가 이 Project를 등록하거나 상태를 수집하지 않는다.

## 첫 확인

새 Project는 생성 시 v2 authority가 초기화된다. 최초 commit 전후에 다음을 확인한다.

```bash
python3 tools/projectctl.py check
python3 tools/projectctl.py show project
git status --short
```

`show project`의 Goal과 Scope가 의도와 다르면 Task를 시작하기 전에 `project amend`로 preview하고 수정한다. `.harness/*.json`을 직접 편집하지 않는다. 설치된 Hook은 fail-open 관찰 장치이므로 `.codex/hooks.json`과 `.codex/hooks/observe.py`를 직접 검토하고 Codex `/hooks`에서 신뢰 상태를 확인한다.

## 일반 작업 흐름

```text
Project goal
  → bounded Task contract
  → isolated worktree 또는 Codex adapter 실행
  → structured handoff + deterministic validation
  → parent Agent review
  → 필요한 경우 Task-local Decision
  → 사용자가 actual diff·base·validation 검토
  → selected Promotion만 official branch에 반영
  → reusable Result만 최소 index에 기록
```

Task 하나가 `needs_decision` 또는 `blocked`가 되어도 dependency가 없는 다른 Task는 queue에서 계속 실행할 수 있다. `succeeded`는 handoff가 회수됐다는 의미이지 품질 승인이나 공식 반영이 아니다.

## 가장 작은 v2 Task 예시

```bash
python3 tools/projectctl.py task create update-parser \
  --goal "Parser 오류 처리를 개선한다" \
  --scope "src/parser.py와 관련 test만 변경" \
  --input src/parser.py \
  --output src/parser.py \
  --acceptance "관련 test가 통과한다" \
  --owned-path task-output \
  --validation-command "python3 -m unittest tests.test_parser"

git add .harness
git commit -m "task: create update-parser"
python3 tools/projectctl.py task show update-parser
python3 tools/projectctl.py task start update-parser
```

사람이 worktree에서 작업해 typed handoff를 제출하거나, Task에 `--codex` 실행 계약을 추가해 `task run` 또는 queue worker로 실행할 수 있다. 전체 명령과 handoff 형식은 `GUIDE.md`에 있다.

## 생성 후 목표와 Task 계약 수정

Project와 Task는 생성 뒤에도 고칠 수 있다. `show project` 또는 `task show`를 Project 안의 Markdown proposal로 저장해 사람이 직접 편집한 다음 `project amend --from-markdown` 또는 `task amend --from-markdown`으로 preview한다. 실제 반영은 현재 revision, 변경 이유, actor와 `--apply`를 명시할 때만 일어난다.

Agent가 적용할 때는 사용자 승인 메시지나 해결된 Decision을 `--approval-ref`로 기록해야 한다. 이는 인증 수단이 아니라 Git과 함께 검토하는 provenance다. ready·needs_decision·blocked Task만 개정할 수 있으며 active·review·완료 Task의 계약은 실행 중 몰래 바꾸지 않는다. 상세 예시는 `GUIDE.md`의 생성 후 계약 개정 절차를 따른다.

## 사람과 Agent의 책임

| 주체 | 책임 |
| --- | --- |
| deterministic tool | schema·digest·reference·path 검사, worktree, validation, diff, 상태 전이와 index |
| Task Agent | 계약 범위 안의 코드·문서·연구 결과, findings·limitations와 candidate 작성 |
| 부모 Agent | scope·ownership·acceptance·근거·validation 검토와 candidate 선택 |
| 사용자 | 목표·범위·비용·권한 확대, 상충하는 대안, 외부 변경과 공식 Promotion 판단 |

Rules는 지속 제약, Skills는 사용자가 명시 호출하는 반복 절차, Hooks는 관찰, `projectctl`은 결정론적 workflow, Codex adapter는 CLI 실행 계약과 structured handoff 회수를 담당한다.

## 안전한 기본값

- 새 Task input은 명시된 UTF-8 file과 digest로 고정한다.
- Codex는 `read-only` 또는 `workspace-write`, network-off를 우선한다.
- `danger-full-access`는 network-off 보안 계약으로 사용하지 않는다.
- `allowed_tools`의 shell/apply_patch는 Agent policy이지 OS-level allowlist가 아니다.
- wall-time은 hard limit이고 token ceiling은 완료 뒤 usage로 판정한다.
- 실제 Promotion 전에 `promotion show`의 exact diff와 validation을 읽는다.
- interrupted job은 잔존 process와 worktree를 확인한 뒤에만 명시적으로 resume한다.
- 검증되지 않았거나 superseded/rejected인 Result를 자동 context로 주입하지 않는다.

## 문서 안내

- `GUIDE.md`: 설치·migration·Task·Codex·queue·Decision·Result·Promotion의 실행 절차
- `STRUCTURE.md`: authority, 구성 요소 책임, 상태와 격리 모델
- `AGENTS.md`: Project Agent가 지속적으로 지킬 규칙
- `tasks/_template/`: legacy-compatible 수동 Task 문서 template
- `docs/adr/`: 장기 구조 결정
- `docs/history/`: Task 종료와 Promotion 사건의 짧은 기록

문제 발생 시 전체 문서를 순회하기보다 `projectctl check`, 해당 `task show/review`, `decision show`, `promotion show`, `queue status`와 Git diff 순서로 확인한다.
