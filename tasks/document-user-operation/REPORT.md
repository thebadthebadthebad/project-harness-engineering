# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

공용 하네스로 새 Project 생성부터 독립 Task 수행, REPORT handoff, Project 종료, 선택 Promotion, Skills·subagent·관찰 보고서까지 재현하는 사용자 가이드 후보를 완성했다. 공식 구현과 기존 문서를 대조해 루트·공용 템플릿·실험 안내의 구체적인 교정 대상을 정리하고 전체 회귀 검증을 수행했다.

## Final Goal and Result

최종 목표를 달성했다. 가이드는 사람의 세션 전환·가치 판단과 `projectctl`의 결정적 검사를 구분하고, full-access와 network 허용, Hook trust, explicit-only Skills, instructions-only custom agent의 제약을 현재 구현 그대로 설명한다. 사용자가 Project 수행 결과를 검토할 파일 순서와 장애 대응도 포함한다.

## Findings

- `README`, `STRUCTURE`, `GUIDE`를 소개·구조 계약·실행 튜토리얼로 분리해야 중복 없이 전체 운영 흐름을 설명할 수 있다.
- 루트 `STRUCTURE.md`의 “Hook과 Skill 미포함” 문구는 현재 구현과 충돌한다.
- normal interactive session은 사람이 Hook을 trust해야 하지만 실험 runner는 exact config·script digest 검증 뒤에만 trust를 우회한다.
- completed는 Project handoff/close 조건이며 Promotion 자동 시작 조건이 아니다. `promotion record`도 이미 내려진 판단만 기록한다.
- Engineering 루트 구조 검사는 공용 Project의 `src/`, `data/`를 요구해 실패한다. 책임 없는 빈 디렉터리 추가보다 구조 유형을 구분하는 별도 코드 수정이 적합하다.
- 루트 Task AGENTS는 공용 Task AGENTS보다 오래된 반복 읽기·경계 지시를 포함해 함께 단순화할 필요가 있다.

## Work and Validation

- `python3 project/tools/projectctl.py --root project check`: 통과.
- `python3 -m unittest discover -s tests -v`: 26개 통과.
- `python3 -m compileall -q project tools`: 통과.
- 공식 skill-creator quick validator로 Project/Task Skills 각각 통과.
- `git diff --check`와 Task doing 계약 검사 통과.
- 커밋된 두 통제 실험의 6개 독립 세션, acceptance, token·문서 방문·Hook coverage 수치를 가이드의 관찰 및 검토 절차와 대조했다.
- 존재하지 않는 `experiments/tests`를 지정한 최초 보조 명령은 discovery 오류였고, 실제 단일 test suite인 루트 `tests/`를 다시 실행해 전부 통과했다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| output/GUIDE.md | documentation | 새 Project 생성부터 Promotion·관찰까지의 사용자 운영 가이드 후보 |
| output/documentation-plan.md | documentation | 공식 파일별 변경 내용, 책임 유지 기준, 검증 기준 |
| docs/notes/final-validation.md | evidence | 문서 불일치, 검증 결과, 새 결함과 남은 한계 |

## Limitations

- Engineering 루트 `projectctl check` 결함은 이 문서 Task의 범위를 넓히지 않고 별도 코드 Task에서 수정해야 한다.
- 교정된 Hook document 추출은 unit fixture로 통과했지만 교정 이후 실제 Codex 세션으로 다시 실행하지 않았다.
- observability와 custom agent는 full-access 환경의 보안 경계가 아니다.

## Project Follow-up

Project가 GUIDE와 참조 문서 교정을 공식 위치에 Promotion한다. 그 다음 별도 Task에서 Engineering/public 구조 검사 구분을 구현하고, 전체 테스트와 최소 actual Hook smoke를 실행한 뒤 최종 결과를 다시 분석한다.
