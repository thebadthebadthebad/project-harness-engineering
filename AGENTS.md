# AGENTS.md

## 역할

이 저장소는 반복 사용되는 공용 프로젝트 하네스 자체가 아니라, 다양한 AI Agent 프로젝트에서 재사용할 수 있는 공용 프로젝트 하네스를 설계하고 구축하는 메타 프로젝트다.

Agent는 이 저장소에서 다음 두 층위를 구분한다.

- 이 저장소의 작업 지식: `docs/`
- 다른 프로젝트에 복사해 사용할 템플릿 산출물: `templates/project-harness/`

## 읽기 순서

작업을 시작할 때는 다음 순서로 문서를 확인한다.

1. `AGENTS.md`
2. `docs/MAP.md`
3. `docs/WORK.md`

필요할 때만 다음 문서를 읽는다.

- 목적과 범위가 필요하면 `docs/INTENT.md`
- 구조와 경계가 필요하면 `docs/DESIGN.md`
- 결정 이유가 필요하면 `docs/DECISIONS.md`
- 템플릿 내용을 수정할 때는 `templates/project-harness/`의 대응 파일

## Knowledge Ownership

문서는 주제가 아니라 Knowledge Type의 owner다. 같은 사실을 여러 문서에 반복해서 쓰지 않는다.

- Agent Protocol: `AGENTS.md`
- Knowledge Map: `docs/MAP.md`
- Project Intent: `docs/INTENT.md`
- Work Context: `docs/WORK.md`
- System Model: `docs/DESIGN.md`
- Decision Record: `docs/DECISIONS.md`

## 작성 규칙

- 새 문서를 만들기 전에 기존 owner 문서에 추가할 수 있는지 먼저 판단한다.
- 현재 상태는 `WORK.md`, 목적은 `INTENT.md`, 구조는 `DESIGN.md`, 이유는 `DECISIONS.md`에 쓴다.
- 템플릿 산출물과 이 저장소 운영 문서를 혼동하지 않는다.
- 문서는 한국어 중심으로 작성하되 파일명, 코드, 도구명, 일반 기술 용어는 영어를 자연스럽게 사용한다.
- 임시 작업 메모는 장기 지식으로 확정되기 전까지 owner 문서에 과도하게 확산하지 않는다.

## 작업 완료 시

작업을 마칠 때 다음을 점검한다.

- `docs/WORK.md`의 현재 상태가 최신인가?
- 구조 변경은 `docs/DESIGN.md`에 반영됐는가?
- 장기 결정은 `docs/DECISIONS.md`에 기록됐는가?
- 템플릿 변경이 있었다면 `templates/project-harness/`와 현재 프로젝트 적용 문서가 서로 의도대로 다른가?
