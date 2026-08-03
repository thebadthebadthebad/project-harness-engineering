# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

현재 하네스는 Project별 독립 소유, Task/worktree 격리, Codex structured handoff, 단순 queue와 병렬 background 실행, Task-local Decision, Result reference와 Promotion이라는 사용자의 핵심 운영 의도에 구조적으로 높은 적합성을 보인다. 다만 canonical v2 full check, Promotion freshness와 실제 diff review, symlink path containment, canonical 동시 write, Result provenance가 trusted Project의 안정적 운영 전 보완해야 할 핵심 공백이다.

두 high-reasoning 읽기 전용 subagent의 의도 적합성·운영 위험 review를 코드와 독립 대조했다. lease, heartbeat, PID adoption과 복잡한 event ledger는 실제 필요성이 확인될 때까지 계속 보류했다. 코드·문서·연구 작업의 부가기능은 중앙 서비스가 아닌 Task profile, Project-local skill, deterministic validator adapter와 human View로 도입하는 방향을 권고했다.

## Final Goal and Result

사용자가 직접 실험하기 전에 하네스의 의도 적합성, 미재현 운영 위험과 공통 부가기능의 가치를 평가했다.

- 판정: 제한된 수동 파일럿은 가능하지만 trusted Project의 안정적 일상 운영 전 P0 보완이 필요하다.
- 파일럿 경계: disposable Linux/WSL clone, trusted bundle, dry-run과 backup, read-only/workspace-write Codex, 감시형 worker, crash 뒤 수동 진단, Promotion 실제 diff 별도 검토.
- P0: v2 full authority check, resolved path containment, Promotion freshness/diff packet, canonical writer lock+revision CAS, 실제 의미와 일치하는 execution contract.
- P1: human review packet, validation timeout와 full evidence, Result provenance/filter/rebuild, explicit context pack, code/document/research profile과 scoped skill, interrupted diagnostic.
- P2: Crossref/OpenAlex, link checker, pre-commit/CI, SARIF/GitHub 같은 opt-in adapter.
- P3/Stage E: Tree-sitter·FTS5·native Windows/NFS·자동 orphan 복구는 관찰 근거가 생길 때까지 보류.

## Findings

- 기존 Stage D는 실제 Codex reader 2개의 병렬 vertical slice였지만 실제 writer Promotion, 사용자 Decision, cancel·crash/resume을 수행하지 않았다. 사용자의 이번 직접 실험이 전체 Stage D 증거를 보강한다.
- `projectctl check`는 v2 canonical record를 전수 검사하지 않는다. 현재의 `check passed`는 canonical schema/digest/reference 무결성 증거가 아니다.
- Promotion은 prepare 시점 validation과 diff digest를 기록하지만 approval/apply 시 official base freshness와 validation을 다시 결속하지 않고 실제 diff View도 제공하지 않는다.
- bundle 최초 apply와 Promotion copy는 managed-path collision 및 symlink containment를 더 엄격히 다뤄야 한다.
- Result artifact의 존재·digest·review provenance와 index transaction/rebuild가 부족하다.
- token limit은 hard stop이 아니라 post-run 판정이며 shell/apply_patch allowlist와 hooks는 강한 보안 경계가 아니다.
- 공용성 높은 부가기능은 도구를 강제 설치하는 방식보다 profile·skill·validator adapter·generated View 방식이 현재 구조와 잘 맞는다.

## Work and Validation

- `intent_fit_audit`, `operational_risk_audit` 두 read-only subagent를 reasoning effort `high`로 실행했다.
- 두 review의 사실·추론·미재현 가설을 구분하고 `반영/부분 반영/보류/반영하지 않음`으로 독립 판정했다.
- `lifecycle.py`, `v2.py`, `adapter.py`, `queueing.py`, bundle installer, 관련 Stage D report와 test 근거를 대조했다.
- OpenAI Codex 공식 자료, pre-commit, lychee, Vale, Crossref, OpenAlex, SQLite FTS5, Tree-sitter, GitHub SARIF·dependency review·push protection 공식 문서를 조사했다.
- Task 범위에서는 코드나 Project template을 변경하지 않았고 분석 문서와 handoff만 작성했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| `output/final-assessment.md` | 최종 판정 | 사용자 의도 적합성, 파일럿 절차, P0–P3 권고와 역할 분리 |
| `output/subagent-review-synthesis.md` | review synthesis | 두 subagent 지적의 독립 판정, 근거, 반영·보류 이유와 파일럿 경계 |
| `output/external-feature-research.md` | 외부 조사 | 코드·문서·연구 부가기능의 공통성, 비용, 책임과 도입 순서 |

## Limitations

- 이번 Task는 Plan/review 범위이며 식별한 문제를 수정하거나 adversarial fixture로 재현하지 않았다.
- 운영 위험 다수는 Stage D 실제 사고가 아니라 코드 검토에서 확인한 발생 가능성이다. 문서에서 발생 조건과 파일럿 범위를 구분했다.
- 외부 도구의 가격, 플랜과 지원 범위는 변경될 수 있으므로 실제 adapter 도입 시 공식 문서를 다시 확인해야 한다.
- native Windows, NFS, untrusted repository와 분산·다중 사용자 운영은 현재 권고 범위 밖이다.

## Project Follow-up

1. 사용자가 `output/final-assessment.md`의 제한 조건과 최소 파일럿을 따라 직접 실험하고 다섯 개 피드백 항목을 기록한다.
2. 파일럿 결과를 받은 뒤 P0 correctness/security 보완을 별도 Engineering Task로 분해한다.
3. P1은 human View와 validation/Result provenance부터 작은 vertical slice로 구현한다.
4. P2 adapter는 실제 적용 Project가 필요로 할 때만 opt-in하고 Stage E 보류를 유지한다.
