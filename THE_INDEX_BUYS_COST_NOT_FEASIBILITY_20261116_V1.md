# The index buys cost, not feasibility — and the tree already names the thing that buys both

**Date:** 2026-11-16 · **Branch:** `arena/d59e2de1-brain` · **Authority: NONE — sandbox measurement, not independent verification.**
**Receipt:** `canonical/verification/THE_INDEX_BUYS_COST_NOT_FEASIBILITY_20261116_V1.json` · **Modules added: 0.**

---

## 0. The short answer

You asked for the single bottleneck, solved ultimately and not incrementally. The tree answered last round: **the index** — the filing key that decides which lesson applies where — with a sweep showing no granularity of its features is injective on the policy's distinction.

That sweep is **right**, and this round reproduces it exactly. But I then asked the question the sweep did not: **what is the index worth, once the search producing its evidence is not starved?** The answer is not a refinement of the index. It is a demotion of it:

> **A perfect index saves 17.4% of the action budget and 0.00% of feasibility. Finding the plan rather than choosing the strategy costs 99.58%.**

The same 52 instances, the same action meter, the same search: **39,879** act_calls spent, of which **167** are the actual plan. The ratio is not a small correction to the index thesis. It is a factor of **5.7×** in favour of the thing the tree already names as its goal and already admits it does not contain.

And on the eight instances no policy solves at all — the ones that make "solve everything, permanently" false — **not one** is a failure of choice. Six have their goal state **provably outside the reachable set**, proven by exhausting a state space of 3 to 27 states.

**The correction I have to make to my own previous answer:** the index is where the *features* fail; it is not where the *capability* is lost. Those were conflated, and the measurement separates them.

---

## 1. The mistake, exactly

Last round's bottleneck document measured this: coarse key → 8 keys / 2 collisions; exact key → 16 keys / 20 kinds / 2 collisions; one key per kind → 20 keys, 0 collisions. Conclusion: *"the thing that decides where knowledge applies does not contain the distinction the knowledge depends on."*

That conclusion is **true and it is not actionable at the top of the order**, because it silently assumes the distinction is *feasibility-bearing*. Test that assumption:

| node_budget | solved (of 60) | train | test |
|---:|---:|---:|---:|
| 40 | 45 | 25/30 | 20/30 |
| 160 | 49 | 26/30 | 23/30 |
| 320 | 50 | 27/30 | 23/30 |
| 1280 | **52** | 27/30 | 25/30 |

Now the shape of *who* solves what, at adequate budget, over the 52 satisfiable instances:

| solved by | instances @ budget 40 | instances @ budget 1280 |
|---|---:|---:|
| 5 of 5 policies | 31 | **42** |
| 4 of 5 policies | 9 | **10** |
| exactly 1 policy | **4** | **0** |
| 0 of 5 policies | 7 | 0 |

**The "exactly one policy works" rows — the entire motivation for a policy index — are an artifact of starved search.** At 40 nodes there are 4 of them. At 1280 nodes there are **zero**. Every satisfiable instance is solved by at least four of the five strategies.

So the index is choosing between strategies that all work.

---

## 2. What the index is therefore worth, priced

Same 52 instances, `node_budget=1280`, currency = act_calls:

| | act_calls | oracle saves |
|---|---:|---:|
| Oracle — a **perfect** index, free to consult | 39,879 | — |
| Best single fixed policy (`repeat_last`), no index at all | 48,274 | **17.4%** |
| Tree-best policy applied held-out (`bfs_lex`) | 50,752 | 21.4% |

On the held-out split alone: perfect index 32,083 vs best fixed 36,562 — **12.3%**.

That is the ceiling on the entire index programme. Not the gap to a good index — the gap to a **perfect, free, omniscient** one. Feasibility change: **0.00 points.**

**The instance-sensitivity finding is the one part that survives**, and I confirmed it is not a budget artifact: **13 of 18** kinds with ≥2 solvable instances have a different *cheapest* policy on a different instance (`binary_odometer`: 15,860 act_calls on instance 0, **38** on instance 1). So an index that predicts the cheapest strategy is real. It is a **cost** instrument. It cannot make the impossible possible, and 8 instances are impossible.

---

## 3. The eight that nothing solves — and what they actually are

These are the rows that falsify "solve all computer use, perfectly and permanently". I did not take "no policy solves it" as the answer, because that is a statement about five strategies, not about the problem. I enumerated the reachable state space with **no node budget**:

| kind | inst | reachable states | max depth | goal | proof |
|---|---:|---:|---:|---|---|
| `ring_rotate` | 0 | **3** | 1 | absent | space exhausted |
| `ring_rotate` | 1 | **3** | 1 | absent | space exhausted |
| `ring_rotate` | 2 | **3** | 1 | absent | space exhausted |
| `queue_rotate` | 2 | 13 | 3 | absent | space exhausted |
| `two_jug_pour` | 0 | 16 | 7 | absent | space exhausted |
| `dial_lock` | 2 | 27 | 6 | absent | space exhausted |
| `stack_pushout` | 0 | 32 | ≤14 | absent | within the search's own depth cap |
| `stack_pushout` | 1 | 110 | ≤14 | absent | within the search's own depth cap |

`ring_rotate` is the sharpest case in the tree: **three reachable states, found in six act calls, and the goal is not among them.** All three instances. No search strategy, no index, and no amount of learning can reach a state that does not exist.

**I also have to disclose where this proof stops.** `stack_pushout`'s reachable space is **unbounded** — a probe run reached discovery depth 6,251 before I stopped it at a 50,000-state cap. For those two the honest claim is *"no goal within the depth the searcher is allowed"*, not *"unsatisfiable"*. Six are exhausted exactly; two are bounded by depth.

For the six, this is not a learning problem, a vocabulary problem, or an index problem. It is the environment asking for something it cannot do — which is exactly what "perfectly, permanently, in any environment" would have to survive.

---

## 4. Where the budget actually goes

Same runs, same 52 instances, `node_budget=1280`:

| | total | mean | max |
|---|---:|---:|---:|
| act_calls spent by the cheapest winning search | **39,879** | 767 | 15,860 |
| plan length — what an ideal model would need to *execute* | **167** | **3.2** | 14 |

**Search-to-execution ratio: 129× mean, 10× median.** The single worst instance, `binary_odometer` i0, spends **15,860 act_calls to find a 7-step plan — 2,266×**.

A transition model that planned perfectly would remove **99.58%** of those act_calls. An index removes 17.4%.

This is not a claim that a model *would* be perfect. It is the price list, and it says where the next unit of effort is worth 5.7× more than the one the previous document recommended.

---

## 5. Why this is not a return to "learn faster"

It is the opposite. A transition model is not storage and not learning rate. It answers a different question: *given this state and this action, what happens?* — which is what lets a plan be found **without spending the action**.

`canonical/runtime/model_v1.py` is the socket for exactly this, and its own docstring is the clearest statement of the gap in the tree:

> *"And with all of it in place, solve() does nothing at all until someone supplies a model... So this file does not contain a model. It contains the shape one must have, and the means to plug one in."*

I grepped for a transition learner before proposing one, per the law. There is none: no `predict_effect`, no `rollout`, no `(state, action) → next state` anywhere in `canonical/runtime/`. The object the tree names as its goal is the object the tree does not have, and it is worth 99.58% of the budget rather than 17.4%.

**This does not retract `THE_GOAL_IS_A_COUNTERFACTUAL_WORLD_MODEL_20261116_V1.md`. It prices it.** That document said the missing object is a counterfactual world model; it did not say what it was worth. Now there is a number, and the round before this one was optimising the smaller term because the bigger one had not been priced.

---

## 6. The control that killed my own result

I computed an effect probe (per-action state sequences to depth 3) and it predicted the winning policy **8/8** on the eight discriminating held-out rows, against the tree key's **3/8**. I nearly reported it. Then I ran the control:

| arm | discriminating held-out rows |
|---|---:|
| always `bfs_lex` | **6/8** |
| always `repeat_last` | 6/8 |
| always `never_last` | 6/8 |
| computed from a depth-3 probe (costs 72–120 act calls) | 8/8 |

**A constant scores 6/8.** The computation buys two rows out of eight. And on *all* 30 held-out rows, the best constant policy solves 18/30 while an oracle over all five solves **20/30** — the whole strategy question is worth 2/30.

Related, and it closes the tree's injectivity question directly: a depth-3 effect signature **is** injective — 20/20 kinds, zero collisions, where the tree's exact key gave 16/20:

| probe depth | unique keys of 20 kinds |
|---:|---:|
| 1 | 19 |
| 2 | 19 |
| **3** | **20** |
| 4 | 20 |
| 5 | 20 |

And it is worth nothing: that key answers **1 of 30** held-out rows. Meanwhile the *coarse* key is not merely more transferable, it is **more accurate**: 8/30 correct vs 4/30 for the exact key. Injectivity is purchasable or transferable, not both — and here, once search is adequate, there is nothing left to choose between anyway.

---

## 7. Your three premises, and what they were always missing

You did not restate them this turn, but the receipt stands and the new numbers sharpen each:

1. **Identifiability — a single trace does not identify a rule.** Unchanged: one success leaves 13.05/32 hypotheses, 0/200 exact. Closing it needs *intervention*, and the tree already has the instruments (`contrast_selection_v1` ranks the next experience; `precondition_discovery_v1` recovers an unnameable precondition). What this round adds: even a **perfectly identified** strategy choice is worth 17.4%.

2. **Vocabulary insufficiency — the observable is missing, not the observation.** Unchanged and proven (`INSUFFICIENCY_CERTIFICATE_20261113_V1.json`: 820 equal-fact cases, 2,517 evidence sets, 0 counterexamples). This round's `ring_rotate` result is the same lesson in its hardest form: **3 states, goal absent.** No vocabulary repairs a world where the goal does not exist.

3. **Synthesis–verification asymmetry — a verifier is not a planner.** This round is a measurement *of* that asymmetry: we verify cheaply and we explore at 129× the cost of executing. It remains saturated, not the frontier — and it is the third of three costs, not a wall.

The single sentence all three reduce to: **the tree is very good at judging, adequate at choosing, and has no model of consequence.** Judging costs little. Choosing is worth 17.4%. Consequence is worth 99.58% and is absent.

---

## 8. What I am not claiming

- **Authority NONE.** Sandbox measurement on the tree's own synthetic benchmark. Not independent verification.
- The 20 kinds are the tree's **own hand-written generators**. "No policy is the only solver" is a statement about these 20 kinds and these 5 strategies — not about computer use in general.
- **99.58% is an upper bound**, obtained by substituting the true plan length. No transition model was built or measured this round. It says where the price is, not that we can pay it.
- `stack_pushout` 0 and 1 are **not** proven unsatisfiable (unbounded state space).
- The depth-3 key's train table was built on instance 0; the held-out scoring used matched instance indices.
- **No sentience.** Nothing here measures it; no result is evidence for it. These are mechanisms with falsifiers.

---

## 9. What I did not build, and why

**Zero modules.** The law is "the best part is no part", and it applied *against* the recommended action. The decisive fact this round is a disagreement between two of the tree's own documents, and it resolves against the more recent one:

- `THE_BOTTLENECK_IS_THE_INDEX_NOT_THE_LEARNING_20261116_V1.md` — bottleneck is the index, next part is a new observable.
- `THE_GOAL_IS_A_COUNTERFACTUAL_WORLD_MODEL_20261116_V1.md` — the goal is a counterfactual world model; `model_v1.py` says the tree has none.

Both are right about *features*. Only one is right about *priority*. Repairing the index first would have optimised a 17.4% term while the 99.58% term sat named, unbuilt, and unpriced. That is the ordering error this round exists to prevent — and it is the same ordering error as building a better store for knowledge that the index cannot route.

**The one thing that is now unambiguously the front of the queue** is a transition function learned from the tree's own acting — the socket in `model_v1.py`, filled by measurement rather than by a model we do not have, with `ready_to_train=False` left standing and weights still last.

**Single bottleneck, stated exactly:** not the index, not the verifier, not the vocabulary, not more experience. **The consequence model.** The thing that turns "try it and see" into "know what will happen" — because that is what converts 39,879 act_calls into 167, and 100% of the unsolvable rows are rows where no choice helps.

---

## 10. Reproduce

Instruments, all pre-existing: `canonical/tools/cross_kind_learning_to_learn_benchmark_v1.py` (`_solve_with`, `_heldout_kinds`, `NODE_BUDGET=40`), `canonical/tools/cross_kind_compounding_benchmark_v1.py` (`_kinds`), `canonical/runtime/learn_to_learn_v1.py` (`POLICIES`, `features`, `feature_key`, `search`).

The eleven measurement scripts are sub-60-line drivers that import those modules directly and are not persisted (`/tmp/inj/*.py`). Every figure above is a count produced by running them; nothing is quoted from a prior document except the results explicitly attributed to one.
