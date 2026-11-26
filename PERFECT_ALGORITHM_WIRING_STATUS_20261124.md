# Perfect Algorithm V1 — What Is Wired, What Is Measured, What Is Blocked

Commit `938a580a` on `arena/39d26eb4-brain`. Replaces the earlier claim-oriented
summary with the state of the code as it now exists and the numbers that can be
checked.

## 1. What was built

`canonical/runtime/perfect_algorithm_v1.py` — the mechanism layer: Universal
Meaning Graph (semantic equivalence across syntax), causal graphs, backward
synthesis, differential state tomography, algebraic skill composition,
adversarial input minimization, and the K1 interface prior. Stdlib only, zero
model calls.

## 2. What is actually wired into the live loop

An import that nobody calls is not wiring. Each operator below is called on a
real path, and a test asserts it fires.

| Operator | Wired into | Effect | Authority change |
|---|---|---|---|
| K1 prior | `autonomous_verified_self_improvement_v1._select_active_skill` | contributes a tie-break term to candidate ranking | none — every candidate still passes independent re-authentication, scope, invalidator, precondition and exact-skeleton checks |
| Differential state tomography | `_effect_may_have_occurred(..., state_diff=...)` | a detected state change counts as effect evidence | none — additive by construction; can turn False into True, never True into False |
| Universal Meaning Graph | `executable_skill_program_v7.induce_candidate` | adds a diagnostic `semantic_ir` digest to the candidate | none — candidate still needs an identical executable skeleton and still cannot self-verify |

Measured: the K1 prior is consulted 4 times and ranks 4 skills across the
existing self-improvement suite, whose 33 tests still pass unchanged.

## 3. What is measured, and the claim that was corrected

The original docstring said the prior "cuts branching factor from 8.34 to ~2".
That is not true. Measured on ten elements:

- goal names one of ten interchangeable elements → reported effective branching
  factor 9, with the named element ranked first;
- goal names nothing → reported effective branching factor 9, same ranking.

The metric accumulates score mass, so it tracks the candidate count rather than
the size of the search. A prior **reorders**; it cannot filter. What the prior
genuinely buys is that the search's first try becomes the goal-named element.

The honest measurement is now reported directly: `goal_relevant_rank` is 1 when
the goal names an element and `None` when it names nothing, and
`prior_is_a_reordering_not_a_filter` states the invariant. Three tests cover the
discriminating and non-discriminating cases, so the old overstatement cannot
come back quietly.

## 4. Naming collision, resolved

`canonical/swe_kernel/perfect_algorithm_v1.py` and
`canonical/runtime/perfect_algorithm_v1.py` both declared
`PROJECT_BRAIN_PERFECT_ALGORITHM_V1` for different jobs. The swe_kernel module
is the interactive control loop over a wall-and-lock grid (scan / ask / retrieve
/ fetch / plan / act / learn / admit / save / report) with its own durable
memory. The runtime module is the code/GUI/state mechanism layer and writes no
memory.

The runtime module now carries `PROJECT_BRAIN_PERFECT_ALGORITHM_RUNTIME_V1` and
a guard that raises a named error if both are imported into one process. Both
modules are kept, cross-referenced in their headers.

## 5. Test state

201 passed, 919 subtests, over the twelve suites that touch this surface,
including the unified-model partition test. That test is what caught the new
module: every file under `canonical/runtime` must be either a capability or
indexed source, so the tracked artifact
`canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` was recompiled rather
than the test being relaxed.

Note: `pytest` is not installed in the sandbox image. Two of the suites import
it at module level and therefore error under `python3 -m unittest`, which is not
a defect in those suites. They pass under a pytest installed in a scratch venv.

## 6. SWE-bench Pro V2 HARD-51: blocked, not run

Preflight `qualification_results/pro_hard51_full_metadata_preflight_20261124.json`
is metadata integrity only. It reports `execution_authorized: false`,
`docker_cli_found: false`, `harbor_cli_found: false`, `isolation_verified: false`,
`instances_executed: 0`, status `PREFLIGHT_ONLY_EXECUTION_BLOCKED`. All 51 tasks
are `NOT_RUN_ONESHOT_CARRIER_UNQUALIFIED`.

`which docker harbor` returns nothing in this sandbox. Nothing here qualifies a
score, and no HARD-51 result exists. Running the suite needs an isolated VM with
a container runtime and the Harbor CLI; that is an environment the user must
provide, not something this sandbox can fake without producing an unqualified
number.

## 7. What the next real step is

The bottleneck identified before this work is unchanged and untouched: the
verifier, not the search. The two operators now connected are a tie-break and a
diagnostic. Neither makes the Brain solve a task it could not solve before — the
first measured evidence of that has to come from a real benchmark run on a real
carrier, which is exactly what HARD-51 would provide and what is currently
blocked. Building further operators before that evidence exists would add
untested surface, not capability.
