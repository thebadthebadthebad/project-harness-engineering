# AGENTS

이 규칙은 Project의 공식 `docs/`에 적용된다. Task 내부 문서에는 적용되지 않는다.

- 새 문서나 디렉터리는 명확한 장기 책임이 있을 때만 만든다.
- 성격이 다른 문서를 한 디렉터리에 섞지 않는다.
- Task의 조사 원문, 실험 로그, 자유 메모는 공식 문서로 Promotion하기 전까지 Task 내부에 둔다.

## ADR

- `adr/`에는 프로젝트 전체에 장기 영향을 주는 결정만 기록한다.
- ADR이 필요한지는 Project Agent와 사용자가 판단한다.
- ADR 파일명은 날짜 없이 `<decision-name>.md` 형식의 영문 kebab-case를 사용한다.
- ADR은 최소한 `Decision`, `Reason`, `Impact`를 설명한다.
- Task 내부의 임시 판단, 실험 중간 결정, 작업 로그는 ADR로 기록하지 않는다.

## History

- `history/`는 Project 사건을 찾기 위한 짧은 기록이며 Task REPORT의 요약본이 아니다.
- 기본 파일명은 `YYYY-MM-DD-HHMM-<action>-<task-name>.md`다.
- Task 관련 action은 `completed`, `stopped`, `promoted`, `not-promoted`를 사용한다.
- 내용에는 사건, Task 경로, 관련 공식 경로만 간결하게 기록한다.
- 중요한 결정의 이유는 History가 아니라 ADR에 기록한다.
