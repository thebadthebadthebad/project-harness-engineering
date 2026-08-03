# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

검토 종합 판정을 실제 공용 하네스 개선으로 반영했다. 기존 구성 요소와 책임이 겹치거나 기본 workflow에 선택·문서 noise를 늘리는 기능은 별도 도입하지 않고, 현재 core의 정확성·사람용 View·재사용 근거와 문서 흐름을 강화했다.

주요 결과는 v2 canonical full check, bundle/Task/Promotion resolved-path containment, 최초 managed replace 확인, 짧은 canonical writer lock과 revision CAS, Promotion current-base·fresh validation·actual diff packet, bounded validation full log, Result artifact/reviewer provenance·filter·rebuild, 실제 enforcement를 드러내는 Codex contract와 process-group cancel이다. Root README와 공용 Project README/GUIDE/STRUCTURE/Rules/Skills도 현재 v2 흐름을 기준으로 재작성·정렬했다.

## Final Goal and Result

목표를 달성했다.

- 검토 지적과 부가기능 후보를 중복, workflow 영향과 context noise 기준으로 재평가해 `output/feature-selection.md`에 채택·통합·보류 조건을 기록했다.
- `projectctl check`가 v2 Project·Task·handoff·Decision·Result·Promotion의 schema/digest/internal reference와 Result index/artifact를 검사한다.
- Legacy migration은 partial/missing Task source inventory를 별도로 보고하고 silent omission이 있는 plan/apply를 차단한다.
- Bundle과 Task/Promotion input·candidate에 lexical traversal뿐 아니라 parent/final symlink containment를 적용했다.
- 최초 apply의 managed replace는 dry-run review 뒤 `--accept-managed-replace`를 명시해야 한다.
- Canonical mutation은 re-entrant Project-local lock과 stale revision CAS를 사용하되, 긴 Codex turn과 validation은 lock 밖에서 실행해 독립 Task 병렬성을 유지한다.
- Promotion은 clean exact base와 Task digest를 고정하고 approve/apply에서 validation을 새로 실행한다. Human View에 actual diff와 validation/log digest를 표시한다.
- Validation은 argv, 기본 300초 timeout, Git-local full log와 digest를 남긴다.
- Task/handoff/Promotion/Result View가 output, dependency, acceptance, validation, findings, limitations, effective Codex contract와 provenance를 보여준다.
- Result는 실제 artifact path·byte·SHA-256, reviewer/note를 기록하며 단순 filter와 canonical-record 기반 rebuild를 지원한다.
- Root README는 Harness Engineering의 목적, 저장소/적용 Project 경계, 기능, 개발·배포·검증과 안전 경계를 설명한다.
- 공용 template 문서는 v2 기본 흐름과 legacy migration을 분리하고 실제 CLI·관찰·장애 대응과 일치하도록 개선했다.

## Findings

- Specialized code/document/research Skill 세 개는 Task contract와 기존 `run-task-workflow` 책임을 반복하고 generic checklist noise를 만들 가능성이 커 도입하지 않았다. 유형별 최소 품질 lens만 기존 Skill과 GUIDE에 통합했다.
- 별도 context-pack record는 bounded input/context-ref의 path·digest를 중복하므로 도입하지 않았다. 현재 View를 완성하고 실제 line/symbol context 실패가 관찰될 때 재검토한다.
- pre-commit, link/style checker, Crossref/OpenAlex, SARIF/JUnit은 유용하지만 언어·network·provider·호스팅 종속성이 있어 공용 core가 아닌 Project validation/Skill/MCP의 opt-in 책임으로 유지했다.
- Canonical lock이 validation 전체를 감싸면 한 Task가 다른 handoff를 막는다. 긴 작업은 병렬로 두고 마지막 canonical compare-and-write만 잠그는 것이 사용자 요구와 맞는다.
- JSON self-digest는 인증이 아니며 bundle checksum도 출처를 인증하지 않는다. 신뢰된 commit과 local bundle 전제를 유지했다.
- Interactive `projectctl session` full-access, parent environment 상속, Promotion apply의 완전한 transaction journal은 남은 위험이다.

## Work and Validation

- 초기 Engineering baseline: `007dd1766a2922008a76bc963d153bd264bcc9e9`.
- 사용자가 요청한 official root/template 변경은 구현 commit `a1ea0a563f9a5d09864066441c76cc1f98d58266`에 별도 기록했다.
- Legacy audit는 initial baseline 대비 official 변경을 의도대로 경계 이탈로 보고했다. 구현 commit 뒤 기준점을 명시적으로 다시 고정해 최종 audit가 handoff 문서 변경만 검사하도록 했으며 두 commit 범위를 REPORT에 보존했다.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: 55개 통과.
- `python3 project/tools/projectctl.py --root . check`: 통과.
- `python3 project/tools/projectctl.py --root project check`: 통과.
- `python3 -m py_compile tools/harnessctl.py project/tools/project_harness/*.py`: 통과.
- `git diff --check`: 통과.
- 실제 versioned bundle package → 새 v2 Project 생성 → 최초 commit → full check → Task 생성·human View smoke test: 통과.
- 추가 회귀는 canonical/Result 손상, partial legacy inventory, managed replace 확인, bundle/Task symlink, Promotion base drift·actual diff, 동시 Result write·rebuild, misleading full-access/network contract와 문서 link/책임을 포함한다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| `output/feature-selection.md` | 설계 판단 | 기능 채택·통합·보류와 재검토 조건 |
| `output/document-review.md` | 문서 검토 | 문서별 문제·개선, 책임 분리와 관찰 surface |

## Limitations

- Promotion의 code cherry-pick과 canonical record commit은 아직 하나의 복구 journal transaction이 아니다. 중간 실패는 Git 상태를 보고 forward repair해야 한다.
- Codex subprocess는 process group으로 종료하지만 부모 environment를 상속한다. MCP별 credential allowlist는 별도 계약이 필요하다.
- 기존 provenance 이전 형식 Result는 읽을 수 있도록 유지했으며 새 `result add`부터 artifact digest와 reviewer 규칙을 강제한다.
- Native Windows/NFS, bundle signature, remote/multi-user actor 인증은 지원하지 않는다.
- Lease, heartbeat, PID adoption, fencing, orphan 자동 복구와 mutation retry는 Stage E로 보류했다.
- 외부 link/style/research provider/CI adapter는 설치하지 않았다. 실제 Project가 선택한 validation 또는 Skill/MCP로 추가한다.

## Project Follow-up

1. 사용자가 새 Project와 기존 Project disposable clone에서 updated GUIDE의 최소 흐름을 직접 수행하고 이해하기 어려운 View·명령을 피드백한다.
2. 실제 운영 전 trusted bundle, dry-run, read-only/workspace-write Codex와 actual Promotion diff review 경계를 유지한다.
3. Promotion 중간 commit 실패 또는 parent environment secret 문제가 실제로 관찰되면 각각 작은 독립 Engineering Task로 처리한다.
4. Worker orphan overlap이 재현되기 전에는 Stage E 자동 복구를 구현하지 않는다.
