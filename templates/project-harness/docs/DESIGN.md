# DESIGN

이 문서는 System Model을 소유한다. 결정의 이유는 `DECISIONS.md`, 현재 진행 상태는 `WORK.md`가 소유한다.

## System Overview

TODO: 만들고 있는 대상의 구조를 간단히 설명한다.

## Components

TODO: 주요 구성요소와 각 책임을 정리한다.

## Boundaries

TODO: 구성요소 간 경계, 책임 분리, 의존 방향을 정리한다.

## Data or Control Flow

TODO: 데이터 흐름이나 제어 흐름이 중요하다면 설명한다.

## Invariants

TODO: 유지되어야 하는 구조적 원칙이나 깨지면 안 되는 조건을 정리한다.

## Extension Points

TODO: 향후 확장 가능성이 있는 지점을 정리한다.

## Optional Splits

다음 조건이 생기면 별도 문서로 분리할 수 있다.

- `docs/ARCHITECTURE.md`: 시스템 codemap이 `DESIGN.md`와 다른 lifecycle을 가질 때

## Work and References

- `docs/work/`는 여러 세션에 걸친 개별 작업의 실행 맥락을 소유한다.
- `docs/references/`는 외부 근거와 참고 자료를 소유한다.
- 두 디렉터리는 durable knowledge의 최종 저장소가 아니다. 작업 결과는 `INTENT.md`, `DESIGN.md`, `DECISIONS.md`, `WORK.md` 중 적절한 owner로 승격한다.
