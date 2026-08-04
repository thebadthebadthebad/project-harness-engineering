# Project Harness Engineering

이 저장소는 큰 목표를 여러 독립 Task로 나누고, 사람과 Codex가 병렬로 작업하며, 검토된 결과만 공식 Project에 반영하기 위한 공용 로컬 하네스를 설계·검증·배포한다.

여기에서 제품 Project를 중앙 등록하거나 실행 상태를 수집하지 않는다. 이 저장소는 versioned bundle과 template만 제공하고, 적용된 각 Project가 자신의 `.harness`, Git 이력, queue와 실행 근거를 독립적으로 소유한다.

이 README는 Harness Engineering 저장소 자체를 설명한다. 배포된 Project에서 실제 하네스를 사용하는 절차는 [Project 운영 가이드](project/GUIDE.md)를 따른다.

## 해결하려는 문제

장기 Project에서는 리서치, 구현, 실험과 검증이 서로 다른 속도로 진행된다. 모든 중간 문서와 대화를 Project root에 누적하면 핵심 목표가 흐려지고, 반대로 대화 컨텍스트에만 의존하면 Agent 교체·중단·병렬 작업에서 결정과 근거가 유실된다.

이 하네스는 다음 원칙으로 그 문제를 다룬다.

- Project는 안정적인 목표, 공식 코드·데이터·문서와 검토된 결과만 소유한다.
- Task는 bounded goal, input, output, ownership과 완료 조건을 가진 독립 실행 단위다.
- JSON authority는 기계 상태의 원본이고 CLI가 사람이 읽는 View를 생성한다.
- Codex 실행, validation과 queue는 자동화할 수 있지만 결과 해석과 공식 반영은 부모 Agent와 사용자가 검토한다.
- 한 Task의 Decision이나 실패는 다른 독립 Task를 멈추지 않는다.
- worktree가 checkout을 격리하고 exact-diff Promotion이 선택 결과만 공식 branch로 옮긴다.
- lease·heartbeat·orphan 자동 복구 같은 고급 orchestration은 실제 필요성이 확인될 때까지 도입하지 않는다.

## 저장소와 배포 Project의 경계

```text
Harness Engineering repository
  project/                 공용 template 원본
  tools/harnessctl.py      bundle package/new/apply/update
  tests/                   배포·상태·실행·복구 회귀 검증
  tasks/                   하네스 자체를 개선하는 Engineering Task
           │
           │ versioned bundle
           ▼
Applied Project repository
  .harness/                Project가 소유하는 canonical JSON
  tools/projectctl.py      Project-local lifecycle CLI
  src|tools|data|docs/     공식 자산
  task/integration worktree와 queue/runtime는 Git-local
```

Harness Engineering은 적용 Project를 검색·등록·원격 관리하지 않는다. bundle update도 사용자가 명시한 Project 경로에서만 실행한다.

## 현재 제공 기능

- 새 v2 Project 생성과 기존 Project의 dry-run 기반 apply/update
- legacy Markdown 상태의 side-by-side 변환, semantic parity 검증, authority 전환과 제한된 rollback
- sealed Project·Task·Decision·Result·Promotion JSON과 generated human View
- 생성 후 Project/Task 계약의 Markdown proposal, before/after preview, revision CAS와 승인 근거가 있는 controlled amendment
- bounded Task input, dependency, owned path, validation과 context reference
- Task·integration Git worktree 격리와 candidate 단위 Promotion
- Codex CLI capability probe, reasoning fallback, sandbox·web·network·MCP·Skill 계약, structured handoff
- Task-local Decision request/resolve
- Project-local SQLite queue, background worker, reader/writer 병렬 제한과 명시적 cancel/resume
- Result artifact digest·검토 provenance, filter와 rebuild 가능한 최소 index
- canonical full check, symlink containment, short canonical writer lock과 revision CAS
- fail-open Hook 관찰과 Git-local summary report

현재 범위는 local Linux/WSL Git Project다. distributed scheduler, 중앙 dashboard, native Windows/NFS 보장, 자동 orphan adoption은 제공하지 않는다.

## 디렉터리 안내

| 경로 | 책임 |
| --- | --- |
| `project/` | 다른 저장소에 배포하는 공식 공용 Project template |
| `tools/harnessctl.py` | template을 checksummed bundle로 만들고 대상 Project에 적용 |
| `tools/create_project.py` | 개발용 template 직접 복사 경로; 공식 배포 검증은 bundle 흐름 사용 |
| `tests/` | bundle, migration, lifecycle, Codex adapter, queue와 관찰 회귀 테스트 |
| `experiments/` | 통제 실험 시나리오와 과거 실행 결과 |
| `tasks/` | 하네스 자체를 변경하는 Engineering Task와 근거 |
| `PROJECT.md` | Harness Engineering의 안정적인 Goal과 Scope |
| `STATE.md` | 현재 Engineering Goal과 현재 Task |
| `STRUCTURE.md` | 이 저장소에서 template 변경을 검토·반영하는 구조 |
| `AGENTS.md` | 사람과 Agent가 따르는 Engineering 규칙 |

루트 `tasks/`와 `project/tasks/_template/`은 다르다. 전자는 하네스 자체를 바꾸는 작업 공간이고, 후자는 배포 bundle에 포함되는 legacy-compatible Task template이다.

## 빠른 시작: 새 Project 생성

Harness Engineering 저장소 root에서 bundle을 만든다. version은 release 또는 pilot 식별자로 명시한다.

```bash
python3 tools/harnessctl.py package \
  --template project \
  --version 2.0.0-local \
  --output /tmp/project-harness-2.0.0-local
```

새 Project를 생성하면 v2 authority와 Git 저장소가 초기화된다.

```bash
python3 tools/harnessctl.py new /absolute/path/to/my-project \
  --source /tmp/project-harness-2.0.0-local \
  --project-id my-project \
  --goal "Project goal" \
  --scope "Initial scope"

cd /absolute/path/to/my-project
git add .
git commit -m "chore: initialize project harness"
python3 tools/projectctl.py check
python3 tools/projectctl.py show project
```

그다음 [공용 Project README](project/README.md)와 [운영 가이드](project/GUIDE.md)의 Task 생성→격리 실행→검토→Decision→Promotion 흐름을 따른다.

## 기존 Project에 적용 또는 업데이트

`apply`와 `update`는 기본적으로 dry-run이다.

```bash
python3 tools/harnessctl.py apply /absolute/path/to/existing-project \
  --source /tmp/project-harness-2.0.0-local
```

최초 apply에서 기존 managed `.codex`, `.agents`, `tools` 또는 guide를 교체하려면 dry-run의 모든 `replace`를 검토하고 backup을 만든 뒤 명시적으로 확인한다.

```bash
python3 tools/harnessctl.py apply /absolute/path/to/existing-project \
  --source /tmp/project-harness-2.0.0-local \
  --apply --accept-managed-replace
```

설치 이력이 있는 Project의 update는 기존 bundle checksum, Project 파일과 새 bundle을 비교한다. 양쪽이 바뀐 managed 파일은 자동 병합하지 않고 conflict로 중단한다.

```bash
python3 tools/harnessctl.py update /absolute/path/to/existing-project \
  --source /tmp/project-harness-2.0.0-local
python3 tools/harnessctl.py update /absolute/path/to/existing-project \
  --source /tmp/project-harness-2.0.0-local --apply
```

## 이 저장소에서 하네스를 개발하는 방법

새 세션이나 컨텍스트 압축 뒤 root에서 한 번 현재 상태를 확인한다.

```bash
python3 project/tools/projectctl.py --root . context
```

하네스 변경은 root `tasks/`의 Engineering Task로 수행한다. Task 생성·활성화·baseline·audit·close에는 같은 CLI를 `--root .`로 사용한다. 공식 template 변경은 다음 순서로 검토한다.

```text
Engineering Task 계약과 baseline
  → 코드·문서·테스트 변경
  → 관련 회귀와 bundle로 만든 disposable Project 검증
  → REPORT와 Task audit
  → Project close·History·commit
```

`project/tools/projectctl.py`는 배포 template의 도구 원본이다. 도구를 수정했다면 최소한 전체 unittest와 실제 bundle 생성 후 새 Project check를 실행한다.

```bash
python3 -m unittest discover -s tests -p 'test_*.py'

tmp_bundle=$(mktemp -d)/bundle
python3 tools/harnessctl.py package \
  --template project --version validation-local --output "$tmp_bundle"
```

## 안전성과 승인 경계

- checksum은 bundle 내용의 무결성을 확인하지만 출처를 인증하지 않는다. 신뢰된 commit에서 만든 bundle을 사용한다.
- worktree와 `owned_write_paths`는 격리·감사 경계이며 hostile code를 막는 완전한 보안 sandbox가 아니다.
- Codex `read-only` 또는 `workspace-write` sandbox를 기본으로 사용한다. `danger-full-access`는 network를 포함할 수 있어 network-off 계약으로 인정하지 않는다.
- wall-time은 hard stop이지만 token ceiling은 완료 usage를 기준으로 사후 판정한다.
- Hook은 fail-open 관찰 장치이며 보안 enforcement나 완전한 action ledger가 아니다.
- Promotion 전에 actual diff, current base와 validation을 확인한다. 승인 뒤 base·Task·diff가 바뀌면 새 packet을 만든다.
- Project와 Task 계약은 JSON을 직접 편집하지 않고 `project amend|task amend` preview를 거친다. Agent가 적용할 때는 실제 사용자 승인 참조를 남기며 실행 중 Task 계약은 바꾸지 않는다.
- worker crash 뒤에는 잔존 process와 worktree를 확인하기 전 `queue resume`을 실행하지 않는다.

## 문서 지도

- [공용 Project 입문](project/README.md)
- [설치부터 Task·Promotion·장애 대응까지의 운영 가이드](project/GUIDE.md)
- [배포 Project의 책임·상태·디렉터리 구조](project/STRUCTURE.md)
- [Harness Engineering 저장소 구조](STRUCTURE.md)
- [통제 실험 결과](experiments/RESULTS.md)

구현 근거가 필요할 때는 관련 Engineering Task의 `REPORT.md`와 Relevant Files를 우선 확인한다. 모든 Task 메모를 기본 컨텍스트로 로드하지 않는다.
