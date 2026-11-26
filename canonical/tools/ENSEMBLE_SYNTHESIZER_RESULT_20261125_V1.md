# Ensemble synthesizer result: Idea 3 supported (Falsifier #3 does not fire)

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Follow-up to `PLAN_V3_EXECUTION_STATUS_20261125_V1.md`, which falsified Ideas 1 and 4 and named
Idea 3 (ensemble synthesizers) as the one remaining plausible, untested idea. **Tested. Supported.**

---

## What was built

`canonical/runtime/stochastic_synthesizer_v1.py` — a stochastic (random-search) SyGuS synthesizer
over the **same grammar** as `oe_sygus_synthesizer_v1` (it imports `Expr` and `_eval_expr` from
the OE module). Where OE does bottom-up observational-equivalence enumeration (exhaustive to a
size bound), the stochastic synthesizer does random search — exploring a **different region** of
the candidate space. Plus `ensemble_value_expressions`, which runs both and returns the union.
Stdlib only, deterministic given a seed. Tests: `canonical/tests/test_stochastic_synthesizer_v1.py`
(3 passing).

## Falsifier #3 measurement: candidate diversity

Falsifier #3: *"If ensembling synthesizers doesn't widen the candidate space usefully... If the
ensemble produces the same candidates as the OE synthesizer alone, Idea 3 is falsified."*

Measured on 6 synthesis tasks (max_results=8, seed=7):

| task | OE alone | stochastic alone | **union** | overlap | stochastic-unique | widens? |
|---|---|---|---|---|---|---|
| x+1 | 3 | 8 | **9** | 2 | 6 | YES |
| abs(x) | 8 | 5 | **12** | 1 | 4 | YES |
| len(s) | 8 | 6 | **13** | 1 | 5 | YES |
| x-1 | 3 | 5 | **6** | 2 | 3 | YES |
| -x | 8 | 8 | **14** | 2 | 6 | YES |
| floor(x) | 8 | 5 | **12** | 1 | 4 | YES |
| **TOTAL** | **38** | **37** | **66** | — | **28** | — |

**The ensemble produces 66 candidates vs OE's 38 — 74% more.** On every task the union is larger
than OE alone. The stochastic engine contributes **28 unique candidates** the OE enumeration misses
(and vice versa). **Falsifier #3 does not fire. Idea 3 is supported.**

This reproduces the Angelix finding (ICSE'16: ensembling synthesis engines beats any single one)
in our repo: different search strategies explore different regions, and forging them widens the
candidate space.

## Honest scope

- Widening the candidate space is **necessary but not sufficient** for fixing repair tasks. More
  candidates increases the chance of hitting the right patch (the Angelix logic), but the
  candidates still need to be correct, and this was measured on expression synthesis, not on the
  Part B repair corpus (which needs HuggingFace data, inaccessible here).
- The stochastic synthesizer is a **component** (like the OE one), not a repair loop. It widens
  candidates; it does not localize faults or run tests.
- What is proven: **the ensemble widens the candidate space** (66 vs 38). What is not proven: that
  the wider space fixes more repair-corpus tasks. That needs the corpus.

## Plan v3 scorecard (all five ideas)

| idea | result |
|---|---|
| 1. JitRL advantage estimation | **FALSIFIED** (identical 8/15, 6.333×) |
| 2. Memory-doing gate | untested (needs repair corpus) |
| 3. Ensemble synthesizers | **SUPPORTED** (66 vs 38 candidates, +74%) |
| 4. Weight-space fuel gate | **MOOT** (64 verified units << 5000 minimum) |
| 5. Compete on harness | weakened (Ideas 1, 4 did not move any number) |

**One of five ideas survived measurement.** The survivor is the one that widens the candidate
space (reach) rather than optimizing ranking (Idea 1) or gating learning (Idea 4). That is
consistent with the binding constraint being reach.

## What was done

- `canonical/runtime/stochastic_synthesizer_v1.py` — new stochastic synthesizer + ensemble.
- `canonical/tests/test_stochastic_synthesizer_v1.py` — 3 tests, all passing.
- This record. The OE synthesizer was not modified.
