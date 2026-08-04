# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

생성 뒤 고칠 수 없던 v2 Project·Task canonical 계약에 controlled amendment를 추가했다. 사용자는 명시적 field 또는 사람이 편집한 Markdown proposal로 before/after를 preview하고, current revision·reason·actor를 지정해 apply할 수 있다. Agent apply에는 실제 사용자 승인 참조가 필수다.

V2 context도 legacy `PROJECT.md`·`STATE.md`가 아니라 canonical JSON을 읽도록 수정했다. 따라서 직접 편집한 proposal은 apply 전 운영 상태를 바꾸지 않으며, apply 뒤에는 새 revision이 모든 Agent context에 일관되게 반영된다.

## Final Goal and Result

목표를 달성했다.

- `project amend`가 goal, scope, current objective, invariants와 canonical roots를 preview/apply한다.
- `task amend`가 core Task 계약, bounded input과 Codex execution contract를 preview/apply한다.
- `show project`와 `task show` 출력은 Project 안의 Markdown proposal로 저장·편집·import할 수 있다.
- Apply는 expected revision, reason과 actor를 요구하고 stale revision과 no-op을 거부한다.
- Agent actor에는 `approval_ref`가 필수이며 user actor와 구분해 canonical record에 마지막 변경 근거를 남긴다.
- Task amendment는 `ready|needs_decision|blocked`에서만 허용하고 active·review·완료 Task의 의미 변경을 차단한다.
- Project/Task View와 `context`가 revision과 마지막 amendment를 보여준다.
- 공용 README, GUIDE, STRUCTURE, AGENTS와 Project/Task Skill의 책임·절차를 새 흐름과 일치시켰다.

## Findings

- 생성 뒤 계약을 영구 불변으로 두는 것보다 controlled mutation을 제공하는 것이 장기 Project의 실제 요구와 맞는다.
- Markdown 자체를 authority로 되돌리면 다중 writer와 schema 검증이 약해진다. Markdown은 proposal, sealed JSON은 authority로 분리하는 편이 사람이 직접 편집하는 경험과 일관성을 함께 보존한다.
- Decision은 실행 중 선택, Promotion은 산출물 반영, amendment는 계약 변경으로 책임을 분리해야 중복과 승인 noise가 줄어든다.
- 모든 amendment를 별도 append-only ledger로 만들 필요는 없다. 최신 provenance는 record에, 전체 역사는 Git에 맡기는 최소 구조가 충분하다.
- 기존 v2 `context`가 legacy Markdown을 읽어 canonical 상태와 다를 수 있던 실제 결함도 함께 확인해 수정했다.

## Work and Validation

- 초기 Engineering baseline: `f2a78a2d01032906ac3a378727997d44a5f4b48b`.
- 구현 commit: `842939d2eae1bfeacb56f6b12de934910f80b606`.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: 57개 통과.
- `python3 project/tools/projectctl.py --root . check`: 통과.
- `python3 project/tools/projectctl.py --root project check`: 통과.
- `python3 -m py_compile project/tools/project_harness/*.py tools/harnessctl.py`: 통과.
- `git diff --check`: 통과.
- 실제 bundle package → 새 v2 Project → Project preview/apply → Task 생성 → Agent approval-ref Task apply → canonical Task context → full check smoke test: 통과.
- 회귀는 Markdown proposal, preview 비변경, stale revision, Agent approval-ref 누락, execution patch의 owned path 보존과 active Task 변경 차단을 포함한다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| `output/amendment-contract.md` | 설계 계약 | amendment 책임 경계, human workflow, 안전 속성과 알려진 한계 |

## Limitations

- `actor`와 `approval_ref`는 로컬 provenance이며 사용자 신원 인증이나 전자서명이 아니다.
- Task Markdown proposal은 사람이 읽는 core 계약만 import한다. Input과 Codex execution contract는 명시적 CLI option을 사용한다.
- active·review·completed·stopped Task는 retroactive amendment를 허용하지 않는다. 후속 또는 replacement Task가 필요하다.
- 최신 amendment만 canonical record에 포함하며 전체 이력은 Git에 의존한다.
- 기존 적용 Project는 Harness Engineering이 중앙에서 찾아 갱신하지 않는다. 사용자가 해당 경로에 새 bundle update를 명시해야 한다.

## Project Follow-up

1. 사용자가 실제 Project에서 `show > Markdown proposal > preview > apply > check > commit` 흐름을 수행하고 View와 option 명칭의 이해도를 평가한다.
2. 기존 적용 Project에는 새 version bundle을 dry-run한 뒤 사용자가 명시적으로 update한다.
3. 실제 운영에서 인증된 actor 증명이 필요해질 때만 서명 또는 외부 identity adapter를 별도 Engineering Task로 검토한다.
4. 실행 중 Task의 목표 변경 요구가 반복되면 stop/replacement lifecycle을 먼저 설계하고 active mutation은 도입하지 않는다.
