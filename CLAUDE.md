## Commands

- run: `python3 -m focus_guard status` (verdict, never locks); `python3 -m focus_guard lock` (demo window with a close button)
- test: `xvfb-run -a .venv/bin/python -m pytest -p no:cacheprovider -q`
- test-changed: `scripts/test_changed.sh`
- lint: `ruff check .`
- coverage: `python3 -m pytest -q --cov --cov-branch --cov-report=xml`
- coverage-gaps: `coverage-gaps coverage.xml`
- e2e: `scripts/e2e_xvfb.sh short|met|hold|hold-lift`, `scripts/e2e_milestone.sh lock|done|trip|phone|mock|slot` (private Xvfb on the first free :120+, never :0; `lock` drives real xdotool clicks)

## Invariants

- Rule: yesterday was a project day and missed `daily_minutes`, today is a project day: locked until `minutes_for(today) >= unlock_minutes`. Sick or free day: this minute rule never locks, owes nothing (the milestone lock below stands down for sick days only).
- No typed override. The only ways out are the numbers, a sick or free day (a milestone lock: sick day only, or completing it), or ending the project; the lock re-reads all of them on every file event and every 15 s.
- `focus_project` is called through the module (`focus_project.minutes_for`), never from-imported: tests and the e2e driver patch one attribute.
- Unreadable registry: arming fails open (logged); a lock already up stays up.
- `JUDGE_FROM` in `_constants.py` is the first judged "yesterday".
- `focus-project` is pinned to a `kuhyx/utils` tag in `pyproject.toml` like gatelock; bump the tag when its API changes.
- Test holds: `_standdown.active()` (`holds.covers("focus")`) stands the verdict down (`Verdict.held`); an open lock lifts on the next 15 s poll, the gate then waits (`holds.next_change`) and re-judges when the hold ends, so "yesterday fell short" is not erased. `holds` missing or raising: logged, behave as before (fail closed). Tests patch `_standdown.holds`.
- Interview milestones (focus_project >= 0.9.0): after the hold check, `owed_lock(now)` locks the earliest missed milestone. Only a sick day stands it down (a FREE day does not: `_sick` vs `_off` in `_verdict.py`); minutes never lift it, only completing it (late) does; the test day never locks. `decide(today, now=...)` takes the moment; `Verdict.owed`/`.milestone` says which.
- The milestone window has zero text (textgate): the milestone's icon (eye rules, suitcase trip_ask, phone, webcam mock, calendar slot) and its action; taps record via `_actions` (refused or failed write: logged, lock stays, hero tints red). `_milestone_view` + `_milestone_forms` + `_form_kit`; pictures for the rules picker come from `Paths.pick_dirs`. `MILESTONE_KINDS` must match `_milestone_forms.FORMS` (a kind with no form locks nothing, logged).
- After a milestone window closes, `run_gate` re-judges: a different owed lock opens its own window; the same one still owed does not reopen (no loop).
