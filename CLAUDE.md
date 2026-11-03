## Commands

- run: `python3 -m focus_guard status` (verdict, never locks); `python3 -m focus_guard lock` (demo window with a close button)
- test: `xvfb-run -a .venv/bin/python -m pytest -p no:cacheprovider -q`
- test-changed: `scripts/test_changed.sh`
- lint: `ruff check .`
- coverage: `python3 -m pytest -q --cov --cov-branch --cov-report=xml`
- coverage-gaps: `coverage-gaps coverage.xml`
- e2e: `scripts/e2e_xvfb.sh short|met|hold|hold-lift` (private Xvfb on the first free :120+, never :0)

## Invariants

- Rule: yesterday was a project day and missed `daily_minutes`, today is a project day: locked until `minutes_for(today) >= unlock_minutes`. Sick or free day: never locks, owes nothing.
- No typed override. The only ways out are the numbers, a sick or free day, or ending the project; the lock re-reads all of them on every file event and every 15 s.
- `focus_project` is called through the module (`focus_project.minutes_for`), never from-imported: tests and the e2e driver patch one attribute.
- Unreadable registry: arming fails open (logged); a lock already up stays up.
- `JUDGE_FROM` in `_constants.py` is the first judged "yesterday".
- `focus-project` is pinned to a `kuhyx/utils` tag in `pyproject.toml` like gatelock; bump the tag when its API changes.
- Test holds: `_standdown.active()` (`holds.covers("focus")`) stands the verdict down (`Verdict.held`); an open lock lifts on the next 15 s poll, the gate then waits (`holds.next_change`) and re-judges when the hold ends, so "yesterday fell short" is not erased. `holds` missing or raising: logged, behave as before (fail closed). Tests patch `_standdown.holds`.
