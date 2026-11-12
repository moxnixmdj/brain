# A use nobody showed is settled by the project's own check

**2026-11-12.** Base `fe07e791`. Branch `arena/dcaf3b90-brain`. Follows #6686.

The taught action that repeats a change worked out from examples had one honest gap, measured in
#6686: one example cannot say which parts of the changed code matter. `self.thread.isAlive()` shown
once says nothing about `t.isAlive()`, so the action refused or left such places — on the held-out
set of that round the refusals cost 18 of 59 right edits and prevented not one wrong one. The two
notes of the same day say why from both sides: *one example is a point, a test is a quantifier* —
a demonstration cannot identify a program, only a domain statement can — and the version-space
learner keeps **every** reading the successes allow rather than guessing one.

This round closes the gap without guessing: the places the examples do not settle are **tried**, one
at a time, against the project's own check, and the check's answer is written back into the lesson.

## 1. What was built

`edit_by_example_v1` gains a fifth action, `repeat_tried` (target, lesson, check), taught to the
front door as *"edit {target} the way {lesson} remembers and try the rest with {check}"* (bundle:
11 skills).

* **The wider reading.** Beside the rules the examples prove, the lesson is read more widely:
  each part the change merely copied — unchanged in the new code and starting from a variable, not
  from an import, a definition or a builtin — may be any other code (`wider`). Nobody showed this
  reading, so it is never used unasked.
* **A try needs two runs to be kept.** A tried place is kept only when (1) no test of the check
  that passed on the file as it is fails with the place changed, and (2) a test that passes with it
  **fails when that place is made to fail** (the place is replaced by code that raises). A check
  that passes either way — it never runs that line, or swallows its errors — settles nothing, and
  the place stays as it was. This is the mutation-score idea pointed at the exact places the edit
  touches: a green test that cannot see the line failing is a rubber stamp, and is treated as one.
* **The check's answer compounds.** The tried file is added to the lesson as an example: a kept
  place widens the rules (the next file needs no try), a place a test defended counts as left
  alone (it kills the wider reading where it is wrong), and the places the check could not settle
  are written as `not settled`, so they count neither way at the next use.
* **What the lesson itself shows is not up for debate.** The check gates only the tries; a check
  that fails after the shown change refuses the whole edit and the file is put back byte for byte.

## 2. The measurement, on other people's commits

Protocol as in #6686, now a tracked tool: `canonical/tools/edits_repeated_across_projects_v1.py`
finds merged commits of one kind of change on GitHub by fixed rules (no hand-picking; kinds written
down before their commits were looked at; `collect` refuses to run twice on a set), keeps the
commit list in `edits_repeated_across_projects_commits_v1.json`, and compares statement for
statement. The first commit of a kind teaches; every file of the kind's other commits is a
question. `tried` is measured as the most a **sufficient** check can give (every try settled),
because other projects' test suites cannot be run here; it is a ceiling, not a free result.

56 kinds, 171 commits, 266 files; the `held_out` set (40 kinds named before collection, 27 learned,
97 target files) was collected after the engine was frozen.

| set | questions | `repeat` same | `repeat_tried` same | different | changed what the person left |
|---|---|---|---|---|---|
| seen (16 kinds, 58 files) | 103 | 30 | **69** | 2 | **0** |
| held_out (27 kinds, 97 files) | 169 | 116 | **141** | 1 | **0** |

* The tries more than double agreement on the seen set (+39) and add +25 on the held-out set —
  exactly the places #6686 could only refuse.
* `extra = 0` on both sets: the wider reading, even with every try accepted, never touched a
  statement the person left alone. The remaining `left` places have shapes the example cannot
  reach at all (the marker inside a larger rewrite); the 3 `different` are places where the person
  changed more than the kind while touching the marker.
* `repeat` and `repeat_shown` agree with people on everything they dare to touch (0 different),
  as in #6686.

## 3. Receipts

```
python3 -m pytest -q canonical/tests/test_a_use_nobody_showed_is_settled_by_the_projects_own_check_v1.py   16 passed
python3 -m pytest -q canonical/tests/test_a_change_shown_once_… test_an_edit_is_worked_out… \
    test_two_refactorings… test_a_taught_skill_does_not_destroy…                           246 passed (all five files)
PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py --check                           11 skills, same bundle
python3 canonical/tools/edits_repeated_across_projects_v1.py measure seen|held_out         the table above
```

Door flow, fresh database seeded from the tracked bundle: *remember … was changed into …* then
*edit pool.py the way kept/alive.lesson remembers and try the rest with check_pool.py* →
`PASS__COMPILED_WORKFLOW_SKILL`, the tested use changed, the untested one left, the lesson widened
to `?1.isAlive -> ?1.is_alive` — all inside the namespace sandbox.

## 4. Non-claims

The `tried` column is the ceiling of a sufficient check: a project whose tests never run the tried
line gets nothing settled and keeps the refusal, by design. The two-run rule is per place, not a
proof: a test can in principle pass the changed code and fail the made-to-fail code while the
change is still wrong for an input the check does not hold — a check is a domain statement exactly
as strong as its domain. Checks are run with the project's own interpreter state only where a
single file imports cleanly; cross-file fixtures, pytest-only suites and binary dependencies are
out of reach of the runner. The commit search sees only public GitHub and the kinds here are
API migrations — small, named, repeated changes; nothing is claimed about edits of other shapes.
No capability is registered beyond the taught sentence; `truth.achieved` stays false; $0; the
result-bearing path has zero model dependency.
