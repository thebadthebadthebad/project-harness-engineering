# Engineering Session Root Design

## 책임 분리

- 루트 `AGENTS.md`: 새 세션에 자동 로드되는 저장소 정체성, bootstrap 명령, 지속 행동 규칙
- 루트 `PROJECT.md`: Harness Engineering의 안정적인 Goal과 Scope
- 루트 `STATE.md`: 현재 유지보수 Goal과 현재 Task만 관리
- 루트 `.codex/config.toml`: 신뢰된 Engineering 저장소의 권한, feature, project root와 subagent 한도
- 루트 `.codex/hooks.json`과 `hooks/observe.py`: content-free Git-local 관찰
- 루트 `.codex/agents/`: 사용자가 허용한 독립 읽기 작업의 좁은 custom agent
- `project/`: 다른 저장소로 복사되는 공용 템플릿이며 루트 Engineering 상태를 포함하지 않음

동적 상태를 `.codex` developer instructions에 복제하지 않는다. Codex는 `AGENTS.md`를 세션 시작 시 자동 로드하고, AGENTS가 지시한 `projectctl context`가 PROJECT와 STATE의 현재 값을 한 번 제공한다.

## 상태 전환

기존 Current Goal의 여섯 Engineering Task는 모두 completed이고 History에서 promoted로 기록됐다. 기존 표를 유지하면 현재 context 구현은 완료 Task를 Promotion 대기로 표현한다. 안정화 Goal을 종료하고 실제 사용자 적용·후속 개선 Goal로 전환하면서 Current Tasks를 비우면 새 세션은 정확히 다음 Task 정의부터 시작한다. 완료 근거는 Task REPORT, History와 `experiments/RESULTS.md`에 보존된다.

## Codex 설정

- `approval_policy = "never"`와 `sandbox_mode = "danger-full-access"`: 현재 full-access/no-approval 운영 의도를 직접 root 실행에도 적용
- `approvals_reviewer = "user"`: auto-review를 선택하지 않음을 명시. approval never에서는 reviewer 호출 자체가 없음
- `web_search = "live"`: 허용된 network를 최신 리서치에 사용
- `project_root_markers = [".git"]`: Harness Engineering Git root에서 설정·AGENTS 탐색 종료
- Hooks와 multi-agent stable features 활성화
- `max_threads = 3`, `max_depth = 1`: 병렬 읽기가 명확할 때만 직접 child를 제한적으로 사용

프로젝트 `.codex` layer와 Hook은 저장소가 신뢰된 경우에만 로드된다. 일반 세션은 `/hooks`에서 exact Hook을 검토·trust해야 한다. actual smoke 자동화만 config와 script digest를 먼저 검증한 뒤 trust를 우회한다.

## 검증 계획

1. TOML·JSON·Python 형식과 executable Hook fail-open 검사
2. 후보 Hook과 검증된 공용 Hook의 source 일치 확인
3. Engineering/public `projectctl check`와 전체 unittest
4. Promotion 후 root `projectctl context`가 빈 Current Tasks와 `define or create the next Task`를 출력하는지 확인
5. 새 `codex exec` session이 root AGENTS를 바탕으로 Engineering identity와 public template 관계를 설명하고 context를 정확히 한 번 호출하는지 확인
6. Git-local Hook event와 observability report 확인

## 공식 근거

- Codex는 새 run마다 Git root부터 현재 디렉터리까지 `AGENTS.md` instruction chain을 한 번 구성한다: <https://learn.chatgpt.com/docs/agent-configuration/agents-md>
- project `.codex/config.toml`과 project-local Hooks는 trusted repository에서 적용된다: <https://learn.chatgpt.com/docs/config-file/config-advanced>
- Hook은 sibling `hooks.json`에서 등록하고 non-managed command Hook은 exact definition을 검토·trust한다: <https://learn.chatgpt.com/docs/hooks>
