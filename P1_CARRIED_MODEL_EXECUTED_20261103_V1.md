# P1 executed: carrying a model now saves work

**2026-11-03.** `OPTIMAL_PLAN_20261103_V1.md` §2 P1, done. This records the measurement, the
three defects found while doing it (one of them in my own first attempt), and the test that had
to be corrected rather than kept.

Authority: **NONE**. Producer-run measurement in five constructed environments. Not independent
verification. No capability, family, terminal or sentience credit. `truth.achieved` stays
`false`. Spend $0, model dependency 0.

---

## 1. Result

`transfer_learning_new_instance_probe_20261103.py`, 5 families × 3 seeds, identical target
instance in both arms, source instance differs in a varied parameter. Disposable state per arm.

| | before P1 | after P1 |
|---|---|---|
| cases | 15 | 15 |
| COLD solved | 15 | **15** (unchanged — the control may not regress) |
| WARM solved | 15 | 15 |
| **genuine saving** (fewer trials **and** no more act calls) | **1 / 15** | **8 / 15** |
| reached the goal in **one trial** | 1 / 15 | **8 / 15** |
| median trial speedup | 1.00× | **8×** (mean 6.33×) |
| mean act-call speedup | 0.977× | **2.26×** |
| WARM **worse on trials** than COLD | 0 / 15 | **0 / 15** |
| WARM spent more act calls | 14 / 15 | 7 / 15 (worst 1.40×) |

Independently corroborated on the second instrument, `canonical/tools/changed_state_transfer_
benchmark_v1.py` (10 target cases, different constructions): **6 of 10 now finish in one trial**
on `CARRIED_MODEL_PLAN_EXECUTED_GOAL_OBSERVED`, and cold is still 10/10. Before P1 that number
was 0 of 10 with `direct_plan_replays: 1`.

And on the older three-dial sequence in `test_transfer_learning_v1.py`, measured both ways:

```
before P1: 80 trials with transfer, 80 without   -> 0% saving
after  P1: 73 trials with transfer, 80 without   -> 8.8% saving, second encounter = 1 trial
```

The tree's own test docstring had claimed "72 with transfer against 112 without". On this tree
that was false in both directions, before my change as well as after it.

---

## 2. What the change actually is

Three edits in `canonical/runtime/transfer_learning_v1.py`:

1. **`walk_carried_model`** — plan through the carried model *before* paying for a search, and
   check the goal against **real observations**. New status
   `PASS__ENVIRONMENT_SOLVED_BY_CARRIED_MODEL`, new authority
   `CARRIED_MODEL_PLAN_EXECUTED_GOAL_OBSERVED`.
2. **Three authorities instead of one.** `RECALLED_PLAN_…` (exact replay),
   `CARRIED_MODEL_…` (planned through the carried model), `MODEL_LEARNED_…` (searched). All
   three used to print `PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN`, which is how a 1.00×
   speedup was readable as 15/15 transfer.
3. **A miss costs act calls, never trials.** A failed walk leaves the trial budget untouched.

---

## 3. Three defects found while doing it

**Defect 1 — my first version passed a state KEY to `is_goal`.** `environment_learning_v1.
shortest_plan` takes a predicate over keys, and its callers build the goal-key set by testing
`is_goal` against *snapshots they observed*. A carried model has no snapshots — only
`key -> {action: key}` — so my first version asked every goal predicate about a string. Result:
**1/15 → 2/15**, not the 7/15 the headroom measurement had promised. A silent no-op that looks
like a working feature. Fixed by executing the walk in the real environment and testing real
states. The lesson generalises: *a planner that reasons over recorded keys is only as good as
the snapshots you kept.*

**Defect 2 — charging the failed walk as a trial made things worse.** To be "honest" I set
`spent = 1` after a failed walk. That re-quantised the chunk loop (chunks of 8 → 9 trials to
cover the remainder) and made WARM lose on **both** counters in 5 of 15 cases. The walk is
exploration, not a trial: it is paid for in act calls, which are reported separately in
`carried_walk`. Removing the charge gave the exact guarantee now tested:
`warm_worse_on_trials == 0`.

**Defect 3 — dead pruning that claimed an effect.** The first `walk_carried_model` built the
whole BFS tree, walked it, and *then* tried to mark contradicted edges as refuted. The pruning
ran after the tree was finished, so it removed nothing — while its comment claimed it had cut
overhead from 1.80× to 1.49×. That number was produced by the *bound*, not the pruning. Caught
by reading the function back before committing. Rewritten to validate each edge during the walk,
so a state the model invented is never expanded from.

---

## 4. A test was corrected, not kept

`test_the_carried_model_grows_with_each_encounter` asserted that `prior_transitions` grows on
every encounter. It now fails — and it should:

```
old code: model grew 158 -> 207 on the third encounter, and spent the same 80 trials as carrying nothing
new code: model STOPS at 158, because the third encounter is solved by the carried model in 1 trial
```

Growth was a proxy for "learning pays off". The proxy got weaker exactly as the thing it proxies
got stronger. So the assertion is replaced by the invariant it was standing in for —
`test_carrying_a_model_saves_trials` (measured both ways, with the old and new numbers recorded
in the docstring) — and the stopping behaviour is pinned deliberately in
`test_the_carried_model_stops_growing_when_it_is_already_enough`, so nobody "fixes" it back by
forcing the model to keep absorbing transitions a search did not need to collect.

One other test needed a widening, not a weakening:
`test_changed_state_transfer_benchmark_v1` enumerated two authorities; there are three now, and
the cold arm is still asserted to be `MODEL_LEARNED_…` only.

---

## 5. What is still wrong, and is not fixed here

- **7 of 15 cases still spend more act calls than carrying nothing** (worst 1.40×). That is the
  residual: the walk explores a carried model that is correct about the source instance and
  blind to the new target, then gives up. Bounded at 96 act calls and reported as `truncated`,
  not hidden. A sharper fix is to make the bound adaptive — scale it with the *observed success
  rate* of the carried model rather than a constant — but that needs more than one measurement
  to justify, and a constant that is reported beats a heuristic that is not.
- **3 pre-existing failures in `test_computer_env_v1`** and **10 in `test_composer_route_v1`**
  are red **with and without** this change (13 red without it, 13 red with it, the same tests).
  They are `PASS__COMPOSER_ROUTE_FOUND` vs `PASS__PERFORMED_ON_REAL_FILE` and gzip/channel
  expectations — unrelated to `drive`, and now on the P2 list rather than lost.
- **This is still five constructed families.** The whole probe rests on a compact hashable
  `state()`. Nothing here says anything about pixels, a real desktop, or a 10-million-line repo.
- **The front door still does not route to the learner.** P1 makes the learner *worth* routing
  to. It does not connect it. That is P3, and it still needs an independent verifier.

---

## 6. Why this was the right first move

The capability was already there — the stored lesson could plan 7 of 15 targets before any code
changed. What was missing was a call. That is the cheapest kind of progress available in this
tree, and it was invisible because three different outcomes printed the same status string.

The generalisable lesson, which is worth more than the 8/15: **when a system reports one status
for several behaviours, you cannot tell a real gain from a label.** Splitting the authority
labels is what made the 1.00× speedup visible in the first place.
