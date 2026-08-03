# Final Assessment

## 결론

현재 하네스는 사용자의 핵심 의도에 맞게 구현됐다. 특히 Project별 독립 적용, Task 단위 격리, Codex structured handoff, 단순 queue와 병렬 background 실행, Task-local Decision, Result reference, exact-diff Promotion이라는 큰 방향은 적합하다. scheduler·lease·heartbeat·event ledger를 한꺼번에 도입하지 않은 선택도 타당하다.

다만 판정은 **“제한된 수동 파일럿 가능, trusted Project의 안정적 일상 운영 전 보완 필요”**다. 현재 우선순위는 고급 orchestration이 아니라 다음 네 경계를 닫는 것이다.

1. canonical v2 전체 상태를 실제로 검사하는 `check`.
2. symlink를 포함한 bundle·Promotion 파일 경로 containment.
3. current base·validation·actual diff를 한 승인 packet에 결속하는 Promotion.
4. canonical 동시 writer와 Result provenance·index consistency.

사용자가 직접 수행할 실험은 기존 Stage D에서 빠졌던 실제 사용자 관찰을 보충한다. disposable clone과 제한된 실행 계약을 사용하면 이 실험을 먼저 진행해도 된다.

## 사용자 의도 적합성

| 사용자 의도 | 현재 판정 | 근거와 남은 공백 |
| --- | --- | --- |
| 여러 큰 Task의 독립·병렬 진행 | 높음 | Project-local queue, dependency와 reader/writer limit, background worker가 구현됐다. crash 후 중복 방지는 아직 수동이다. |
| 사용자 작업과 Agent 작업의 공존 | 높음 | 한 Task의 `needs_decision/blocked`가 독립 Task를 막지 않는다. 실제 사용자 Decision 파일럿은 아직 없다. |
| 일부 Task의 무개입 Codex 실행 | 중상 | non-interactive adapter, structured output, timeout/cancel이 있다. token limit은 hard limit이 아니며 process tree·environment 경계가 약하다. |
| Project마다 독립 하네스 소유 | 높음 | `.harness`, queue와 runtime이 Project-local이고 중앙 registry가 없다. |
| Task 결과의 Project-level 승격과 재사용 | 중상 | Result index와 context ref가 있다. artifact digest·review provenance·index rebuild가 부족하다. |
| 중요한 결정의 사용자 통제 | 중상 | Task-local Decision과 Promotion이 있다. actual diff View와 validation/base freshness를 보강해야 한다. |
| 실패·중단에서 복구 가능 | 중간 | worktree와 evidence 보존, 수동 resume은 있다. 자동 orphan 판별은 없으며 Stage E로 보류하는 것이 맞다. |
| 문서 노이즈를 줄이고 핵심 흐름 유지 | 중상 | JSON authority와 generated View 방향은 적합하다. 현재 View가 일부 핵심 필드를 생략하고 legacy 안내와 혼재한다. |

## 사용자가 지금 실험할 수 있는 범위

### 사전 조건

- disposable local Linux/WSL clone을 사용한다.
- bundle은 이 저장소의 신뢰된 commit에서 직접 만든 것을 사용한다.
- 적용 전 dry-run 결과와 외부 backup을 보관한다.
- adapter는 `read-only` 또는 `workspace-write`, network-off를 사용한다.
- worker는 처음에는 foreground 또는 사용자가 PID와 log를 확인할 수 있게 실행한다.
- crash 후 자동/즉시 resume을 하지 않는다.
- Promotion 전 integration worktree의 실제 `git diff`를 별도로 읽는다.

### 최소 사용자 파일럿

| 순서 | 수행 | 사용자가 관찰할 것 | 통과 기준 |
| --- | --- | --- | --- |
| 1 | 새 Project에 bundle `apply` dry-run 후 적용 | 어떤 managed 파일이 add/replace되는지, 기존 파일 의미가 보존되는지 | 예상하지 않은 replace가 없고 apply 뒤 기본 check가 통과 |
| 2 | code 또는 document writer Task 1개 생성 | Task View만 보고 goal, scope, inputs, output, ownership, acceptance를 이해할 수 있는지 | 별도 원문 JSON을 읽지 않고 실행 계약을 설명 가능 |
| 3 | 독립 reader Task 2개와 writer Task 1개 queue | 시작 순서, 병렬성, writer 제한, 다른 작업을 계속할 수 있는지 | reader 병렬 실행, writer 경계 준수, 상태 이해 가능 |
| 4 | 한 Task에서 의도적으로 Decision 요청 | option, recommendation, impact가 충분한지, 다른 Task가 계속되는지 | 해당 Task만 대기하고 선택 후 명시적으로 재개 가능 |
| 5 | structured handoff review | findings, limitations, changed paths, validation이 충분히 보이는지 | 부모가 scope와 acceptance 충족 여부를 독립 판단 가능 |
| 6 | 작은 실제 candidate Promotion | actual diff, base, validation, 선택 범위가 명확한지 | 승인한 diff와 적용된 diff가 같고 결과가 main에만 반영 |
| 7 | Result 등록 후 새 Task에서 reference | 이전 결과를 찾고 신뢰도·한계를 이해할 수 있는지 | 해당 artifact와 source 근거를 혼동 없이 재사용 |
| 8 | cancel 또는 timeout 1회 | Task-local failure, worktree 보존, diagnostic, 다른 Task 진행 | 다른 Task는 계속되고 사용자가 안전한 다음 action을 판단 가능 |

crash/resume, symlink escape와 migration custom fixture는 안전성 engineering test이지 첫 사용자 경험 테스트의 필수 항목은 아니다. disposable fixture에서 별도로 실행할 수 있다.

### 피드백 기록 최소 항목

각 단계마다 아래 다섯 가지만 기록하면 다음 개선 우선순위를 정할 수 있다.

1. 완료 여부와 걸린 시간.
2. 추가로 원문 JSON이나 소스 코드를 읽어야 했는지.
3. 어떤 상태·명령·승인 대상을 이해하기 어려웠는지.
4. 예상과 실제 결과가 달랐는지.
5. 같은 작업을 다시 할 때 자동화하고 싶은 한 가지.

## 도입 가치가 있는 기능

### P0 — trusted Project 사용 전 core 보완

| 기능 | 해결하는 실제 요구 | 완료 조건 |
| --- | --- | --- |
| v2 full authority check | 손상된 canonical 상태를 `check passed`로 오인하지 않음 | 모든 record schema/digest/reference/index 손상 fixture가 실패 |
| resolved path containment | bundle·Promotion이 저장소 밖 파일을 읽거나 쓰지 않음 | source/target/parent symlink escape fixture 전부 거부 |
| Promotion freshness + diff packet | 사용자가 실제로 검증된 최신 diff를 승인 | HEAD/base drift 차단 또는 restage, 승인 직전 validation, 실제 diff View |
| canonical writer lock + revision CAS | 병렬 Task에서 Result/Decision/generation lost update 방지 | concurrent add/resolve에서 한 update도 유실되지 않음 |
| truthful execution contract | sandbox/network/tool/token 의미를 과신하지 않음 | 지원 불가 조합 거부, effective contract와 fallback human View |

### P1 — 파일럿 직후 편의성과 품질 개선

| 기능 | 사용자 가치 | 공통 적용 방식 |
| --- | --- | --- |
| Task·Review·Promotion packet | 무엇을 보고 판단할지 명확 | JSON authority를 유지하고 generated CLI/Markdown View 강화 |
| validation timeout·full evidence | hang 방지와 재현 가능한 실패 진단 | Project-local log artifact + digest + 짧은 summary |
| Result provenance/filter/rebuild | 과거 결과를 신뢰 가능한 범위에서 쉽게 재사용 | artifact digest, source/reviewer, simple filters, index rebuild |
| explicit context pack | prompt 과다·누락 감소 | file/line/result 선택, byte·token preview, pack digest |
| code/document/research profiles | 반복 지시 감소와 일관된 handoff | 작은 schema profile + Project-local scoped skills |
| interrupted diagnostic/cleanup | 자동 복구 없이도 안전한 재개 | process/worktree/diff/log packet과 명시적 cleanup candidate |

### P2 — Project가 선택하는 adapter

- 연구: Crossref/OpenAlex query manifest, DOI dedupe, inclusion/exclusion, claim–evidence table.
- 문서: local structure validator, lychee link check, 선택형 Vale style rule.
- 코드: validation discovery, opt-in pre-commit/CI bridge, 선택형 JUnit/SARIF export.
- 호스팅: GitHub dependency review, push protection, code scanning 연동.

이 기능들은 bundle이 도구를 강제 설치하지 않는다. capability probe가 설치 여부를 보여주고 Task가 명시적으로 선택할 때만 실행한다.

### P3 — 관찰 근거가 생길 때만

- Tree-sitter 기반 범용 symbol context.
- Result index의 SQLite FTS5.
- native Windows/NFS 지원.
- lease, heartbeat, PID adoption, attempt fencing, orphan 자동 복구와 retry.

Stage E는 worker crash 후 실제 orphan overlap이 반복되거나, 무인 장시간 운용이 필수라는 지표가 생길 때만 진입한다. 그 전에는 diagnostic과 수동 resume 경계를 유지한다.

## 역할별 책임

```text
Deterministic tools
  schema/digest/reference/path 검사, diff, validation, timeout, log와 index
        ↓ evidence
Task Agent
  코드·문서 작성, 연구 해석·검색·종합, handoff와 한계 작성
        ↓ structured handoff
Parent Agent
  scope·ownership·acceptance·근거 검토, 결과 통합, candidate 선정
        ↓ only material choices
User
  목표·범위·비용·권한 확대, 유효 대안 선택, 위험한 공식 반영
```

hooks는 관찰 장치, skills는 반복 작업 절차, workflow는 위 단계 연결, Codex adapter는 실행 계약의 실제 CLI 전달과 structured evidence 회수만 담당한다. 같은 책임을 여러 위치에서 중복 강제하지 않는다.

## 최종 권고

1. 사용자는 위 제한 조건으로 수동 파일럿을 수행한다.
2. 파일럿과 병행하지 않고 그 결과를 받은 뒤, P0 correctness/security 보완을 첫 Engineering 묶음으로 계획한다.
3. P1은 human review packet과 validation/Result provenance를 먼저 구현하고, 세 Task profile을 작은 vertical slice로 검증한다.
4. P2 provider/tool은 실제 적용 Project에서 필요할 때 opt-in한다.
5. P3와 Stage E는 현재 보류를 유지한다.

이 권고는 중앙 Project registry나 외부 orchestration service를 추가하지 않는다. 각 적용 Project가 자신의 `.harness`, 선택한 skills/adapters와 상태를 계속 독립 소유하며, Harness Engineering 저장소는 공통 bundle·template·version을 제공한다.
