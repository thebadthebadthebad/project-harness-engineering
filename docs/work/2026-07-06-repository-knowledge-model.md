# Repository Knowledge Model 초기 구현

Status: completed

## Goal

다양한 AI Agent 프로젝트에서 재사용할 수 있는 Repository Knowledge Model을 템플릿으로 구현하고, 현재 저장소에 적용한다.

## Scope

- Knowledge Type 기반 문서 ownership 모델 정의
- 현재 저장소의 `AGENTS.md`와 `docs/` 구성
- 공용 템플릿 `templates/project-harness/` 작성
- optional knowledge owner인 `docs/work/`, `docs/references/` 구조 추가

## Related Owners

- `docs/INTENT.md`
- `docs/DESIGN.md`
- `docs/DECISIONS.md`
- `docs/WORK.md`
- `templates/project-harness/`

## Acceptance Criteria

- 공용 템플릿에 `AGENTS.md`, `MAP.md`, `INTENT.md`, `WORK.md`, `DESIGN.md`, `DECISIONS.md`가 있다.
- 현재 프로젝트에도 동일한 Knowledge Model이 적용되어 있다.
- `work/`와 `references/`의 책임과 out of scope가 명확하다.
- 템플릿 폴더명은 사용 목적을 드러내는 `project-harness`를 사용한다.

## Result

초기 구현은 완료됐다. durable knowledge는 다음 문서에 반영됐다.

- 시스템 모델: `docs/DESIGN.md`
- 현재 상태: `docs/WORK.md`
- 결정 이유: `docs/DECISIONS.md`
- 외부 조사 요약: `docs/references/repository-knowledge-cases.md`

## Handoff

다음 작업은 skills, hooks, rules, plugins, subagents 같은 하네스 구성요소를 이 Knowledge Model 안에서 어떻게 관리할지 설계하는 것이다.
