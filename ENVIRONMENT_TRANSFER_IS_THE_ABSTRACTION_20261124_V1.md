# Environment transfer is the abstraction, not the experience

*2026-11-24 · branch `arena/839ba1ac-brain` · base `c4f529eb` · receipt `canonical/verification/ENVIRONMENT_TRANSFER_GIT_PROBE_20261124_V1.json` · probe `canonical/runtime/environment_transfer_git_probe_v1.py`*

Authority: sandbox measurement by the producer. Nothing here is a verifier's run, a benchmark, or a terminal result.

---

## 1. Requirements I am bound by (restated)

- Own model only. Zero model calls, zero stored parameters in anything that ships. Knowledge lives outside the weights, can be added or removed without retraining, and learning writes to that store from a single experience.
- Research before building. Search the project first, then the web. Treat everything found as input to test, not as truth.
- Test on hard, unseen cases. Report honestly: verified, unverified, failed. No "done" without the done criteria.
- Remove before adding. No parts that do not justify themselves.
- Honest about what is not solved. Do not ask the user questions; resolve ambiguity myself and state the choice.

**§2 contradiction, resolved (and checked against evidence here).** Instant learning needs a store. The store is an inspectable transition table `(state_key, action) -> state_key`, written by acting, containing no weights and no facts about the world beyond what was observed. That keeps the test in §2 satisfied: removing a row removes a learned transition, and nothing is retrained. The probe confirms `model_calls = 0` and `stored_parameters = 0`. What the evidence adds is a sharper boundary: the store is only reusable across environments if its *state keys* are abstract. Raw keys store instance facts, and instance facts do not transfer (§3). So the boundary is: **store transitions over abstract states; keep the abstraction explicit and learnable.**

## 2. What exists in the project (searched, including non-obvious names)

| name | what it is | status when I ran it |
|---|---|---|
| `canonical/runtime/environment_learning_v1.py` | generic `reset/act/state` learner: builds `(state,action)->state` by acting, then BFS shortest plan over the learned table, then executes and checks the goal | works (below). Known gap: `drive(budget=0)` with a prior model fails closed because prior goal states are not carried (§3.3) |
| `instant_learning_demo.py` | top-level demo of "do it once, learn permanently" via `solve_or_learn` | **fails**: both calls return `FAIL__RAW_GOAL_COMPILATION_GAP`, tier `tier2_unconfined_documentation_execution_refused`. The script still prints "This is 'do it once, learn permanently'" and a speedup figure that compares two failures. Those prints are narrative, not measurements. |
| `canonical/runtime/instant_condition_store_v1.py`, `procedure_memory_v1.py`, `scan_and_diff_against_memory_v1.py`, `acquired_operator_memory_v1.py`, `experience_v1.py` | memory / procedure stores with the same flavor | not yet run here; they are the candidate homes for an abstraction store |
| `canonical/runtime/goal_compiler.py`, `capability_planner.py`, `same_identity_supervisor.py`, `BOUND_CAPABILITY_REGISTRY_V1.json` | goal compiler (fails closed on unknown goals), precondition/effect planner, same-identity runtime, bound tools | present; not exercised in this round |
| `canonical/runtime/bound_capabilities/`, `canonical/swe_kernel/` | software-repair and verification machinery | present; not exercised in this round |
| `THE_BRANCH_IS_THE_MODEL_20261128_V1.md`, `THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_20261128_V1.md`, `THE_REPERTOIRE_IS_A_QUERY_20261129_V1.md`, `THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_20261129_V1.md` | the most recent research rounds on this exact question (plan by executing, goal as a statistic of the trace, actions as a queryable catalogue, counterexample-guided refinement of the abstraction) | **not reproducible in this checkout**: their scripts are not present and the local git history is one commit. I did not rely on their numbers. |

Where the rounds' ideas point is the same as this probe's result: planning by execution (copy, run, read the exit status) removes the need for a predicted world model. Their open problem, the one this probe measures, is the abstraction.

## 3. What I measured (real `git`, no model, no fixtures written by hand except the start state)

Repository A: `main` with `a.txt`; the agent sits on `feature` with an uncommitted edit to `a.txt` and an untracked `junk.txt`. Goal: on `main`, clean tree, `a.txt` at its `main` content. Repertoire: 13 real git invocations (`checkout`, `stash`, `clean`, `add -A`, `commit`, `reset --hard`, `merge --abort`, `checkout -f`, ...). The learner is not told what any of them does.

**3.1 Learning on one instance works, cheaply.** Budget 300 walks, seeds 0 and 1:

| seed | states | transitions | plan found | goal observed after executing | seconds |
|---|---|---|---|---|---|
| 0 | 21 | 164 | `clean -fdq`, `checkout -f main` | yes | 15 |
| 1 | 20 | 175 | `add -A`, `checkout -f main` | yes | 16 |

Honest reading: this environment is tiny (about 20 states). "Learn everything reachable" was affordable here, so the question of goal-directed versus learn-everything is **not decided** by this measurement. It only shows that exhaustive learning of a small environment costs about 15 seconds.

**3.2 Transfer to a new repository needs an abstraction. Measured 2 of 2 vs 0 of 2.** Learn on A, then plan on a new repository B (different tag, same structure), with zero new actions on B except observing its start state:

| state abstraction | B's start state is in A's model | goal reached on B by the plan from A's model |
|---|---|---|
| `projected`: content class (main / feature / missing) | 2 of 2 | **2 of 2** (plans as in 3.1, executed on B, goal checked on B) |
| `raw`: literal content of `a.txt` (includes the instance tag) | 0 of 2 | **0 of 2** (no plan exists) |

Honest reading: the transfer succeeded because I wrote the abstraction by hand. The probe measures that the mechanism transfers *when the state is abstract*, not that the learner found the abstraction. The raw result is the first hard measurement of the actual bottleneck: **what the store keys on decides whether experience transfers at all.**

**3.3 Two defects found along the way (reported, not yet fixed).**
- `drive(..., budget=0, prior=model)` returns `FAIL_CLOSED__GOAL_NEVER_OBSERVED` even when the prior model contains the goal. The goal is evaluated only against observations from the current run, and the prior carries keys, not snapshots, so the goal cannot be re-evaluated. The fix is to carry the goal predicate's satisfying keys (or the snapshots) inside the stored model. I did not change `drive()` in this round because the right fix changes the model format.
- The plan the learner found, `add -A` then `checkout -f main`, and the plan `clean -fdq` then `checkout -f main`, both **discard the user's uncommitted edit** to `a.txt`. The goal I wrote does not say to preserve user work, so the planner is correct about my goal and wrong about what a person wants. This is the central goal-specification problem in one line: the goal must include what must not change. It is not solved by more experience.

**3.4 The instant-learning demo fails** (§2). Its success prints must not be cited as evidence.

## 4. Verdict on the claims

| claim | verdict | evidence |
|---|---|---|
| "Instant learning is solved." | **Unproven; the demo in the repo fails.** One-instance learning works in a small environment (3.1). | 3.1; `instant_learning_demo.py` output |
| "Give the agent each action once and it owns everything on a computer." | **False as stated.** One experience gives the effect of an action in the state it was tried in. Transfer needs an abstraction that the experience alone does not supply. | 3.2 raw row: 0 of 2 |
| "Save the exact experience." | **False as a store design.** Raw keys do not transfer. | 3.2 |
| "Save the important learning and generalize." | **True in direction, unimplemented.** The generalization is the abstraction, and the abstraction is currently mine. | 3.2 projected row |
| "Plan by executing, not by predicting the world." | **Supported.** Plans executed on B reached the goal with zero predicted transitions; the planner only ever ran real `git`. | 3.2 projected row |
| "Learn everything, then generalize." vs "be goal-directed." | **Undecided here.** Exhaustive learning cost 15 s on a 20-state machine; that does not show it scales. The goal decides what to plan, but it also needs the "must not change" part (3.3). | 3.1, 3.3 |
| "The web can supply what the environment's own documentation holds." | **Unproven here.** Not tested. The rounds above claim a catalogue of ~4,600 options from `--help` pages on one machine; I could not reproduce it. Web-retrieved text would still need to become executable, checked action models; retrieval alone is not learning. | not measured |
| "A model can be learned from web and trace data." | **Literature direction, not evidence for us.** Trace-grounded world models exist (Trace2Env, arXiv 2610.06100; Trace2World, arXiv 2610.30792, which reports 91.1% end-to-end reproduction on its own benchmark). Those are their numbers, not measured here, and they use learned models, which our runtime may not. We keep the idea (abstraction from traces), not the model. | web search, unverified |

## 5. The real bottleneck, from first principles

1. **Abstraction discovery is the limiting factor.** The table transfers exactly when its keys are abstract, and the learner today cannot choose the abstraction. Everything else (exploration, planning, executing and checking) already works in this measurement.
2. **Goal specification needs an explicit "must-not-change" part.** Without it, the planner discards user work and reports success. This is the most dangerous failure in the list because the reported result looks correct.
3. **The prior/goal carrying defect** (3.3) blocks reuse of any stored model on a new instance even when the abstraction is right.

## 6. The plan (minimal) and rejected ideas

**Plan, next round:**
1. Automatic abstraction, first principles: partition the observed states into the coarsest classes that are (a) deterministic under every action seen (same class and action give the same successor class) and (b) constant on the goal predicate. This is partition refinement / bisimulation minimization, and it needs no model and no parameters. Candidate features are the raw components (branch, dirty set, stash depth, content). A feature is kept only if removing it breaks determinism or goal-consistency on the observed runs.
   - Pass: on three or more unseen git repositories with different file names and content, the learned abstraction gives a zero-experience plan that reaches the goal, with no wrong goal claims.
   - Fail: any plan that reaches a state the goal does not hold in, or any abstraction that is only consistent on A.
2. Make the goal explicit with a must-not-change clause (for example, "uncommitted user edits survive"), and show the planner refuses the destructive plans above.
3. Store the goal's satisfying keys inside the model, so `drive(budget=0, prior=...)` works (3.3).
4. Repair `instant_learning_demo.py` so it reports what happened, or remove it. Its current prints are not evidence.

**Rejected:**
- *Store raw episodes.* Measured: 0 of 2 transfer (3.2). Rejected.
- *Learn a neural world model to predict successors.* Not needed. Executing the action and reading the exit status gives the successor exactly. Adding a predictor adds parameters, errors, and a model dependency. Rejected by "best part is no part."
- *Fetch the environment's manual at run time and act on its text.* Text is not an executable, checked action model. Rejected until a checked action model comes out of it.
- *Declare generalization because one hand-written abstraction transfers.* That is the same mistake as counting the author's abstraction as the agent's. Rejected; the probe labels it as such.

## 7. Done criteria (§6): not met

The system does not yet run on its own store with zero model calls on the hard, unseen environments the mission requires. Measured in this round: one small environment (learning works), one hand-abstraction transfer (works, not learned), one raw transfer (fails), and two defects. This is progress and the next bottleneck is named above.

## 8. Notes

- Some files in the repo are dated after 2026-11-24 (for example `THE_GUIDE_IS_A_TEST_SUITE_20261204_V1.md`). I treated all of them as unverified.
- I did not touch the governance files, the referee, or the protected paths. `execution_guard/repo_integrity_guard_v1.py` reports 0 violations and `agent_orientation_check_v1.py verify` passes with this change.
- Two state files under `canonical/astra_runtime/state/` were modified by running the existing demo. I restored them; they are not part of this change.
