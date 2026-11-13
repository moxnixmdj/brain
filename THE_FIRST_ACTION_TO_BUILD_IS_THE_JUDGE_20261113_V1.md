# The first advanced action to build is the judge — measured on this tree's own test generator

**13 November 2026.** Branch `arena/9bcff20d-brain`, base `ca531123de`. Authority **NONE**:
producer-run sandbox measurement, `$0`, zero model calls, **no new capability registered**, no
family flipped, `truth.achieved` untouched, no test weakened, no protected path touched.

The plan under review says: *Phase 1 — prove it on advanced coding tasks now; build test generation
first; prove learning by counting causal models 10 → 25 → 40.* This round did the cheap thing
before the expensive thing: it ran the advanced actions **that already exist here** and asked what
their success actually means.

---

## 1. The actions you want to build are already in this tree

`canonical/runtime/bound_capabilities/` already ships fifteen test/mutation capabilities, including
`python.tests.generate.scaffold.v1`, `python.tests.mutation_score.v1`,
`python.tests.advance.mutation_kill.v1` (a survivor-killer loop), `python.tests.synthesize.pynguin.v1`,
`python.test.guided_patch_search.v1`, `python.review.diff_mutation_gate.v1`,
`python.repo.diff_apply.full_testgate.v1`, and `python.refactor.test_scaffold.fusion.v1`.

Phase 1 does not need a new action inventory. It needs to know whether the inventory's `verified`
flags mean anything. So that was measured.

## 2. The generator passes its own tests and detects nothing

One two-function module (`discount`, `in_range`), this tree's own generator, then this tree's own
mutation engine on the generator's output:

```text
python3 canonical/tools/test_oracle_strength_measure_20261113_v1.py

generator: generated=2 refused=1 tests_run=2 passed=2 failed=0 verified=False
    its only oracle: self.assertNotIsInstance(result, BaseException)

arm                        mutants killed   score  verdict
scaffold_as_shipped             12      0   0.000  REJECT
no_assertions                   12      0   0.000  REJECT
partial_value_assertions        12      7   0.583  REFINE
value_asserting                 12     10   0.833  ADMIT
```

Two tests generated, two passed, zero failed — and **zero of twelve mutants killed**. The suite is
indistinguishable, to the mutation engine, from a suite with no assertions at all. The generator is
honest about this: it labels itself SMOKE and returns `verified=False`. The failure would be
*ours*, if we counted its output as verification.

This is the local instance of *All Smoke, No Alarm* (arXiv:2606.18168): across 86,156 agent-authored
test-file patches in 2,807 repositories, **80.2% carry weak or no explicit oracle signal**. Agents
produce test *structure* far more reliably than oracle *logic*.

## 3. The survivor-killer already here cannot run

`python.tests.advance.mutation_kill.v1` is the right design — gate, synthesize, re-gate, require
`kill_after > kill_before`. Run here on the same fixture:

```text
pynguin importable: False
ran: verified=False amplified=False tests_generated=0 kill 0.428571 -> 0.428571
synthesizer said: /usr/bin/python3: No module named pynguin
```

It composes an external synthesizer that is not installed, generates nothing, and correctly reports
`verified=False`. An action you cannot execute is not an capability you have.

## 4. The trap: amplification without an independent oracle cements the bug

Seed one realistic defect — `in_range`'s upper bound made exclusive (`value <= high` → `value < high`)
— then run the obvious amplification loop: find inputs where a surviving mutant differs, take the
**current program's** output as the expected value, write the assertion, re-score.

```text
expectations harvested from the running program: killed 7 -> 10, verdict ADMIT
the same suite once the defect is FIXED:         REFUSED (BASELINE_TEST_SUITE_FAILED_OR_EMPTY)
```

The mutation score went **up**, the suite was **admitted**, and it now **defends the bug**: apply the
correct fix and the suite goes red. Higher detection power, pointed the wrong way.

This is not a local quirk. *On the Risks of using LLM-Generated Tests for Regression Testing*
(arXiv:2610.11835, 8 Oct 2026) injected faults into 145 merged PRs in SciPy, Qiskit and pandas:
**8–17% of generated tests enforce the fault, only 2.4–4.8% reveal it**, and after later commits
**83–91% of the fault-enforcing tests still pass** while developer suites detect only **14–30%** of
the accumulated faults. *Do LLMs generate test oracles that capture the actual or expected
behaviour?* (arXiv:2410.21136, Oct 2026 revision) reaches the same mechanism from the oracle side,
with mutation scores of roughly **18–21%** for LLM oracles against **17–20%** for EvoSuite's.

**This is why "show it once and it learns forever" is dangerous rather than merely incomplete.**
Permanent learning of a wrong oracle is permanent wrongness with a green checkmark. It is the same
shape as the token-space hole (#6847) and the weight-space hole (#6855): the write succeeds, the
receipt says success, and nothing independent checked the content.

## 5. What was built: a judge, and a gate on what may be written

`canonical/swe_kernel/test_suite_admission_v1.py` — no new capability, no receipt, authority NONE.
It **reuses** `python.tests.mutation_score.v1` rather than inventing a second notion of "kills".

| verdict | condition |
| --- | --- |
| `REJECT` | baseline passes, **zero** mutants killed — no equivalence excuse applies when nothing dies |
| `REFINE` | some kills, below the caller's bar; every survivor named |
| `ADMIT` | baseline green, no flaky tests, ≥1 kill, score ≥ the caller's bar |
| `REFUSED` | the engine could not judge it (failing baseline, no mutants, flaky tests, broad scan) |

Then the part that makes a refusal useful. For each survivor it searches a bounded input grid for a
call where mutant and program disagree:

- `DISTINGUISHED_BUT_UNASSERTED` → here is the exact call and the value to assert;
- `NO_DISTINGUISHING_INPUT_ON_GRID` → probably an equivalent mutant, **not a proof** (the grid is finite).

Both survivors of the strong suite come back the second way: `rate < 0` → `rate <= 0` and
`rate > 100` → `rate >= 100` are equivalent at the boundary for `discount`. Demanding a score of 1.0
would be demanding the impossible; the bar is caller policy and survivors are candidates, not defects.

And the gate on writing. `amplify()` writes an assertion **only** if an independent expectation table
confirms the value. Measured, same fixture, same round:

```text
gated on an independent expectation table:  DEFECT_FOUND, 2 defects named, 0 assertions written
    in_range(-1, -1, -1): program returns False, spec requires True
    in_range(-1, -1, 0):  program returns True,  spec requires False
the same gate on the correct program:       AMPLIFIED, killed 7 -> 10
```

Identical machinery, opposite outcomes, decided by one input that does not come from the program
under test. On the defective program it **finds the bug and writes nothing**; on the correct program
it earns the same +3 kills as the naive loop, with every written assertion traceable to the spec.
Candidates the spec is silent about are withheld, not guessed.

## 6. What this says about the four phases

- **Phase 1 (advanced coding actions).** The inventory is not the bottleneck; three of the actions
  measured here report success while detecting nothing, and one cannot execute at all. Build the
  judge first, then every existing action becomes measurable.
- **"Prove learning by counting causal models 10 → 25 → 40."** Counting artifacts is the same error
  as counting passing smoke tests. The count that means something is *defects detected that were
  not detected before*, on inputs the learner did not choose, judged by something other than itself.
- **Phase 2 (analysis → code modification).** `next_assertions` already emits the exact call and
  value; `amplify` already writes only what a spec confirms. That is the safe version of the loop.
- **Phases 3–4 (adjacent domains, any computer use).** Every domain needs its own independent
  oracle. A GUI task's oracle is the terminal state, not the agent's report — the failure that
  inflated one benchmark from **65.5% to 94.3%** and flipped its ranking (arXiv:2610.16067).

## 7. Verification

```text
.venv/bin/python -m pytest canonical/tests/test_test_suite_admission_v1.py -q     19 passed
+ generate_scaffold, mutation_score_is_measured, tests_as_the_judge,
  lesson_admission_gate, weight_update_admission                                 114 passed
+ review_diff_mutation_gate, test_audit, test_guided_patch_search                  46 passed
```

The 19 new tests assert the executed counts (0/12, 7/12, 10/12), the bug-cementing arm, the
`DEFECT_FOUND` arm, and that a silent spec writes nothing. One pre-existing flake reappeared and is
reported, not hidden: `test_wake_sleep_recall_and_specialist_controller_v1`'s `wall_ms < 50` timing
assertion failed once under load and passed on rerun (6 passed). The assertion was not relaxed.

## 8. What this does not claim

Mutation score is a **lower bound on detection over the mutants generated**, not a correctness
proof; `adequacy_proved` is `False` in every report. The grid is finite, so
`NO_DISTINGUISHING_INPUT_ON_GRID` is not an equivalence proof. The expectation table here was written
by the producer for a two-function fixture — it is independent of the *program*, not independent of
*me*, and a real deployment needs it authored by someone who is not writing the code. That is the
next thing to build, and it is a specification problem, not a model problem.
