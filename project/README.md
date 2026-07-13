# Project

이 디렉터리는 Project와 독립 Task를 함께 운영하기 위한 공용 프로젝트 템플릿이다.

이 문서는 사람을 위한 소개와 시작 안내이며 Agent의 기본 작업 컨텍스트로 사용하지 않는다.

## Project Introduction

TBD

## Getting Started

1. `PROJECT.md`에 프로젝트 Goal과 Scope를 작성한다.
2. `STATE.md`에 Current Goal을 작성한다.
3. `python3 tools/projectctl.py check`를 통과시키고 최초 commit을 만든다.
4. Hook 명령을 검토하고 `python3 tools/projectctl.py session project`로 Project 세션을 연다.
5. 상세 절차는 `GUIDE.md`를 따른다.

## Reference Documents

- `PROJECT.md`: 프로젝트의 안정적인 목표와 범위를 관리한다.
- `STRUCTURE.md`: Project와 Task의 관계, 디렉터리 역할, 운영 절차를 설명한다.
- `STATE.md`: 현재 목표와 현재 목표의 Task만 관리한다.
- `AGENTS.md`: Project와 모든 Task가 함께 따르는 Agent 규칙을 정의한다.
- `GUIDE.md`: 생성, 세션 전환, Task lifecycle, Promotion, 관찰의 실행 절차를 안내한다.
