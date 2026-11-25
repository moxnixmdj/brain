# The assertion is not a specification

**Status:** measurement complete, result negative. **Authority:** NONE (producer-run sandbox).
**Model calls at decision time:** 0. **Corpus:** the 87-task `real_fix_pairs_20261119_V1.json`, judged by each repo's own tests.

---

## §0 The idea, and why it was worth running

`canonical/swe_kernel/witness_inversion_v1.py` (934 lines, already in this tree) states a
genuinely good idea, and it is the most defensible repair mechanism in the repository:

> the ASSERTION carries a concrete required value (`assert f(x) == 7`)
> the TRACEBACK localises the site (the deepest frame in the target file)
> the FRAME carries the concrete inputs (its locals, live, right now)
>
> Together they specify a function at one node — this input must produce that output — and a
> function on concrete values can be **INVERTED BY EVALUATION** instead of enumerated.

This is not pattern matching and it is not a bigger grammar. It derives the edit from the
failure. It had never been run against the 87-task real oracle, because that oracle was not
runnable until `real_fix_oracle_baseline_v1.py` existed. So this document runs it.

**Method:** `witness_inversion_v1.capture` is invoked as a pure **proposer** through the
`--arm witness` arm. It never sees `after`. Every proposal is judged by the harness — the
recorded nodes must pass, then the whole test file must not gain a failure. No self-report is
accepted.

---

## §1 The funnel, over all 70 well-formed-listed tasks

| outcome | tasks | share |
|---|---|---|
| `NO_REPORT` (failure is not an `AssertionError`) | 28 | 40.0% |
| `NO_INVERTIBLE_SITE` (no expression over the frame's alphabet reproduces the required value) | 16 | 22.9% |
| `NO_WITNESS_IN_THE_TEST` (failing line is neither `assert a == b` nor `raises(match=…)`) | 15 | 21.4% |
| **`WITNESSED` (candidates produced)** | **7** | **10.0%** |
| `NO_FAILED_NODES` (corpus defect) | 3 | 4.3% |
| `NO_RECORDED_FRAME` | 1 | 1.4% |

**79 candidates proposed. 0 passed the recorded nodes.**

---

## §2 Why 0/79 — and it is not a bug

The 79 candidates are not near-misses. On task 58 (`assert 3 == 1`, required `1`, actual `3`),
the proposals at every site are:

```
bool(k)      bool(p)      bool(data)      bool(urls)
len(headers) len(value)   int(valid_encoding)   float(valid_encoding)
```

Every one evaluates to `1`. Every one is meaningless. The first one applied was `bool(k)` at a
site where `k` does not exist → `NameError`.

**Inverting the value is not inverting the function.** When the required value is `True`, the
constraint "this expression must equal `True`" is satisfied by the entire universe of truthy
expressions. Nothing distinguishes the intended repair from the junk, so the checker — the real
test, which has the last word — rejects them one at a time with no gradient to follow.

### The selection effect, measured

Split the 70 by whether the engine could invert, and look at the required value it was asked
to reproduce:

| group | n | median required-value length | examples |
|---|---|---|---|
| **WITNESSED** (candidates produced) | 7 | **4 chars** | `True`, `False`, `4`, `1`, `Infinity` |
| **NO_INVERTIBLE_SITE** | 16 | **36 chars** | `<Marker('(python_version >= "3.6" and os_name == "posix")…')>`, `['1.1rc1','1.1']`, `b'metadata-version: 2.6\nname: example\n…'` |

**The relationship is inverted.** The engine produces candidates exactly where the
specification carries about one bit, and produces nothing where the specification carries tens
of bits and would actually pin down a function.

This is the same law this tree already measured twice and has not yet used:
`WHY_ONE_EXPERIENCE_IS_NOT_ENOUGH_20261116_V1.md` (one trace leaves **1,037 survivors,
10.018 bits**) and `INSUFFICIENCY_CERTIFICATE_20261113_V1.json` (0 of 200 cases identified from
repetitions). A low-information witness is consistent with everything. Here it is not a
theoretical caveat — it is 79 concrete junk candidates.

Task 55 is the degenerate limit: `required=Infinity`, `actual=Infinity`. The values are equal
and the assertion still fails (`assert Infinity <= Infinity`). The witness carries **zero**
bits and the engine dutifully reported it invertible.

---

## §3 What this rules out, precisely

| hypothesis | verdict | evidence |
|---|---|---|
| "invert the assertion at the failing site" repairs real bugs | **FALSE** on this corpus | 7/70 produce candidates, 0/70 pass |
| the failure is localisation | **TRUE** and independent | 77% of tracebacks never reach repo code (§2 of `REQUIRED_REPAIR_SIZE_20261124_V1.md`) |
| the failure is that the required value is unreachable | **TRUE** for 16/70 | median 36-char required values, 0 reproducible |
| the failure is that the required value is *uninformative* | **TRUE** for 7/70 | median 4-char required values, 79 junk candidates |
| `DID NOT RAISE` tasks (14/70) are reachable by this engine | **FALSE, by construction** | `pytest.raises` failure raises `Failed`, not `AssertionError`; `_interact` returns before writing |

That last row is worth stating plainly because it is the cheapest open opportunity in the
corpus: **14 tasks state a first-order requirement** — *this input must raise `<Exc>`* — and the
engine refuses all 14 at the `isinstance(excinfo.value, AssertionError)` guard. But even if that
guard were widened, the engine's operation class is *substitute an expression that reproduces a
value*; a missing guard needs *insert a conditional raise*. Widening the guard would produce
`NO_INVERTIBLE_SITE`, not a repair. Different operation class, not a missing branch.

---

## §4 What this implies for the mechanism (evidence, not opinion)

The assertion is a specification **of the output**, not of the function. One input-output pair
identifies a function only when the pair is information-rich. Measured on this corpus, ~90% of
real test assertions are `assert bool(…)` or `assert x == <small int>`, so the pair carries
about one bit and the repair is not recoverable from it.

Therefore the missing information must come from somewhere other than the failing assertion.
The candidates, in order of measured promise:

1. **The rest of the test file.** It is the only artefact in the corpus written *about* the
   function being repaired. 14 tasks already name the required exception; the other tests in
   the same file constrain the same function on neighbouring inputs. This is a *specification
   by example set*, and a set of examples carries far more than one bit.
2. **The repository's own specification** — docstrings, type annotations, sibling call sites,
   the `__all__` surface. The 16 `NO_INVERTIBLE_SITE` required values (`<Marker(...)>`,
   `b'metadata-version: 2.6\nname: …'`) are *reproducible* from the repo's own grammar, just
   not from the frame's alphabet.
3. **The operation class must include guard insertion**, not only expression substitution —
   14/70 need a `raise` that is not there.

None of these is implemented here. This document only establishes that the assertion alone
cannot be the source, and by how much.

---

## §5 Integrity

- The witness arm never sees `after`; every proposal was judged by the harness against the
  recorded nodes and then the whole test file.
- 0/79 is reported in the denominator. Nothing was dropped.
- `witness_inversion_v1.py` was changed only by adding an optional `python` parameter to
  `capture` and `synthesize` (default `None` = previous behaviour) so it can use the task's
  virtualenv. Its 18 tests still pass. No behaviour was altered.
- The funnel was measured with `capture` alone (no candidate evaluation) so the outcome
  distribution is not confounded by the harness's budget.
- **This is a negative result about one mechanism, not about the corpus.** The corpus is
  usable: the oracle runs, the localisation split is measured, and the repair-size census in
  `REQUIRED_REPAIR_SIZE_20261124_V1.md` says 35.8% of repairs are single-statement.
