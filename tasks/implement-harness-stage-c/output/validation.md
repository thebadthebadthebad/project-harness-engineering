# Stage C Validation

- Candidate Stage C acceptance suite: 5/5 passed.
- Existing official regression suite: 38/38 passed.
- Candidate modules passed `python3 -m py_compile`.
- Parallel fixture: two 0.8-second writer runs with `max_writers=2` completed below 1.6 seconds; default `max_writers=1` was at least 0.45 seconds slower.
- Independent-state fixture: one Task reached `needs_decision`, one independent Task reached `succeeded`, and one unmet dependency stayed `queued`.
- Running cancellation terminated the fake Codex process and ended only that job as `cancelled`.
- A second coordinator was rejected by a non-blocking local file lock.
- A stale `running` row became `interrupted`, did not auto-run, and required explicit resume with attempt 2.
- Detached worker reported ready and stopped through the SQLite shutdown flag without persisted PID adoption.
- Task baseline audit passed.

Commands:

```bash
python3 -m unittest -v tasks/implement-harness-stage-c/scripts/tests/test_stage_c.py
python3 -m unittest discover -s tests -v
python3 -m py_compile tasks/implement-harness-stage-c/scripts/project_harness/*.py
python3 project/tools/projectctl.py --root . task audit implement-harness-stage-c
```
