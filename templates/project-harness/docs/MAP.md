# MAP

이 문서는 repository knowledge의 routing table이다. 본문 지식을 설명하지 않고, 어떤 Knowledge Type을 어디에서 관리하는지만 정의한다.

## Knowledge Owners

| Knowledge Type | Owner | 읽는 조건 |
| --- | --- | --- |
| Agent Protocol | `AGENTS.md` | 항상 |
| Knowledge Map | `docs/MAP.md` | 항상 |
| Project Intent | `docs/INTENT.md` | 목적, 범위, 성공 기준 확인이 필요할 때 |
| Work Context | `docs/WORK.md` | 항상 |
| System Model | `docs/DESIGN.md` | 구조, 경계, 시스템 모델을 다룰 때 |
| Decision Record | `docs/DECISIONS.md` | 결정 이유, 대안, trade-off 확인이 필요할 때 |
| Work Unit Context | `docs/work/` | 여러 세션에 걸친 개별 작업 맥락이 필요할 때 |
| Evidence / Reference | `docs/references/` | 외부 근거, 조사 사례, 참고 링크가 필요할 때 |

## 탐색 순서

1. `AGENTS.md`에서 agent protocol을 확인한다.
2. 이 문서에서 지식 owner를 확인한다.
3. `docs/WORK.md`에서 현재 작업 맥락을 확인한다.
4. 필요한 owner 문서만 추가로 읽는다.

## 새 문서 생성 기준

새 문서는 다음 조건을 모두 만족할 때만 만든다.

- 기존 owner 문서가 소유하지 않는 Knowledge Type이다.
- 한 번 쓰고 버릴 임시 정보가 아니다.
- 기존 문서의 섹션으로 넣으면 책임 경계가 흐려진다.
- 다른 agent가 나중에 독립적으로 찾아야 한다.
- lifecycle이 기존 owner 문서와 다르다.

기본값은 새 문서 생성이 아니라 기존 owner 문서 수정이다.
