# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- Harness Engineering Git 루트를 Codex project root로 사용하는 `.codex` 설정 후보를 작성한다.
- 새 세션이 루트 Engineering Project와 `project/` 공용 배포 템플릿을 혼동하지 않도록 `AGENTS.md` 후보를 정리한다.
- 완료된 안정화 Goal을 후속 유지보수 Goal로 전환하고 Current Tasks를 비우는 `STATE.md` 후보를 작성한다.
- 실제 새 Codex 세션에서 context·Hook·권한 설정을 검증한다.

## Inputs

- 루트 `AGENTS.md`, `PROJECT.md`, `STATE.md`, `STRUCTURE.md`, `README.md`
- 공용 `project/.codex/` 설정과 Hook
- `project/tools/projectctl.py`의 context, session, check, observe 기능
- 완료 Task History와 `experiments/RESULTS.md`

## Data

별도 데이터는 없다. Hook raw event는 Git-local `.git/harness/`에만 기록한다.

## Workflow

```text
현재 context와 완료 기록 대조
→ 루트 AGENTS·STATE 후보 작성
→ Engineering .codex config·Hook·agents 후보 작성
→ Task-local 형식 검증과 REPORT
→ Project Promotion
→ actual 새 Codex session smoke와 최종 clean handoff 확인
```

## Outputs

- `output/root/AGENTS.md`: 새 세션 bootstrap 지침 후보
- `output/root/STATE.md`: 다음 유지보수 Goal과 빈 Current Tasks 후보
- `output/root/.codex/`: Engineering 루트 config, Hook, custom agents 후보
- `docs/notes/session-root-design.md`: 책임 분리와 검증 계획

## Completion Criteria

- 새 세션에서 자동 로드되는 AGENTS가 Engineering root와 공용 `project/` 템플릿의 관계를 명시한다.
- 새 세션은 `projectctl context` 한 번으로 다음 Engineering Task 정의 상태를 받는다.
- `.codex/config.toml`은 full-access, approval 없음, auto-review 미사용, Hooks, 보수적 multi-agent 한도를 명시한다.
- root Hook은 content-free Git-local observability를 유지하고 fail-open이다.
- custom agents는 독립 읽기 작업에만 사용되는 좁은 역할이다.
- Engineering/public `projectctl check`, 전체 unittest, config·Hook 형식 검사와 actual session smoke가 통과한다.
