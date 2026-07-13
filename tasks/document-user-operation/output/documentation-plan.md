# Documentation Promotion Plan

## 문제

공식 구현에는 modular `projectctl`, 구조 검사, handoff, Promotion 기록, 명시적 Skills, 관찰 Hooks, custom readers와 두 통제 실험이 포함됐지만 참조 문서는 이전 단계의 설명을 일부 유지한다. 특히 루트 `STRUCTURE.md`의 “Hook과 Skill 미포함”은 현재 상태와 정면으로 충돌한다.

## 변경 후보

| 공식 파일 | 변경 | 이유 |
| --- | --- | --- |
| `project/GUIDE.md` | `output/GUIDE.md`를 새 사용자 운영 가이드로 Promotion | 처음부터 끝까지 재현 가능한 단일 진입점이 없다. 기존 문서 책임으로는 단계별 튜토리얼을 담기 어렵다. |
| `project/README.md` | GUIDE 링크, 현재 lifecycle·관찰 시작 순서로 축약 | 기존 Getting Started가 새 명령과 Hook trust를 누락한다. |
| `project/STRUCTURE.md` | 구조·상태 의미는 유지하고 현재 deterministic commands, Skills/Hooks/subagent 경계와 간결한 흐름으로 교정 | 현재 구현과 절차를 한 곳에서 일치시킨다. GUIDE와 중복되는 상세 예시는 두지 않는다. |
| `README.md` | 생성 도구, 공용 GUIDE, 실험 결과 진입점 추가 | Engineering 저장소의 사람용 index를 완성한다. |
| `STRUCTURE.md` | 사용자 승인형 Engineering Promotion 서술을 현재 자동 수행된 운영 기록으로 일반화하고 Hook/Skill 미포함 문구 제거 | 구현과 상충하는 공식 설명을 제거한다. |
| `experiments/README.md` | 두 시나리오, Hook digest trust, compare/analyze, 출력·privacy·acceptance 설명 갱신 | runner가 현재 제공하는 기능을 재현 가능하게 설명한다. |
| `experiments/RESULTS.md` | 교정 Hook의 unit 검증 상태와 raw 증거 한계를 정확히 유지 | 실제 run을 교정 후 run인 것처럼 오해하지 않게 한다. |
| `tasks/_template/AGENTS.md` | 공용 Task 규칙과 같은 원칙으로 중복된 상위 경계·수동 문서 검사 지시를 줄임 | Engineering Task에서 이미 시스템/런처가 처리하는 규칙과 문서 재방문 노이즈를 제거한다. 명령 경로 차이만 유지한다. |

## 유지할 경계

- `README.md`: 사람용 소개와 링크만 담당한다.
- `PROJECT.md`: Goal과 Scope만 담당하며 Information 또는 Non-goals를 추가하지 않는다.
- `STATE.md`: Current Goal과 현재 Task만 관리하며 로그를 쌓지 않는다.
- `STRUCTURE.md`: 문서·디렉터리 책임과 운영 상태 전이를 정의한다.
- `GUIDE.md`: 사용자가 그대로 따라 할 수 있는 명령, 검토 지점, 장애 대응을 담당한다.
- Task `TASK.md`: 실행 계약, `STATUS.md`: 현재 상태, `REPORT.md`: 종료 handoff의 책임을 유지한다.
- `docs/history/`: 사건 기록, `docs/adr/`: 날짜 없는 장기 결정 이름과 근거를 유지한다.

## 검증 기준

- 모든 문서의 명령이 현재 `projectctl --help`와 일치한다.
- normal session과 experiment Hook trust 우회가 구분된다.
- full-access를 sandbox 보안으로 표현하지 않는다.
- Skills가 explicit-only이고 subagent가 사용자 승인형 독립 읽기 작업으로 제한됨을 명시한다.
- Promotion 판단은 자동화하지 않고 `promotion record`는 이미 내려진 결정을 기록한다고 설명한다.
- `projectctl check`, 전체 unittest, 두 Skill quick validation이 통과한다.
