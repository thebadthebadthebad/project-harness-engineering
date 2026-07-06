# DECISIONS

이 문서는 Decision Record를 소유한다. 현재 작업 상태는 `WORK.md`, 구조의 최신 상태는 `DESIGN.md`가 소유한다.

## 기록 형식

각 결정은 다음 형식을 사용한다.

```markdown
## YYYY-MM-DD: 결정 제목

Status: accepted | proposed | superseded

Decision:
...

Rationale:
...

Alternatives:
...

Consequences:
...
```

## 2026-07-06: Knowledge Type을 문서 구조보다 먼저 정의한다

Status: accepted

Decision:
문서명이나 디렉터리보다 먼저 Knowledge Type, Ownership, Lifecycle을 정의한다.

Rationale:
문서명을 먼저 정하면 시간이 지나며 문서의 책임이 넓어지고 중복이 생긴다. Knowledge Type을 먼저 정의하면 어떤 정보가 어디에 속하는지 더 안정적으로 판단할 수 있다.

Alternatives:
- `docs/` 아래에 주제별 문서를 자유롭게 추가한다.
- 프로젝트별 도메인 문서를 먼저 만들고 나중에 정리한다.

Consequences:
- 새 문서를 만들기 전 기존 Knowledge Owner를 먼저 찾아야 한다.
- 문서 수보다 책임 경계가 더 중요한 설계 기준이 된다.

## 2026-07-06: Current State 대신 Work Context를 사용한다

Status: accepted

Decision:
현재 상태를 관리하는 Knowledge Type은 `Current State`가 아니라 `Work Context`로 정의한다.

Rationale:
`State`는 프로젝트 상태, 시스템 상태, 릴리즈 상태 등으로 넓게 해석될 수 있다. 실제로 필요한 것은 agent가 다음 작업을 이어가기 위한 현재 작업 맥락이다.

Alternatives:
- `STATE.md`를 사용한다.
- 모든 현재 상태를 `PROJECT.md`에 포함한다.

Consequences:
- 표현 문서는 `docs/WORK.md`를 사용한다.
- 현재 작업과 장기 지식이 섞이는 것을 줄인다.

## 2026-07-06: 공용 템플릿 산출물 위치는 templates/project-harness로 둔다

Status: accepted

Decision:
다른 프로젝트에 복사해 사용할 공용 하네스 템플릿은 `templates/project-harness/`에 둔다.

Rationale:
`repository-knowledge`는 개념 이름에 가깝고 폴더의 사용 목적을 직접 드러내지 못한다. `project-harness`는 복사해 사용할 프로젝트 하네스 템플릿이라는 목적을 더 명확히 표현한다.

Alternatives:
- `templates/repository-knowledge/`
- `templates/agent-project-docs/`
- `templates/base-project/`

Consequences:
- 향후 skills, hooks, rules, plugins, subagents도 이 템플릿 산출물 아래에서 확장할 수 있다.

## 2026-07-06: 본 프로젝트는 GitHub MCP를 사용해 PR 중심으로 운영한다

Status: accepted

Decision:
본 프로젝트는 GitHub MCP를 연결하고, 변경 관리와 리뷰 흐름은 GitHub PR을 중심으로 운영한다.

Rationale:
본 프로젝트는 공용 프로젝트 하네스를 지속적으로 개선하는 메타 프로젝트이므로, 변경 제안, 리뷰, 병합, 이력 확인을 GitHub PR 단위로 관리하는 것이 효율적이다. MCP를 사용하면 agent가 PR, issue, workflow 상태를 직접 조회하고 운영 자동화에 활용할 수 있다.

Alternatives:
- 로컬 git 이력과 문서만으로 변경을 관리한다.
- GitHub CLI만 사용하고 MCP는 사용하지 않는다.
- 외부 task tracker를 먼저 도입한다.

Consequences:
- GitHub PR은 변경 제안과 리뷰 흐름의 owner가 된다.
- repository docs는 장기 지식의 Source of Truth로 유지한다.
- GitHub issue/PR과 `docs/WORK.md`, `docs/DECISIONS.md` 사이의 책임 경계를 별도로 설계해야 한다.

## 2026-07-06: 본 프로젝트의 GitHub repository를 연결한다

Status: accepted

Decision:
본 프로젝트는 `https://github.com/thebadthebadthebad/project-harness-engineering.git` repository에서 관리한다.

Rationale:
본 프로젝트는 공용 프로젝트 하네스 환경을 지속적으로 개선하는 장기 프로젝트이므로, GitHub repository를 기준으로 변경 이력, PR, review, issue, workflow를 관리하는 것이 적합하다.

Alternatives:
- 로컬 repository로만 관리한다.
- 별도 private 저장소나 다른 이름의 repository를 사용한다.

Consequences:
- 첫 커밋 이후 변경은 가능한 한 branch와 PR 단위로 관리한다.
- GitHub MCP는 이 repository의 PR, issue, workflow 확인에 사용한다.
- repository docs는 장기 지식의 Source of Truth로 유지한다.
