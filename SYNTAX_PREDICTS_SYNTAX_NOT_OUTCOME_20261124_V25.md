# SYNTAX PREDICTS SYNTAX, NOT OUTCOME — accuracy 1.0 by never saying "fail"
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project then web; name the
> real limiting factor; kill the idea before building it; verified / unverified / failed; hardest real
> tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The gap, and the smallest honest way across it

Last round: a syntactic vocabulary transfers across codebases at 0.9796 accuracy (within: 0.9896). But the
target was itself syntactic — a return-shape *class* — so "syntax predicts syntax" is close to a tautology.

So I changed the target to something that **happens**: *will this test pass?*

**Labels come from execution.** 2,233 tests from `canonical/tests/test_*.py` were run in-process with the
real code, and pass/fail came out of junit XML. Not a hand-assigned judgement, not an LLM, not a borrowed
answer. 1,472 trained, 761 held out, split by file. **42 of the held-out tests fail.**

## 2. The result, with the baseline that decides it

| | value |
|---|---|
| best vocabulary | 5 relations (`BRANCH_ON_CALL`, `BRANCH_ON_NAME`, `BRANCH_ON_SUBSCRIPT`, `COUNTS_ON_OPERATION`, `LINES`) |
| predictions | 97 of 761 |
| wrong | **0** |
| accuracy | **1.0000** |
| coverage | 0.1205 |
| majority class (always "pass", full coverage) | 0.9448 |
| **always "pass" at the vocabulary's own coverage** | **1.0000** |
| **failures predicted** | **0** |
| **held-out failures the vocabulary ever spoke about** | **0 of 42** |

Accuracy 1.0 beats the majority class by 5.5 points, and that number is worthless. **At equal coverage,
"always pass" scores exactly 1.0000.** The vocabulary reaches a perfect score by refusing 664 of 761 tests
and never once saying "fail" — and since 94.5% of tests pass, never saying "fail" is free.

`said_fail: 0`. `said_fail_right: 0`. `failures_spoken_about: 0`.

## 3. What this closes

Between them, the last two rounds answer the question the prompt's store plays all rest on:

| question | answer | evidence |
|---|---|---|
| Does knowledge cross an environment boundary? | **Yes, if it is stated over syntax** | 0.9796 across vs 0.9896 within, two code-groups |
| Does it predict *outcome*? | **No** | 1.0000 accuracy that equals the base rate at equal coverage, zero failure predictions |

Both results point at the same mechanism, and it is now the clearest statement this project has:

> A relation over syntax is portable and vacuous. A relation over ground state is informative and
> immobile. **Nothing in the current vocabulary is both.**

That is the real limiting factor, measured three ways across five rounds (V15 transfer failure, V16 partial
lift, V24 syntactic transfer, V25 collapse to base rate, plus the V22 finding that the vocabulary is a
precision dial over a coverage band it cannot leave). It is not a tuning problem. It is the difference
between *describing code* and *modelling what code does*.

## 4. Why this is the honest stopping point for this sequence, not a failure to try harder

I could add features until something predicts a failure. Every mechanism that would do it — dataflow to
assignment sites, call-graph reachability, execution tracing of the tests themselves — moves the feature
closer to the label until it becomes the label, which is the leak I have now committed twice and caught
twice. The measurement above says something sharper than "we need better features": it says **the available
evidence (a test's own source) does not determine its outcome**, and any predictor that appears to succeed
will be reading the answer.

The next real step is not more features. It is acquiring the evidence that *does* determine outcome —
which means executing the code under varied inputs, i.e. the "mental world model" the prompt asks for in
§9.3.4, and this project has never built one.

## 5. Defects found in this round, in my own work

* **First run collected zero labels.** The tool globbed `canonical/tests/*.py`, which includes
  `fixtures/` — 10 collection errors, and pytest's junit XML then reported the *collection errors* as
  test cases with empty names. Fixed with `test_*.py` and `--continue-on-collection-errors`.
* **The first "win" was reported before the equal-coverage baseline existed.** 85 predictions, 0 wrong, and
  I nearly wrote it up. The baseline that kills it is three lines of arithmetic.
* **A test asserted a wrong expectation.** `assert g() == 1` is a `Compare`, so its origin class is
  `OPERATION`, not `CALL`; my test asserted `COUNTS_ON_CALL`. The failure was correct and the expectation
  was wrong. I then garbled the file with a bad edit and had to rewrite the function cleanly.
* **A 22-minute run** because the tool shells out to pytest over 300 files: 1,349 s. Recorded, not hidden.

## 6. Verified / unverified / failed

**Verified by execution:** 2,233 labelled tests from a real run; 42 held-out failures; 97 predictions with
0 wrong and 0 failures predicted; equal-coverage baseline identical at 1.0000.

**Failed, mine, this round:** the hypothesis that a syntactic vocabulary predicts test outcome. It predicts
the base rate.

**Unverified:** whether any static feature can predict test outcome at all. I believe the answer is no for a
test's own source, for the reason in §4, but that is reasoning and is labelled as such.

**Not publishable:** any benchmark row — `docker: command not found`, logged once. Nothing here is a claim
about SWE-bench Pro, Terminal-Bench 4.0, or OSWorld 2.0, and no comparison to any frontier model is made.

## 7. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 1,349.6 s (pytest over 300 files)
```

5 new tests, including one that fails if the vocabulary ever starts predicting failures — if that changes,
this report's conclusion no longer holds and the test says so. Guard PASS (17 rules).

## 8. Next

The store the prompt describes needs entries that are *about behaviour*, and this project has none. The
smallest buildable object that is about behaviour and is not a leak: **a precondition-effect record for one
function, earned by executing it on two inputs that differ in one argument**, stored with the input pair as
its witness. That is the first thing here that could carry causal content rather than shape, it needs no
model call, and it can be wrong in a way a test can catch.
