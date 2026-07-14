# REPORT

이 문서는 Task 종료 시 Project가 공유 대화 컨텍스트 없이 결과를 검토할 수 있도록 작성하는 최종 handoff 문서다.

## Outcome

completed

허용값은 `completed` 또는 `stopped`다.

## Summary

Harness Engineering Git 루트를 새 Codex 세션의 project root로 사용하기 위한 AGENTS, 다음 유지보수 STATE, `.codex` config·Hooks·custom agents 후보를 완성했다. 현재 Codex CLI의 strict config actual run에서 approval never와 danger-full-access가 적용됐고 전체 29개 test와 두 Project 구조 검사가 통과했다.

## Final Goal and Result

최종 목표를 달성했다. 새 세션은 자동 로드되는 루트 AGENTS에서 Engineering Project와 배포용 `project/`의 관계를 이해하고 `projectctl context`를 한 번 실행한다. 완료된 안정화 Goal의 Task 표는 History와 REPORT에 보존한 채 새 실제 적용 Goal에서는 비워, 다음 사용자 요구를 새 Engineering Task로 정의하는 상태로 시작한다.

## Findings

- 공식 Codex 동작은 `AGENTS.md`를 새 run마다 Git root부터 한 번 조합하므로 동적 상태를 `.codex` instructions에 복제할 필요가 없다.
- trusted project `.codex/config.toml`은 권한·features·project root·agent 한도에 적합하고, 현재 상태는 `projectctl context`가 담당하는 편이 중복이 없다.
- 현재 완료 Task 여섯 개는 모두 promoted인데 기존 Current Goal 표에 남아 context가 Promotion 대기로 표시했다. Goal 전환과 빈 표가 가장 단순하고 기존 STATE 정책에도 맞다.
- `approval_policy = never`이면 auto-review가 평가할 approval 자체가 없다. `approvals_reviewer = user`도 함께 두어 auto-review 미선택을 명시했다.
- Engineering Hook은 공용 템플릿에서 actual smoke를 통과한 content-free fail-open source와 동일하게 유지할 수 있다.
- custom agent는 root full-access를 상속하므로 read-only 지시는 보안 경계가 아니며 사용자 승인형 독립 읽기 작업에만 사용해야 한다.

## Work and Validation

- Codex 0.144.3 `--strict-config` actual run: exit 0, approval never, sandbox danger-full-access, 응답 `config-ok`.
- Python 3.11 TOML parse와 설정값 assertion: 통과.
- Hook JSON exact 9 events, Python compile, invalid stdin fail-open·무출력: 통과.
- candidate Hook과 검증된 `project/.codex/hooks/observe.py` byte comparison: 동일.
- candidate STATE Current Tasks empty와 새 Current Goal parse: 통과.
- 두 custom agent의 필수 name, description, developer_instructions: 통과.
- Engineering/public `projectctl check`: 각각 통과.
- `python3 -m unittest discover -s tests -v`: 29개 통과.
- `git diff --check`와 completed Task 계약 검사를 수행한다.

## Relevant Files

Project가 확인해야 할 Task 파일의 경로와 의미를 기록한다.

| Path | Type | Purpose |
| --- | --- | --- |
| output/root/AGENTS.md | instructions | 새 Engineering 세션 identity, bootstrap와 지속 규칙 후보 |
| output/root/STATE.md | state | 실제 적용·후속 개선 Current Goal과 빈 Task 표 후보 |
| output/root/.codex/config.toml | config | full-access, no approval/review, live network, Hooks와 agent 한도 |
| output/root/.codex/hooks.json | config | root lifecycle Hook 등록 후보 |
| output/root/.codex/hooks/observe.py | code | content-free Git-local fail-open 관찰 Hook |
| output/root/.codex/agents | config | 보수적 research·verification reader 후보 |
| docs/notes/session-root-design.md | design | 책임 분리, 상태 전환, 공식 근거와 검증 계획 |

## Limitations

- 후보 경로 actual config run에서는 Hooks를 비활성화했다. root Hook actual event는 공식 Promotion 후 exact digest를 확인하고 새 root session에서 검증해야 한다.
- full-access custom agent의 read-only 제약은 instructions-only다.
- project-local `.codex`와 Hooks는 사용자가 저장소를 신뢰하고 Hook definition을 review해야 정상 interactive session에서 적용된다.

## Project Follow-up

Project가 AGENTS, STATE와 `.codex` 후보를 루트에 Promotion한다. root/public check와 전체 test를 다시 실행한 뒤 exact digest를 검증한 actual 새 Codex root session에서 context 1회, Engineering identity, 빈 Current Tasks, Hook event를 확인하고 clean commit으로 종료한다.
