# A demand learned from the run is not the missing demand language either

**2026-11-21 · branch `arena/67c67d7e-brain` · authority `NONE__PRODUCER_RUN_SANDBOX` · receipt `intake/RECEIPT_THE_DEMAND_IS_LEARNED_FROM_THE_RUN_20261121_V1.json`**

---

## 0. Requirements restated before acting

Own model, own weights, own runtime; zero runtime model calls; no parametric world-fact warehouse;
inspectable external knowledge that can be deleted; every parameter computed; one experience in an
unseen environment; hardest honest tests; no borrowed output, hand-solving, leakage or counting
another system's work; research the project and the frontier first; one minimal ultimate plan, bad
ideas killed before building; verified, unverified and failed strictly separated; no §6 claim until
it is earned. §2 remains resolved as: computed mechanisms in weights, typed facts outside them,
removable without retraining. `truth.achieved` stays `false`.

## 1. Research before the design

**Project.** `THE_DEMAND_IS_A_RELATION_20261125_V1.md` measured 2 verified repairs in 75 real
one-line fixes and wrote the next move down explicitly: not an eighth hand-written relation, but
"a function learned from the run, with the witness judge as its signal", built over the
`(question, value, frame)` pairs the probe already produces. `the_relation_not_the_value_v1.py`
already supplies the run-selected guard sites, the witness-footprint judge and the control that
refuses a broken oracle. `PURPOSE_GATE_20261121_V1.md` independently names the same boundary:
a residual of names is not a residual of meaning, so an answer must be separation-tested on real
runs. `identify_a_real_bugs_fix_v1.py` supplies project-owned suites and the fresh-bytecode
discipline; the single-line corpus of 45 unseen commits supplies the test.

**Frontier (inputs only, never runtime dependencies).** TraceRepair uses injected runtime snapshots
as *constraints* on generated candidates and reports 392 fixed Defects4J defects, with the authors'
own warning that a candidate can still satisfy tests by coincidence [1](https://arxiv.org/pdf/2604.02647).
DynaFix reruns instrumented programs after each patch and uses execution-level feedback to narrow
the next attempt [2](https://arxiv.org/html/2512.24635v2). The 2026 APR survey records the same
split: trace grounding and stronger hidden oracles are useful, but retrieval-free, model-free
specification inference remains open, and 39 of 66 surveyed systems need extra validation beyond
the public test [5](https://arxiv.org/pdf/2506.23749). These results justify *learning a predicate
from execution* and *judging it with the project's suite*; they contribute no capability or
parameter to this runtime.

## 2. §3 verdict

- **Real:** a run can supply enough typed facts to *compute* candidate predicates, and the
  project's suite can judge them without a model. 43 of 45 rows had a real failing test and an
  accepted human-edit control.
- **False:** that a predicate learned from one suite's guard values thereby finds the demand.
  56 candidates were judged on real commits; **0** were verified. The pre-registered L4 failed.
- **Unproven:** that a different feature family or a larger candidate budget changes this.
- **Missing:** the relation that spans frames. The selected features describe a value at one
  guard; the corpus's remaining demands change which question is asked of a value, move a
  condition out of its enclosing frame, or make two sites agree.

Why not "experience the actions once"? A probe records each value and the test that reached it.
Learning which type-level feature separates red from green is still learning a question about
*one value*. The human fix is one line, but the demand is often a relation between two frames;
no number of replays of the same guard creates the second frame.

## 3. One plan; ideas killed before or during the build

**Plan:** instrument boolean-position guards, run the suite once, score each builtin type-level
feature by fail-matches minus pass-matches at the same site, compile at most four top-scoring
polarities into guard replacements, prefilter on failing nodes, then judge with the full suite
and the strict witness-footprint rule. The human edit is used **only** to validate the judge.

| route | verdict | reason |
|---|---|---|
| hand-write another relation | killed | one hand-written form bought 1/45; the project report prices an eighth form at ~1 row |
| enumerate all guards | killed already | 616 candidates on one row, correct site past attempt 80 |
| learn from observed values | tested here | 56 candidates, 0 verified |
| use the human line to choose | rejected | hand-solving/leakage; forbidden |
| accept a test coincidence | rejected | strict witness footprint plus no broken passing tests |
| store the learned rule as a parameter | rejected | §2; all rules are recomputed from the run |

Killed during execution: an empty verdict map was initially labelled `NO_FAILING_TEST`; that
mistakes a collection error for a green parent suite. The tool now emits `NO_ORACLE`. Missing
`hypothesis`, `trustme`, `ephemeral_port_reserve`, `xprocess`, `uvicorn`, `httpcore` and
`pytest-timeout` in a fresh venv were environment failures, not findings; they were installed and
the affected rows re-measured. The httpx row was rerun after `httpcore`/`h11` and its replacement
row is recorded with an explicit note; no criterion was relaxed.

## 4. Evidence

Pre-registered criteria, all declared in the tool before execution:

| criterion | result |
|---|---|
| L1 candidates computed from probes/failures; human edit only as control | MET (no exception, no unresolved oracle remains) |
| L2 real failing test and accepted control | **43** rows (1 row had no failing test, as in the prior engine) |
| L3 at most 4 compiled candidates per row, chosen by separation gain | MET: 56 candidates, 56 judged attempts |
| L4 ≥1 row previously missed becomes VERIFIED | **FAILED: 0** |
| L5 zero model calls, zero parameters, zero network calls | MET |

Stage counts after the dependency repair: `NO_SEPARATING_RULE` 24, `NO_LEARNED_REPAIR` 20,
`NO_FAILING_TEST` 1. No candidate broke a passing test *and* flipped the witness — those that
flipped anything were rejected as partial flips or broken suites. Total producer time 660.2 s plus
a 10.5 s single-row rerun. Notable: on packaging `b80e6eb0a6`, one row the fixed-form engine had
verified, the learned instrument proposed `empty_collection` and `nonempty_collection` and did
**not** re-derive the repair. This is evidence against the claim that the general feature family
subsumes the hand-written one.

## 5. Tests

`canonical/tests/test_the_demand_is_learned_from_the_run_v1.py` — **6 passed**: a strict separator
is learned and a merely present feature is not; a passing observation is required; rule compilation
rewrites exactly one span; the judge still refuses partial flips and broken passing tests; L4 cannot
count a row the fixed engine solved; one small end-to-end repo verifies a guard learned from two
real executions. Those tests pin the instrument, not capability.

## 6. Non-claims and next bottleneck

Not claimed: OSWorld/SWE-bench performance, GUI/browser use, natural-language understanding, live
wiring, registered capability, independent verification, or §6 completion. The judge is each
project's own test file; the human edit is only a control on that judge. `truth.achieved` stays
`false`.

**Next bottleneck:** the unit of synthesis. Every instrument so far edits one boolean site, and
the corpus's residual demands are relations across frames. The next falsifier must generate and
verify a *multi-site* edit selected by the failing run — for example, splitting a guard into the
enclosing frame or making two guards agree — with no read of the human line and the same strict
judge. If that also fails, the honest conclusion is that a single-run relation language, not just
a single relation form, is the ceiling of this approach.
