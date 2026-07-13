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
Engineering Task가 REPORT와 completed STATUS 작성
→ Engineering Project가 handoff·audit·close
→ Project가 결과 가치와 공식 위치 판단
→ 필요한 결과만 project/ 또는 Engineering 공식 경로에 반영
→ 구조 검사·관련 테스트
→ promoted 또는 not-promoted 기록
```

Task completed 상태는 알림만 만들며 Promotion을 자동 시작하지 않는다.

## Records

- ADR 파일명은 날짜 없이 `<decision-name>.md`를 사용한다.
- History 파일명은 `YYYY-MM-DD-HHMM-<action>-<task-name>.md`를 사용한다.
- History는 사건, Task 경로, 공식 반영 경로만 기록하고 REPORT를 요약하지 않는다.

## Deterministic Automation

- 자동화: 세션 context 생성, Task scaffold, 코드 복사, data symlink, 상태·REPORT 형식, Git 기준점, checksum, 변경 감사, 종료 상태와 이미 내려진 Promotion 결정 기록
- 자동화하지 않음: Final Goal 결정, Scope·Workflow 작성, 결과 해석, Promotion 판단, ADR 판단, 자동 복구
- 명시 호출형 Project/Task Skills는 정해진 lifecycle 절차만 보조하고 판단이나 세션 전환을 대신하지 않는다.
- Hook은 Git-local metadata로 문서 방문, context, Skill, lifecycle, compaction, subagent event를 관찰하며 작업을 차단하지 않는다.
- custom agent는 사용자가 허용한 독립 읽기 작업만 대상으로 하고 full-access 환경의 보안 경계로 취급하지 않는다.
- `tools/harness_experiment.py`는 통제된 독립 Codex 세션의 raw JSONL, 정규화 액션 로그, acceptance와 비교 보고서를 생성한다.

## Validation

- `python3 project/tools/projectctl.py --root project check`: 공용 템플릿 무결성
- `python3 project/tools/projectctl.py --root . check`: Engineering Project 무결성
- `python3 -m unittest discover -s tests -v`: 공용 도구·관찰·실험 회귀 테스트
- `experiments/RESULTS.md`: 실제 Project/Task/Project 세션 결과와 남은 한계
