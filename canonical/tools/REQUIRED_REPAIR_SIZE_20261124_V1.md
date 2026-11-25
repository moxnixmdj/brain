# Required repair size, measured — the 79% figure was upstream-diff size

**Status:** measurement complete. **Authority:** NONE (producer-run sandbox). **Model calls at decision time:** 0.
**Scope:** the 87-task `real_fix_pairs_20261119_V1.json` corpus, judged by the repo's own tests.

---

## §0 Why this document exists

`VERIFICATION_AND_THE_REAL_WALL_20261124_V1.md` reported that **79% of the corpus is LARGE**
(multi-hunk, >3 lines a side) and drew the conclusion that "the fix is not an expression".
That number was computed on the **upstream diff** — what the author of the fix commit wrote.

An upstream diff is not a specification. It carries refactoring, docstrings, helpers for
later commits, and formatting. The only specification of the repair in this corpus is the
recorded `failed_nodes`. So the number that decides whether the single-expression wall is
real is:

> **what is the smallest subset of the upstream diff that still makes the recorded nodes pass?**

This document answers it, at three granularities, and then states what the wall actually is.

**Integrity note, stated once and applying to every number below.** The minimiser is a
*measurement*. It sees `after`, which the solver arm never sees. A task whose minimal repair
is 2 statements is **not thereby solved** — finding those 2 statements without the fix is
the entire problem. Nothing here is a solve rate.

---

## §1 The three granularities

Measured over **67 tasks** (see §5 for why 67 and not 70).

| unit | min | p25 | **median** | p75 | max |
|---|---|---|---|---|---|
| upstream added lines | 1 | 4 | **11** | 20 | 102 |
| hunk-minimal lines | 1 | 4 | **10** | 18 | 85 |
| **statements touched** | 1 | 1 | **2** | 5 | 30 |
| statements **added** | 0 | 0 | **0** | 0 | 7 |

Two different facts, both load-bearing:

1. **Line count barely moves** (11 → 10). At line granularity the 79% figure is essentially
   confirmed: the mass of these fixes is real.
2. **Statement count collapses** (median **2**). Lines overstate the repair, because a
   single statement is often 10 lines long. The honest unit for *"could one expression
   express this repair?"* is the statement, not the line.

### Statements touched — the distribution

| statements | tasks | share |
|---|---|---|
| 1 | 24 | **35.8%** |
| 2 | 12 | 17.9% |
| 3 | 6 | 9.0% |
| 4 | 7 | 10.4% |
| 5–8 | 9 | 13.4% |
| 9–30 | 9 | 13.4% |

- **≤1 statement: 24/67 = 35.8%**
- **≤2 statements: 36/67 = 53.7%**
- **≤3 statements: 42/67 = 62.7%**

### Statements added — the finding that kills the blind arm's premise

**80.6% of repairs add no statement at all.** Median 0, p75 0.

The blind arm (`wrap-a-call`, `add-sibling-import`) is an *addition* mechanism. It was aimed
at 19.4% of the corpus. The dominant shape is an **edit to an existing statement** — rewrite a
call's arguments, collapse a `try/except` into one line, `result =` → `return`. That is why
0/18 solved: wrong operation class, not insufficient search.

---

## §2 The wall, restated with evidence

The old claim was *"the fix is not an expression, because 79% of diffs are large."*
That inference is **invalid** — it conflates what the author wrote with what the tests require.
The correct statement has three parts, each measured:

**(a) Localisation is the binding constraint, not repair size.**
`--tb=line` over all 70 well-formed tasks:

| traceback reaches non-test repo source? | tasks | share |
|---|---|---|
| yes | 16 | 22.9% |
| no | 54 | 77.1% |

77% of failures never produce a frame inside repository code. They are `assert a == b`
mismatches and `DID NOT RAISE <Exc>`: the failing line is **in the test**, and the repair
site is wherever the wrong value was computed. A traceback cannot name that line.

> **CORRECTION (§6 of `THE_ASSERTION_IS_NOT_A_SPECIFICATION_20261124_V1.md`).** At least 7
> of these 14 are **not** missing guards: the `raise <Exc>` is already present in the target
> function and does not fire, so the repair is its predicate or literal. The label below is
> the *failure message* shape, not the repair shape.

**(b) The dominant failure shape is a missing guard.** Merged classification:

| repair shape | tasks | share |
|---|---|---|
| WRONG_VALUE (`assert a == b`) | 23 | 32.9% |
| OTHER (assert-diff, unclassified) | 21 | 30.0% |
| **MISSING_GUARD** (`DID NOT RAISE X`) | **14** | **20.0%** |
| MISSING_API (`no attribute`, `cannot import name`) | 7 | 10.0% |
| WRONG_RAISE | 3 | 4.3% |
| WRONG_MESSAGE | 2 | 2.9% |

14 tasks state their specification directly: *this input must raise `<Exc>`*. That is the
cheapest possible specification and nothing in the current pipeline consumes it.

**(c) 36% of repairs are single-statement.** That subset is reachable in principle by a
single-expression mechanism — *if* the statement can be located. §2a is why it usually cannot.

**Verified:** every number above, by execution against the repo's own tests.
**Unverified:** that any mechanism can *find* the single statement in the 24 single-statement
tasks without seeing the fix. That is the open problem, and it is not the same problem as
repair size.

---

## §3 The local arm, run honestly

`real_fix_oracle_baseline_v1.py --arm local`: localise from the traceback, mutate only the
statement the failure raised from, using **grammar-derived** mutations only (guard removal,
comparison/arithmetic/boolean duals on word boundaries, literal nudges, return coercion,
assert negation). It never sees `after`.

| metric | value |
|---|---|
| well-formed tasks attempted | 56 |
| tasks with ≥1 localised candidate | 12 (21.4%) |
| candidates tried | 97 |
| **solved** | **1** |
| candidates rejected by the whole-file oracle | 2 |

**Solved:** `pypa/packaging` `fe8f0bb99c` — *"Remove URL validation from requirement parsing"*.
`drop_raise` at `src/packaging/requirements.py:48`, first candidate, 5.32 s, accepted by the
failure-subset oracle over the whole test file. The fix commit's own subject is literally the
mutation the grammar produced. **1/56 = 1.8%.**

**Why not more.** Of the 56, only 12 had a localisable site; the rest are §2a. And within
those 12 the correct repair is frequently not a mutation of the raising statement at all —
task 0's `__new__` raises *by design* (`test_cannot_construct_directly` requires it to raise),
so the repair is a new `__reduce__`/`__getstate__` **elsewhere**. Traceback localisation
points at the guard; the repair is at the protocol boundary. That is a principled failure,
not a search failure.

---

## §4 Oracle defects found while measuring (reported, not dropped)

1. **3 tasks have an empty `failed_nodes` list.** The original validate run passed them as
   well-formed because `pytest` with no node ids runs the *whole suite*, which redefined the
   oracle silently. True well-formed count is **67/87**, not 70/87. Defective: 20/87
   (17 unresolvable node ids + 3 empty node lists).
2. **7 of 67 minimal patches satisfy the recorded nodes but break their own test file.**
   The corpus rule is "the recorded nodes pass", which is strictly weaker than "the repair is
   correct". Any future solve claim must state which oracle it used.
3. **`-x` cannot express "no new failures".** The first regression oracle used `-x` and
   `--deselect`, and silently passed everything. The fix is a **failure-set subset** test
   (`Oracle.fail_set`), which is what rejected the 2 bad candidates above.

---

## §5 Method

`canonical/tools/real_fix_minimal_repair_census_v1.py`

1. `difflib.SequenceMatcher` over `before`/`after` → opcodes; non-equal opcodes are the
   reversible units.
2. Greedy delta debugging, **largest hunk first**, revert and keep every revert the recorded
   nodes still accept, iterate to fixpoint (≤3 passes).
3. Statement granularity: AST statements whose whole extent lies inside a diff-introduced
   range are *added*; statements that intersect a changed range and have no changed child
   statement are *touched* (innermost, so a one-line change inside a 12-line `def` counts
   once, not thirteen).
4. Final minimal patch re-checked against the **whole test file** as a failure-subset test.

Median cost ≈ 11 oracle runs/task; mean oracle run 0.54 s.

---

## §6 What this changes about the plan

| belief before | measured | consequence |
|---|---|---|
| "79% of fixes are not expressions" | median **2 statements**, 35.8% are 1 | the wall is lower than claimed — but by statement count, not line count |
| "the repair is an addition" | **80.6% add nothing** | addition mechanisms are aimed at 19% of the corpus |
| "localise from the traceback" | **77% of tracebacks never reach repo code** | localisation must come from *provenance of the wrong value*, not the traceback |
| "the test tells you nothing" | **14 tasks name the required exception** | a missing-guard specification is directly extractable and unused |
| "70/87 usable" | **67/87** | 20 corpus defects, not 17 |

**Next, in order:** (1) aim the mined-invariance engine at the 24 single-statement tasks;
(2) build the provenance-based localiser for wrong-value failures, since that is 77% of the
corpus; (3) consume the `DID NOT RAISE <Exc>` specification directly — it is the only place
where the corpus hands over a first-order requirement.

**Nothing in this document is a capability claim.** No repair was produced without seeing the
fix except the one in §3, which is reported with its denominator.
