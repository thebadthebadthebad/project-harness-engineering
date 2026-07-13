# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- `scripts/projectctl.py`를 기존 CLI 호환 진입점으로 유지하면서 작은 모듈로 분리한다.
- Project/Task context를 동적 정보 중심으로 줄이고, 종료 전 handoff만 기본 Project context에 포함한다.
- Project/Task 세션 역할을 환경변수로 전달하고 Project 전용 lifecycle 명령의 우발적 Task 실행을 차단한다.
- 확정된 구조 규칙을 검사하는 `check`, 명시적 `task handoff`, 판단 이후 기록만 수행하는 `promotion record`를 추가한다.
- 공용 템플릿에서 새 Git Project를 안전하게 만드는 독립 생성 도구를 작성한다.
- linked data checksum 충돌과 상태 파일의 비원자적 갱신을 수정한다.
- Hook, Skill, Subagent 설정, 실험 실행, 최종 사용자 가이드 작성은 후속 Task 범위다.

## Inputs

| Input | Use |
| --- | --- |
| `scripts/projectctl.py` | 현재 `project/tools/projectctl.py`의 Task snapshot |
| `../../tests/test_projectctl.py` | 기존 CLI와 lifecycle 회귀 동작 참고 |
| `../../project/STRUCTURE.md` | 유지해야 하는 Project/Task 운영 계약 |
| `../../.harness/analysis-v2-final/REPORT.md` | context 축소 전 기준 실험 결과 |

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
기존 CLI와 테스트가 보장하는 동작 목록 작성
→ 문서 파싱, lifecycle, context, 관찰 지원의 최소 모듈 경계 정의
→ 기존 명령의 인자·출력·exit code를 유지하는 candidate 구현
→ 동적 context, 세션 역할 가드, check, handoff, Promotion 기록 구현
→ 새 Project 생성 도구와 checksum·atomic write 수정 구현
→ 기존 회귀 및 신규 오류·경계 테스트 실행
→ 결과와 Promotion 대상 파일을 REPORT에 정리
```

## Outputs

- `scripts/projectctl.py`: 호환 CLI 진입점 candidate
- `scripts/project_harness/`: 역할별 구현 모듈
- `scripts/create_project.py`: 공용 템플릿 복사·Git 초기화 도구 candidate
- `scripts/tests/`: 기존 회귀와 신규 경계 테스트
- `docs/notes/design.md`: 모듈 책임, 공개 CLI, 호환성 메모

## Completion Criteria

- 기존 `context`, `session`, `task create|validate|activate|baseline|audit|close|status` 회귀 테스트가 통과한다.
- Task 역할에서 Project 전용 lifecycle 명령이 실패하고 자신의 context·validate는 성공한다.
- 기본 Project context는 close된 Task의 REPORT 전문과 정적 명령 설명을 반복 출력하지 않는다.
- `check`, `task handoff`, `promotion record`, 새 Project 생성의 정상·실패 경로가 테스트된다.
- 중첩 linked data의 동일 파일명 checksum이 서로 덮어쓰이지 않는다.
- 상태와 메타데이터 파일 갱신 실패 시 기존 내용이 보존된다.
- 구현은 Python 표준 라이브러리만 사용하고 각 공개 함수의 역할과 입력·출력이 명확하다.
- Task 외부 파일은 수정하지 않고, 모든 candidate와 검증 결과가 REPORT의 Relevant Files에 기록된다.
