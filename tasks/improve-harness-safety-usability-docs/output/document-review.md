# Document Review

## Review criteria

공용 template과 Harness Engineering root 문서를 다음 질문으로 검토했다.

- 적용 Project의 목적과 하네스의 목적이 혼동되지 않는가.
- 사람과 Agent가 서로 다른 세션·컨텍스트에서도 같은 authority와 현재 상태를 찾는가.
- new/apply/update, Task, Codex, queue, Decision, Result, Promotion과 migration의 순서가 실제 CLI와 일치하는가.
- 각 기능에서 무엇을 관찰하고 무엇을 승인하는지 알 수 있는가.
- Rules, Skills, Hooks, workflow와 script가 같은 책임을 중복 설명하거나 서로 다른 보장을 약속하지 않는가.
- 실패·중단 시 안전한 다음 action과 자동화하지 않는 경계가 드러나는가.

## 확인된 문제와 개선

| 문서 | 기존 문제 | 개선 결과 |
| --- | --- | --- |
| root `README.md` | 저장소가 template을 관리한다는 한 문장과 파일 목록만 있어 Project 의도, 배포 경계, 기능, 개발·검증 절차를 이해하기 어려움 | 문제 정의, Project별 독립 소유, architecture, 기능·제외 범위, bundle new/apply/update, Engineering workflow, test, 안전 경계와 문서 지도를 포함한 저장소 입문으로 재작성 |
| `project/README.md` | `Project Introduction: TBD`와 legacy 중심 5단계만 있어 새 v2 Project 사용자가 다음 행동을 알기 어려움 | v2 authority, canonical/runtime 구분, 첫 확인, 최소 Task, 역할·안전 기본값과 문서 지도를 제공하는 적용 Project 입문으로 재작성 |
| `project/GUIDE.md` | v2 install/Task 설명 뒤에 legacy lifecycle 전체가 다시 시작해 authority와 명령이 혼재하고, actual diff·Result provenance·contract 한계가 충분히 설명되지 않음 | v2 기본 workflow를 설치→Task→Codex/queue→Decision→Result→Promotion 순으로 재작성하고 legacy를 migration 부록으로 분리. 각 단계의 관찰 View, 통과 조건과 장애 대응 추가 |
| `project/STRUCTURE.md` | manual full-access Task 설명과 v2 adapter/queue 모델이 동시에 일반 규칙처럼 서술됨. `check`, Promotion과 Result의 실제 보장보다 강하거나 오래된 표현 존재 | manual/legacy session과 v2 adapter를 분리하고 short canonical lock, full check, fresh Promotion, Result provenance와 구성 요소 책임을 현재 구현에 맞춤 |
| `project/AGENTS.md` | v2 기본 규칙은 대체로 적합하지만 symlink, full check 오류, reviewed Result와 stale Promotion 대응이 없음 | 지속 규칙에 path, canonical integrity, reviewer/evidence와 current base·fresh validation 경계만 추가 |
| Project Skill | Promotion과 Result 명령은 있으나 새 review·provenance 조건이 반영되지 않음 | 기존 explicit lifecycle Skill에 actual diff/base/log review와 Result rebuild·reviewer 규칙을 통합. 새 Skill은 만들지 않음 |
| Task Skill·AGENTS | 모든 Task에 동일한 일반 수행 지시만 있어 코드·문서·연구의 품질 관점이 드러나지 않음 | 해당 Task 유형에 필요한 lens만 적용하고 별도 profile 문서를 반복 생성하지 않도록 기존 Skill·규칙에 최소 항목 통합 |
| `TASK/STATUS/REPORT` template | section과 lifecycle 계약은 도구 parser/test와 긴밀히 결합돼 있으며 역할은 명확함 | 형식을 바꾸지 않고 GUIDE와 Task 규칙에서 각 section의 작성·review 기준을 보강. 호환성 없는 template schema 확장을 피함 |
| `data/docs AGENTS` | 공식 자산과 Task 임시 근거의 경계를 적절히 설명 | 유지. 새 Result와 Promotion 절차는 상위 Guide/Rules가 담당해 중복 추가하지 않음 |

## 문서 책임의 최종 분리

```text
Harness Engineering README
  이 저장소가 왜 존재하고 template을 어떻게 개발·배포하는가

Applied Project README
  새 사용자가 이 Project에서 무엇을 먼저 확인하고 어떤 흐름을 따르는가

GUIDE
  실제 명령, 순서, 관찰 지점, 성공 조건과 장애 대응

STRUCTURE
  authority, 상태, 디렉터리, 구성 요소와 사람/Agent 책임

AGENTS
  모든 turn에 지속 적용할 짧은 제약

Skills
  사용자가 명시 호출하는 반복 checkpoint와 현재 Task 수행 절차
```

CLI View가 실제 상태를 보여주므로 GUIDE에 현재 Task 상태나 실행 결과를 중복 기록하지 않는다. README도 전체 명령 reference를 복제하지 않고 GUIDE로 연결한다.

## 워크플로우 관찰 가능성

문서와 View의 연결을 다음처럼 정리했다.

| 단계 | 사람이 보는 기본 View | 판단 또는 조치 |
| --- | --- | --- |
| 설치 | `harnessctl apply/update` dry-run JSON | create/preserve/replace/conflict와 최초 replace 확인 |
| Project | `projectctl check`, `show project` | authority 무결성, Goal·Scope 확인 |
| Task 계약 | `task show` | input/output/dependency/ownership/acceptance/validation/requested contract 확인 |
| Codex 실행 | `task review`, Git-local run evidence | findings/limitations/effective contract/fallback/usage 확인 |
| Queue | `queue list/status` | 병렬성, blocked/needs_decision/interrupted와 다음 action |
| Decision | `decision show` | option·권고·영향·safe default를 보고 해당 Task만 resolve |
| Result | `result list/show`, `result rebuild` | verification/reusable/reviewer/artifact digest와 index 일관성 |
| Promotion | `promotion show` | current base, validation/log, actual exact diff와 candidate 범위 승인 |
| 관찰 | `observe report` | Hook coverage와 lifecycle timeline; 완전 audit로 오인하지 않음 |

## 사람과 Agent가 잘못 수행하지 않도록 한 경계

- 새 v2 Project 사용자가 legacy `activate/baseline/close`를 일상 명령으로 사용하지 않도록 legacy 흐름을 부록으로 이동했다.
- interactive full-access session과 Task adapter의 `workspace-write`를 같은 sandbox로 설명하지 않는다.
- `allowed_tools`와 token ceiling이 강한 사전 제한이라는 표현을 제거했다.
- Queue `succeeded`, Task `completed`와 Promotion approval을 서로 다른 checkpoint로 유지했다.
- Result `verified`를 호출자 flag 하나로 신뢰하지 않고 reviewer와 실제 evidence를 요구한다.
- Promotion digest만 보여주지 않고 actual diff와 fresh validation을 검토하도록 했다.
- Hooks와 worktree/ownership을 보안 enforcement로 표현하지 않는다.

## 남은 한계

- 문서의 external link를 자동 검사하는 binary를 bundle에 강제하지 않았다. 필요 Project는 Task validation으로 opt-in한다.
- 사용자 실험에서 실제로 읽기 어려운 용어와 단계가 확인되면 README/GUIDE 분량을 다시 줄여야 할 수 있다.
- Legacy custom Markdown과 partial Task의 모든 의미를 문서만으로 자동 보존할 수 없다. Migration inventory가 별도로 필요하다.
- CLI JSON error와 generated Markdown의 한국어 localization은 이번 범위가 아니다.
