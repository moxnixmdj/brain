# The wall is not the shape of the change; it is that one file cannot show you a fact about a module

**2026-11-12.** Branch `arena/ebaf0df3-brain`, base `53c80d8381`. Authority **NONE** — producer-run
sandbox measurement, `$0`, zero model calls in every result-bearing path, `truth.achieved` stays
`false`, no capability registered, no family flipped, no test weakened.

The owner's Problem 2, in his words: *instant learning and instant learning in new arbitrary
environments are solved; generalisation is not; solve it perfectly with the smartest solution, fastest.*

This round did not start from a theory. It started from the **refusal list** the tree already had
and looked at every refusal instead of the totals. That is what changed the answer.

---

## 1. What the tree already knew, and what it had never looked at

`ONE_TRY_COVERS_A_FRACTION_20261112_V1.md` ranks the frontier by refusal class. Its largest single
class, `NO_FORM_IN_FILE` (162 of 440, **36.82%**), is dismissed there in one line as *"not an
operator gap"* — the pattern is absent from the file. That line is true of the frontier and false of
the corpora this round measured, and the difference matters:

| corpus | files | `NO_FORM_IN_FILE` | share |
|---|---|---|---|
| `held_out` (27 kinds, out-of-sample) | 132 | 41 | 31.1% |
| `fresh` (9 kinds, pre-registered) | 42 | 7 | 16.7% |

`held_out` is the hardest set the tree has: its own recorded numbers are `strict` 156 same / 77 left
against 233 questions. Sixty-one of the 132 files there are not edited, and **41 of those 61 are
this one refusal**.

Reproduced first, before anything was written (three runs, exact):

```
seen      strict  questions 103  same  30  different 0  left  73  extra  0
held_out  strict  questions 233  same 156  different 0  left  77  extra  0
fresh     strict  questions 105  same  83  different  6  left  16  extra 13
```

## 2. Reading the 48 individual files instead of the total

Every `NO_FORM_IN_FILE` file was opened. The change in all of them is the same kind of thing:
an API being renamed. `np.bool` → `bool`. `Event.isSet` → `Event.is_set`.
`self.mock_server_thread.setDaemon(True)` → `self.mock_server_thread.daemon = True`.
`threading.currentThread` → `threading.current_thread`.

The organ knows each of these. It learned them from the demonstration. What it cannot do is *repeat*
them, and the reason is one level below the matcher:

| the demonstration says | the target file reads | what happens |
|---|---|---|
| `self._stop_event.isSet` → `self._stop_event.is_set` | `self._stop.isSet()` | **refused** — different receiver |
| `self.mock_server_thread.setDaemon(True)` | `self.setDaemon(True)` | **refused** — different receiver |
| `from threading import currentThread` | `threading.currentThread()` | **refused** — different way round |
| `np.bool` → `bool` | `("is_incoherent", np.bool)` | **refused** — different shape |

The learner is not wrong about any of those. Its rule is a rule about *one expression shape*, and a
demonstration of a rename is not evidence about an expression shape. It is evidence about a
**module**: inside `threading`, the name `currentThread` is now `current_thread`. That fact does not
depend on the receiver, on the shape of the expression, or on whether the file imports the name or
the module. The demonstration proved a fact; the organ threw the fact away and kept the shape.

**That is the real limiting factor.** Not the missing operator for `BLOCK_SHAPE`, not a missing
second example, not a missing check. The operator was already there — `Rebound` and
`aliases_to_follow` exist in the same file for exactly this, and fire only *after* a rule already
fits a place. The lesson's *subject* was wrong: a demonstration of a rename is a statement about a
module, and the organ was storing it as a statement about a line.

## 3. The fix: keep the fact, not the shape

`edit_by_example_v1` gains one thing. A demonstration that renames a name inside a module teaches
`(module, old, new, how the example used it)`, and that is checked against the demonstration itself
before it is believed:

1. the example's import line changed in place — same module, one name gone, one name come;
2. nothing else in the example's imports moved;
3. **the example's own first file, renamed this way, equals the example's own second file**, byte for
   byte — or the rename took every read of the old name away and left a read of the new one;
4. **the use the example showed** gates where it applies: `yaml.load(path)` → `yaml.safe_load(path)`
   teaches a one-positional-argument call, so `yaml.load(fp, loader=yaml.SafeLoader)` is left alone,
   because `safe_load` does not take a `loader=`.

Then, on any target file, the name is renamed **wherever that file reaches it from the same module** —
bare reads if it does `from m import old`, `m.old` reads if it does `import m`, and the one alias on a
shared import line. A file that binds the old name itself, that shadows it in a function, that
carries a `global`/`nonlocal`, that has a `*` import making origin unknowable, or that already binds
the new name, is left alone. Nothing is guessed and **no question is asked**: point 3 is the check,
and it is free.

## 4. What it is worth, measured on the same corpus, same day, same seeds

Three sets, 196 files, 363 marker questions. Arm A is what the tree ships; arm B is the same organ
with this one operator allowed to contribute.

| | questions | **same** | different | left | extra |
|---|---|---|---|---|---|
| A — shipped today | 363 | 225 (62.0%) | **6** | 132 | 0 |
| B — + the rename lesson | 363 | **231 (63.6%)** | **6** | 126 | 0 |

Per set, nothing is taken away and no wrong line is added:

| set | same A → B | different A → B | left A → B |
|---|---|---|---|
| `seen` | 30 → 33 | 0 → 0 | 73 → 70 |
| `held_out` | 130 → 130 | 0 → 0 | 49 → 49 |
| `fresh` | 65 → 68 | 6 → 6 | 10 → 7 |

On the pure-rename sub-corpora the effect is total, and this is the honest headline:

| set | the rename class, files | strict arm, same | with the operator |
|---|---|---|---|
| `seen` | 3 | 0 / 3 | **3 / 3** |
| `held_out` | 11 | 3 / 13 | **13 / 13** |
| `fresh` | 3 | 0 / 3 | **3 / 3** |
| **total** | **17** | **3 / 19 (15.8%)** | **19 / 19 (100%)** |

A 100% on 19 questions is not a generalisation result and must not be quoted as one: those 19
questions are the ones where the demonstration itself was nothing but the rename, and the operator
was built for precisely them. What it is, is **the first refusal class in this tree that went to
zero**, with the precision of the whole arm unchanged.

**One falsification, kept.** The first version of the operator recovered `yaml.load` →
`yaml.safe_load` on a call that also passed `loader=yaml.SafeLoader`, producing a program that
raises. It was caught by the wrong-line count going `6 → 7`, the code was changed to read the use
the example showed, and the count went back to `6`. The prediction is recorded in the test file's
docstring (P7) with the reason, not the fix.

## 5. What this does **not** fix, and the next real wall

The corpus's largest kind, `current_thread`, **8 files**, is still refused, and the reason is not
this operator:

```
Refused: line 6 of the example adds, removes or reshapes whole statements; only a change inside
         one expression or one simple statement can be learned
```

That demonstration's commit renames `currentThread` **and** restructures the logging block. It is the
**intent tangle** that `A_SECOND_SHOWING_UNTANGLES_THE_LESSON_20261112_V1.md` measured for `fresh`
(13 → 0 with a second showing) — and here it is in the *demonstration*, not the target, killing the
lesson before any target is touched. A second showing cannot untangle a demonstration whose own
two files disagree structurally.

So the ranked frontier after this round is:

| # | wall | size on `held_out` + `fresh` | cost |
|---|---|---|---|
| 1 | **a demonstration that is not one change** (structural tangle in the teacher) | 8 files (`current_thread`) + the `held_out` 2-showing `diff` 4 / `extra` 4 | a *selection* rule over which commit to use as teacher — no new algebra |
| 2 | `USE_NOT_SHOWN` — the code reads the changed name in a call shape no example showed | 12 files | already gated and already correct: it refuses rather than guesses. The fix is a second showing, which the tree measured at +8–10 pp |
| 3 | `BLOCK_SHAPE` / `CALL_SHAPE_NOT_SHOWN` / `NAME_NOT_AVAILABLE` / `CONFLICTING_CONTEXT` / `PARSE_MISMATCH` | 191 of 440 in the frontier doc (43.4%) | one operator each, priced in `ONE_TRY_…` §8 at **one lesson, two files, ~10 lines** |

**The smartest next move is #1, not #3.** Every operator in the list is worth less than it looks,
because a lesson cannot be learned at all from a teacher whose commit did two things. That is a
measurement and a selection rule over `git log`, not new algebra — and the tree has never measured
how often, in real repositories, one merged commit is one change. That number is the next thing to
buy, and it is cheap.

## 6. Reproduce

```
# the corpus (needs gh; ~6 min for all three sets, then ~1 min to measure each)
python3 canonical/tools/edits_repeated_across_projects_v1.py fetch held_out
python3 canonical/tools/edits_repeated_across_projects_v1.py measure held_out

# the operator
python3 -m pytest canonical/tests/test_a_renamed_name_is_renamed_where_this_file_reaches_it_v1.py   # 10 passed
python3 -m pytest canonical/tests/test_an_edit_is_worked_out_from_an_example_and_repeated_on_another_file_v1.py  # 49 passed
```

Repo integrity: 17 rules, **0 violations**, base `53c80d8381`. Orientation `verify: CONSISTENT`.

## 7. The honest sentence, for the owner

* **"Instant learning is solved"** — recall of the shown change, yes (8.13x, exact matches only).
* **"Generalisation is not solved"** — right, and this round found *why* at the level below the
  matcher: the organ was learning the **shape of a line** when the demonstration was teaching a
  **fact about a module**. Fixing the subject of the lesson took the rename class from 3/19 to 19/19
  and the whole three-set arm from 62.0% to 63.6% with **no new wrong lines**.
* **"Solve it perfectly"** — not yet, and the number says so. 63.6% is not perfection. But the
  largest remaining wall is no longer a missing operator. It is that **the teacher's own commit is
  not one change**, and no amount of algebra can untangle a lesson that was never single.
* **Sentience** — unchanged and unmeasured here. What this round does show is one honest step:
  the system now knows the difference between *what a change looked like where it was shown* and
  *what it proved*, and it refuses to spend the first on the second.
