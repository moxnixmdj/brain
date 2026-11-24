# The abstraction is learned from counterfactual resets, transfers to new instances, and is not yet sound on new structures

*2026-11-24 · branch `arena/839ba1ac-brain` · follows `ENVIRONMENT_TRANSFER_IS_THE_ABSTRACTION_20261124_V1.md`*

Authority: sandbox measurement by the producer. Not an independent verification, not a benchmark, not a terminal result. Real `git`, one environment, no model calls, no stored parameters.

---

## 1. Requirements I am bound by (restated)

- Zero model calls and zero stored parameters in anything that ships. Knowledge is an external, inspectable store. Learning writes to that store from experience.
- Research before building, then test on unseen, hard cases. Report verified, unverified, failed separately.
- "Remove before adding." Every probe, field and line must justify itself.
- No questions to the user. Ambiguity is resolved by the most defensible choice and stated.
- §6 is not met. This round does not change that.

**§2 contradiction, still resolved as before.** The store is an explicit transition table over *abstract* states. This round measured what the abstract state must be (§3.1) and where the store fails (§3.3).

## 2. What exists (searched first)

- `canonical/runtime/environment_learning_v1.py`: the generic learner from the last round. Unchanged.
- No generic trace-abstraction module existed. Searching for `nuisance`, `bisimulation`, `partition refinement`, and `invariant` turned up only domain-specific quotient modules for acceptance rules (`acceptance_quotient_simulation_v*.py`, `c_load_bearing_state_quotient_v1.py`, `computed_equivalence_quotient_v1.py`, `recursive_abstraction_v5.py`, `semantic_operator_counterfactuals.py`). None operates on environment transitions. I did not reuse them.
- Web (one search, depth 1): trace-grounded world models (Trace2Env, arXiv 2610.06100; Trace2World, arXiv 2610.30792) and computer-use world models (CUWM, arXiv 2602.17365). Their numbers are their claims. They use learned models, which our runtime cannot, so I took only the idea of abstraction from traces.

## 3. What was built and measured

### 3.1 Abstraction from counterfactual resets (new mechanism)

`canonical/runtime/environment_abstraction_v1.py`. The mechanism:

1. **Intervene on the reset.** Run the same environment from several starts that differ only in instance identity (a tag in a file, an untracked file name). Each start is one counterfactual.
2. **Invariant vocabulary** = tokens that occur in every start. Tokens that change with the start are nuisance, so the agent learns them without being told.
3. **Abstract** each observation by masking non-invariant tokens *in place*. The masking keeps whitespace layout.
4. **Gate.** Accept only if the abstract transition system is deterministic and every abstract state is goal-consistent. Otherwise refuse. The gate is fail-closed, not patched.

Bug found and fixed during the build: a first version split and re-joined tokens, which erased whitespace. Porcelain status `" M a.txt"` (unstaged) and `"M  a.txt"` (staged) collapsed into one abstract state, which produced one real nondeterministic edge. The gate refused, and a debug run located the cause (`commit -qm wip` succeeds on the staged variant and fails on the unstaged one). The fix is one line: mask in place.

### 3.2 Same-structure transfer (the previous round's test, now learned)

Probe `canonical/runtime/environment_abstraction_git_probe_v1.py`, receipt `canonical/verification/ENVIRONMENT_ABSTRACTION_GIT_PROBE_20261124_V1.json`.
Train: three starts (`tagT1..3`), budget 300 walks each. Held-out: two unseen instances (`tagH1`, `tagH2`) with the same structure and unseen tags and names. Root-only observation, then plan, execute, check.

| control / goal | result |
|---|---|
| abstraction, learned from 3 starts | ACCEPTED, 0 nondeterministic edges, 0 goal-mixed states (seeds 0, 1, 2) |
| goal `loose` (main, clean, main content) | plan `add -A`, `checkout -f main` reaches the goal on **2 of 2**, and **destroys the user's edit on 2 of 2** |
| goal `strict` (loose + user edit survives) | plan `add -A`, `checkout main`, `stash` reaches the goal on **2 of 2** with the edit preserved on **2 of 2** |
| raw single-start vocabulary (identity abstraction) | accepted, but the held-out root is unknown: **0 of 2** transfer |
| every token masked | REFUSED (goal mixed). Fail-closed works. |

What this shows: a counterfactual reset is enough to learn which parts of a state are instance noise, and the learned abstraction transfers to a new instance **with zero new actions**. What it does not show: that the *strict* goal is the right one. "Edit survives" is satisfied by stashing the edit, which a user may or may not accept. That is a goal-specification choice, and I have stated it rather than decided it for the user.

### 3.3 Unseen structure: not solved

Probe `canonical/runtime/environment_abstraction_shift_probe_v1.py`, receipt `canonical/verification/ENVIRONMENT_ABSTRACTION_SHIFT_PROBE_20261124_V1.json`.
The new start is the same repository with the user's edit **already staged**. The root observation is outside the training data. Ten seeds.

| arm | goal reached after execution (of 10) |
|---|---|
| zero experience on the new start | root unknown, no plan (0 of 1 tested) |
| one action on the new start, then plan | **1 of 10** |
| one walk (up to 6 actions) on the new start, then plan | **4 of 10** |
| closed loop: one step, observe, record, replan | 1 of 10 (one action); 4 of 10 (one walk) — **no gain** |

Failure analysis, from the trails:
- **Stuck replanning.** Closed-loop runs end with `NO_PLAN` after `stash`/`stash pop`/`checkout -f main` cycles, because the new start has too few observed edges to route back to the goal.
- **Unsound extrapolation.** Several plans were predicted by the abstract model and then did not reach the goal when executed (`reset --hard` followed by `add -A`, `stash`, `stash pop`, ...). The abstraction is consistent with the transitions it observed, but the planner assumes it is sound on states it has not seen. The gate checks observed data only, so it cannot catch this.
- **Lossy predicate.** `edit_survives` is a single boolean. It is true when the edit is in the worktree *or* in any commit reachable from `--all`, and the two cases lead to different futures. The abstraction merges them, so the same abstract state is reached by routes that are not equivalent.

So the honest status is:
- **Verified (sandbox):** counterfactual-reset abstraction is learned, is consistent, and transfers zero-experience to new instances of the same structure. Three training seeds, two held-out instances each, one environment.
- **Failed (sandbox):** transfer to a new structure. One walk reaches the goal in 4 of 10 seeds. Closed-loop replanning does not improve it.
- **Unverified:** whether these numbers hold for any other environment. Only git was measured.

## 4. Mapping to the four leaps in the new brief

- **Semantic equivalence (leap 2).** The invariance abstraction is a first, observation-level form of it: it decides which parts of a state matter by intervention, not by a rule. It is not semantic yet. It works on tokens, not on what the tokens mean, and it fails on structure (§3.3).
- **Data-flow and causal lineage (leap 1).** `edit_survives` is the only causal lineage in this probe, and it is a hand-written predicate. Deriving lineage from the environment's own history (for example, which action moved a byte from the worktree into an object) is the next question, not something this round solved.
- **Goal-directed invention, CEGIS (leap 3).** Not built. The gate in §3.1 is the refusal half of a counterexample loop. The counterexamples that would refine the abstraction (the unseen-structure plans in §3.3) are now recorded as concrete cases. Turning them into refinements is the next build.
- **Executable mental models (leap 4).** The model in this probe is a transition table, not a simulator. The failure in §3.3 is what happens when that table is too sparse: replanning has nothing to route through. The fix is exploration that is aimed at the gaps, which is a different mechanism from the one measured here.

## 5. Real bottlenecks, ranked

1. **Soundness on unseen structure.** The abstraction is validated on observed transitions only. The planner extrapolates to unobserved ones. A sound mechanism has to refine when a plan fails, which is CEGIS on this table. The counterexamples are now in hand.
2. **Lossy goal-relevant features.** A boolean summarising a history is not enough. The abstraction needs the kind of history that matters (where the edit currently lives), derived from the environment, not hand-written.
3. **Exploration of gaps.** One walk leaves most of the new start unobserved. The learner should spend its budget where the planner has no edge, not uniformly at random.
4. **Goal specification.** The strict goal is one defensible reading of "must not change." The user has to be able to state the must-not-change set in the environment's own terms.

## 6. Plan (minimal) and rejected ideas

**Next build, in order:**
1. Counterexample-guided refinement of the abstraction: when a predicted plan fails on the real environment, record the first divergent transition, split the abstract state by the observed token that differs, re-check determinism and goal consistency, and only then replan. Pass criterion: the §3.3 arm reaches the goal in at least 8 of 10 seeds with zero unsound plans reported as success.
2. Gap-directed exploration: choose actions from the abstract states that lack successors, not uniformly. Pass criterion: same seeds, same budget, strictly better than uniform random.
3. Derive `edit_survives` from the environment's own history rather than a hand-written predicate. Pass criterion: the same predicate computed from raw history on training and held-out starts, with zero hand-written edit-location logic.

**Rejected:**
- *Closed-loop replanning alone.* Measured: no gain (§3.3). It needs refinement to have anything to route through.
- *Storing raw episodes.* Still rejected (no transfer, last round).
- *Predicting successors with a learned model.* Not needed; execution gives them exactly, and it avoids a model dependency.
- *Asking an LLM to suggest the abstraction.* Forbidden at runtime, and it would not be our capability anyway.
- *Declaring success on the strict goal because the edit survives.* That goal is one reading of the user's intent. It is recorded as a choice, not as the answer.

## 7. Done criteria (§6)

Not met. The system still does not solve unseen structures, and it has run on one environment. This round adds a sound, measured mechanism for learning which parts of a state are noise, and it names the next failure precisely.

## 8. Notes

- Receipts: `canonical/verification/ENVIRONMENT_ABSTRACTION_GIT_PROBE_20261124_V1.json` and `canonical/verification/ENVIRONMENT_ABSTRACTION_SHIFT_PROBE_20261124_V1.json`. Both record `model_calls: 0` and `stored_parameters: 0`. Both are `NONE__SANDBOX_MEASUREMENT`.
- Scratch experiments (debug and transfer variants) live outside the repository in `/home/user/scratch_elexp` and are not part of the change.
- The earlier demo `instant_learning_demo.py` still fails, as reported last round. Nothing here changes that.
