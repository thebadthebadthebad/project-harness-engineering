# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- `project_harness/observability.py`에 run 목록·요약·Markdown 보고 기능을 추가하고 CLI에 `observe list|report`를 연결한다.
- Hook 입력에서 내용이 아닌 이벤트·역할·도구 분류·문서 경로·lifecycle 명령 분류만 기록하는 fail-open observer candidate를 만든다.
- 공용 `.codex/config.toml`, `.codex/hooks.json`과 Hook script candidate를 만든다.
- Project와 Task에서 사용자가 명시적으로 호출하는 최소 Skill 두 개를 공식 생성 도구로 scaffold한다.
- 병렬 읽기가 명확히 유용할 때만 선택할 수 있는 research-reader와 verification-reader custom agent 설정을 만든다.
- 사용자 프롬프트·도구 출력·patch 본문·전체 shell 명령은 로그에 기록하지 않는다.
- Hook은 context 주입, command 차단, lifecycle 실행, 자동 Promotion을 하지 않는다.

## Inputs


| Project Source | Task Snapshot |
| --- | --- |
| project/tools/project_harness | scripts/project_harness |
| project/tools/projectctl.py | scripts/projectctl.py |

추가 참고 입력은 `../../project/AGENTS.md`, `../../project/tasks/_template/AGENTS.md`, 현재 설치된 Codex Hook·Skill·custom agent 공식 규격이다.

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
관찰 event schema와 민감정보 제외 규칙 확정
→ projectctl observe list/report 구현
→ fail-open Hook script와 config 구현
→ 명시 호출형 Project/Task Skill scaffold 및 검증
→ 읽기 전용 custom agent와 동시성 상한 설정
→ Hook fixture, report, Skill metadata, config 검증 테스트
→ REPORT에 후보와 운영 한계 정리
```

## Outputs

- `scripts/project_harness/`: observe 명령 candidate
- `output/public-config/.codex/`: config, hooks, custom agents candidate
- `output/public-config/.agents/skills/`: Project 명시 호출형 Skill candidate
- `output/task-config/.agents/skills/`: Task 명시 호출형 Skill candidate
- `output/task-config/AGENTS.md`: Task 공통 규칙 candidate
- `scripts/tests/`: 관찰·Hook·설정 테스트
- `docs/notes/observability.md`: 수집 범위와 fail-open 계약

## Completion Criteria

- context 내부 문서 목록과 Hook 이벤트가 같은 run JSONL에 합쳐진다.
- `observe report --latest`가 timeline, 문서 방문 횟수, Skill, Hook, compaction, subagent, lifecycle 분류와 event coverage를 생성한다.
- Hook은 잘못된 입력이나 기록 실패에도 exit 0이며 프롬프트·출력·전체 command를 저장하지 않는다.
- Skill 두 개 모두 `allow_implicit_invocation: false`이고 `quick_validate.py`를 통과한다.
- custom agent는 파일 수정과 lifecycle 명령을 금지하는 읽기 전용 지시이며 max depth는 1이다.
- 설정과 Hook의 정상·손상 fixture 테스트가 통과한다.
- Task 외부 파일을 수정하지 않고 Promotion 후보가 REPORT에 기록된다.
