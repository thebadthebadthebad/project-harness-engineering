# TASK

이 문서는 Task 수행 계약을 정의한다. Task의 Final Goal과 현재 실행 상태는 `STATUS.md`가 관리한다.

## Scope

- Stage A v2 Task에 model, reasoning effort, sandbox, approval, network/web, allowed tools·MCP·skills, 시간·토큰 제한과 fallback 실행 계약을 추가한다.
- 로컬 Codex CLI capability를 probe하고 계약을 실제 `codex exec` argv/config로 낮춰 전달하는 adapter를 구현한다.
- JSONL event와 output-schema final message를 Git-local run evidence로 회수하고 typed handoff를 canonical Task에 연결한다.
- 추가 권한·외부 변경·범위 확대 요구는 자동 실행하지 않고 해당 Task만 `needs_decision` 또는 `blocked`로 바꾸는 decision request/resolve를 구현한다.
- experiment, failure, review, decision, reusable asset을 후속 Task가 stable ref로 찾는 최소 result index를 구현한다.
- Agent 역할·입출력·파일 소유권·parent 검토 책임을 실행 계약과 문서에 반영한다.

범위 밖:

- background worker, queue와 병렬 scheduling
- lease, heartbeat, PID/orphan 자동 복구, mutation retry와 범용 evidence graph
- 실제 외부 시스템 변경이나 사용자 대신 권한 승인

## Inputs


| Project Source | Task Snapshot |
| --- | --- |
| project/tools/project_harness | scripts/project_harness |
| project/tools/projectctl.py | scripts/projectctl.py |

## Data


| Project Data | Task Link |
| --- | --- |
| None | None |

## Workflow

```text
capability probe → execution contract normalization → Codex argv/schema/context adapter → structured handoff → decision request/resolve → result index → acceptance/fault tests
```

## Outputs

- `scripts/project_harness/adapter.py` Codex adapter 후보
- `scripts/project_harness/v2.py`, `cli.py` Stage B 상태/CLI 후보
- execution/handoff JSON Schema와 prompt template 후보
- `scripts/tests/test_stage_b.py` adapter/decision/result acceptance suite
- `output/validation.md`와 REPORT

## Completion Criteria

- reasoning effort가 `-c model_reasoning_effort=...`로 실제 전달되고 unsupported 값의 fallback이 기록된다.
- sandbox·approval·network/web·tool/MCP/skill 제한과 시간·토큰 budget이 정규화된 실행 계약과 argv/evidence에 남는다.
- fake Codex JSONL/output-schema fixture에서 structured handoff와 thread id·usage가 회수된다.
- timeout, malformed output, permission/scope/external-effect 요청이 Task-local 상태로 전환되고 다른 Task 상태를 변경하지 않는다.
- decision request View에 선택지·권고·영향·기본값·대기 가능 여부가 표시되고 explicit resolve만 상태를 재개한다.
- result index가 최소 유형, Task/decision/source refs, 검증 상태, supersession과 재사용 경로를 제공한다.
- 기존 Stage A와 전체 회귀가 통과하고 Task audit이 통과한다.
