# Problem 2 is not one problem: where generalisation stops, and what actually moves it

**2026-11-12.** Base `dbdf4969`. Branch `arena/5c61b6c7-brain`.

The owner's framing, restated exactly as given:

> **Problem 1: Exact Recall (SOLVED)** — solve it instantly if I see the exact task again. 8.13x.
> **Problem 2: Generalization (NOT SOLVED)** — if I see a *similar* task, adapt. Exact matches only.
> **Focus on solving problem 2 perfectly with the smartest solutions in the fastest way.**

That framing is right about one thing and wrong about another, and the difference decides what to
build. It is right that exact recall is a solved, cheap thing. It is wrong that generalisation is a
single unsolved thing. Generalisation is a **ladder of six writings of one lesson**, it is *partly*
solved, and the half that is unsolved is not solved by a better learner.

Measured this round, on merged pull requests written by other people:

| one demonstration, then every other file (132 pairs, 12 tasks) | of the developers' work recovered | precision | wrong changes made |
|---|---:|---:|---:|
| literal: the changed line must already be there | 0.010 | 0.636 | 4 |
| **the shipped learner, one demonstration** | **0.529** | **1.000** | **0** |
| the shipped learner, two demonstrations | 0.891 | 1.000 | 0 |
| every rung of the learner's own ladder, widest first | 0.048 | 0.455 | 42 |
| the ladder, gated by the file's own tests | 0.000 | — | 0 |

Reproduce the whole table with
`python3 canonical/tools/generalization_rung_gradient_v1.py --pulls <collected.json> --check tests`.
The record is `canonical/verification/GENERALIZATION_RUNG_GRADIENT_20261112_V1.json`; every figure
above is pinned by `canonical/tests/test_the_check_is_the_difference_v1.py` (15 tests).

Authority **NONE**. Producer-run, one machine, zero model calls, `$0`, no capability registered, no
family flipped, `truth.achieved` stays `false`.

---

## 1. What is actually true, before any new mechanism

Three of the four claims in the owner's framing survive contact with the record:

* **Exact recall is real.** One demonstration reproduces the developers' change with precision
  **1.000** — 384 changes made, 384 of them the ones the people made, **zero** wrong. It is not a
  lottery. That is the strongest number in this document.
* **It covers about half, not all.** 0.529 of the developers' changes on those tasks. So Problem 2
  as stated ("exact matches only") is too pessimistic: on 12 tasks of one kind of change across
  files, one showing already gets half of it right and none of it wrong.
* **A second showing is not "more of the same"** — 0.529 → 0.891 on the identical 132 pairs. The
  second example is worth **+36 points of coverage**, and it costs one more demonstration.

And one claim does not survive:

* **"Widen the rule" makes it worse.** The learner writes one demonstration down at six rungs, from
  *exactly this code* to *this shape anywhere, with names taken from wherever it lands*. Taking the
  widest rung first: coverage collapses from 0.529 to 0.048 and precision from 1.000 to 0.455 —
  **42 wrong changes** where the narrow reading made none. The ladder is not a dial you turn up.
  Anyone who says "make the skill more general" is asking for the wrong 42 edits.

So: generalisation is not absent. It is **narrow, precise, and short by about half**.

## 2. The thing that is actually missing — and it is not a learner

With no check, a wrong generalisation is kept. With a check, it is refused. Constructed, because
the real corpus cannot answer this question at all (see §3), and labelled as constructed:

```
one demonstration:   "the upper bound is exclusive"    return x <= hi   ->   return x < hi

pkg/limits.py     same defect, same shape    no check: edited, correct=True    check: edited, correct=True
pkg/edges.py      same defect, same shape    no check: edited, correct=True    check: edited, correct=True
pkg/inclusive.py  `<=` IS REQUIRED here      no check: EDITED, correct=FALSE  check: REFUSED, correct=True
```

Same lesson, same learner, same demonstration. The only variable is whether the target file's own
tests run. Without them the skill is **confidently wrong**; with them it declines to touch the file
and leaves it correct.

The first version of this table proved less than it looked. The demonstration's own test pinned one
boundary (the edge is out) while the demonstration's own code stated two (`x <= hi` also accepts
zero), so the lesson it produced was under-determined *on the file it was shown* — `x > hi`, `x < 0`
and `False` each satisfied it. In that state, three corrections were rejected on `pkg/inclusive.py`
and the number said "the check saved it", when the honest reading was "the demonstration was
half a demonstration". The fix was not to make the rule more general; it was to state the second
boundary in the demonstration's own test. All three corrections are still refused, and the count of
attempts is printed (`wrong_edits_tried: 3` per file) so that "nothing got through" cannot quietly
mean "nothing was tried".

And the check is only worth what it pins. `pkg/limits.py`'s test asserts only that the edge is
excluded — so `return x > hi` passes it. That is not a flaw in the measurement; it is the measurement:
**a test that pins one side of a boundary is not a test of the boundary.** Real projects are full of
these, which is why "we have tests" is not the same as "we can verify anything". The demonstration,
not the rule, is where a boundary gets stated — which is why §5's next lever is the check and not
the learner.

This is the same conclusion the previous round reached from the other direction (an unguarded token
rule rewrote a required `<=`), now with the counterfactual: the guard, where it exists, works.

## 3. The measurement that had to fail before it could mean anything

The corpus is 12 merged pull requests where people made one kind of change across files
(`assertEquals→assertEqual`, `isAlive→is_alive`, `logging.warn→warning`,
`assertRaisesRegexp→assertRaisesRegex`, f-strings, removing `six`). 42 changed files, 132 ordered
demonstration→target pairs, whole project trees fetched so a test module in another directory could
be found. Then the check was asked to run on each changed file, and it could not:

```
CHECK_NO_TEST_MODULE         6     no test module imports the changed file
CHECK_DEPENDENCY_MISSING     6     the tests import a dependency that is not installed
```

**Zero of 42 changed files in real projects can be verified on this machine.** Not because the
check is broken — the positive control proves it discriminates (accepts the project, accepts a
correct edit, rejects a wrong edit that still compiles, rejects a broken file) — but because the two
things verification needs are exactly the two things missing: a test that imports this module, and
the project's dependency environment.

That is the limiting factor, stated in one line:

> **One demonstration is enough to learn a change, and a check is what makes the learning safe to
> use. Neither is missing. What is missing is standing up a project's checks — its dependencies and
> its test entry point — for each new environment.**

Which reframes the owner's plan. "Give the model the most advanced actions, let it experience each
once" is not blocked by the experiencing, and not blocked by the storing. It is blocked by the fact
that *installing a project's dependencies* is the step that turns a confident guess into a verified
skill, and it is work, not experience.

## 4. Am I right or wrong — the four claims, split

| claim | verdict |
|---|---|
| exact recall is solved | **TRUE** — precision 1.000, 384/384 right, 0 wrong |
| generalization is not solved / exact matches only | **FALSE as stated** — one showing recovers 0.529 with no wrong changes |
| generalize *better* by making the rule wider | **FALSE** — 0.048 coverage, 0.455 precision, 42 wrong changes |
| a second, different demonstration is a real lever | **TRUE** — 0.529 → 0.891 on the same pairs |
| a check converts a wrong generalisation into a refusal | **TRUE** — constructed counterfactual, §2 |
| we can verify real code today | **FALSE here** — 0 of 42 changed files; reasons counted, §3 |
| so we can do anything on a computer once and keep it | **FALSE** — nothing in this round executed a computer action at all |

"You were right" is true of the cheap half and false of the expensive half. The expensive half is
not a smarter learner.

## 5. The smartest next action, and the ones I killed

**Killed:** widening the ladder (measured worse: 42 wrong changes), adding a semantic guard to the
token matcher (that is the check's job, and a hand-written guard would be a new way to be confidently
wrong), and generating a bigger skill library (0.048 precision at the widest rung says the library
would grow in the wrong direction).

**Killed on evidence:** "pick the demonstration better" — already measured on `main`, r = 0.88, and
silent on 7 of 10 tasks.

**The action that moves the number: make standing up a check cheap.** Concretely, in this tree:

1. **A dependency resolution step in front of the check.** `CHECK_DEPENDENCY_MISSING` was half the
   failures. Detecting the project's declared dependencies and installing them into an isolated
   environment is the difference between "cannot verify" and "can verify" on 6 of 12 tasks — and it
   is the only step that turns §2's counterfactual into something that happens on real code.
2. **A test-entry-point finder that reports its own uncertainty.** `CHECK_NO_TEST_MODULE` was the
   other half. The honest output is not "no tests" but "here are the modules that import this file,
   these are the candidates, this is the one I would run".
3. **Only then** count how much of the 0.529 that becomes verified. That number, not a bigger
   library, is what "instant learning in a new environment" means.

Note the order, and note what it costs: the next round is about *environments*, not about learners.
This repository's failure mode is adding the mechanism before measuring what it sees; the ladder
measurement above is what stops "just widen it" from being the next fourteen rounds.

## 6. Receipts

```
$ python3 canonical/tools/generalization_rung_gradient_v1.py --pulls /tmp/pulls_g.json --check tests

ON REAL MERGED PULL REQUESTS  (one demonstration, then every other file)
  arm               pairs  edited  right  wrong precision of the work
  literal             132      13      7      4     0.636       0.010
  exact               132      28    384      0     1.000       0.529
  two_showings        132      62    647      0     1.000       0.891
  any_rung            132      34     35     42     0.455       0.048
  any_rung_check      132       0      0      0         -       0.000
  check_only          132       0      0      0         -       0.000

  the check was unavailable on 132 pairs (no test module imports the file)

  POSITIVE CONTROL (a project that ships a check): discriminates=True  module=tests.test_bounds
    accepts_the_project_as_it_is                 True
    accepts_the_correct_edit                     True
    rejects_a_wrong_edit_that_still_compiles     True
    rejects_a_broken_file                        True

  WHY THE CHECK COULD NOT RUN (one line per task, not per pair)
    CHECK_DEPENDENCY_MISSING         6
    CHECK_NO_TEST_MODULE             6

  THE SAME LESSON WITH AND WITHOUT A CHECK (constructed: three modules, one test each)
    pkg/limits.py      check=True  without: edited=True correct=True  with: edited=True correct=True
    pkg/edges.py       check=True  without: edited=True correct=True  with: edited=True correct=True
    pkg/inclusive.py   check=True  without: edited=True correct=False  with: edited=False correct=True

pytest -q canonical/tests/test_the_check_is_the_difference_v1.py     15 passed
```

## 7. Seven mistakes this instrument made, none of which survived into a number

Recorded because the pattern is the finding: the learner was never the thing that was wrong.

1. **Restored the candidate instead of the original** after a check run, so every later candidate was
   judged against an earlier guess.
2. **`ok = (returncode == 0) == (expect == "PASS")`** — an inversion that, in repair mode, accepted
   files whose tests still **failed**. The opposite of what an oracle is for.
3. **"The module name appears in the test file"** as the criterion for a check. It picked
   `stem.util.test_tools` — a helper — as the check for a test-package `__init__.py`. An import is
   the criterion; a mention is not.
4. **Compared the wrong two objects**: precision was computed against the number of edited files
   instead of the number of changes made, which reported 11.885 for a value of 1.000.
5. **One place instead of every place** — the rung arms edited a single site where the shipped organ
   edits all of them, so the first comparison measured "one edit vs all edits", not the ladder.
6. **A control corpus whose before and after were the same file**, which taught the learner nothing
   and read as "the lesson reaches nothing".

7. **A counterfactual whose demonstration pinned half of itself.** The one-demonstration lesson was
   learned from a file whose test asserted one boundary while its code stated two, so three
   corrections that dropped the second boundary were refused on `pkg/inclusive.py` — and the number
   read "the check saved it". It did not; the demonstration was incomplete, and the check was
   carrying a burden that belonged to the demonstration. Fixed by stating the second boundary in
   the demonstration's own test, and by printing `wrong_edits_tried` so refusals cannot be
   manufactured by trying fewer things. Both fixes are pinned by tests; the corpus numbers did not
   move, because the corpus never used that construction.

Each was caught by making the tool's failure visible rather than by reading its output charitably.
That is the same rule as everywhere else in this tree: a check whose success case is "I didn't look"
is not a check.

## 8. What this does not claim

Not a benchmark, and not first contact: these 15 change kinds were read in earlier rounds. The 12
tasks are one family of changes (mechanical migrations), which is the regime one-shot learning is
*best* at — the 0.529 is an upper bound for this learner, not an average. The constructed control in
§2 is constructed, and is labelled so in the record (`"constructed": true`). No test of any project
was passed to claim correctness of any edit; the check that could not run is reported as not run. No
capability is registered, no family is flipped, and `truth.achieved` remains `false`.
