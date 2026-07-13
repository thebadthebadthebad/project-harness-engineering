# Final Documentation Validation

## 확인된 문서 불일치

- 루트 `STRUCTURE.md`가 현재 구현된 Hook과 Skills를 “미포함”으로 설명한다.
- 공용 `README.md`와 `STRUCTURE.md`가 `check`, `task handoff`, `promotion record`, `observe` 명령을 충분히 안내하지 않는다.
- 공용 문서에 normal Hook trust와 실험 runner의 digest 검증 후 trust 우회 차이가 없다.
- 루트 Task template의 AGENTS가 공용 Task template보다 오래된 반복 읽기·경계 지시를 포함한다.
- `experiments/README.md`가 두 번째 research+code 시나리오, compare, Hook/Skill 관찰과 현재 acceptance를 누락한다.

## 검증 결과

- `python3 project/tools/projectctl.py --root project check`: 통과
- `python3 -m unittest discover -s tests -v`: 26개 통과
- `python3 -m compileall -q project tools`: 통과
- 공식 skill-creator `quick_validate.py`:
  - `project/.agents/skills/manage-project-workflow`: 통과
  - `project/tasks/_template/.agents/skills/run-task-workflow`: 통과
- `git diff --check`: 통과
- Task doing 계약 검사: 통과

처음에는 존재하지 않는 `experiments/tests`를 별도 unittest 경로로 지정해 discovery 오류가 발생했다. 공식 테스트는 루트 `tests/`에 모두 모여 있으며, 올바른 명령으로 26개를 다시 실행해 전부 통과했다.

## 실험 근거와 해석

- lifecycle v3와 research+code의 Project/Task/Project 독립 세션 6개가 모두 exit 0이고 hard acceptance를 통과했다.
- lifecycle v3는 같은 parser로 재분석한 v2보다 input token 11.4%, output token 37.0%, Markdown path 13개가 감소했다.
- 두 실제 run에서 변경 없는 Markdown 재방문, 상위 경로 탐색, Task의 Project lifecycle 실행, malformed JSONL은 0이었다.
- 명시적 Project/Task Skill marker와 SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop Hook event가 각 역할에서 관찰됐다.
- compaction과 subagent는 시나리오에 해당 동작이 없어 관찰되지 않은 상태를 coverage에 그대로 남긴다.

## 새로 발견한 정합성 결함

`python3 project/tools/projectctl.py --root . check`는 Engineering 루트에 공용 Project용 `src/`, `data/`가 없어서 실패한다. Engineering 저장소의 공식 구조는 Harness 코드·실험·공용 `project/` 템플릿을 관리하며 빈 `src/`, `data/` 추가는 책임 없는 디렉터리를 만든다. 검사기가 공용 Project와 Engineering Project의 필수 디렉터리를 명시적으로 구분하는 별도 수정 Task가 필요하다.

## 남은 한계

- 실제 Codex run의 raw Hook event는 document visit 교정 전 Hook으로 생성됐다. 교정 후 함수는 fixture와 unit test로 검증됐지만 actual Codex Hook run은 아직 다시 수행하지 않았다.
- Hook은 일부 unified shell과 비-shell 동작을 빠뜨릴 수 있다. 보고서는 관찰 evidence이지 완전한 보안 감사가 아니다.
- custom agent는 full-access 환경에서 instructions-only 제한이다.
- raw Codex JSONL은 prompt와 Agent 출력을 포함할 수 있어 커밋하거나 자동 공개하지 않는다.

## Promotion 대상

- `output/GUIDE.md` → `project/GUIDE.md`
- `output/documentation-plan.md`에 식별한 루트·공용·실험 참조 문서 교정
- Engineering check 결함은 문서 Promotion과 분리한 코드 Task로 처리

