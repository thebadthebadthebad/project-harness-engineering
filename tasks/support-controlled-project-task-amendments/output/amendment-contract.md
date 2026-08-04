# Controlled Amendment Contract

## Problem

v2 canonical JSON은 여러 Agent가 같은 Project와 Task 의미를 읽게 하지만, 생성 뒤 목표·범위·실행 계약을 공식적으로 바꿀 mutation이 없었다. `PROJECT.md`나 generated Task View를 고쳐도 canonical record에는 반영되지 않았고, JSON 직접 편집은 digest·revision과 변경 근거를 깨뜨렸다.

## Adopted Boundary

- 일반 코드와 제품 문서는 Project Git 규칙 안에서 직접 편집한다.
- Project/Task canonical 계약은 `project amend`와 `task amend`만 변경한다.
- Markdown은 사람이 편집하는 proposal이며 authority가 아니다.
- Preview는 before/after, current revision과 digest를 보여주며 state를 변경하지 않는다.
- Apply는 preview의 current revision, reason, actor를 요구한다.
- `actor=agent`는 실제 사용자 메시지·issue·해결된 Decision 같은 `approval_ref`가 필수다.
- Approval reference는 provenance이지 인증이나 전자서명이 아니다.
- Task amendment는 `ready|needs_decision|blocked`에서만 허용한다. 실행·review·완료 상태는 follow-up 또는 replacement Task로 다룬다.

## Non-overlap

- Decision: 실행 중 가치 판단이나 권한·범위 확대 선택을 해당 Task에서 대기시킨다.
- Promotion: Task 후보 산출물의 exact diff를 공식 branch에 반영한다.
- Amendment: Project 목표나 Task 실행 계약 자체를 revision CAS로 바꾼다.

Amendment는 별도 event ledger나 범용 approval 시스템을 만들지 않는다. 최신 provenance만 canonical record에 남기고 전체 변경 이력은 Git이 담당한다.

## Human Workflow

```text
show Project/Task
→ Project 안에 Markdown proposal 저장
→ 사람이 필요한 section 편집
→ amend preview
→ before/after와 expected revision 검토
→ 사용자 직접 apply 또는 사용자 승인 참조를 가진 Agent apply
→ show/context/check와 Git diff
→ canonical 변경 commit
```

## Safety Properties

- Canonical JSON 직접 편집 불필요
- Project-local writer lock과 exact revision/digest CAS
- stale revision과 no-op 변경 거부
- Agent amendment의 approval reference 누락 거부
- Project-contained non-symlink proposal만 허용
- active/review/completed/stopped Task 계약 변경 거부
- v2 context는 stale `PROJECT.md`·`STATE.md`가 아니라 canonical record만 사용

## Known Limits

- `actor`와 `approval_ref`는 로컬 attribution이며 사용자 신원을 인증하지 않는다.
- Markdown Task proposal은 core contract section만 import한다. Input과 Codex execution contract는 명시적 CLI option으로 개정한다.
- 이미 실행된 Task의 contract를 retroactively 바꾸지 않는다.
- 별도 append-only amendment ledger는 만들지 않았으며 Git commit이 장기 이력을 보존한다.
