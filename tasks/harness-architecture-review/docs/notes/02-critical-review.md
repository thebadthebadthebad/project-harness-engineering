# 현 구조 강한 비판

## 관점과 결론

현재 하네스는 소수 Task를 순차 수행하고 사용자가 매 lifecycle checkpoint를 조작하는 경우에는 작동한다. 그러나 Task 수와 동시성이 커지면 격리·통일성·저노이즈가 schema가 아니라 문서 규율과 수동 절차에 의존한다. 사용자의 대형 프로젝트 의도에는 핵심 구조 보강이 필요하다.

## 구조적 불일치

1. Task context는 Project 전체 노이즈를 피하는 대신 Goal, 공통 불변조건, 용어, interface, 적용 결정까지 함께 잃는다.
   - Task가 따라야 할 작은 Project Kernel과 선택된 canonical reference가 필요하다.

2. `STATE.md`는 Task 이름과 상태만 표현하며 의존성, 충돌 영역, 통합 순서, review queue가 없다.
   - completed Task를 Current Goal 동안 유지하면 장기 Goal에서 기본 context가 계속 증가한다.

3. pending handoff는 작은 승계 패킷이 아니라 길이 제한 없는 REPORT다.
   - 여러 Task가 동시에 끝나면 Project bootstrap context가 REPORT 수와 길이에 비례한다.
   - 결정·관찰·재사용 코드라는 사용자의 승계 단위가 schema에 없다.

4. Task 독립성은 권한 격리가 아니라 공유 worktree의 사후 audit다.
   - 두 active Task가 다른 Task 디렉터리를 변경해도 상대 audit에서는 경계 밖 변경이 된다.
   - 병렬을 지원하려면 worktree/branch가 필요하고, 지원하지 않으면 active Task 하나만 강제해야 한다.

5. Task STATUS와 Project STATE의 이중 상태는 handoff 대기를 의도적 불일치로 표현한다.
   - `draft → ready → active → review → closed` 같은 단일 authoritative phase가 더 명확하다.

6. Promotion 기록은 Task source artifact, target, digest, 검증, integration commit을 연결하지 않는다.
   - 재현·감사 가능한 append-only Promotion event가 필요하다.

## Workflow 실패 모드

- baseline을 다시 저장할 수 있으면 감사 기준이 앞으로 이동할 수 있다. 최초 생성은 immutable하게 하고 rebaseline은 별도 사용자 승인 사건으로 다뤄야 한다.
- 역할 분리는 full-access 실행과 환경변수 기반 guard에 의존하므로 보안 경계가 아니다. 신뢰 기반 workflow mode라는 표현을 유지해야 한다.
- 사람이 create, 문서 편집, validate, activate, commit, baseline, session switch, handoff, audit, close, commit, Promotion, record를 기억해야 한다. 사용자 상호작용과 기계적 반복 작업을 구분해 후자는 묶을 필요가 있다.
- Markdown heading/TBD 중심 형식 검사는 실제 운영 계약, enabled feature, Promotion 경로와 evidence linkage를 충분히 검증하지 못한다.

## Directory와 문서 문제

- Engineering root와 배포 `project/`는 유사 문서, Task template, Codex 설정과 Hook을 중복 보유한다. 수동 Promotion에 의존하면 drift와 bootstrap 결합이 생긴다.
- 모든 Task에 `scripts`, `data`, `docs/research`, `docs/notes`, `output`을 강제하여 간단한 문서/조사 Task에도 빈 구조가 누적된다.
- code snapshot 복사는 source commit, patch identity, merge base가 없는 수동 fork가 된다. 여러 Task가 같은 파일을 복사하면 통합 충돌도 사전에 드러나지 않는다.
- active/completed/stopped Task가 한 평면 `tasks/`에 계속 누적되어 저장소 탐색 노이즈가 커진다.

## 핵심 문서 평가

- `PROJECT.md`: Goal/Scope만으로는 대형 Project의 non-goal, invariant, domain vocabulary, compatibility policy가 부족하다.
- `STATE.md`: active state, review queue, dependency를 표현하기에 너무 단순하고 completed 기록까지 섞는다.
- `STRUCTURE.md`와 `GUIDE.md`: 아키텍처, 상태, 명령, 보안, runbook이 중복된다.
- `AGENTS.md`: 지속 작업 원칙과 runtime/lifecycle 세부가 섞여 있다.
- `TASK.md`: immutable Goal이 `STATUS.md`에 분리되고 dependency, inherited Project Kernel, integration target, open question이 없다.
- `STATUS.md`: Work Plan 표와 Current Work 문자열을 수동 동기화하는 micromanagement 비용이 있다. 이 Task에서 병렬 subagent 세 개를 실행했지만 정확히 하나의 doing만 허용한 것이 실제 예다.
- `REPORT.md`: Task 회고와 Project 승계 패킷이 섞이고 섹션 중복과 길이 제한 부재가 있다.
- `docs/AGENTS.md`: ADR/History 구분은 타당하지만 종료와 Promotion 사건은 별도 append-only event여야 한다.
- `data/AGENTS.md`: 유용하지만 데이터가 없는 Project에도 고정 배포되는 점은 선택 기능 관점에서 재검토할 수 있다.

## Skill, Hook, subagent

- 현재 Skill은 대부분 AGENTS/GUIDE의 lifecycle 명령을 반복한다. 유지한다면 Task 분해·질문 구성·handoff 축약처럼 상호작용을 돕는 기능으로 재정의해야 한다.
- 모든 Pre/PostToolUse에 Hook을 실행하지만 coarse metadata만 생성하고 정확성이나 보안을 보장하지 않는다. 일반 Project 핵심 기능이 아니라 opt-in diagnostics 후보로 볼 수 있다.
- read-only research/verification agent만으로는 사용자가 허용하려는 Task 분해, 문서 초안, 요구 구체화 지원을 충족하지 못한다.
- 부모가 사용자 상호작용과 통합 책임을 유지하고, decomposition planner, researcher, document drafter, verifier를 승인된 범위와 비용 한도 안에서 사용할 수 있어야 한다.

## 재설계 후보

```text
PROJECT.md
  goal / non-goals / invariants / domain contracts

.harness/state.*
  active tasks / phase / dependencies / review queues

tasks/<task>/
  TASK.md
  HANDOFF.md
  work/                  # 필요할 때만

docs/adr/
docs/history/            # append-only close/promotion events
```

- `STATUS.md`의 상세 Work Plan을 제거하거나 machine state + optional checkpoint로 축소한다.
- 상세 Task 보고서와 compact HANDOFF를 분리한다.
- completed Task를 active state와 기본 context에서 즉시 제거한다.
- code snapshot 대신 Task worktree/branch 또는 source commit 기반 patch를 사용한다.
- root/public template의 canonical source를 하나로 만들고 배포물은 생성·검증 결과로 취급한다.
- Hook과 단순 wrapper Skill은 opt-in bundle 또는 상호작용 도우미로 재배치한다.

## 우선순위와 위험

### P0

1. 순차 단일 active Task 또는 worktree 기반 병렬 지원 중 하나를 명시적으로 선택한다.
2. 단일 Task phase와 active/review/archive queue를 설계한다.
3. Project Kernel과 compact typed handoff를 만든다.
4. Promotion source/target/digest/commit provenance를 구현한다.

### P1

1. Engineering source와 public template 중복을 생성 기반 단일 source로 바꾼다.
2. STRUCTURE/GUIDE/CLI help의 책임을 분리한다.
3. manifest에 선언된 기능 전체를 검사하도록 `check`를 강화한다.

### P2

1. Hook/observability를 opt-in diagnostics로 이동한다.
2. lifecycle wrapper Skill을 제거하거나 상호작용 Skill로 재작성한다.
3. 제한된 planning/writing subagent를 추가한다.

상태·worktree·배포 source를 한 번에 바꾸면 migration 위험이 크다. compact handoff와 context queue부터 독립적으로 검증한 뒤, 동시성 요구가 확인되면 worktree 전환을 수행하는 순서가 필요하다.

## 근거

- `project/PROJECT.md`
- `project/STATE.md`
- `project/STRUCTURE.md`
- `project/GUIDE.md`
- `project/AGENTS.md`
- `project/tasks/_template/{TASK,STATUS,REPORT,AGENTS}.md`
- `project/.agents/skills/manage-project-workflow/SKILL.md`
- `project/tasks/_template/.agents/skills/run-task-workflow/SKILL.md`
- `project/.codex/hooks.json`
- `project/.codex/agents/*.toml`
- `experiments/RESULTS.md`
