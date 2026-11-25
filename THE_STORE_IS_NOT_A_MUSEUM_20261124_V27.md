# THE STORE IS NOT A MUSEUM — flipping two recorded contrasts breaks six real tests
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project then web; name the
> real limiting factor; kill the idea before building it; verified / unverified / failed; hardest real
> tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The chain, in one place

Last round harvested 49 behavioural entries by executing functions on contrasting inputs, and I ended by
saying the store is a museum until something consumes it. Two steps:

1. **Do the entries connect to anything?** 4 of the 49 have a RAISE contrast. All 4 of those functions are
   called by the repo's own tests: **1,853 call sites, 151 of them at the contrasting argument position.**
   A parser flags **none** of those functions as able to raise — so the entries are not restating the source.
2. **Does an entry change an outcome?** For each contrast, monkeypatch the function so the contrasting
   position receives the *other* witness value, and run the test file.

## 2. The intervention, with its control

| | trials | moved |
|---|---|---|
| identity control (identical wrapper, no swap) | 4 | **0** |
| intervention (witness flipped) | 4 | **2** |

```
a_name_gets_its_value_from_the_run_v1::convert    11 passed  →   5 passed, 6 failed
causal_dependency_repair_v1::read_set_argv        11 passed  →  10 passed, 1 failed
argument_construction_v1::measure                 11 passed  →  11 passed
a_name_gets_its_value_from_the_run_v1::main       26 passed  →  26 passed
```

**Flipping two recorded contrasts breaks six real tests, and the identity control moves nothing.** Those
tests depend on the behaviour the entry recorded. That is the first time in twenty-seven rounds that
something this project learned from one execution has been shown to *matter* to an outcome it did not come
from.

The two that moved nothing are recorded, not smoothed: a test file that never reaches that argument at that
position cannot testify either way, and it does not show the entry is wrong.

## 3. The measurement bug that nearly made this a false negative

The first run reported **4 of 4 contaminated controls**. The cause was not contamination — it was that
`outcome_moved` compared pytest's summary *line*, which ends in a wall clock:

```
"11 passed in 1.34s"   vs   "11 passed in 1.85s"
```

Every run differed, so the identity control "moved" every time, and the whole intervention result was
inadmissible. Fixed by comparing only `(passed, failed, errors)`. The durations are still recorded for
reporting and a test now asserts they never enter the comparison.

This is the third comparator-of-convenience bug in this project — after the mean-of-ratios coverage that hid
zero-prediction runs (V21) and the selection objective that disagreed with its own price table (V23). The
pattern: **the most convenient number to compare is usually not the one that carries the meaning.**

## 4. What this is and is not

**Is:** a demonstrated causal connection between an entry earned by execution and outcomes on real tests it
was not derived from. The evidence chain is complete and each link is measured: entry → call sites →
intervention → outcome change → clean control.

**Is not:**
* a benchmark result. Four contrasts, two moves. SWE-bench Pro, Terminal-Bench 4.0 and OSWorld 2.0 remain
  untouched and `docker: command not found`.
* general. The entries are single argument positions at single value pairs, and the ladder is 3–4 values
  deep, which is why only 4 of 49 carried a raise contrast.
* a predictor. Nothing here predicts an unseen task; it establishes that the entries *bind* to reality.

## 5. The honest table, seven rounds

| finding | status |
|---|---|
| lifting moves coverage 0.126 → ~0.70 on ten machine worlds | verified, scope-limited |
| vocabulary transfers across codebases (stated over syntax) | verified — 0.9796 vs 0.9896 |
| vocabulary predicts test outcome | **failed** — equals "always pass" at equal coverage, 0 failures predicted |
| cross-machine law transfer | **failed** (twice) |
| guards · saturating questions · accuracy-gated stopping | **failed** (three rounds) |
| behavioural entries earned by execution | verified — 49, all replayable |
| **entries bind to real outcomes under intervention** | **verified — 2 of 4, clean control, 6 test failures** |
| any benchmark row | **not producible** (`docker: command not found`, logged once) |

## 6. Verified / unverified / failed

**Verified by execution:** 1,853 call sites and 151 at-contrast sites; 0 of 4 functions flagged by a parser;
2 of 4 interventions moving outcomes with 0 of 4 controls moving; 6 and 1 real test failures under flip.

**Failed, mine, this round:** the summary-line comparator, which produced a false "all four contaminated"
and would have killed a true result had I not investigated it.

**Unverified:** whether an entry can predict the outcome of a test it was not derived from *before* running
it. This round shows binding, not prediction. Prediction needs held-out contrasts and is the next step.

**Not publishable:** any benchmark row. Nothing here is a claim about SWE-bench Pro, Terminal-Bench 4.0, or
OSWorld 2.0, and no comparison to any frontier model is made.

## 7. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 23.2 s (4 test files x 4 runs)
```

5 new tests including one that fails if a timing ever re-enters the comparison. Guard PASS (17 rules).

## 8. Next

Binding is proven; prediction is not. The next instrument splits the 49 entries into two halves by function,
learns "contrasts of this shape matter" from one half, and asks whether it predicts which *held-out*
contrasts will move a test — before running them. If that fails, the store carries evidence but no
inference, and the honest next move is to say so and stop growing it.
