# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

기존 단일 파일 `projectctl.py`를 여섯 책임의 표준 라이브러리 모듈과 얇은 CLI 진입점으로 재구성했다. 기존 Task lifecycle을 유지하면서 동적 context, Task 역할 가드, 구조 검사, 명시적 handoff, 판단 이후 Promotion 기록, 새 Project 생성 기능을 candidate로 구현했다.

## Final Goal and Result

최종 목표를 달성했다. lifecycle과 context의 기존 핵심 동작은 유지되고, Project 전용 명령은 launcher가 선언한 Task 세션에서 거부된다. closed Task REPORT는 기본 Project context에 재주입되지 않으며, 새 결정적 명령과 안전한 Project 생성 경로가 테스트된다.

## Findings

- `projectctl.py`를 얇게 유지하면 CLI 호환성과 내부 책임 변경을 분리할 수 있다.
- Project context에는 close를 기다리는 Task handoff만 필요하다. 완료 Task의 상태 행은 유지해도 REPORT 본문을 계속 포함할 이유는 없다.
- full-access 환경의 역할 경계는 보안 sandbox가 아니라 우발적 lifecycle 실행을 막는 명시적 guard로 구현할 수 있다.
- linked directory checksum 키에 target-relative 경로가 없으면 서로 다른 하위 디렉터리의 동일 파일명이 충돌한다.
- Promotion 도구는 가치 판단이나 파일 복사를 하지 않고 이미 내려진 결정을 History에 기록하는 데 한정해야 한다.

## Work and Validation

- `python3 -m unittest discover -s scripts/tests -v`: 5개 테스트 통과.
- 전체 completed lifecycle, close 전후 handoff 포함 여부, Promotion 기록을 임시 Git Project에서 검증했다.
- Task 역할에서 own context·validate 성공 및 activate·다른 Task validate 실패를 검증했다.
- 두 하위 디렉터리의 `same.txt` checksum 키가 별도로 저장되는지 검증했다.
- `check`의 정상 경로와 날짜형 ADR 파일명 실패, 원자적 replace 실패 시 기존 파일 보존, 새 Project 생성 및 기존 목적지 거부를 검증했다.
- `python3 -m compileall -q scripts`: 성공.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| scripts/projectctl.py | code | 기존 CLI를 유지하는 얇은 candidate 진입점 |
| scripts/project_harness | code | 문서, 저장소, lifecycle, context, 관찰, CLI 책임별 candidate 패키지 |
| scripts/create_project.py | code | 공용 템플릿 복사·Git 초기화·구조 검사 candidate |
| scripts/tests/test_workflow_core.py | test | 기존 lifecycle과 신규 경계 통합 테스트 |
| docs/notes/design.md | documentation | 모듈 책임, 호환성, 새 명령과 context 규칙 |

## Limitations

- Hook 이벤트 수집·관찰 보고서, 명시 호출형 Skill, custom agent 설정은 이 Task 범위에 포함하지 않았다.
- 역할 guard는 launcher 환경변수가 있는 세션의 우발적 명령을 방지하며 보안 경계가 아니다.
- 사람의 Promotion 가치 판단과 공식 파일 선택은 의도적으로 자동화하지 않았다.

## Project Follow-up

Project가 candidate 모듈과 생성 도구를 공식 `project/tools/`, 루트 `tools/`, 회귀 테스트에 Promotion한다. 이후 별도 Task에서 Hook·Skill·custom agent와 관찰 보고 기능을 이 안정된 CLI 위에 추가하고, 통제 실험 및 사용자 가이드를 완성한다.
