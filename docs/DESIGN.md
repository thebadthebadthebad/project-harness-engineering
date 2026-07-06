# DESIGN

이 문서는 이 저장소와 공용 프로젝트 하네스 템플릿의 System Model을 소유한다. 결정의 이유는 `DECISIONS.md`, 현재 진행 상태는 `WORK.md`가 소유한다.

## Repository Knowledge Model

이 프로젝트의 문서 구조는 파일 이름보다 Knowledge Type을 우선한다.

```text
Knowledge Type
  -> Ownership
    -> Lifecycle
      -> Representation
```

## Core Knowledge Types

| Knowledge Type | 책임 | Lifecycle | Representation |
| --- | --- | --- | --- |
| Agent Protocol | agent 행동 규칙과 문서 탐색 규칙 | 장기 유지, 작고 안정적 | `AGENTS.md` |
| Knowledge Map | 지식 owner와 탐색 경로 | 문서 구조 변경 시 갱신 | `docs/MAP.md` |
| Project Intent | 목적, 범위, 성공 기준 | 거의 변하지 않음 | `docs/INTENT.md` |
| Work Context | 현재 목표, 진행 작업, 다음 액션 | 자주 갱신, 현재성 중심 | `docs/WORK.md` |
| System Model | 구조, 경계, 구성요소, invariant | 프로젝트 동안 계속 갱신 | `docs/DESIGN.md` |
| Decision Record | 결정, 이유, 대안, trade-off | 누적형, 가능하면 append-only | `docs/DECISIONS.md` |
| Work Unit Context | multi-session 작업의 실행 맥락 | 작업 중 유지, 완료 후 정리 | `docs/work/` optional |
| Evidence / Reference | 외부 근거와 참고 자료 | 필요할 때 보관 | `docs/references/` optional |

## Template Layout

재사용 가능한 공용 하네스 템플릿은 다음 위치에 둔다.

```text
templates/project-harness/
  AGENTS.md
  docs/
    MAP.md
    INTENT.md
    WORK.md
    DESIGN.md
    DECISIONS.md
    work/
      README.md
      TEMPLATE.md
    references/
      README.md
      TEMPLATE.md
```

`templates/project-harness/`는 다른 프로젝트에 복사해 사용할 산출물이다. 이 저장소의 현재 작업 상태를 직접 소유하지 않는다.

## Current Project Layout

현재 저장소 자체도 동일한 Knowledge Model을 적용한다.

```text
AGENTS.md
docs/
  MAP.md
  INTENT.md
  WORK.md
  DESIGN.md
  DECISIONS.md
  work/
    README.md
    2026-07-06-repository-knowledge-model.md
  references/
    README.md
    repository-knowledge-cases.md
templates/
  project-harness/
    AGENTS.md
    docs/
      MAP.md
      INTENT.md
      WORK.md
      DESIGN.md
      DECISIONS.md
      work/
        README.md
        TEMPLATE.md
      references/
        README.md
        TEMPLATE.md
```

## Boundary Rules

- `AGENTS.md`는 실행 규칙만 소유하고 프로젝트 지식 본문을 소유하지 않는다.
- `MAP.md`는 routing만 소유하고 본문 요약을 소유하지 않는다.
- `INTENT.md`는 목적과 범위만 소유하고 현재 진행 상태를 소유하지 않는다.
- `WORK.md`는 현재 작업 맥락만 소유하고 장기 설계를 소유하지 않는다.
- `DESIGN.md`는 구조와 경계만 소유하고 결정의 이유를 소유하지 않는다.
- `DECISIONS.md`는 결정 이유만 소유하고 작업 로그를 소유하지 않는다.
- `docs/work/`는 개별 작업 실행 맥락만 소유하고 durable knowledge의 최종 저장소가 아니다.
- `docs/references/`는 외부 근거만 소유하고 프로젝트의 최종 판단을 소유하지 않는다.

## Extension Points

다음 항목은 필요해질 때 추가한다.

- `docs/ARCHITECTURE.md`: 시스템 codemap이 `DESIGN.md`와 다른 lifecycle을 가질 때
- scripts: 템플릿 복사, 검증, 동기화가 반복될 때
- skills/hooks/plugins/subagents: agent 작업을 안정화하는 구현 수단이 필요할 때
