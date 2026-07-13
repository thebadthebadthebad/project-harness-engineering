# Final Harness Analysis

## 결론

현재 하네스는 사람이 Project와 Task 세션을 전환하고 결과 가치를 판단하는 운영 의도를 유지하면서, 반복 가능한 lifecycle·형식 검사·변경 감사·관찰을 결정적 도구로 보조할 수 있다. Project Agent가 Task Agent를 자동 지휘하거나 모든 프로젝트를 한 세션에서 수행하는 구조가 아니다.

공용 템플릿은 실제 Project/Task/Project 세션, 리서치+코드 작업, 최종 Hook smoke에서 동작했다. 다만 full-access 환경의 보안 격리 또는 Hook의 완전한 action capture를 제공한다고 해석하면 안 된다.

## 구현 결과

### 역할과 문서

- `PROJECT.md`: 안정적인 Goal과 Scope
- `STATE.md`: Current Goal과 현재 Goal의 Task 상태만 유지
- `TASK.md`: 독립 작업의 Scope, Inputs, Workflow, Outputs, Completion Criteria
- `STATUS.md`: Final Goal, Work Plan, Current Work, 현재 Status
- `REPORT.md`: 공유 대화 컨텍스트 없이 Project가 검토하는 종료 handoff
- `STRUCTURE.md`: 책임과 lifecycle 상태 전이
- `GUIDE.md`: 사용자가 따라 하는 전체 실행 절차

README, 구조 계약, 실행 가이드를 분리해 한 문서가 잡다한 운영 저장소가 되는 것을 피했다. ADR은 날짜 없는 결정 이름, History는 도구가 생성하는 사건 이름을 사용한다.

### 코드와 deterministic controls

단일 `projectctl.py` entry point 아래 문서, repository, lifecycle, context, observability, CLI 모듈을 분리했다. 함수는 역할·입력·출력이 드러나는 작은 경계를 사용하며 atomic Markdown 갱신으로 실패 시 원본을 보존한다.

- context는 Project/Task 계약을 새 세션에 한 번 제공한다.
- create/activate/baseline은 독립 Task와 clean Git 기준점을 만든다.
- validate/handoff/audit/close는 종료 형식, Relevant Files, Task 밖 변경, linked data를 검사한다.
- promotion record는 이미 내린 promoted/not-promoted 결정을 History에 기록한다.
- check는 일반 Project와 Engineering Project를 구분하고 Engineering에서는 nested 공용 템플릿까지 검사한다.
- create_project는 숨김 설정을 포함한 템플릿 복사, Git init, 구조 검사를 수행하며 기존 목적지를 덮어쓰지 않는다.

### 보수적 Codex 기능

- Project/Task Skills는 `allow_implicit_invocation: false`이며 정확한 lifecycle 명령만 보조한다.
- subagent 설정은 research reader와 verification reader 두 개, max threads 3, depth 1이다.
- subagent는 사용자가 허용한 독립 읽기 병렬화에만 사용하며 작은 순차 시나리오에서는 호출하지 않았다.
- 세션 launcher는 network/full-access/no-approval이고 auto-review를 추가하지 않는다.
- bubblewrap가 없는 환경이므로 custom agent에 호환되지 않는 `sandbox_mode`를 선언하지 않는다.

### 관찰

Hook source는 `.codex/hooks/observe.py`, 등록은 `.codex/hooks.json`에 둔다. Hook은 fail-open이며 Git-local events에 content-free metadata만 남긴다. public report는 Hook coverage, 문서 방문, context/lifecycle, Skill, compaction, subagent, role과 timeline을 보여준다.

문서 방문과 lifecycle action은 같은 tool-use의 Pre/Post event를 `tool_use_id`로 중복 제거한다. content read 명령만 Markdown visit으로 추출하고 glob, `rg --files`, `git diff` 같은 non-read path는 제외한다.

## 실험 결과

### Lifecycle v2 대비 v3

같은 parser로 원본을 재분석한 비교다.

| Metric | v2 | v3 | Delta |
| --- | ---: | ---: | ---: |
| Markdown paths | 22 | 9 | -13 |
| Context calls | 4 | 3 | -1 |
| Input tokens | 539,273 | 477,610 | -61,663 (-11.4%) |
| Output tokens | 15,195 | 9,577 | -5,618 (-37.0%) |

v3의 세 독립 session은 exit 0, hard acceptance PASS, 변경 없는 반복 read 0이었다. command 수 증가는 explicit Skill marker와 CLI help 확인 때문이었고, 반복 오용된 `task status <name>`을 exact Skill 예제로 교정했다.

### Research plus code

세 독립 session이 공식 Python CSV 근거 조사, standard-library 구현, fixture, output, unittest 2개, REPORT와 close를 완료했다. hard acceptance를 모두 통과하고 변경 없는 반복 read는 0이었다. input 1,224,973과 output 21,853은 작업 비용 관찰값이지 품질 gate가 아니다.

### 교정 후 actual Hook smoke

최종 template의 실제 Project session 하나가 exit 0, commands 3, failures 0, changes 0, context 1, Markdown content read 1로 끝났다. 8개 hard acceptance가 모두 PASS였다.

Hook events 10개는 malformed 0이었다. README content command의 Pre/Post는 같은 tool-use로 중복 제거돼 visit 1이 됐고 `git diff -- README.md`의 Hook event에는 document가 없었다. public `observe report`도 PROJECT, STATE, README를 각각 1회로 보고했다. 금지한 content field는 0건이었다.

## 최종 검증

- Engineering root `projectctl check`: 통과
- 공용 template `projectctl check`: 통과
- unittest: 29개 통과
- Project/Task Skills 공식 quick validation: 각각 통과
- compileall과 `git diff --check`: 통과
- actual Hook smoke: session 1/1 exit 0, hard acceptance 8/8 PASS

## 사람이 개입하는 지점

자동화하지 않는 지점은 유지된다.

1. Project Goal과 Current Goal 결정
2. Task 이름, Final Goal, Scope, Workflow, Completion Criteria 확인
3. Project 세션 종료와 Task 세션 시작
4. 조사·실험 설계 및 결과 해석
5. Task 종료 후 Project 세션 복귀
6. REPORT 결과 가치, Promotion 대상과 공식 위치 판단
7. ADR 필요성 판단
8. subagent 사용 허용

Task status가 completed/stopped이면 handoff 검토 시점은 결정적으로 알 수 있지만 Promotion 가치는 자동 판단하지 않는다.

## 남은 한계와 보수적 선택

- full-access와 instructions-only custom agent는 write sandbox가 아니다. Git baseline/audit는 사후 감지다.
- Hook은 일부 unified shell과 non-shell action을 놓칠 수 있다. coverage는 관찰 범위를 보여줄 뿐 absence를 증명하지 않는다.
- compaction과 subagent event는 실제 시나리오에서 동작이 없어 아직 actual trigger coverage가 없다. 필요 없는 동작을 coverage를 채우기 위해 호출하지 않았다.
- raw Codex JSONL은 prompt와 Agent message를 포함하므로 ignored `.harness/` 밖으로 자동 공개하지 않는다.
- dataset README metadata, ADR 의미, Promotion 가치 같은 형식이 아직 확정되지 않은 판단은 추가 자동화하지 않았다.
- Hook이나 Skill 실패가 본 작업을 막지 않도록 관찰은 fail-open, Skills는 explicit-only로 유지한다.

이 한계들은 현재 운영을 막는 결함이 아니라 보안·관찰 범위를 과장하지 않기 위한 명시적 경계다. 다음 자동화는 실제 사용에서 반복 누락이 관찰되고 입력·출력·실패 처리가 안정적으로 정의될 때만 추가하는 편이 적절하다.
