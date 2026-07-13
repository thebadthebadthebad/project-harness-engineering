# STRUCTURE

이 저장소는 공용 Project/Task 템플릿을 설계·검증하는 Engineering Project다.

## Repository Responsibilities

- 루트 `PROJECT.md`, `STATE.md`, `docs/`, `tasks/`: Harness Engineering의 공식 내용과 작업 공간
- `project/`: 다른 프로젝트에 복사할 공용 배포 템플릿
- 루트 `tasks/_template/`: Engineering Project가 사용하는 Task 템플릿
- `project/tasks/_template/`: 공용 배포용 Task 템플릿
- `project/tools/projectctl.py`: Engineering 루트와 배포 Project가 함께 사용하는 결정적 관리 도구

## Engineering Workflow

Engineering Task 생성·실행·완료 절차는 공용 `project/STRUCTURE.md`와 동일하다. 새 세션에서는 context를 한 번 실행하며 Engineering 루트에서는 다음 명령을 사용한다.

```bash
python3 project/tools/projectctl.py --root . context
python3 project/tools/projectctl.py --root . task <command>
```

Task 세션은 full-access와 network 허용으로 실행한다. Project write는 sandbox로 차단하지 않으며 Git 기준점과 data checksum으로 예상 외 변경을 감사한다.

## Public Template Promotion

```text
Engineering Task completed 및 audit 통과
    ↓
사용자가 공용 템플릿 Promotion 요청
    ↓
Project Agent가 project/ 변경 계획 제시
    ↓
사용자 사전 확인
    ↓
Project Agent가 project/ 수정 및 검증
    ↓
사용자에게 diff와 검증 결과 제시
    ↓
사용자 사후 확인
    ↓
History 기록
```

Task completed 상태는 알림만 만들며 Promotion을 자동 시작하지 않는다.

## Records

- ADR 파일명은 날짜 없이 `<decision-name>.md`를 사용한다.
- History 파일명은 `YYYY-MM-DD-HHMM-<action>-<task-name>.md`를 사용한다.
- History는 사건, Task 경로, 공식 반영 경로만 기록하고 REPORT를 요약하지 않는다.

## Deterministic Automation

- 자동화: 세션 context 생성, Task scaffold, 코드 복사, data symlink, 상태·REPORT 형식, Git 기준점, checksum, 변경 감사, 종료 상태 반영
- 자동화하지 않음: Final Goal 결정, Scope·Workflow 작성, 결과 해석, Promotion 판단, ADR 판단, 자동 복구
- `tools/harness_experiment.py`는 통제된 Codex 세션의 원본 JSONL과 정규화 액션 로그를 생성한다.
- Hook과 Skill은 현재 구현에 포함하지 않는다. 통제 실험으로 도구만으로 해결되지 않는 반복 작업이 확인된 뒤 검토한다.
