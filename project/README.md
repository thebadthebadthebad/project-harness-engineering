# Project

이 디렉터리는 Project와 독립 Task를 함께 운영하기 위한 공용 프로젝트 템플릿이다.

이 문서는 사람을 위한 소개와 시작 안내이며 Agent의 기본 작업 컨텍스트로 사용하지 않는다.

## Project Introduction

TBD

## Getting Started

1. `PROJECT.md`에 프로젝트 목표와 범위를 작성한다.
2. `STATE.md`에 현재 목표와 현재 목표에 필요한 Task를 작성한다.
3. 새 Project 세션에서 `python3 tools/projectctl.py context`로 현재 운영 정보를 한 번 확인한다.
4. 새 Task는 `python3 tools/projectctl.py task create ...`로 만든다.
5. 생성 결과를 확인한 뒤 Task를 activate하고 baseline을 만든다.
6. Task Agent가 REPORT와 STATUS를 종료 상태로 작성하면 Project 세션으로 돌아와 `task close`를 수행한다.
7. Promotion은 사용자가 명시적으로 요청할 때만 검토한다.

## Reference Documents

- `PROJECT.md`: 프로젝트의 안정적인 목표와 범위를 관리한다.
- `STRUCTURE.md`: Project와 Task의 관계, 디렉터리 역할, 운영 절차를 설명한다.
- `STATE.md`: 현재 목표와 현재 목표의 Task만 관리한다.
- `AGENTS.md`: Project와 모든 Task가 함께 따르는 Agent 규칙을 정의한다.
