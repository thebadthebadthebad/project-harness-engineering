# Subagent Review Synthesis

## Review setup

사용자가 요청한 두 개의 독립 읽기 전용 review를 reasoning effort `high`로 수행했다.

| Reviewer | 관점 | 범위 |
| --- | --- | --- |
| `intent_fit_audit` | 사용자 의도·Project 성격 적합성 | Project별 독립성, Task 분해, 병렬·background 실행, Decision·Promotion, 결과 재사용, Stage A–D 증거 |
| `operational_risk_audit` | 운영·보안·복구 위험 | bundle 적용, migration, canonical state, worktree·Promotion, Codex contract, queue, hooks, portability |

두 reviewer 모두 파일을 변경하지 않았다. 주 Agent는 의견을 권위 있는 결론으로 취급하지 않고 코드·테스트·기존 파일럿 근거와 대조했다. 아래에서 `반영`은 현행의 결함 또는 명시해야 할 제한으로 채택한다는 뜻이며, 곧바로 구현을 승인한다는 뜻은 아니다.

## 종합 판정

현재 하네스는 사용자가 명시한 운영 모델에 **구조적으로 높은 적합성**을 보인다.

- 각 적용 Project가 `.harness`와 runtime을 독립 소유하고 중앙 registry가 없다.
- Project를 명시적 Task 계약으로 분해하고 worktree에 격리한다.
- Codex adapter, 단순 queue와 background worker가 독립 Task의 병렬 실행을 지원한다.
- 한 Task의 Decision이 다른 독립 Task를 막지 않는다.
- Result index와 context reference가 Task 결과의 Project-level 승격 경로를 제공한다.
- 사용자 통제는 Task 실행 중 반복 승인보다 Decision과 Promotion 경계에 집중된다.
- lease, heartbeat, PID adoption과 자동 mutation retry는 근거가 생길 때까지 Stage E로 보류됐다.

그러나 **안전한 장기 운영까지 완성됐다고 보기는 어렵다.** 가장 중요한 이유는 canonical v2 전체 검증, Promotion freshness와 실제 diff review, symlink 경계, 동시 canonical write, Result provenance가 충분히 닫히지 않았기 때문이다. 기존 Stage D는 실제 Codex reader 2개를 병렬 실행했지만 실제 writer Promotion, 사용자 Decision, crash/resume을 실행하지 않았다. 사용자가 수행할 이번 실험이 이 운영 증거의 첫 본격 보강이다.

## Review 의견 판정

### 즉시 반영한 핵심 의견

| 지적 대상 | 판정 | 독립 판단과 영향 | 권고 |
| --- | --- | --- | --- |
| v2 canonical `check` | 반영 · 높음 | `check_project()`는 구조와 legacy 문서는 검사하지만 authority가 v2이면 `.harness/**/*.json`의 schema, digest, index와 참조를 전수 검사하지 않는다. `check passed`를 canonical 무결성 증거로 사용할 수 없다. | Project·Task·Decision·Result·Promotion·index의 schema/digest/reference를 순회하는 full check와 손상 fixture를 추가한다. trusted Project 사용 전 수정 대상이다. |
| Promotion freshness와 review | 반영 · 높음 | `prepare` 때 validation을 실행하지만 `approve`는 diff만 새로 계산하고, `apply`는 official `HEAD == base_commit`을 확인하지 않는다. `promotion show`도 실제 diff와 validation 상세를 보여주지 않는다. | HEAD pin 또는 명시적 restage, 승인 직전 validation 재실행, diff 본문·명령·출력의 review packet, 부분 실패 복구 절차를 추가한다. |
| bundle 최초 적용 충돌 | 반영 · 높음 | 첫 `apply`는 managed 경로의 기존 `.codex`, `.agents`, `tools`, `tasks/_template` 등을 replace할 수 있다. dry-run이 있지만 기존 설정의 의미를 자동 병합하지 않는다. | 최초 적용은 dry-run plan 저장과 managed-path collision 확인을 필수 흐름으로 만들고, replace에 별도 명시 확인을 요구한다. 기존 저장소에서는 외부 backup 후 적용한다. |
| bundle·Promotion symlink 경계 | 반영 · 높음 | lexical relative-path 검사만으로는 source/target parent symlink가 저장소 밖을 가리키는 경우를 막지 못한다. parent process의 `copyfile/copy2`가 외부 파일을 읽거나 덮어쓸 수 있다. | resolved path containment와 symlink 거부를 공통 파일 연산 경계에 추가하고 benign escape fixture로 검증한다. security-sensitive Promotion 전 수정 대상이다. |
| canonical 동시 write | 반영 · 중상 | atomic file replace는 찢어진 파일을 막지만 stale read-modify-write에 의한 Result index·generation·Decision lost update는 막지 못한다. Stage C의 동시 작업 요구와 직접 관련된다. | 모든 canonical mutation에 하나의 Project-local writer lock과 revision compare-and-swap을 적용한다. 복잡한 event ledger는 필요 없다. |
| Codex contract의 실제 경계 | 반영 · 높음 | 기본 `workspace-write`, network-off는 합리적이지만 `danger-full-access + network_access=false`는 network 차단 계약이 아니다. `allowed_tools` 중 shell/apply_patch는 강한 실행 allowlist가 아니고, token limit은 실행 후 usage로 판정한다. | 지원 조합을 명시적으로 거부/경고하고, `allowed_tools`와 token limit의 이름·View를 실제 의미에 맞춘다. capability 결과와 effective argv를 review surface에 노출한다. |
| 실행 환경과 종료 | 반영 · 중상 | adapter는 부모 환경을 상속하고 timeout/cancel은 Codex PID를 대상으로 한다. secret-rich 환경과 descendant process 잔존 가능성이 있다. | 최소 environment allowlist/denylist, process-group 종료, JSONL 크기 제한, hard wall-time과 post-hoc token ceiling의 구분을 도입한다. |
| Result provenance·index 일관성 | 반영 · 중상 | artifact path는 존재와 digest를 확인하지 않고 `verified/reusable`은 호출자가 지정한다. record와 index가 별도 write여서 crash/concurrency 시 어긋날 수 있다. | artifact 존재·SHA-256·크기, source Task/handoff, reviewer/verification 근거를 기록하고 index rebuild/check 명령을 제공한다. |
| validation evidence | 반영 · 중상 | deterministic argv라는 장점은 있으나 command timeout이 없고 stdout/stderr 마지막 4,000자만 canonical handoff에 남는다. 검증이 무기한 걸리거나 진단 근거가 유실될 수 있다. | 명령별 timeout, 전체 Git-local log artifact와 digest, human summary를 추가한다. |
| 실제 사용자 파일럿의 부재 | 반영 · 높음 | Stage D는 실제 모델 vertical slice였지만 Decision 0건, Promotion candidate 0개였고 writer·cancel·crash가 관찰되지 않았다. | 이번 사용자 파일럿에서 최소 writer→review→Decision→Promotion과 병렬 reader를 직접 관찰한다. Stage D 완료 판정의 남은 증거다. |

### 부분 반영한 의견

| 지적 대상 | 판정 | 반영 범위 | 보류한 범위 |
| --- | --- | --- | --- |
| legacy semantic parity | 부분 반영 · 높음 | 표준 heading과 완전한 Task 3문서만 parity model에 포함되므로 독립 file inventory와 custom/partial Task fixture가 필요하다. | 범용 Markdown 의미 추론기는 만들지 않는다. 지원 형식을 명시하고 extension field 또는 수동 exception report로 처리한다. |
| Task 계약 필수성 | 부분 반영 · 중간 | 큰 Task profile에는 output, acceptance, ownership, validation 누락 경고가 유용하다. | 모든 작은 읽기 Task에 동일 필드를 강제하지 않는다. Task 유형·위험별 profile을 사용한다. |
| Decision resolve와 queue resume | 부분 반영 · 중간 | human View에 resolve 후 `queue resume`이 별도 단계임을 표시하고 동시 resolve CAS를 검증한다. | local single-user 기본에서 actor 인증 시스템은 우선순위가 낮다. 외부 협업·원격 승인 도입 시 다시 평가한다. |
| hooks completeness | 부분 반영 · 중간 | hooks는 fail-open 관찰 장치이고 log 누락은 무행동 증거가 아니라는 문구, hash review와 retention/redaction을 강화한다. | hooks를 보안 enforcement 또는 완전 event ledger로 승격하지 않는다. |
| cleanup·portability | 부분 반영 · 중간 | worktree/branch/runtime의 list와 안전한 GC, disk usage View를 운영 기능 후보로 둔다. 현재 지원 범위를 local Linux/WSL로 명확히 한다. | native Windows·NFS 호환성은 실제 대상 Project 요구가 있을 때 구현한다. |
| Result 검색 확장 | 부분 반영 · 중간 | 먼저 kind/status/reusable/text filter와 index rebuild를 추가한다. | 작은 index에 SQLite FTS나 범용 evidence graph를 즉시 추가하지 않는다. |
| 문서의 v2/legacy 혼재 | 부분 반영 · 낮음 | 신규 사용자 기본 흐름과 legacy migration 부록을 분리하면 인지 부담이 줄어든다. | 기능 안정성보다 앞서 대규모 문서 재편을 하지는 않는다. |

### 보류 또는 반영하지 않은 의견

| 제안 또는 암시 | 판정 | 근거 |
| --- | --- | --- |
| lease, heartbeat, PID adoption, orphan 자동 복구를 지금 구현 | 보류 | restart overlap은 실제 장애가 아니라 코드 검토 가설이며 사용자가 Stage E 보류를 명시했다. 파일럿에서는 crash 후 process tree 확인 전 resume 금지로 제한한다. 반복 사고 또는 무인 장시간 운용 지표가 생기면 fencing token부터 재검토한다. |
| append-only runtime ledger와 다중 record transaction 전면 도입 | 반영하지 않음 | 현재 문제는 단일 Project-local canonical writer lock, revision CAS, rebuild 가능한 index로 더 단순하게 완화할 수 있다. |
| 모든 bundle에 서명 인프라 도입 | 보류 | 신뢰된 local build artifact만 사용하는 현재 배포 모델에서는 출처·commit·manifest 기록으로 먼저 충분성을 시험할 수 있다. 외부 release channel이나 제3자 bundle을 배포할 때 서명을 재검토한다. |
| 모든 Task 필드를 무조건 필수화 | 반영하지 않음 | 읽기 전용 소규모 Task까지 계약 비용이 커진다. `reader`, `writer`, `research`, `document` profile별 최소 계약이 더 적합하다. |
| 모든 approval actor의 인증 | 보류 | 현재 범위는 local single-user Project다. actor는 감사 라벨이지 신원 보안 경계가 아니다. 원격·다중 사용자 승인 기능이 생길 때 필요하다. |
| 범용 evidence graph와 즉시 FTS5 | 반영하지 않음 | 현재 Result 규모와 사용자의 최소 결과 index 요구에 비해 복잡하다. 단순 filter와 provenance를 먼저 개선한다. |

## 코드 대조로 확인한 근거

- `project/tools/project_harness/lifecycle.py`의 `check_project()`는 v2 canonical record scan을 수행하지 않는다.
- `project/tools/project_harness/v2.py`의 `prepare_promotion()`, `approve_promotion()`, `apply_promotion()`은 validation freshness와 official base를 하나의 apply gate로 결속하지 않는다.
- 같은 파일의 `render_task()`는 outputs, dependencies, validation commands를 생략하고 `render_handoff_review()`는 findings와 limitations를 생략한다.
- `add_result()`는 artifact 상대경로만 검사하며 존재·digest·reviewer를 결속하지 않는다.
- `run_validations()`에는 timeout이 없고 출력은 끝 4,000자만 record에 남긴다.
- `project/tools/project_harness/adapter.py`의 token limit은 Codex 종료 뒤 usage 합계로 판정된다.
- `project/tools/project_harness/queueing.py`는 재시작 시 running을 interrupted로 바꾸지만 PID adoption이나 attempt fencing을 구현하지 않는다.

## 사용자 파일럿 전 운영 경계

이번 수동 실험은 다음 조건이면 진행 가능하다.

1. 가치 있는 원본이 아닌 disposable local Linux/WSL clone과 신뢰된 bundle을 사용한다.
2. `apply/update` 전에 dry-run 결과의 모든 `replace/conflict`를 저장·검토하고 별도 backup을 둔다.
3. Codex Task는 `read-only` 또는 `workspace-write + network-off`만 사용한다. interactive full-access session은 신뢰된 저장소에서만 별도 수행한다.
4. worker는 먼저 foreground 또는 사용자가 감시하는 background로 실행한다.
5. worker/crash 후에는 Codex descendant와 worktree diff를 확인하기 전에 `resume`하지 않는다.
6. 실제 Promotion은 CLI의 digest만 보지 말고 integration worktree의 `git diff` 본문을 직접 검토한다.
7. symlink·untrusted repository·native Windows·network filesystem을 이번 성공 범위에 포함하지 않는다.

이 경계를 지키면 알려진 문제는 실험을 일괄 차단하지 않는다. 반대로 가치 있는 기존 저장소에 최초 bundle을 바로 적용하거나, untrusted repository에서 full access를 사용하거나, crash 뒤 무인 resume을 허용하는 실험은 현재 근거로 권고하지 않는다.
