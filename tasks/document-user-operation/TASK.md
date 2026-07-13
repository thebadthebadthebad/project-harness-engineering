# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- 공용 `project/` 템플릿의 실제 운영 순서를 사용자 관점에서 문서화한다.
- Engineering 저장소의 README, STRUCTURE, 실험 안내가 현재 구현과 일치하도록 변경 후보를 작성한다.
- 사람의 판단과 결정적 자동화의 경계를 명시한다.
- 구현과 문서의 최종 정합성 및 회귀 테스트를 검증한다.

## Inputs

- `PROJECT.md`, `STATE.md`, `STRUCTURE.md`, `README.md`, `AGENTS.md`
- `project/` 공용 템플릿 전체
- `experiments/README.md`, `experiments/RESULTS.md`, 커밋된 실험 요약
- `tools/create_project.py`, `tools/harness_experiment.py`
- 완료된 세 Engineering Task의 REPORT와 관련 History

## Data

별도 데이터 입력은 없다. 커밋된 실험 요약과 테스트 결과만 근거로 사용한다.

## Workflow

```text
현재 공식 문서와 구현의 불일치 조사
→ 사용자 운영 가이드 후보 작성
→ 루트·공용 템플릿·실험 참조 문서 변경 후보 작성
→ 결정적 명령과 사람 판단 지점 교차 검토
→ 전체 테스트 및 구조 검사
→ REPORT handoff 작성
```

## Outputs

- `output/GUIDE.md`: 공용 템플릿용 사용자 운영 가이드 후보
- `output/documentation-plan.md`: 공식 문서별 변경 후보와 검증 근거
- `docs/notes/final-validation.md`: 최종 검증 결과와 남은 한계

## Completion Criteria

- 새 Project 생성부터 Task 종료, Promotion, 관찰까지 명령과 책임 주체가 끊김 없이 설명된다.
- full-access, Hook trust, 명시적 Skill, 보수적 subagent의 제약이 현재 구현과 일치한다.
- 사람 판단 지점과 자동화 가능 지점이 혼동되지 않는다.
- 모든 공식 문서 변경 대상과 유지할 내용을 handoff에서 식별한다.
- 프로젝트 구조 검사, 단위 테스트, Skill 검증이 통과한다.
