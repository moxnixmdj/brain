# Plan v3 execution status: the two highest-leverage ideas are falsified

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Execution of `THE_SMARTEST_PLAN_V3_20261125_V1.md`. **Outcome: Ideas 1 and 4 are falsified.**
The plan's core thesis — that JitRL-style advantage estimation and weight-space continual learning
are the path ahead — does not survive measurement.

---

## Falsifier #4 (Idea 4, weight-space fuel gate): FIRES — Idea 4 is moot

Ran `canonical/tools/weight_space_fuel_v1.py`:

```
source                    records   units  verified  verdict
execution_receipts            305       0         0  NO_SIGNAL
trajectory_store               24      66         0  NO_SIGNAL
taught_action_corpora           0       0         0  NO_SIGNAL
controller_checkpoints        451     192        64  THIN_BUT_REAL

total units a shaper could condition on   258
of those, independently verified          64
minimum worth a held-out split            5000
ready to train                            False
```

**64 verified units vs a 5000 minimum — we are 78× short of fuel for weight-space learning.**
`execution_receipts` hold no situation/choice (0 units). `trajectory_store` is all hand-seeded
`success` with the same four steps (cannot express failure). Only `controller_checkpoints` has a
natural pass/fail split, and it is thin. **Weight-space learning is not viable.** The finding is
that JitRL (Idea 1) was the only viable continual-learning path — and it is also falsified (below).

## Falsifier #1 (Idea 1, JitRL advantage estimation): FIRES — Idea 1 falsified as implemented

Implemented JitRL-style advantage estimation in `transfer_learning_v1.recall`: when
`use_advantage=True`, each candidate's evidence is compared to the baseline (mean evidence across
retrieved candidates), and the score is adjusted via the closed-form
`sim * (evidence + beta * (evidence - baseline))` — the plan-scoring analogue of JitRL's
`z' = z + beta * A_hat`. Threaded `use_advantage`/`beta` through `drive`. Ran the 15-case probe
with advantage on vs the baseline:

| | baseline (plain recall) | JitRL (advantage on) |
|---|---|---|
| genuine saving | **8/15** | **8/15** |
| mean trial speedup | **6.333×** | **6.333×** |
| mean act speedup | 2.259× | 2.259× |
| worse on trials | 0 | 0 |

**Identical.** The advantage adjustment does not change which plans are recalled or their order in
any way that helps. **Why:** in this transfer setting, `evidence` (Laplace-smoothed success rate)
*is* the return. So `advantage = evidence - baseline` is a rescaling of evidence, not new
information. It cannot improve ranking because it carries no signal beyond what evidence already
has. The 7 non-saving cases are not "wrong plan ranked first" — they are "recalled plan works but
does not save work" (`warm_solved: 15`, `warm_genuine_saving: 8`). The bottleneck is **plan
effectiveness (reach), not plan ranking**. Advantage estimation optimizes the wrong thing.

A stronger JitRL would estimate advantage from detailed trajectory returns (`agent_replay`), not
from success rates. But the transfer store does not keep trajectory-level returns, and integrating
`agent_replay` into `transfer_learning` is a substantial, uncertain lift. As implemented and
measured, **Idea 1 is falsified.**

## What this means for the plan

- **Idea 4 (weight-space gate):** moot. No fuel (64 << 5000). The gate would always report
  TOO_THIN. Not worth building.
- **Idea 1 (JitRL):** falsified. Advantage estimation over success rates adds no signal.
- **Idea 3 (ensemble synthesizers):** not tested this turn. The Angelix literature (+50%) suggests
  it helps, but it was not verified in our repo. It remains the most plausible untested idea.
- **Idea 2 (memory-doing gate):** not tested. Requires the repair corpus (HuggingFace, inaccessible).
- **Idea 5 (compete on harness):** meta-strategy; the harness improvements (Ideas 1-4) did not move
  any number, which weakens it.

## The honest bottom line

Two of the plan's five ideas were testable, and **both were falsified**. The plan's thesis — that
training-free continual learning (JitRL) and gated weight-space learning are the path ahead — is
wrong for this repo. We have no fuel for weight-space learning, and advantage estimation over
success rates adds no signal to transfer.

**The binding constraint is still reach** (0 passes on the repair corpus, 0/51 certified), and
neither JitRL nor weight-space learning addresses it. The transfer bottleneck is not ranking or
fuel — it is that recalled plans do not save work on 7/15 instances. That is a reach problem, not
a learning-algorithm problem.

The one idea that remains plausible and untested is **Idea 3 (ensemble synthesizers)**, because it
directly widens the candidate space (reach) rather than optimizing ranking or gating learning. But
it is unproven in our repo, and the Angelix +50% figure is from a 2016 paper on a different
benchmark.

## What was done

- Ran `weight_space_fuel_v1` → Falsifier #4 fires (64 verified units, 5000 minimum).
- Implemented JitRL advantage estimation in `transfer_learning_v1` (`use_advantage`/`beta`,
  default off) and ran the 15-case probe → Falsifier #1 fires (identical 8/15, 6.333×).
- The `use_advantage` code is left in place (opt-in, default off) as a record of the attempt; it
  does not change default behaviour. No other code edited.
