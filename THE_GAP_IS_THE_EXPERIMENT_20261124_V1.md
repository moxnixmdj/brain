# The gap is the experiment: checkpointed, gap-directed exploration reaches the goal on two unseen structures, and the must-not-change clause is enforced by checkpoint, not by hope

*2026-11-24 · branch `arena/839ba1ac-brain` · follows `THE_ABSTRACTION_IS_LEARNED_BUT_NOT_YET_SOUND_20261124_V1.md`*

Authority: sandbox measurement by the producer. Not an independent verification, not a benchmark, not a terminal result. Real `git`, one environment, no model calls, no stored parameters.

---

## 1. Requirements I am bound by (restated)

- Zero model calls and zero stored parameters in anything that ships. Knowledge is an external, inspectable store, written from experience.
- Research before building. Test on unseen, hard cases. Report verified, unverified, failed separately.
- Remove before adding. Every piece must justify itself.
- No questions to the user. Resolve ambiguity by the most defensible choice and state it.
- §6 is not met. This round does not change that.

**§2, still resolved.** The store is a table over abstract states, with reliability marks and unsafe-action marks. It stores edges and marks, not raw trajectories (§5 answers what gets saved).

## 2. Research and what exists (searched first)

- The last round's plan named this step: gap-directed exploration with refinement. The project already has `canonical/runtime/explore_v1.py`, which I read before building. It is a one-step bandit over commands at the root, scoring by filesystem tokens. It has no transition model and no multi-step plans, so it cannot provide this mechanism. I did not reuse it.
- The new module `canonical/runtime/environment_gap_explorer_v1.py` is small: an abstract transition table with reliability marks, a planner over reliable edges, gap-directed choice of untried actions, and checkpointed enforcement of a must-not-change predicate.
- Literature (not re-searched this round; the references from the previous rounds still apply): CEGAR (Clarke et al., 2000) is the family of the refinement idea I deferred. Checkpoint-and-restore before risky actions is the same discipline as the probe-and-restore contract already in `environment_learning_v1.probe_closeness`.

## 3. What was built and measured

Probe `canonical/runtime/environment_gap_explorer_probe_v1.py`, receipt `canonical/verification/ENVIRONMENT_GAP_EXPLORER_PROBE_20261124_V1.json`.

Training: the three counterfactual starts from the previous round (tags T1–T3), with the abstraction learned by `environment_abstraction_v1`. Two **unseen structures**, neither in training:
- `staged`: the user's edit is in the index.
- `committed`: the user's edit is a commit on `feature`.

Budget: 40 real actions per run, 10 seeds per arm. A checkpoint is a copy of the repository and is **not** charged to the budget. A restore is counted.

Must-not-change predicate (`keep`): the user's edit still exists in the worktree, the index, or a commit reachable from `--all`. The goal: on `main`, clean tree, `a.txt` at main content, and `keep` true.

| structure | arm | goal reached (of 10) | restores | must-not-change violated at end |
|---|---|---|---|---|
| staged | model + checkpoint | **10** | 9 | 0 |
| staged | no model + checkpoint | **10** | 18 | 0 |
| staged | model, no checkpoint | 4 | 0 | **6** |
| committed | model + checkpoint | **10** | 0 | 0 |
| committed | no model + checkpoint | **10** | 0 | 0 |
| committed | model, no checkpoint | **10** | 0 | 0 |

Per-run actions: staged with model, `[20, 11, 6, 6, 14, 16, 3, 11, 18, 15]` (median about 13); staged without model, median about 18; committed with model, one action in every run; committed without model, median about 4.

## 4. What this shows, and what it does not

**Verified (sandbox):**
- The explorer reaches the goal on both unseen structures in 10 of 10 runs when the checkpoint is enforced. The success check is the real goal on the real final state. No plan was counted as success on prediction alone. The number of mismatches between predicted and actual successors was 0 in the enforced arms.
- The checkpoint is what enforces the must-not-change clause. Without it, 6 of 10 staged runs ended with the user's edit destroyed, including runs that reached `main`. With it, 0 of 10 did. The checkpoint caught 9 destructive attempts in the staged arm.
- The learned abstraction gives a real but modest transfer benefit on the staged structure (median about 13 actions with the model, about 18 without) and a larger one on the committed structure (one action with the model, median about 4 without).

**Unverified:**
- Anything beyond git. Anything beyond these two structures. Anything beyond ten seeds with one fixed training set.
- The restore count is not charged to the budget. A real machine may not allow cheap checkpoints of its whole state; a directory copy is not a general computer snapshot.
- Whether the gap-directed choice is better than uniform random exploration. The plan from the previous round named that comparison and it was **not measured**. The no-model arm is also gap-directed, so it does not isolate the choice.

**Failed or limited:**
- The explorer depends on a hand-written must-not-change predicate. The mechanism enforces the predicate; it does not learn what must not change. That is the goal-specification problem from earlier rounds, and it remains open.
- "Learn everything first" is not measured here. The claim that exploration can cover the whole state space of a larger environment is untested.

## 5. Answers to the questions in the brief, from this evidence

- **What should be saved?** Edges of the abstract table, reliability marks for conflicting edges, and unsafe-action marks. Raw trajectories are not saved. The table is what transferred and what was used.
- **Goal-directed or learn everything?** In this measurement, goal-directed exploration with gap choice reached the goal in 3 to 24 actions. A full exploration of the environment was not timed, so the comparison is not settled. What is settled: a plan with no route yet is replaced by an untried action from the current abstract state, and that is cheaper than uniform action search on these structures.
- **Must the agent be safe?** Yes, and the evidence is concrete: without the checkpoint, the goal was reached while the user's edit was lost in 6 of 10 staged runs. Safety is not a property of the goal alone.

## 6. Bottlenecks, ranked (updated)

1. **Goal specification.** The must-not-change set is handed in. Without learning or stating it in the environment's terms, the agent cannot know what to protect in a new environment.
2. **Checkpoint cost and scope.** Whole-directory checkpoints work here. Real computers need a notion of reversible action that is not the whole machine.
3. **Coverage on larger environments.** Untested.
4. **Refinement when the abstraction is wrong.** Not triggered in these runs (0 mismatches), so the CEGIS refinement from the previous round is still unbuilt. It is needed when a structure breaks the abstraction, which these two structures did not.

## 7. Plan (minimal) and rejected ideas

**Next, in order:**
1. Measure gap-directed vs uniform random exploration on the same two structures, same seeds, same budget. Pass: gap-directed strictly better in median actions, with no safety regression.
2. Find a structure that breaks the abstraction (for example, a conflicted merge, where tokens carry meaning the mask hides). Then build the refinement step. Pass: the explorer reaches the goal on that structure, with 0 unsafe successes.
3. Derive the must-not-change predicate from the user's stated goal in the environment's own terms, rather than from a hand-written `edit_survives`. Pass: the same results with no edit-specific code.

**Rejected:**
- *Reusing `explore_v1.py`.* It is a single-step bandit with no transition model and no plans (§2).
- *Closed-loop replanning without exploration of gaps.* Measured earlier with no gain.
- *Learning everything before acting.* Not measured, and the cost of a full sweep is unknown. Not chosen until measured.
- *Relying on the restore count being free.* It is reported, not hidden. A real environment may charge for it.
- *Declaring success on the goal alone.* The goal is a reading; the must-not-change check is what made the success meaningful here.

## 8. Done criteria (§6)

Not met. One environment (git), two unseen structures, and no independent verification. The system does not yet solve arbitrary computer use, and no claim here reaches the done criteria.

## 9. Notes

- Receipts: `canonical/verification/ENVIRONMENT_GAP_EXPLORER_PROBE_20261124_V1.json`. Both `model_calls: 0` and `stored_parameters: 0` are recorded.
- The earlier demo `instant_learning_demo.py` still fails, as reported earlier. Nothing here changes that.
- Scratch experiments are in `/home/user/scratch_elexp`, outside the repository.
