# Validation Evidence

## Final legacy pilot

- Bundle creation and `apply`: passed.
- Migration plan and semantic verification: `semantic_parity=true` with identical digests.
- Project-owned document SHA-256 comparison: 3/3 identical.
- New-authority full `projectctl check`: passed.
- Migration rollback: passed.
- Original legacy source repository status: clean.

## Final parallel pilot

- Queue jobs: 2 succeeded, 0 interrupted, 0 blocked, 0 `needs_decision`.
- Concurrent start: both jobs started within the same recorded second.
- Structured handoff validation: 2/2 passed.
- Declared validation commands: 2/2 exited 0.
- Reviewed source changes: none.
- Promotion candidates: none; empty selection rejected.
- Result index: 2 reviewed reusable records.
- Follow-up context: both `result:<id>` references resolved and rendered.
- Project check after the run: passed.

## Isolation and authority

- The actual Project's reviewed `src/` tree remained unchanged.
- Operational Task, handoff, and Result state remained owned by that Project under `.harness` and its Git metadata.
- The Harness Engineering repository did not register or manage either pilot Project.
