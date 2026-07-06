# work

이 디렉터리는 Work Unit Context를 소유한다. `WORK.md`가 현재 작업의 요약 상태를 소유하고, 이 디렉터리는 여러 세션에 걸쳐 이어지는 개별 작업의 실행 맥락을 소유한다.

## 생성 기준

작업 문서는 다음 조건 중 하나 이상을 만족할 때만 만든다.

- 작업이 여러 세션에 걸친다.
- 여러 문서나 코드 영역을 함께 수정한다.
- handoff가 필요하다.
- acceptance criteria, 진행 메모, 검증 결과를 별도로 추적해야 한다.

단순한 한 번의 수정, 짧은 질문 답변, owner 문서 하나만 수정하는 작업은 별도 work 문서를 만들지 않는다.

## 책임

work 문서는 특정 작업의 실행 맥락만 소유한다.

- 목표와 범위
- 관련 owner 문서
- acceptance criteria
- 진행 메모
- handoff
- 검증 결과

## Out of Scope

work 문서는 영구 지식의 최종 저장소가 아니다.

- 프로젝트 목적은 `docs/INTENT.md`로 승격한다.
- 구조와 경계는 `docs/DESIGN.md`로 승격한다.
- 결정 이유는 `docs/DECISIONS.md`로 승격한다.
- 현재 작업 요약은 `docs/WORK.md`에 남긴다.
- 외부 근거는 `docs/references/`에 남긴다.

## 완료 기준

작업이 끝나면 durable knowledge를 적절한 owner 문서로 반영한다. 이후 work 문서는 완료 상태로 남기거나, 장기 참조 가치가 낮으면 정리할 수 있다.
