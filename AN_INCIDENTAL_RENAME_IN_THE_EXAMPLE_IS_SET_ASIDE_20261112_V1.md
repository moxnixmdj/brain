# An incidental rename in the example is set aside

**2026-11-12.** Base `ac6364e8`. Branch `arena/7e49a844-brain`. Follows #6730.

Seven measurable held-out kinds refuse at learning. A census of all of them (this turn, probe over
the tracked corpus) shows exactly three failure classes, and they are the measured answer to "why
can't the model just experience every smart action once and learn it":

1. **The example restructures whole statements** (assert_count_equal, current_thread, getchildren,
   torch_sigmoid, running_loop, exception_message): one showing underdetermines the rule — the
   person's edit depends on intent that is not a function of the code's visible shape.
2. **The example contradicts itself** (tf_cast): the same code is changed one way and left alone or
   changed another way elsewhere in the very same showing. No function exists from shape to edit.
3. **The example tangles two edits** (np_int): an incidental local rename (`I` → `I_state`) rides
   the same commit as the real lesson (`np.int` → `int`), and the coupled rename poisons learning.
   This is the long-documented *tangled commit* phenomenon — empirical studies put 11–40% of real
   commits in this class (Herzig & Zeller, MSR 2013 line of work).

Class 3 is fixable soundly, and now is. Classes 1 and 2 are intrinsic to one-showing learning and
stay refusals — a sufficient check (`tried`) can settle class 1 sometimes; nothing can settle 2.

## 1. What was built

`rename_undone` in `edit_by_example_v1`, applied to every example as it enters `learn_all`: when
the example's second file binds exactly one plainly assigned non-builtin name the first does not,
the first binds exactly one such name the second dropped, and neither name is ever an import, a
def, a class, a parameter, or a global/nonlocal in its file, the new name is put back to the old
one at every bare-name use. The result is the same program (an alpha-rename of one local), and the
lesson underneath becomes visible. Never set aside: import renames (that *is* the lesson — #6730),
def/class/parameter renames, globals, two renames at once, builtin names, and an example that was
nothing but the rename — that one keeps its old refusal, because it teaches nothing repeatable.

## 2. The measurement, same tracked sets

Declared before measuring: kinds not learned 7→6, `same` rises, `diff` stays 0, `extra` stays 0,
seen set unchanged. Landed:

| held_out | #6730 | now |
|---|---|---|
| kinds not learned | 7 | **6** |
| questions in reach | 169 | **179** (np_int's 10 enter the pool) |
| `repeat` same / diff / extra | 125 / 0 / 0 | **130 / 0 / 0** |
| `repeat_tried` same | 150 | **160** (all 10 np_int answers under a sufficient check) |

Strict refused files 11→14: the three np_int person files hold `np.int` forms the example never
showed, so the strict way now declines them by name instead of not knowing the kind at all — the
shown way still refuses only the 3 unresolvable-import files, and `tried` settles every np_int
question. The seen set did not move by one digit.

## 3. Receipts

```
pytest -q canonical/tests/test_an_incidental_rename_in_the_example_is_set_aside_v1.py   11 passed
pytest -q  (all nine taught-action test files)                                         291 passed
PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py    11 skills, bundle e32579f9… (re-taught)
python3 canonical/tools/edits_repeated_across_projects_v1.py measure held_out|seen      the table
```

## 4. Non-claims

The guard is deliberately narrow: one rename pair per example file, plainly assigned names only,
builtins excluded. A tangled commit with two renames, or a rename of a parameter, still refuses —
that is the conservative out, not a gap claim. The remaining six unlearned kinds are classes 1–2
above: they are *why one try is not a learning signal in general*, and no engine change is planned
that would paper over them. `tried` remains the ceiling of a sufficient check; truth.achieved stays
false; $0; the result-bearing path has zero model dependency.
