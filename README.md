# Project Harness Engineering

이 저장소는 여러 프로젝트에서 재사용할 Project/Task 운영 하네스를 설계하고 관리한다.

공용 배포 템플릿은 `project/`에 있다. 이 README는 사람을 위한 소개 문서이며 Agent의 기본 작업 컨텍스트로 사용하지 않는다.

## Repository Guide

- `PROJECT.md`: Harness Engineering Project의 목표와 범위
- `STATE.md`: 현재 Engineering 목표와 현재 Task
- `STRUCTURE.md`: 저장소 구조와 공용 템플릿 Promotion 절차
- `AGENTS.md`: Project와 Engineering Task가 함께 따르는 규칙
- `tasks/`: 공용 템플릿을 조사·설계·검증하는 독립 Task
- `project/`: 검토가 끝난 공용 Project 템플릿
- `project/GUIDE.md`: 새 Project 생성부터 Task·Promotion·관찰까지의 사용자 가이드
- `experiments/`: 공용 템플릿을 독립 Codex 세션으로 검증하는 시나리오와 실행 안내
- `tools/harness_experiment.py`: 통제 실험 실행 및 JSONL 액션 로그 분석기

## Create a Project

```bash
python3 tools/create_project.py /absolute/path/to/new-project
```

생성된 저장소에서 `PROJECT.md`와 `STATE.md`를 작성하고 최초 commit을 만든 뒤 [공용 운영 가이드](project/GUIDE.md)를 따른다. 구현 근거와 관찰 수치는 [실험 결과](experiments/RESULTS.md)에 있다.
