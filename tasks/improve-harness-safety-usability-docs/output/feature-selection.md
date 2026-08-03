# Feature Selection

## 선택 기준

이전 review의 모든 후보를 그대로 구현하지 않고 다음 순서로 다시 평가했다.

1. 기존 Rules, Task contract, Skill, Hook, workflow, Result 중 같은 책임을 이미 맡는 요소가 있는가.
2. 기능이 독립 Task의 병렬 진행이나 중요한 사용자 판단 흐름을 불필요하게 막는가.
3. 기본 context, 문서, 상태 record와 운영 명령에 반복 정보나 선택지를 과도하게 늘리는가.
4. 여러 Project에서 반복되는 문제를 결정론적으로 줄이는가.
5. 기능을 제거하거나 opt-in으로 남겼을 때 핵심 workflow가 계속 완전한가.

## 최종 도입

| 기능 | 기존 기능과의 관계 | workflow 영향·noise 판단 | 최종 책임 |
| --- | --- | --- | --- |
| v2 full authority check | 기존 `check`의 선언된 책임을 실제 canonical JSON까지 완성 | 새 상태나 사용자 단계를 만들지 않고 false success를 제거 | `projectctl check`가 schema, digest, internal refs, Result index와 artifact를 전수 검사 |
| resolved path containment | 기존 lexical `safe_relative`를 대체·보강 | 정상 경로에는 추가 단계가 없고 symlink escape만 차단 | bundle installer와 Task/Promotion file boundary의 공통 deterministic guard |
| 최초 managed replace 확인 | 기존 dry-run을 실질적 사용자 checkpoint로 완성 | 기존 Project 최초 적용에만 한 번 명시 확인; 일상 update에는 추가 질문 없음 | `harnessctl apply --accept-managed-replace` |
| canonical lock + revision CAS | SQLite queue나 event ledger와 겹치지 않고 JSON writer만 보호 | 짧은 mutation만 직렬화해 병렬 validation/Codex 실행은 유지 | Project-local lock과 exact revision replace |
| Promotion freshness·diff View | 기존 exact-diff Promotion의 핵심 보증을 완성 | prepare/approve/apply 단계 수는 유지; actual diff와 최신 validation만 추가 | base pin, approve/apply validation, task digest, human diff packet |
| bounded validation evidence | 기존 validation command 실행을 보강 | 명령별 timeout과 Git-local full log만 추가해 canonical 문서 noise를 제한 | deterministic runner + digest + short View |
| human Task/handoff/Promotion View | JSON authority와 중복 원본을 만들지 않고 generated View를 완성 | 원본 JSON을 읽는 비용을 줄이며 새 상태를 만들지 않음 | `task show`, `task review`, `promotion show`, `result show` |
| Result provenance/filter/rebuild | 기존 최소 Result index를 확장하되 graph로 바꾸지 않음 | artifact metadata와 단순 filter만 추가; FTS/graph noise 없음 | Result record, compact index, `result list/rebuild` |
| truthful Codex contract | 기존 adapter contract의 표현을 실제 enforcement에 맞춤 | 지원 불가 조합을 조기 거부하고 오해를 줄임 | requested/effective contract View, hard/CLI/policy/post-run 경계, process-group 종료 |
| 통합 문서 흐름과 root README | 흩어진 GUIDE/STRUCTURE/README 책임을 정리 | v2 기본 흐름과 legacy 부록을 분리해 중복 설명 감소 | root README=Engineering 저장소, Project README=적용 Project 입문, GUIDE=실행 절차, STRUCTURE=책임·상태 모델 |

Canonical lock은 긴 validation이나 Codex turn을 감싸지 않는다. 그렇지 않으면 한 Task의 submit/Promotion이 다른 독립 Task의 canonical handoff를 막으므로, 긴 작업은 lock 밖에서 수행하고 마지막 짧은 compare-and-write만 잠근다.

## 기존 기능에 통합하고 별도 기능으로 만들지 않음

| 후보 | 판단 | 통합 방식 |
| --- | --- | --- |
| code/document/research Task profiles | 별도 schema·Skill 세 개는 현재 Task contract와 `run-task-workflow` 역할을 반복하고 generic checklist를 모든 Project에 노출한다. | GUIDE에 Task 유형별 계약 예시와 검증 책임을 두고 실제 Project가 반복성을 확인했을 때 scoped Skill로 승격 |
| explicit context pack | bounded `--input`과 `context-ref`가 이미 최소 pack 역할을 한다. 별도 manifest는 같은 digest·path를 중복 저장한다. | Task View에 input·context·size·digest를 완전하게 표시; line/symbol selection은 관찰 후 확장 |
| interrupted diagnostic | queue status, worktree, run evidence와 안내가 분산돼 있지만 자동 복구와는 분리할 가치가 있다. | 이번에는 GUIDE의 수동 진단 순서를 명확히 하고 별도 runtime record는 만들지 않음 |
| pre-commit/CI bridge | validation command와 역할이 겹친다. 모든 Project에 hook dependency를 강제하면 설치 시간과 기존 config 충돌이 생긴다. | Project가 이미 pre-commit/CI를 쓰면 동일 validation argv를 호출하도록 문서화 |
| research provider adapter | Crossref/OpenAlex는 연구 Project에 유용하지만 API key·비용·license와 query schema가 일반 코드 Project에는 noise다. | `research` Task의 artifact/result 규칙만 공통 제공하고 provider는 적용 Project의 opt-in Skill/MCP로 둠 |
| link/style checker | Markdown 구조 검사는 기존 `check` 책임과 일부 겹치고 external link/style은 언어·network 정책에 따라 다르다. | local 필수 section은 core check, lychee/Vale 등은 Task validation command로 opt-in |
| SARIF/JUnit export | canonical validation evidence와 다른 책임인 외부 도구 교환 형식이다. | canonical 원본으로 채택하지 않고 필요한 CI adapter가 export |

## 보류

- Tree-sitter symbol context: grammar와 언어별 유지비가 있고 bounded input 누락 지표가 아직 없다.
- SQLite FTS5: Result 수가 작고 simple filter로 충분하다.
- native Windows/NFS: 현재 runtime의 `fcntl`, worktree와 SQLite 전제가 local POSIX다.
- bundle signing: 현재 신뢰된 local bundle 배포에는 commit·manifest·checksum을 우선 사용한다.
- lease, heartbeat, PID adoption, fencing, orphan 자동 복구, mutation retry: Stage E 진입 조건이 충족되지 않았다.
- append-only event ledger와 범용 evidence graph: 현재 current-state queue와 compact Result index에 비해 복잡성이 크다.

## 다시 검토할 관찰 조건

- 같은 Task 유형의 계약·review 지시가 세 Project 이상에서 반복되면 scoped profile/Skill 후보로 전환한다.
- Result가 약 100개를 넘고 simple filter로 원하는 결과를 찾지 못하는 사례가 반복되면 FTS를 검토한다.
- line/symbol 선택 없이 context limit 초과 또는 누락이 반복되면 deterministic context pack과 Tree-sitter adapter를 검토한다.
- worker crash 뒤 살아 있는 Codex process와 새 attempt가 실제로 겹치면 Stage E의 process identity와 fencing부터 검토한다.
- bundle을 제3자 release channel로 배포하면 signature와 provenance policy를 검토한다.
