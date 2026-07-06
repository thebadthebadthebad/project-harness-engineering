# WORK

이 문서는 현재 Work Context를 소유한다. 장기 목적, 시스템 구조, 결정 이유는 각각 `INTENT.md`, `DESIGN.md`, `DECISIONS.md`가 소유한다.

## Active Goal

공용 AI Agent 프로젝트 하네스에 사용할 Repository Knowledge Model의 초기 버전을 유지하고, 다음 하네스 엔지니어링 대상을 점진적으로 설계한다.

## Active Work

- Repository Knowledge Model 초기 구현은 완료됐다.
- 현재 저장소는 `AGENTS.md`와 `docs/`에 같은 모델을 적용하고 있다.
- 재사용 템플릿은 `templates/project-harness/`에 있다.
- 본 프로젝트는 GitHub MCP를 연결했으며, PR 중심 운영을 전제로 한다.
- 본 프로젝트의 GitHub repository는 `https://github.com/thebadthebadthebad/project-harness-engineering.git`이다.

## Next Actions

- 하네스 엔지니어링 대상인 skills, hooks, rules, plugins, subagents를 어떤 Knowledge Type으로 관리할지 설계한다.
- GitHub PR 기반 운영 규칙을 본 프로젝트와 공용 프로젝트 템플릿에 어떻게 반영할지 설계한다.
- 템플릿 복사 또는 동기화를 자동화할 필요가 있는지 판단한다.
- `docs/work/`와 `docs/references/`가 실제 운영에서 과도한 문서 증가를 유발하지 않는지 다음 작업에서 검증한다.

## Open Questions

- `docs/work/`가 필요한 수준의 multi-session 작업 관리가 언제 발생하는지 기준을 더 구체화할 것인가?
- 템플릿 복사 또는 동기화를 자동화하는 스크립트를 둘 것인가?
- 향후 `DESIGN.md`에서 architecture를 독립 문서로 승격할 조건을 어떻게 검증할 것인가?
- GitHub issue/PR과 repository docs 사이의 Source of Truth 경계를 어디까지 강제할 것인가?

## Handoff

현재 합의된 기본 모델은 다음과 같다.

- `AGENTS.md`: agent protocol
- `docs/MAP.md`: knowledge routing
- `docs/INTENT.md`: project intent
- `docs/WORK.md`: active work context
- `docs/DESIGN.md`: system model
- `docs/DECISIONS.md`: decision rationale
- `docs/work/`: multi-session work unit context
- `docs/references/`: external evidence and references
- `templates/project-harness/`: 다른 프로젝트에 복사할 공용 하네스 템플릿
- GitHub MCP: 본 프로젝트의 PR, issue, workflow 확인과 운영 자동화에 사용
- Git remote: `https://github.com/thebadthebadthebad/project-harness-engineering.git`

초기 파일 생성은 완료됐다. 다음 작업은 문서 구조 자체보다 하네스의 다음 구성요소를 이 Knowledge Model 안에서 어떻게 관리할지 정하는 것이다.
