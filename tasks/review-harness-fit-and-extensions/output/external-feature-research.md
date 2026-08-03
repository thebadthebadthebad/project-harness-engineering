# External Feature Research

## 목적과 판단 기준

코드 작성, 문서 작성, 연구 검색·취합의 편의와 결과 품질을 높이는 기능을 공식 문서 중심으로 조사했다. 특정 언어·호스팅 서비스에 종속된 제품을 공용 bundle의 필수 구성으로 넣기보다 다음 기준으로 분류했다.

- 여러 종류의 Project에서 반복되는 실제 문제를 해결하는가.
- 결정론적 검사, Agent 판단, 부모 Agent review, 사용자 판단 중 책임 주체가 명확한가.
- Project별 독립 소유와 명시적 capability 허용 모델을 유지하는가.
- 초기 비용과 유지보수 부담이 기대 효과에 비례하는가.
- 기능이 없어도 기본 흐름이 동작하고, opt-in adapter로 추가할 수 있는가.

## 조사한 공식 자료

| 자료 | 확인한 적용점 |
| --- | --- |
| [OpenAI Codex best practices](https://learn.chatgpt.com/guides/best-practices) | Goal·Context·Constraints·Done이 분명한 prompt, 복잡한 작업의 plan, 실용적인 AGENTS 규칙, test/review, worktree 병렬화 |
| [OpenAI Build Skills](https://learn.chatgpt.com/docs/build-skills) | 반복 workflow를 instructions·references·scripts로 묶고 필요할 때만 context에 여는 progressive disclosure |
| [OpenAI Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) | `codex exec`, JSONL과 output schema, 명시적 sandbox, CI에서 secret과 untrusted code 분리 |
| [OpenAI Docs MCP](https://developers.openai.com/learn/docs-mcp) | 공식 OpenAI 문서를 검색·열람하는 public read-only MCP; 외부 API action과 구분 |
| [pre-commit](https://pre-commit.com/) | 여러 언어의 작은 deterministic check를 commit 전에 같은 방식으로 실행하고 hook 환경을 격리 |
| [lychee](https://lychee.cli.rs/) | Markdown·HTML 링크 검증, 로컬/CI 실행과 JSON 출력 |
| [Vale](https://docs.vale.sh/) | Markdown 등 prose의 규칙 기반 style 검사; offline·custom rule 지원, 내용 사실성 검사는 아님 |
| [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | DOI 중심 scholarly metadata의 공개 JSON 검색·filter와 polite usage |
| [OpenAlex API](https://developers.openalex.org/api-reference/introduction) | works/authors/sources 등의 검색·filter·select; API key와 현재 사용 비용 정책 고려 필요 |
| [SQLite FTS5](https://www.sqlite.org/fts5.html) | 로컬 full-text query와 ranking; 작은 Result index에는 아직 과도할 수 있음 |
| [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) | 여러 언어의 syntax tree를 이용한 symbol 단위 context 추출; grammar 유지비 존재 |
| [GitHub SARIF](https://docs.github.com/en/code-security/concepts/code-scanning/sarif-files) | 정적 분석 결과의 교환 형식과 GitHub code scanning upload; 호스팅·플랜 종속성 존재 |
| [GitHub dependency review](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review) | PR의 dependency 변경, 알려진 취약점과 license 영향 review; GitHub 종속 기능 |
| [GitHub push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection) | 식별 가능한 secret의 push 차단; 지원 범위·플랜에 따라 달라지는 보조 경계 |

외부 도구의 현재 가격·지원 범위는 변경될 수 있으므로 설치 시점에 다시 확인해야 한다. 특히 OpenAlex 검색은 현재 문서에 API key와 호출 비용 정책이 명시돼 있어 자동 대량 검색의 기본 provider로 무제한 가정하면 안 된다.

## 현재 하네스에 이미 있는 확장 지점

- Task는 input, owned path, acceptance, validation command, execution contract를 가질 수 있다.
- Codex adapter는 model, reasoning, sandbox, web/network, MCP, Project-local skill을 명시하고 effective contract와 fallback을 남긴다.
- worktree, structured handoff, Decision, Promotion과 Result reference가 있다.
- bundle에는 현재 Project-local workflow skill 하나만 있고, code/document/research 유형별 skill은 없다.
- Result index는 작은 JSON 목록이며 kind, verification, reusable 정보를 저장하지만 filter·provenance 검증은 약하다.

따라서 새 중앙 서비스보다 **Task profile + Project-local skill + deterministic validator adapter + 더 나은 View**가 기존 구조에 가장 자연스럽게 맞는다.

## 도입 가치가 높은 공통 기능

### 1. 사람이 읽는 Task·Review·Promotion packet

**해결 요구:** 사용자가 무엇을 관찰하고 어떤 근거로 승인해야 하는지 즉시 이해해야 한다.

현재 `task show`에는 outputs, dependencies, validation commands가, `task review`에는 findings와 limitations가 빠져 있다. Promotion View도 실제 diff 본문 없이 digest만 보여준다. 다음을 하나의 읽기 전용 View로 제공하는 것이 가장 높은 효용을 가진다.

- Goal, scope, inputs와 digest, outputs, owned paths, dependencies.
- acceptance 항목별 충족 근거.
- requested/effective Codex contract와 fallback.
- findings, limitations, validation command·exit·log link.
- pending Decision과 영향.
- Promotion 대상별 실제 diff, base commit, freshness, 되돌리기 방법.

공통성은 매우 높고 외부 dependency가 없다. **즉시 도입 후보**다.

### 2. Task 유형별 최소 profile과 Project-local skill

**해결 요구:** 사용자가 매번 같은 수행·review 지시를 반복하지 않으면서도 Agent 자율성을 유지해야 한다.

OpenAI의 Skills guidance처럼 하나의 skill은 한 종류의 반복 작업에 집중하고 필요할 때만 로드한다. 공용 bundle은 세 profile의 최소 계약과 선택형 skill을 제공할 수 있다.

| Profile | 최소 계약 | Agent handoff | 부모 review |
| --- | --- | --- | --- |
| `code-change` | owned path, acceptance, test command, compatibility | changed files, tests, risks, candidates | diff, test evidence, scope, regression |
| `document-change` | audience, source authority, required sections, link check | document, source list, unsupported claims, limitations | factual support, readability, broken links |
| `research-synthesis` | question, source policy, recency, inclusion/exclusion | query manifest, evidence table, synthesis, uncertainty | source quality, claim support, contradictions |

Schema를 크게 늘리기보다 profile 선택 시 누락을 warning하고 skill이 작업 절차를 제공한다. 작고 단순한 reader Task에는 기존 최소 계약을 유지한다. **즉시 도입 후보**다.

### 3. deterministic validation discovery와 review evidence

**해결 요구:** 코드 종류마다 test/lint/build 명령을 사용자가 매번 찾아 적는 비용을 줄이고, Agent의 “검증 완료” 주장을 재현 가능하게 만들어야 한다.

`projectctl doctor project` 같은 읽기 전용 probe가 manifest와 CI 파일을 탐지해 검증 명령 후보를 제안한다. 자동 설치나 network 실행은 하지 않고 사용자가 Task contract에 채택할 명령만 선택한다. 실행은 다음을 남긴다.

- argv, cwd, 시작·종료 시각, exit code, timeout.
- 전체 Git-local log artifact, SHA-256, 짧은 human summary.
- 가능하면 JUnit/SARIF 같은 표준 결과의 optional parser/export.
- validation이 실행된 exact commit/diff digest.

언어별 command는 adapter/plugin으로 분리한다. SARIF는 canonical state가 아니라 호스팅 연동용 export다. **core evidence는 즉시 도입, 언어별 discovery는 파일럿 도입**이 적합하다.

### 4. 명시적 context pack

**해결 요구:** 전체 저장소를 prompt에 넣지 않고도 Agent가 필요한 문맥을 빠뜨리지 않아야 한다.

현재 입력은 whole-file과 크기 제한 중심이다. 다음의 deterministic pack을 추가할 가치가 있다.

- 선택한 파일·line range·Result artifact와 각 digest.
- 총 byte/token 추정치와 잘린 항목.
- 사람이 실행 전에 보는 Markdown preview.
- Task 결과에 실제 사용한 pack digest 기록.

처음에는 명시 경로·line range만 지원한다. Tree-sitter symbol selection은 언어 grammar 유지비가 있으므로 코드 Project에서 효용이 확인된 뒤 optional adapter로 추가한다. **단순 context pack은 즉시, Tree-sitter는 보류 파일럿**이다.

### 5. Result provenance, filter와 rebuild

**해결 요구:** 이전 실험·실패·review·결정을 후속 Task가 신뢰 가능한 범위에서 발견하고 재사용해야 한다.

범용 evidence graph 없이 다음만 추가한다.

- artifact 존재, SHA-256, 크기, media type.
- source Task/handoff/Decision와 reviewer·검증 근거.
- `verified`, `reusable` 변경 주체와 시각.
- `--kind`, `--verification`, `--reusable`, simple text filter.
- records에서 index를 재생성하고 양방향 consistency를 검사하는 `result rebuild/check`.
- superseded/rejected 결과의 기본 context 제외.

이는 JSON authority를 유지하면서 index의 발견성과 복구성을 높인다. Result가 수십~백여 개로 늘고 simple filter가 느리거나 부정확하다는 관찰이 생길 때만 FTS5를 추가한다. **즉시 도입 후보**다.

### 6. 연구 query manifest와 claim–evidence table

**해결 요구:** 검색 결과를 많이 저장하는 대신, 어떤 질문·조건으로 무엇을 채택했는지 재현하고 후속 연구가 재사용해야 한다.

`research-synthesis` skill과 작은 script가 다음을 생성한다.

- provider, query, filters, retrieved-at, tool/version, 비용·rate-limit 메모.
- result identifier, DOI/URL, title, author, date, source type.
- inclusion/exclusion와 이유, duplicate cluster.
- 핵심 claim, supporting/contradicting source, 신뢰도와 한계.
- 사용한 원문 위치와 접근일; 저작권 있는 본문 전체는 저장하지 않음.

Crossref는 DOI metadata 보강·중복 제거에, OpenAlex는 논문·저자·출처 탐색에 opt-in provider로 적합하다. 둘 중 하나를 진실의 단일 원천으로 취급하지 않고 DOI와 bibliographic fields를 대조한다. API key, 비용, license·copyright를 execution contract에 표시한다. **research Task용 선택형 bundle 기능으로 파일럿 도입**이 적합하다.

### 7. 문서 품질 profile

**해결 요구:** 링크 손상과 문서 구조 오류 같은 반복적 결함은 Agent review 전에 결정론적으로 차단해야 한다.

- Markdown heading·필수 section·local reference는 자체 script로 검사한다.
- `lychee`는 link 검증 adapter로 opt-in한다. network가 필요한 external link check와 offline local link check를 분리한다.
- Vale는 영어 또는 Project가 style vocabulary를 정의한 경우에만 opt-in한다. 한국어 문서의 사실성·자연스러움을 보장하는 기본 검사로 사용하지 않는다.
- rendered preview와 변경된 section 목록을 review packet에 연결한다.

공통 bundle이 binary를 강제 설치하지 않고 capability probe와 명시적 validator 선택을 사용한다. **local structural check는 즉시, lychee/Vale는 파일럿**이다.

### 8. pre-commit/CI bridge

**해결 요구:** 같은 deterministic check가 로컬 Agent 실행과 사람의 commit, CI에서 다르게 동작하지 않아야 한다.

pre-commit은 여러 언어 hook을 격리 실행하고 commit 전 사소한 오류를 줄이는 데 유용하다. 다만 최초 환경 다운로드, hook latency, 기존 Project 설정 충돌이 있다. 따라서 공용 bundle의 mandatory hook이 아니라 다음 역할만 맡긴다.

- 하네스 validation command를 호출하는 opt-in sample/config generator.
- 버전 pin과 offline/cache 조건을 명시.
- CI에서도 같은 command를 별도로 실행해 local hook 우회를 허용하되 결과는 놓치지 않음.

GitHub dependency review, push protection과 SARIF upload도 해당 호스팅을 쓰는 Project의 optional integration이다. 이것들을 하네스 자체의 보안 경계로 간주하지 않는다. **선택형 adapter**가 적합하다.

### 9. capability·security diagnostic packet

**해결 요구:** 실행 전에 모델·reasoning·sandbox·tool/MCP/skill이 실제로 어떻게 낮춰지거나 노출됐는지 사용자가 알아야 한다.

기존 `doctor codex`를 다음의 읽기 쉬운 packet으로 확장한다.

- requested vs supported vs effective contract.
- fallback 이유와 품질·비용 영향.
- enabled/disabled MCP·Project skill·web와 강한 경계인지 prompt 지시인지의 구분.
- sandbox/network의 호환성 검사.
- environment 전달 정책과 secret 이름 redaction.

특히 `danger-full-access + network_access=false` 같은 오해 가능한 조합은 거부하거나 명확히 경고한다. `token limit`은 hard stop이 아니라 post-run usage ceiling이면 그렇게 표시한다. **즉시 도입 후보**다.

### 10. interrupted Task diagnostic과 안전한 cleanup

**해결 요구:** 고급 자동 복구 없이도 중단된 작업을 사용자가 이해하고 안전하게 이어가야 한다.

자동 PID adoption 대신 다음의 읽기 전용 diagnostic packet을 먼저 제공한다.

- worker/job/attempt/run ID와 마지막 상태.
- 알려진 Codex PID/process group 존재 여부.
- worktree status·diff·최근 log·pending Decision.
- resume 시 덮어쓸 가능성과 권고 action.
- 완료된 worktree/branch/runtime의 크기와 안전한 cleanup candidate.

이 기능은 Stage E를 당겨오지 않으면서 현재 recovery UX를 개선한다. 실제 orphan 반복이 관찰될 때만 lease, heartbeat, fencing과 adoption을 검토한다. **진단은 파일럿 도입, 자동 복구는 보류**다.

## 기능별 공통성·비용 요약

| 기능 | 사용자가 얻는 것 | 공통성 | 구현·운영 비용 | 권고 |
| --- | --- | --- | --- | --- |
| Human review packet | 무엇을 보고 승인할지 명확해짐 | 매우 높음 | 낮음 | 즉시 |
| Task profiles + skills | 반복 지시 감소, 작업 품질 기준 일관화 | 높음 | 중간 | 즉시 |
| Validation evidence | 재현 가능한 test/review | 매우 높음 | 중간 | 즉시 |
| Explicit context pack | 누락·과다 context 감소 | 높음 | 중간 | 즉시 |
| Result provenance/filter/rebuild | 과거 결과의 신뢰 가능한 재사용 | 높음 | 중간 | 즉시 |
| Research manifest/evidence table | 검색 재현성·출처 품질 향상 | 연구 Project에서 높음 | 중간 | 파일럿 |
| Doc structural/link checks | 반복 문서 결함 조기 발견 | 높음 | 낮음~중간 | 파일럿 |
| pre-commit/CI bridge | 사람·Agent·CI 검사 정렬 | 중상 | 중간 | opt-in |
| SARIF/GitHub security bridge | 호스팅 UI와 보안 signal 연동 | 조건부 | 중간 | opt-in |
| Tree-sitter context | symbol 중심 코드 context | 코드 Project에서 중간 | 중상 | 관찰 후 |
| SQLite FTS5 | 큰 Result 집합 검색 | 현재 낮음 | 중상 | 관찰 후 |
| automatic orphan recovery | 무인 crash 복구 | 현재 증거 부족 | 높음 | Stage E |

## 책임 분리

| 수행 주체 | 적합한 작업 |
| --- | --- |
| 결정론적 script/hook | schema·digest·reference 검사, path containment, validation 실행·timeout, link check, query manifest normalization, Result index rebuild, diff·log digest |
| Task Agent | 코드·문서 작성, 연구 질문 해석, 검색 전략, 결과 synthesis, alternatives와 limitations 작성 |
| 부모 Agent review | scope/ownership, evidence와 claim 연결, 검증 충분성, subagent 결과 충돌, Promotion candidate 선정 |
| 사용자 판단 | 목표·범위 변경, 외부 비용·network·권한 확대, 상충하는 유효 대안, security-sensitive Promotion, 공개·배포 |

## 권고 도입 순서

1. **운영 정확성:** v2 full check, path containment, Promotion freshness/diff View, canonical writer lock/CAS.
2. **사람 중심 View:** Task·review·Decision·Promotion packet, truthful capability/token/sandbox 표시.
3. **재현성:** validation timeout와 full evidence, Result provenance/filter/rebuild, explicit context pack.
4. **작업 품질:** code/document/research profile과 scoped skills.
5. **선택형 adapter:** research provider, link checker, pre-commit/CI, SARIF/GitHub bridge.
6. **관찰 후 확장:** Tree-sitter, FTS5, native Windows/NFS, Stage E automatic recovery.

이 순서는 새 기능 수를 늘리기보다 현재 core의 신뢰성과 사용자가 읽는 surface를 먼저 닫는다. Project별 `.harness` 독립 소유와 bundle 기반 배포는 유지하며, 모든 provider/tool은 Project가 명시적으로 선택한 경우에만 활성화한다.
