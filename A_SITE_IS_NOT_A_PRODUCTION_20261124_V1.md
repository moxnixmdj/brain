# A SITE IS NOT A PRODUCTION

**The demand was right, the movement was wrong, and the fix contains the real answer.**

Date: 2026-11-24 · Authority: `NONE__PRODUCER_RUN_SANDBOX` · Branch `arena/dd759ae6-brain`
Receipt: `canonical/verification/A_SITE_IS_NOT_A_PRODUCTION_20261124_V1.json`

---

## 1. The question, unchanged

*If instant learning is solved, why can't we hand the model the most advanced coding actions, let it
experience them once, and own the best coding agent on the planet?*

Last round answered a narrower version by measurement: of 30 real fixes, 13 are even addressable by an
instrument that reads a site from two ASTs, and it verifies **1**. Eight of the remaining 17 were
`MORE_THAN_ONE_CHANGE_REGION` — "the demanded value is produced in one place and consumed in another".
The natural next crossing was therefore stated as: **keep the demanded value fixed and ask another
production in the same function to supply it.** One value, one site, no combinatorics. It was declared,
built and run this round.

## 2. Declared before the run

> **Acceptance.** One verified repair whose AST fact is `MORE_THAN_ONE_CHANGE_REGION`; accusations
> zero; no verified row that preserves zero recorded passing values.

Declared first so the run cannot become its own judge. It was **not met**: the shift verifies **0**.

## 3. What was built

* `the_space_is_the_artifact_v1.sites_in_function(source, line)` — every statement-level, single-line
  expression in the innermost function containing the changed line (`Return.value`, `Expr.value`,
  `Assign.value`, `If.test`, `While.test`, `For.iter`), nearest first. The human's line is **excluded by
  construction**: it is the answer key, and a run that reads it is not a run.
* `the_assertion_is_the_demand_v1.explore(..., site_override=, shifted_from=)` — the same demand,
  unchanged, asked at a production of the instrument's choosing, labelled `site_finder="site_shift"` with
  `shifted_from_line` recorded, so a shifted row can never wear the diff-finder's name.

39 tests green, including one that pins "another production is named, the human line is never offered"
and one that pins the shift's label.

## 4. The measurement

30 real commits (click, jinja, attrs), 574.2 s, 0 parameters, 0 model calls.

| stage | rows |
|---|---|
| `EXCLUDED__THE_FIX_IS_NOT_A_SINGLE_EXPRESSION_REPLACEMENT` | 14 |
| `SPEC_DEMAND_FOUND_NOTHING` | 8 |
| `NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE` | 6 |
| `THE_SITE_NEVER_RAN_IN_THE_FAILING_TEST` | 1 |
| `DEMAND_MET` | **1** (attrs `1c962d15a7`, the same repair as before) |

The composition itself: **7 rows reached, 37 shifts attempted, 0 verified.**

| what a shifted attempt returned | count |
|---|---|
| `SPEC_DEMAND_FOUND_NOTHING` | 22 |
| `NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE` | 8 |
| `NO_VALUE_MATCHES` | 5 |
| `THE_SITE_NEVER_RAN_IN_THE_FAILING_TEST` | 2 |

**Falsified:** *a composition is a value produced at another site.* It is not. Asking the same demand at
37 other productions in the same function recovers nothing, and the reason is not the search: it is what
the seven human fixes actually are.

## 5. What the seven fixes actually are (measured, not asserted)

Read from both revisions' ASTs at the changed function — new top-level definitions, changed `If` tests,
added and removed code lines — and from the diffs themselves:

| commit | what the human fix is | why no site shift reaches it |
|---|---|---|
| click `a6256bfb59` | **new function** `_less_uses_raw_mode`, +32/−11, signature widened | the production did not exist anywhere; there was nothing to move |
| click `becbde5cf4` | **new class** `_SkipClose` wrapping a stream | same: a new production, not a moved one |
| attrs `13105a64f2` | **one line**: `if a.converter` → `if a.converter is not None` | the site already holds the demanded object; the defect is the *relation evaluated*, not the value produced |
| click `a3321c9ca1` | `.encode()` and `nl=False` at the echo call | the demanded fact is a **type at an argument** (bytes, not str), not a value the site returns |
| click `91de59c6c8` | assignment **inside** the existing branch + comment | a statement inside a branch: the branch is right, the body is missing a step |
| jinja `a150ff749a` | the same parentheses at **four** sites | the demanded fact is **consistency across sites**, which one site cannot hold |
| click `70c673d37e` | documentation, an import and a new branch on `self._help_option is None` | the demand is stated in prose the suite does not evaluate |

Two of seven create a production that did not exist. One changes the relation at an existing one. None
of them is a value that happens to live elsewhere.

## 6. The one line that names the bottleneck

`attrs 13105a64f2` is the smallest fix in the thirty: one line, same length, no new names.

```python
if a.converter and not isinstance(a.converter, Converter):          # parent
if a.converter is not None and not isinstance(a.converter, Converter):  # child
```

The site **already has** the demanded object. A falsey `MyConv` instance reaches `if a.converter`, is
judged false, and the converter is never wrapped. Forcing a value at that site cannot help — the value
is the one the test wants. What has to change is the **projection**: which relation is asked of a value
that is already there.

And the demand itself is not a value at that site at all. The test says `MyConv()(1) == 2`: the demand
is a **relation between an argument to a call and the value that comes back**, and both live in a frame
the runtime binder never looked at, because it binds values in the frame *at the site*.

> **The law this round adds. A demand is a relation, not a value; and its producer may be in another
> frame.** The instrument's ceiling is its demand language — one value, one site — and that ceiling, not
> the store and not the search, is why 1 of 30 is verified.

This is also the honest answer to "hand it the most advanced action once". An action is finite and
copyable; the relation an action serves is not. Two agents that both "saw" `.encode()` differ entirely in
whether they know *which* call must now receive bytes. What would have to be installed is not the action
but the demand's form.

## 7. A defect found on the way — the accusation class, caught in the oracle

The 39-test suite flipped: the same test passed and failed on unchanged code. Chasing it produced a real
defect, not a flake.

CPython validates a cached `.pyc` against the source's mtime **in whole seconds** and its size. A repair
that replaces a value with a name of the same length, written inside the same second as the previous
candidate, loads the **previous** candidate's bytecode.

* Measured before the fix: **4 of 8** explorations of a one-line fixture reported `FAILED` for an
  expression that passes, with `return x + x` on disk and `assert 3 == 4` in the traceback.
* The mask points **both ways**: a failing candidate scored after a passing candidate of the same size
  reads as `VERIFIED`. That is a fabricated verification — the accusation class, manufactured by the
  oracle itself.
* Fixed in `identify_a_real_bugs_fix_v1.fresh_bytecode()`: delete every `__pycache__`, run with
  `PYTHONDONTWRITEBYTECODE=1` and a fresh `PYTHONPYCACHEPREFIX`. Used by `run_tests_full`, the space
  search's `run_one` and the assertion driver. Regression test: *"a same-size edit in the same second is
  not masked by stale bytecode"* — with the fix reverted, that test's fixture reproduces the mask.
* **Audit of the previous round:** the whole 30-row sweep was re-run after the fix. **0 of 30 stages
  changed.** The one verified repair was not a cache artifact. `4 of 8 → 0 of 8` is the size of the
  defect that had been silently present in every earlier measurement.

## 8. What is false in the claim

1. **False: "expose it once and it has the capability."** What the exposure installs is an action; what
   the population needs is the relation. The seven examined fixes are two new productions, one changed
   relation, one type at an argument, one statement inside a branch, one multi-site consistency, one
   documentation change. None of them is "a new action".
2. **False: "we are blocked by the store."** 0 parameters, 0 model calls, 574 s. The sweep still finds 1
   of 30. More repetition changes nothing about a demand the instrument cannot state.
3. **False: "instant learning in new arbitrary environments is solved."** The environment supplies the
   *test*, and the test's demands are co-authored with the fix. In 8 of 30 rows the strongest demand the
   instrument can bind is a literal from the test file, which is not the demand that justifies the fix.
   Supply of causally isolated contrasts, not model capacity, is the constraint.
4. **False: "a green suite is self-certifying."** It was scoring a file it had not run in 4 of 8
   measured cases, in both directions.

**True, and it matters:** copying an action is free and nearly instantaneous; that part of the user's
intuition holds. What does not follow is that capacity follows from it.

## 9. The single bottleneck, named

**The demand language.** Everything else in this tree has been measured and cleared: the vocabulary is
large enough (1,843 expressions offered at one site), the search is cheap (~50 µs per candidate), the
oracle is exact and now fresh, the site finder is exact, and 0 parameters are needed. What is missing is
that a demand can only be stated as *a value at one site*, when real demands are **relations over
frames**: "this call must return bytes", "this branch must be taken because the object is not `None`
even though it is falsey", "these two sites must agree".

## 10. Next, and how it is falsified

One mechanism, testable on the same 30 rows:

1. instrument the **assertion's own expression** and take the callee's argument and return values;
2. trace the demanded return **backwards** into the callee's frame, to the sites that produce it;
3. allow the three projections at a test site: `x`, `x is not None`, `not x`.

Same declared acceptance — 1 verified repair whose AST fact is `MORE_THAN_ONE_CHANGE_REGION`,
accusations 0, no verified row preserving 0 recorded passing values — and the same rule as this round:
an unmet acceptance is recorded as a falsification, never tuned into a pass.

## 11. Accounting

| | |
|---|---|
| rows | 30 real commits (click `3495fba1…`, jinja, attrs) |
| composition | 7 rows, 37 shifts, **0 verified** |
| verified repairs | 1 (unchanged, re-audited) |
| accusations | 0 |
| parameters stored | 0 |
| model calls | 0 |
| wall clock | 574.2 s |
| tests | 39 green, 2 new for this round, 1 of them the bytecode regression |
| declared acceptance | **NOT MET**, and recorded as the falsification it is |
