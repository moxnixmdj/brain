# The random baseline wins on small git: the gap heuristic is not what helped, and the environment is too small to test it

*2026-11-24 · branch `arena/839ba1ac-brain` · follows `THE_GAP_IS_THE_EXPERIMENT_20261124_V1.md`*

Authority: sandbox measurement by the producer. Not independent verification, not a benchmark, not a terminal result. Real `git`, one environment, no model calls, no stored parameters.

---

## 1. Requirements I am bound by (restated)

- Zero model calls and zero stored parameters in anything that ships. Knowledge lives outside the weights and is written from experience.
- Research before building. Test on unseen, hard cases. Report verified, unverified, failed separately.
- Remove before adding. Every piece must justify itself.
- No questions to the user. Resolve ambiguity by the most defensible choice and state it.
- §6 is not met. This round does not change that.

**§2, still resolved.** The store holds abstract transitions, reliability marks, and unsafe-action marks. This round tested whether the *choice* of action, not only the store, earns its keep.

## 2. What was checked (project, then reuse)

- `canonical/runtime/explore_v1.py` (a one-step bandit over commands) was read in the previous round and rejected. Not reused.
- The explorer module `canonical/runtime/environment_gap_explorer_v1.py` gained one switch: `policy="uniform"` (a random allowed action each step, ignoring the model and the tried set) next to the existing `policy="gap"`. Checkpoint enforcement applies to both. The change is 12 lines.

## 3. What was measured

Same probe as before, `canonical/runtime/environment_gap_explorer_probe_v1.py`, extended with one arm. Same training (three counterfactual starts), same two unseen structures, same ten seeds, same budget of 40 real actions, same must-not-change predicate (the user's edit survives), same checkpoint enforcement. Receipt: `canonical/verification/ENVIRONMENT_GAP_EXPLORER_PROBE_20261124_V2.json`.

| structure | arm | goal reached (of 10) | median actions | restores | must-not-change violated at end |
|---|---|---|---|---|---|
| staged | learned model + gap + checkpoint | 10 | **14** | 9 | 0 |
| staged | no model + gap + checkpoint | 10 | 20 | 18 | 0 |
| staged | model + gap, **no** checkpoint | 4 | 23 | 0 | **6** |
| staged | **uniform random** + checkpoint | **9** | **11** | 14 | 0 |
| committed | learned model + gap + checkpoint | 10 | **1** | 0 | 0 |
| committed | no model + gap + checkpoint | 10 | 5 | 0 | 0 |
| committed | model + gap, no checkpoint | 10 | 1 | 0 | 0 |
| committed | **uniform random** + checkpoint | 10 | 6 | 0 | 0 |

The median action count in the earlier round's staged row was 13. Recomputed on the same run data, it is 14. That round's text said "about 13"; this is the corrected figure.

## 4. What this shows

**Verified (sandbox, this environment):**
- **The gap heuristic is not the source of the advantage.** Without a model, gap choice (median 20, staged) is worse than uniform random (median 11, staged). On committed, gap without model (5) is worse than random (6) only by a little, and the difference is within the noise of ten seeds.
- **The learned transition model is the source of the advantage on the committed structure**: 1 action against 5 without a model, and 1 against 6 for random.
- **On the staged structure, the model does not beat random** on median actions (14 vs 11). It does beat random on restores and on the gap-only control. Random reached the goal in 9 of 10 runs, the model-guided arm in 10 of 10. These differences are small on ten seeds and are not claimed as significant.
- **The checkpoint is the safety mechanism.** Without it, 6 of 10 staged runs ended with the user's edit lost, whatever the policy. With it, none did, for every policy.

**Why random does so well here (the environment is the problem):**
- The environment has about 20 abstract states and 13 actions. Uniform random covers that space quickly. A test that cannot separate random from a planner is not a test of the planner.
- The must-not-change predicate removes some random actions, but only the destructive ones, which the checkpoint restores anyway.

**Unverified:** that gap choice or a learned model helps on any environment large enough that random search fails. That is the real test, and this environment cannot run it.

**Failed:**
- My claim last round that the gap choice is cheaper than uniform action search is **false** on these structures. Corrected in `THE_GAP_IS_THE_EXPERIMENT_20261124_V1.md`.

## 5. Verdict on the question in the brief: goal-directed or learn everything?

On this evidence, neither framing is decided, and the test that would decide it does not exist yet. A learned model helps when the goal's path is long and the start is unfamiliar (committed: 1 action against 5 or 6). A planner earns nothing over random on a tiny space. Learning everything first is equivalent to random exploration with memory, so the question is the same question at a larger scale. The next experiment has to be on a state space large enough that random search fails.

## 6. The real bottleneck (updated)

1. **The test environment is too small to discriminate.** Every planning claim so far is untested against a baseline that could lose. Fixing this is cheaper than any new mechanism.
2. **Goal specification** (the must-not-change set is still hand-written).
3. **Checkpoint scope** (a directory copy is not a general reversible-action model).
4. **Refinement when the abstraction breaks** (not yet triggered by any structure tried).

## 7. Plan (minimal) and rejected ideas

**Next build:** a git environment large enough that uniform random fails within the budget. Candidate: 30–60 tracked files spread over several directories, a multi-branch history with a conflicting merge, several stashes, and untracked artifacts, with a goal that needs several coordinated steps (for example: resolve the conflict in one file, keep the user's edit in another, leave the tree clean on `main`).
- Pass: the model-guided arm reaches the goal in at least 8 of 10 seeds with a median action count **strictly below** uniform random's median, and uniform random is reported with its own success rate. If random also succeeds at the same rate, the pass fails and the environment is still too small.
- Fail: if the model-guided arm is not better than random on the larger environment, the learned abstraction is not what makes a planner valuable, and the next step is to question the abstraction itself, not to add mechanisms.

**Rejected:**
- *Tuning the gap heuristic on the current environment.* The current environment cannot show a difference between heuristics, so tuning would be fitting noise.
- *Calling the random baseline a strawman.* It is the honest baseline for any planner that claims efficiency. It had to be run; now it has been.
- *Adding a learned predictor to make small environments look better.* Rejected: it would add parameters and a model dependency to fix a test problem.

## 8. Done criteria (§6)

Not met. The system has not been measured on any environment where a baseline can lose, and it has run on one environment type (git) with two unseen structures. No claim here reaches the done criteria.

## 9. Notes

- Receipts: `canonical/verification/ENVIRONMENT_GAP_EXPLORER_PROBE_20261124_V1.json` (first run, no uniform arm) and `..._V2.json` (this run, with uniform). Both record `model_calls: 0` and `stored_parameters: 0`.
- Scratch experiments are in `/home/user/scratch_elexp`, outside the repository.
- `instant_learning_demo.py` still fails, as reported earlier.
