# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

현재 공용 하네스를 세 관점으로 독립 분석하고 결과를 교차 종합했다. 현 하네스의 Project/Task 분리, 사용자 통제, Task 완료와 Promotion 분리, baseline/audit는 사용자 의도에 부합하므로 유지해야 한다. 반면 대형 다중 Task 운영을 위해서는 compact typed handoff, 작은 Project Kernel, 명시적 동시성 정책, Promotion provenance가 우선 보강되어야 한다.

전면 greenfield 전환은 즉시 권고하지 않는다. 기존 구조에서 context와 승계 경계를 먼저 개선하고, 실제 병렬성·저장소 규모 benchmark가 임계치를 넘을 때 worktree, machine registry, 외부 work plane을 도입하는 단계적 계획을 제안했다.

## Final Goal and Result

Final Goal은 사용자 의도를 기준으로 공용 Project 구조·workflow·하네싱을 세 관점에서 분석하고 대안과 tradeoff를 종합해 개선 계획을 제안하는 것이었다.

요청한 세 독립 관점의 분석 기록, 공통점과 충돌점, 선택지별 장점·단점·우려, 우선순위·변경 대상·검증 방법이 포함된 5단계 개선 계획을 모두 작성했다. 공용 template의 실제 변경이나 Promotion은 이 Task 범위에 포함하지 않았다.

## Findings

- 현재 철학은 사용자 의도와 맞다. Task 원문을 Project context에서 제외하고 선택 결과만 Promotion하는 구조는 유지해야 한다.
- REPORT는 상세 종료 보고서이지만 Project가 원하는 Decision, Observation, Reusable Asset과 Promotion Candidate를 작은 단위로 표현하지 않는다.
- Task에는 Project 전체가 아니라 Goal, invariant, terminology/interface, 관련 canonical reference로 구성된 작은 Project Kernel이 필요하다.
- 기본 Project context는 active/planned Task, pending review capsule, pending Promotion만 포함하고 closed/결정 완료 Task는 on-demand로 조회해야 한다.
- shared worktree audit와 다중 active Task는 긴장 관계가 있다. 단기에는 한 branch당 active Task 하나를 강제하고 실제 병렬 요구가 확인되면 Task별 worktree/branch를 도입해야 한다.
- Promotion은 candidate ID, source/base/target digest, validation과 integration commit을 연결하는 append-only provenance가 필요하다.
- read-only research/verification 외에도 Task decomposition, 요구 질문, 문서 초안을 돕는 제한된 subagent 역할이 사용자 의도와 맞다. 사용자 상호작용과 통합 책임은 부모 Agent가 유지해야 한다.
- Hook과 Skill의 core 유지 여부, Markdown 대 machine registry, in-repo 대 external work plane은 즉시 결론 내리지 않고 benchmark와 별도 spike로 선택해야 한다.

## Work and Validation

- 사용자 제작 의도를 Task 평가 기준과 완료 조건으로 구체화했다.
- 공식 배포 template의 workflow, directory, Project/Task 문서, lifecycle command surface, Skill, Hook과 agent 설정을 확인했다.
- 공식 실험 결과에서 context 절감과 실제 research+code 비용을 확인했다.
- 사용자 승인 후 현 구조 친화적 분석, 강한 비판, greenfield 설계의 세 read-only subagent를 병렬 실행했다.
- 각 응답을 독립 note로 정리하고 공통점과 양립 불가능한 선택지를 종합했다.
- Phase 0–5 개선 계획에 목적, 예상 변경 대상과 검증 기준을 작성했다.
- `projectctl task validate harness-architecture-review --phase doing`: 통과.
- 작성 문서 `git diff --check`: 통과.
- 세 독립 분석과 종합 계획: 4개 파일, 총 721줄.
- placeholder 검색: 실제 placeholder 없음. 검색된 한 건은 validator 한계를 설명하는 본문 용어였다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| `docs/notes/01-conservative-review.md` | analysis | 현 구조와 철학을 유지하는 점진 개선안 |
| `docs/notes/02-critical-review.md` | analysis | 현 구조의 강한 비판, 실패 모드와 재설계 후보 |
| `docs/notes/03-greenfield-design.md` | design | Capsule–Promotion 기반 신규 하네스 설계 |
| `output/synthesis-and-improvement-plan.md` | result | 세 분석의 종합, 선택지 비교와 단계별 권고 계획 |

## Limitations

- 이 Task는 구조 분석과 개선 계획만 수행했으며 공용 template 구현을 변경하지 않았다.
- subagent가 정적 분석으로 제기한 세부 lifecycle failure mode는 이 Task에서 별도 black-box scenario로 모두 재현하지 않았다. 구현 Task에서 acceptance test로 확인해야 한다.
- greenfield의 Project 6,000 / Task 9,000 token budget은 설계 가설이며 실제 대형 Project benchmark로 조정해야 한다.
- 실제 사용에서 여러 Task를 동시에 수행해야 하는지, 여러 Task로 분리하되 순차 수행해도 되는지는 사용자 선택이 남아 있다.

## Project Follow-up

1. 사용자는 동시성 기본값을 선택한다.
   - 권고 기본값: 한 branch당 active Task 하나
   - 실제 병렬 수행 필수: Task별 worktree/branch spike를 Phase 2 이전으로 당김
2. 다음 Engineering Task로 Phase 0 기준 시나리오와 Phase 1 compact handoff/Project Kernel을 설계·구현한다.
3. Phase 1 결과를 실제 multi-Task context 크기와 사용자 gate 수로 평가한 뒤 machine registry나 외부 work plane 필요성을 결정한다.
4. 이 Task의 종합 문서를 공식 설계 근거로 Promotion할지는 사용자 검토 후 별도로 결정한다.
