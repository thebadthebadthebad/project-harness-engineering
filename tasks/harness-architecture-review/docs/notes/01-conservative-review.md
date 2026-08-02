# 현 구조 친화적 분석

## 관점

현재 하네스의 Project/Task 분리, 사용자 통제, 선택적 Promotion 철학을 유지하면서 실제 운영 마찰만 점진적으로 제거하는 관점이다.

## 현 구조 해석

- 루트는 하네스 자체를 개선하는 Engineering Project이고 `project/`는 배포할 공용 Project 템플릿이다.
- 공식 자산은 `src/`, `tools/`, `data/`, `docs/`가 관리하고 `tasks/<name>/`은 조사·실험·초안·결과를 격리한다.
- Project와 Task 세션은 대화를 공유하지 않으며 `TASK.md`/`STATUS.md`가 하향 계약, `REPORT.md`가 상향 handoff다.
- `projectctl`은 scaffold, 형식 검사, 상태 전이, baseline/checksum, 경계 감사와 결정 기록만 담당한다.
- 목표, Task 계약, 결과 해석, Promotion 가치와 세션 전환은 사용자와 Agent가 판단한다.
- Task 완료와 Promotion이 분리되어 있어 Task 전체가 공식 Project로 유입되지 않는다.

이 기본 모델은 사용자의 제작 의도와 대체로 일치한다.

## 적합성 평가

| 의도 | 평가 | 남은 문제 |
| --- | --- | --- |
| 큰 목표를 독립 Task로 분리 | 좋음 | Task 간 의존성과 실제 병렬 수행 정책이 드러나지 않는다. |
| 핵심 결과만 Project로 승계 | 매우 좋음 | 승계 후보가 자유형 REPORT에 묻혀 있다. |
| Project context 노이즈 억제 | 좋음 | 여러 pending handoff와 같은 Goal의 completed Task가 늘면 다시 커질 수 있다. |
| Project 통일성 | 좋음 | Task에 전달할 공통 불변조건과 Promotion provenance가 약하다. |
| 사용자-Agent 상호작용 | 매우 좋음 | 현재 subagent 역할은 사용자가 위임하려는 문서 초안·Task 분해보다 좁다. |

공식 실험에서는 반복 문서 로딩 억제로 Markdown path가 22개에서 9개로, input token이 11.4% 감소했다. 반면 실제 research+code 사례는 약 122만 input token을 사용했으므로 Project context와 Task 작업량의 분리는 계속 유지해야 한다.

## 주요 우려와 점진적 개선

1. 한 Git branch에서 여러 `doing` Task가 병렬로 변경되면 baseline 이후 Task 밖 변경을 잡는 audit와 충돌할 가능성이 높다.
   - 우선 한 branch당 baseline을 가진 active Task 하나를 명시하고 도구로 강제한다.
   - 병렬 실행이 실제 요구가 될 때 Task별 branch/worktree를 별도 도입한다.

2. close 후 정규화된 handoff를 다시 검토하기 어렵고, Promotion 결정 뒤에도 completed Task가 기본 context에 남을 수 있다.
   - closed Task용 읽기 전용 review 명령을 둔다.
   - 기본 context는 active Task, pending review, pending Promotion만 보여준다.

3. REPORT가 Project가 원하는 승계 유형을 직접 표현하지 않는다.
   - `Findings`를 Decisions, Observations, Reusable Assets로 구분한다.
   - `Project Follow-up`에 `Kind | Source | Proposed Target | Reason | Evidence` 형태의 Promotion Candidates를 둔다.
   - Relevant Files는 전체 산출물이 아니라 검토에 필요한 파일만 포함한다고 강화한다.

4. 큰 Goal을 Task로 분해하는 사용자 승인 checkpoint가 암묵적이다.
   - 요구 질문 → Task map → 독립성/입력/완료조건/예상 승계 유형 → 사용자 승인 → create 순서를 GUIDE에 추가한다.

5. Promotion 기록은 공식 대상과 실제 파일의 연결을 더 강하게 검증해야 한다.
   - 공식 경로 allowlist, 존재 여부, source/target mapping과 digest를 검증한다.
   - 종료와 Promotion 사건을 분리된 append-only 기록으로 남긴다.

## 문서와 보조 기능 평가

- `PROJECT.md`, `STATE.md`, `TASK.md`, `STATUS.md`, `REPORT.md`의 책임 분리는 유지할 가치가 있다.
- `STRUCTURE.md`는 불변식, `GUIDE.md`는 명령과 장애 대응만 담당하도록 중복을 줄인다.
- Task `scripts/`의 snapshot과 작업 코드가 혼합되므로 우선 `scripts/snapshot/`, `scripts/work/` 관례를 시험할 수 있다.
- 명시 호출 Skill과 metadata-only Hook은 사용자 통제와 관찰 목적에 맞지만 핵심 판단을 대신해서는 안 된다.
- `planning_assistant` 같은 response-only 역할을 추가하여 요구 질문, Task map, 문서 초안, 조사 요약을 지원할 수 있다. lifecycle과 Promotion 판단은 계속 부모와 사용자에게 둔다.

## 우선순위

### P0

- 동시성 정책을 명시하고 한 branch당 active Task 하나를 강제한다.
- compact handoff와 typed Promotion Candidates를 REPORT에 추가한다.
- 기본 Project context에서 closed/결정 완료 Task를 제거한다.
- closed Task의 on-demand review를 제공한다.

### P1

- Promotion source/target/digest/commit provenance를 보강한다.
- Task 분해 승인 checkpoint를 GUIDE에 추가한다.
- Project 핵심 파일·선택 기능 설정의 `check` 범위를 강화한다.
- 여러 pending handoff에는 capsule만 자동 포함하고 상세는 요청 시 연다.

### P2

- 문서 책임 중복을 축소한다.
- 제한된 planning/document subagent를 실험한다.
- `scripts/` 하위 관례와 선택적 Task 디렉터리를 검증한다.

## 유지해야 할 요소

- Project와 Task 작업 공간의 분리
- 사용자의 세션 전환과 가치 판단
- Task 완료와 Promotion의 분리
- Task 계약·현재 상태·최종 handoff의 분리
- context 1회와 source digest 기반 재독 억제
- Git baseline, boundary audit, linked-data checksum
- 공식 자산 경로의 책임과 Task 원문/로그의 비승계 원칙
- Hook을 보안 경계로 과장하지 않는 태도

## 근거

- `project/STRUCTURE.md`
- `project/GUIDE.md`
- `project/AGENTS.md`
- `project/tasks/_template/{TASK,STATUS,REPORT,AGENTS}.md`
- `project/.agents/skills/manage-project-workflow/SKILL.md`
- `project/tasks/_template/.agents/skills/run-task-workflow/SKILL.md`
- `project/.codex/agents/*.toml`
- `project/.codex/hooks.json`
- `experiments/RESULTS.md`
