# Two doors count availability differently

Date: 2026-11-12. Branch `arena/8c417005-brain`, base `b86e1823afab5501bcf3dc3cd3b252a2d55bea5b`.
Pre-registered predictions before the run (see the probe docstring,
`door_and_act_availability_census_20261112.py`): five, of which **two held and three
were falsified** — reported below exactly as measured, including the falsifications.

## 1. The claim under test

Round 4 (`A_PERFECT_ACTION_IS_NOT_AN_AVAILABLE_ACTION_20261112_V1.md`) census'd the
chain/macro executor and counted **54 of 145** capabilities
`NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES` from a keyword goal, concluding that binding
arity/defaults were the top availability item. That number was measured at
`grounded_action_v1.act`. The owner's sentences do not arrive there: they arrive at
`live_brain_route_admission_v1.solve` — the sentence door. Round 4 warned that keyword
salad inflates counts (its §1.3 spot-checked four capabilities on realistic sentences).
This round measures **both layers on the same 145 goals**, pre-registers predictions,
and traces the four "most advanced" dispatcher sentences to the exact gate that stops
each one.

## 2. Protocol

- Probe: `door_and_act_availability_census_20261112.py` (committed), run from a
  disposable clone so the repo's own state files are untouched:
  `git clone --quiet --no-local /home/user/brain /tmp/census_clone && cd /tmp/census_clone && python3 door_and_act_availability_census_20261112.py --out /tmp/census.json`
- 145 registry rows, one keyword goal per row (round-4 family), every goal evaluated
  at **both** layers; a raise — including a `SystemExit` from an adapter — is recorded
  as that row's fate, never a process death (commit `3fc2cab2`).
- Runtime 480.8 s, 145/145 rows, 4 adapter exceptions recorded as fates.

## 3. Results (fates, 145 goals each layer)

| `GA.act` (chain/macro executor) | n | `door.solve` (sentence door) | n |
|---|---:|---|---:|
| SELECTED | 64 | EXECUTED (pass) | 24 |
| NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES | 53 | COMPILED_TO_SELF_BUT_FAILED | 39 |
| PRECONDITION_NOT_TRUE_OF_WORLD | 12 | NOT_COMPILED | 52 |
| NOT_A_CANDIDATE | 6 | ROUTED_ELSEWHERE | 26 |
| NO_KEYWORDS | 4 | NO_KEYWORDS | 4 |
| ADAPTER_RAISED (recorded) | 4 | (adapter raises recorded as fates) | — |
| ROUTED_ELSEWHERE | 2 | | |

Door `NOT_COMPILED` statuses: `FAIL__RAW_GOAL_COMPILATION_GAP` **33**,
`FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` **17**,
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` **2** — no
binding-shaped status exists at this layer (there is no `NOT_CALLABLE` at the door).

Cross-layer cells that decide the question:

- act-NOT_CALLABLE ∩ door-NOT_COMPILED: **27** (unreachable at both doors)
- act-NOT_CALLABLE ∩ door-ROUTED: 16; ∩ door-COMPILED_TO_SELF_BUT_FAILED: 7;
  ∩ door-EXECUTED: **3**
- act-SELECTED ∩ door-NOT_COMPILED: **17** (the step executor reaches what the
  sentence door refuses); ∩ door-COMPILED_TO_SELF_BUT_FAILED: 23;
  ∩ door-EXECUTED: 18
- act-PRECONDITION ∩ door-EXECUTED: **0**

The layers disagree in **both** directions. Availability is a property of a door, not
of a capability.

## 4. Pre-registered predictions and verdicts

| # | Prediction (written into the probe before running) | Verdict |
|---|---|---|
| P1 | The sentence door compiles strictly more capabilities to themselves than act selects (64) | **FALSIFIED** — door self-compile = 63 (24 executed + 39 honest fail-closed) ≤ 64 |
| P2 | More than half of act's 53 NOT_CALLABLE reach a different capability at the door | **FALSIFIED** — 26/53 = 49% |
| P3 | The door's dominant non-availability statuses are plan/selection, not binding | **HOLDS** — compilation gap 33 + effect-unserved 17 + confinement 2; zero binding-class statuses |
| P4 | Under the salad goals, git's door row executes (its precondition is world-side) | **FALSIFIED** — git's salad row is `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED`; realistic git sentences pass separately (below) |
| P5 | At most 5 adapter raises at either layer | **HOLDS** — 4 |

## 5. What the two doors are (mechanism)

- **act** — `grounded_action_v1.act`, called by `chain_v1`/`macro_v1` step execution.
  Inputs come from `world_binding.complete_inputs` fill order and
  `declared_argument_default_v1` only. It never imports
  `declared_input_derivation_v1`. Its refusals are therefore binding-layer by
  construction: `NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES`, `PRECONDITION_NOT_TRUE_OF_WORLD`.
- **door** — `live_brain_route_admission_v1.solve`: front compile → `route_admission`
  (named rules) → the SWE derivation merge at line 2116, conditional on
  `is_swe_request(goal)` and `SWE_CID_PREFIXES` → execution → verification. Its
  refusals are plan/selection-layer: which capability the sentence compiles to, and
  whether a stated effect family claims it.

Round 4's 54 is a true act-layer number (reproduced here: 53) and a false statement
about the door. Round 4's "top item: arity+selector defaults" remains the right top
item **for the act layer** and is not the door's blocker.

Realistic-sentence control (measured separately, not from the salad corpus):
`read the git log`, `show the status of the repository`,
`Show the last three git commits` → door pass, `git.repository.operate.v1`,
op=log executed and verified — while act returns PRECONDITION on the same sentence
(`read the git log`). The precondition class at act is not what the owner experiences.

## 6. The four "most advanced" dispatchers, traced to named gates

Each row is a realistic sentence, measured end to end, with the exact gate that stops
it (file:line evidence in parentheses):

| Sentence | act | door | The gate that stops it |
|---|---|---|---|
| `refactor the function stated_family_token in canonical/runtime/swe_typed_plan_v1.py to extract the constant` | NOT_CALLABLE (swe row) | was UNSERVED → **fixes this round** | family trigger read `extract constant`, the sentence says `extract the constant` (`swe_typed_plan_v1._FAMILIES`). With the phrase claimed: `_resolve_family` admits the row with `operation=extract_constant`, `build_plan` decisive. **Next gate:** the egraph synthesizer's baseline probe runs the project suite in-process and is SIGKILL'd (`rc=-9`) → `PROJECT_TEST_BASELINE_UNMEASURABLE` (`egraph_and_deductive_synthesizer_v1.py:104`) |
| `diagnose the root cause of the failing test in canonical/tests/test_swe_git_intent_reuse_v1.py` | NOT_CALLABLE | UNSERVED | derivation only derives `find_root_cause` for the phrase `find the root cause` (`declared_input_derivation_v1.py:2413`); and even claimed, `find_root_cause` ∉ `STATIC_DIAGNOSE_OPERATIONS` (`computer_execution_boundary_v1.py:114`) — the adapter runs the test suite (`run_suite_and_explain_failures`), which is execution, so the confinement boundary refuses **by design** |
| `run ruff lint on the python project` | NOT_CALLABLE (3 rows) | UNSERVED | polyglot's operation enum has no lint operation (5 ops: parse/extract/callers/refs/edit); `python.review.diff_static_triage` needs an existing `diff_path` (admit: `BINDING_REFUSED:diff_path`); running ruff is an external command → boundary by design |
| `format the python source in pkg/calc.py with ruff` | AMBIGUOUS | `COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` | the composer already carries a `ruff format` chain (measured note at `live_brain_route_admission_v1.py:6877`), but automatic command execution has no admitted confinement path (`computer_execution_boundary_v1` docstring: no flag grants authority), and `_serve_by_acting` declines `.py` outputs by pin (`test_the_door_reaches_what_the_machine_can_do_v1.py`) |

Read as a class: **the four dispatchers are not one bug.** One was a phrase near-miss
(fixed here), two end at the deliberate computer-execution boundary (governance, not
dispatch), one ends at an unscalable baseline probe (engineering). Anything that
"fixes binding" would have moved none of these.

## 7. Shipped this round

1. `door_and_act_availability_census_20261112.py` — the dual-layer census with the
   pre-registered predictions in its docstring (commits `5408b113`, `3fc2cab2`).
2. `swe_typed_plan_v1._FAMILIES`: the measured phrase `extract the constant` added to
   the swe family triggers. After: `stated_family_token` claims
   `swe.transform_and_synthesize`, `_resolve_family` →
   `python.swe.transform_and_synthesize.v1` with `operation=extract_constant`,
   `build_plan` decisive; `Branch out the new feature for the report` and
   `what is the constant used for in the documentation` still claim nothing.
3. Pins: `canonical/tests/test_a_near_miss_phrase_is_still_the_sentence_it_states_v1.py`
   (4/4).

## 8. Re-ranked next steps

1. **Egraph baseline scalability** — the extract chain now reaches the synthesizer and
   dies measuring its baseline (`rc=-9`, full-suite discover in one process). Named,
   measured, and the only gate between a whole class of refactor sentences and
   execution.
2. **Sentence-shape derivation coverage** — `diagnose the root cause` (phrase) and the
   diagnose/polyglot `target_path` extraction shapes, for the rows whose chains would
   then be boundary-honest rather than UNSERVED.
3. **Round 4's act-layer arity+selector defaults** — still the top item *for act*
   (53 reproduced), now explicitly scoped to chained/macro steps, not the front door.
4. **Admitted confinement for dynamic operations** (governance): the boundary's own
   docstring states the requirement — a reviewed confinement and effect-verification
   path. This is what stands between the tree and format/lint/diagnose-run sentences,
   and it is deliberately not a phrase table.

## 9. External context (2026)

- *Why Do LLM-based Web Agents Fail? A Hierarchical Planning Perspective*
  ([arXiv 2603.14248](https://arxiv.org/html/2603.14248)): failures decompose into
  high-level planning, low-level execution, and replanning; even with human-authored
  plans executors manage 38.5% plan completion — "execution remains the main
  bottleneck."
- *Do LLM Agents Execute the Plans They Declare?*
  ([arXiv 2609.38108](https://arxiv.org/html/2609.38108v1)): the Plan
  Declaration–Execution Gap — selection and execution failures must be attributed
  separately; final success alone cannot distinguish them.

This round is the same decomposition applied to this tree's own two doors: act is the
executor layer, the door is the selection layer, and the census shows each has its own
dominant failure class.

## 10. Reproduce

```sh
git clone --quiet --no-local /home/user/brain /tmp/census_clone
cd /tmp/census_clone && python3 door_and_act_availability_census_20261112.py --out /tmp/census.json
# predictions and fate tables are in the probe docstring and /tmp/census.json
cd /home/user/brain && python3 -m unittest \
  canonical.tests.test_a_near_miss_phrase_is_still_the_sentence_it_states_v1 -v
```
