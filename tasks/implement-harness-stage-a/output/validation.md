# Stage A Validation

- Candidate acceptance suite: 5/5 passed.
- Existing repository regression suite: 29/29 passed.
- Candidate modules passed `python3 -m py_compile`.
- Manual smoke test completed `package → new → v2 Task → isolated worktree → typed handoff → exact-diff approval → Promotion apply` in a temporary Git repository.
- Legacy smoke test completed `inspect → plan → apply → verify → switch → rollback`; post-switch v2 mutation correctly prevented rollback.
- Fault tests covered managed-file conflict, failed-update rollback, failed validation, and stale approved diff.

Commands:

```bash
python3 -m unittest -v tasks/implement-harness-stage-a/scripts/tests/test_stage_a.py
python3 -m unittest discover -s tests -v
python3 -m py_compile tasks/implement-harness-stage-a/scripts/harnessctl.py tasks/implement-harness-stage-a/scripts/project_harness/*.py
python3 project/tools/projectctl.py --root . task audit implement-harness-stage-a
```
