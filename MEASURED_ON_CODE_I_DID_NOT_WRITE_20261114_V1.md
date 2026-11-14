# I measured on five files I chose, with tests I wrote. Here is the same question on code I did not write.

**14 November 2026.** Branch `arena/98e3c624-brain`. Authority **NONE**. `$0`, zero model calls, no
capability registered, no family flipped, `truth.achieved` untouched.

You were right about the last round, and it is the criticism that matters most: *we keep testing on
bugs we already know work — that is self-congratulation.* My licence was measured on 5 files I
selected, and its tests ran on a fixture I wrote. A fixture cannot disagree with its author.

So this round asks the same question on **29 real merged commits in three public repositories nobody
in this session wrote**, with those projects' own suites and their own runners.

---

## 0. The number

> **19 of 29 real merged code changes could be put back to their pre-fix source, with the fix's own
> tests left in place, and the project's own suite still passed.**

| repository | suite size used | judged code changes | noticed | **not noticed** |
|---|---:|---:|---:|---:|
| `torproject/stem` | 96 | 6 | 0 | **6 (100%)** |
| `pypa/packaging` | 63,795 | 9 | 4 | **5 (56%)** |
| `more-itertools/more-itertools` | 771 | 14 | 6 | **8 (57%)** |
| **total** | | **29** | **10** | **19 (65.5%)** |

The method is the standard the 2026 literature states and nobody here had applied: *"a regression
test never shown to fail on the broken commit is not a regression test, it's an assertion of faith"*
(Who Tests the Tests, Jul 2026). So each fix is reverted and the suite is asked to object.
Record: `canonical/verification/CLAIM_LEDGER_REAL_MERGED_COMMITS_20261114_V1.json`.
Tool: `canonical/tools/revert_test_ledger_v1.py`. 50 minutes of machine time for all three.

**The spread is the finding, not the average.** 0% vs 44% vs 46%. *"This project has a test suite"*
carries no information about what the suite can see. A 63,795-test suite and a 771-test suite landed
in the same place; the worst project by far is the one with the most careful hand-written runner.

---

## 1. Two false measurements that would have been publishable, caught by the instrument

This is the part I want you to hold me to, because it is the difference between a number and a
story. Both of these produced a full, clean ledger before being caught:

**Stem said 0 of 12, and it was measuring nothing.** `python -m unittest discover -s test/unit -t .`
reported **"Ran 1 test ... OK"** for the whole of `test/unit/util` — the package `__init__` is itself a
TestCase and the discovery never descended. Every revert came back `REVERT_NOT_NOTICED`. This
repository has made this exact error before ("our verifier was running zero tests and reporting
PASS"), so the tool now reads *what the runner printed* and refuses with `CHECK_RAN_NOTHING` when it
names no tests. The guard is a test.

**Packaging said 0 of 10, and it was measuring the wrong code.** `sys.path` resolved
`import packaging` to the copy installed in `site-packages`, so the project's tests ran against a
different library than the one being reverted. All ten commits came back `BASELINE_RED`. Same
src-layout trap the licence hit on the same repository, the same day. Fixed with `--extra-path src`.

Both failures produce a *number*. Neither is evidence. That is why the record stores the runner's own
words and why the tool refuses rather than scoring zero.

---

## 2. Three things the figure must not be allowed to say

**It overstates test inadequacy.** 4 of packaging's 5 misses are `perf(...)` commits: behaviour-
preserving refactors for which a green suite after a revert is *correct*. Nobody should write a test
that fails when you revert a pure speedup. They stay counted, and they set a floor.

**It understates stem's.** `stem`'s real procedure is `run_tests.py`, not pytest on one directory. I
did not reproduce it, so stem's 100% is against a partial suite and its true protection is unknown.

**It is not a benchmark.** 29 judged code changes, 3 repositories, chosen because their suites run
here. Direction established; exact value not.

And a mechanical classifier decides what counts, before any counting: docstring-only, version-only
and annotation-only changes are excluded from the headline (no test can be held to them), and the
unfiltered count is published beside it. The classifier was itself corrected by measurement —
`stem`'s "Fix timeout argument **type hint**" was initially a CODE_CHANGE and would have inflated the
headline with a change no suite can catch at runtime.

---

## 3. An author-independent second opinion

The revert test depends on a human having written a fix. To remove the human, I perturbed the
**pre-fix** file of two real fixes with the licence's own mutants and asked whether the suite sees the
guard move:

| file (pre-fix) | sites the suite can see |
|---|---|
| `more_itertools/more.py` | 10 / 14 |
| `stem/util/connection.py` | 11 / 14 |

Both central guards are visible. The invisible sites are arithmetic and one comparison. So **the
projects' suites are not blind in general — they are blind in particular places.** That is why a
per-site answer is the only useful form, and it is the strongest argument for the licence organ built
last round: a single project-level score would have said "fine" for both of these files and been
wrong about the parts that matter.

---

## 4. What this does to your claim

Your claim has five clauses. The previous round measured them; this one puts the numbers on real
code:

| clause | verdict | the number |
|---|---|---|
| 1. Shown once, kept permanently | **TRUE** | 1 row, real store; 384/726 developer changes at precision 1.000 on 12 merged PRs |
| 2. Transfers to an unseen place | **TRUE, same shape** | rewrote an unseen function correctly; refused on 4/4 *different* shapes |
| 3. The check can see the change it blesses | **FALSE** | 0 of 1 at the taught boundary; 24% of licensed sites blind; **19 of 29 real merged fixes unprotected** |
| 4. A wrong version is refused | **TRUE where clause 3 holds** | admission REJECTs it, 0 rows written |
| 5. Covers anything on a computer | **NOT MEASURED** | nothing in this tree executes a real application |

The mechanism is real, the permanence is real, and clause 3 is the wall.

**Now the part that matters for the plan.** Clause 3 is not a property of your model. It is a property
of **each project the model meets**, and it varies from 0% to 46% between projects of the same
language written by competent people. So "give the model the smartest actions once and it learns them
permanently, everywhere" cannot be made true by making the model better. It is made true, project by
project, by *checking whether that project's check can fail* — which is minutes of machine time, and
which is now a tool.

Your instinct about *where* the leverage is was right. The mechanism is not learning; it is testimony.

---

## 5. The smartest next actions, in order — and what I refuse to build

**1. Ask the licence before the first lesson, not after.** The organ exists and is wired into the
choke point; what is missing is the caller. Before an agent learns anything in a new repository, it
should run the licence on the files it is about to touch (bounded, cached, ~4 minutes for 10 sites
against a real suite) and know, in advance, which of them it may be permanently changed by. This is
the single highest-leverage change available and it needs no new idea.

**2. Restrict the mutants to the operators that mean behaviour.** 9 of the 12 blind sites in the
licence were `return X → return None` where `X` is `False`. Replacing that with value-preserving-class
substitutions would raise the measured licence and lower the measured blindness *simultaneously*,
which is how you know it is measuring rather than scoring.

**3. Then the second showing.** Already measured: 0.529 → 0.891 of developers' work at 0 wrong
changes when the rule is shown twice from two places. The organ transfers; the second demonstration
is a human choice today.

**4. Then a confined computer-use surface for clause 5** — observation, rollback, a success predicate,
and the same question asked of it: can the success predicate fail? Not a stub. A stub would make the
row TRUE and mean nothing.

**Killed, with the reason:**

* *"Run the revert test on this repository to score our own capabilities."* Killed: it scores the
  *projects*, not us. Turning it inward would be the self-congratulation you warned about, with better
  instrumentation.
* *"Report the average and drop the per-project detail."* Killed: the average hides a 0% next to a
  46%, and the 0% is the one that would destroy a lesson library.
* *"Treat every revert-not-noticed as a bug in the project."* Killed by the four `perf` commits: a
  behaviour-preserving change *should* survive its revert. Counting it as risk would be a lie in the
  direction that flatters the analysis.
* *"Use a model to judge patch correctness."* Forbidden by your constraint, and it is not independent:
  it is the proposer grading itself one layer up.
* *"Widen the mutants until the number improves."* Killed: that is choosing the measurement to fit the
  claim. The classifier and the two denominators exist so the choice is visible.

---

## 6. What is not claimed

Not a benchmark. Not an independent verification. Not the projects' official test procedures. Not a
statement that any commit is wrong. `truth.achieved` is untouched, no family is flipped, spend is
`$0`, no model is called. The 19-of-29 has a floor (refactors) and a ceiling (stem's partial suite)
and both are named above rather than left for a reader to find.

Reproduce:

```
python3 canonical/tools/revert_test_ledger_v1.py --repo <clone> --limit 20 --out ledger.json \
    --check -- python -m pytest -q tests
python3 -m pytest -q canonical/tests/test_revert_test_ledger_v1.py
```

One sentence: **on real merged code, two thirds of the changes are protected by no test that can
fail, and how unprotected a project is cannot be guessed from its test count — it has to be
asked, per site, and asking costs minutes.**
