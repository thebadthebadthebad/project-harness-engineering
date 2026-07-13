# Engineering Structure Check Design

## 문제

현재 `check_project()`는 모든 root에 `src/`, `tools/`, `data/`, `docs/adr/`, `docs/history/`, `tasks/_template/`을 동일하게 요구한다. 공용 Project에는 맞지만 Harness Engineering root의 공식 제품은 `project/` 템플릿, runner, tests와 Engineering Task이므로 root `src/`, `data/`는 책임이 없다.

## 식별 규칙

Engineering root는 다음 세 marker를 모두 가진 root로 한정한다.

- `tools/create_project.py`
- `tools/harness_experiment.py`
- `project/` 디렉터리

공용 템플릿에는 앞의 두 Engineering 전용 도구가 없으므로 nested 검사 시 재귀 Engineering으로 오인하지 않는다. marker를 함수 `managed_public_template(root) -> Path | None`로 분리해 필수 디렉터리 선택과 nested 검사에서 함께 사용한다.

## 필수 구조

공통:

- `AGENTS.md`, `PROJECT.md`, `README.md`, `STATE.md`, `STRUCTURE.md`
- `tools/`, `docs/adr/`, `docs/history/`, `tasks/_template/`

공용 Project 추가:

- `src/`, `data/`
- `tools/projectctl.py`

Engineering Project 추가:

- `project/`
- `project/tools/projectctl.py`
- nested `project/`에 대한 전체 공용 Project `check_project()`

Engineering nested 오류에는 `project: ` prefix를 붙여 root 오류와 구분한다. `project/` 또는 nested projectctl이 없으면 재귀하지 않고 명시적 missing 오류를 반환한다.

## 단순 구현

```python
def managed_public_template(root: Path) -> Path | None:
    tools = root / "tools"
    if (tools / "create_project.py").is_file() and (tools / "harness_experiment.py").is_file():
        return root / "project"
    return None


def check_project(root: Path) -> list[str]:
    template = managed_public_template(root)
    required_directories = ["tools", "docs/adr", "docs/history", "tasks/_template"]
    required_directories += ["project"] if template else ["src", "data"]
    # 기존 root 문서·상태·이름·config 검사를 유지한다.
    # Engineering이면 존재하는 nested template을 같은 검사기로 검사한다.
```

별도 class hierarchy나 범용 schema layer를 추가하지 않는다. 현재 두 구조에 필요한 한 개 classifier와 재귀 호출만 둔다.

## 실패 동작

- 일반 공용 Project의 `src/` 또는 `data/` 부재: 기존처럼 `missing src/`, `missing data/`
- Engineering `project/` 부재: `missing project/`
- Engineering nested tool 부재: `missing project/tools/projectctl.py`
- Engineering nested 구조 손상: `project: <nested error>`

## 적용 검증

1. candidate regression test를 루트 `tests/test_workflow_core.py`에 반영한다.
2. `projectctl --root . check`와 `projectctl --root project check`가 모두 통과하는지 확인한다.
3. nested public `src/`를 제거한 임시 fixture에서 prefixed 오류가 발생하는지 확인한다.
4. 일반 public fixture의 `src/`를 제거하면 계속 실패하는지 확인한다.
5. 전체 unittest와 `git diff --check`를 실행한다.

