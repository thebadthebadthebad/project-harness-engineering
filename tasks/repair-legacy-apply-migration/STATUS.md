# STATUS

## Status


doing

허용값은 `todo`, `doing`, `completed`, `stopped`다.

## Final Goal


실제 구버전 Project에 bundle 설치 도구를 적용하고 supported legacy 의미를 v2로 변환할 수 있도록 compatibility gate를 수정·검증한다.

## Work Plan


| Work | Status |
| --- | --- |
| 실제 failure fixture 고정 | doing |
| Installation-only check | todo |
| Legacy STATE·History normalization | todo |
| Migration parity 회귀 | todo |
| 전체 검증과 REPORT | todo |

Work Status는 `todo`, `doing`, `completed` 중 하나를 사용한다.

## Current Work

실제 failure fixture 고정

Task가 `completed` 또는 `stopped`이면 `None`으로 작성한다.
