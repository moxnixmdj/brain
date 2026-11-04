# PRE-REGISTRATION — *A refusal must learn*

2026-11-04, V1. Written **before** implementation, after measuring a defect in my own previous merge.
Base `0827db4e`. Branch `arena/f28951fa-brain`.

---

## What the last round actually delivered, measured

Last round repaired the act of concluding: settled became a computed quantity, and three doors that
converted blindness into certainty were closed. That work is real and merged (`4bb84831`).

Then I measured what the *creature* can do, as opposed to what a helper function can do:

```
k=4   real=HELD_OUT_REFUTED  no organ | helper=100/100
k=5   real=HELD_OUT_REFUTED  no organ | helper=100/100
...
k=15  real=HELD_OUT_REFUTED  no organ | helper=100/100
```

- `canonical/swe_kernel/meta_circular_organ_graph_v1.py` calls **three** functions from
  `settlement_v1`, and all three are `derive_probe_space`. `VersionSpace`, `settle`, `Hypothesis` and
  all six settlement statuses are used by **nothing but their own tests** — `grep` count outside the
  module and its test file: `VersionSpace` 0, `settle(` 0.
- `synthesize_periodic_organ` and `ConventionMemory` — the machinery behind the 700/700 claim — are
  called by **no production code at all**.

So the honest summary of last round is: **I closed the door on confident lying, and produced no
capability.** The creature now refuses the whole family. That is better than fabricating 2/10, and it
is not smarter — it is a creature that has learned to say "I can't", and stopped there.

**A refusal that does not teach is only half a repair.**

## The deepest defect this exposes

When the grammar fails, the failure is *terminal and silent about its cause*. `HELD_OUT_REFUTED` says
"the only program my grammar could form was wrong". It does not say **what structure was missing**, so
nothing can be done about it. And the operator basis `Ω` does not grow, because nothing is ever learned
from the failure — the same walls stand in the same place forever.

The previous round's fix made the creature correctly notice it was blind. It did not give it a way to
acquire sight.

## What I measured next, before designing anything

For a periodic function, the period is not a fact that must be looked up; it is a fact that can be
**bought with questions**. From a single seed:

```
k=4   period  4 after  5 questions      k=10  period 10 after 11 questions
k=5   period  5 after  6 questions      k=11  period 11 after 12 questions
k=7   period  7 after  8 questions      k=15  period 15 after 16 questions
```

`k+1` questions recovers structure that the grammar cannot express, with **no pre-collected table**.
This is the difference between a lookup and a probe: the table has to exist before the run, the
questions do not.

## What I will build

1. **Wire the settlement layer into the real path.** `synthesize_or_disambiguate_skill` must use
   `VersionSpace` / `settle` for its disambiguation decision, not a second, parallel implementation.
   Otherwise the tree has two definitions of "settled" and only one of them is tested.

2. **`diagnose_failure`** — when the grammar exhausts itself, classify *why* using only information the
   run already paid for: is the residual sequence periodic (budget for period `k+1`), monotone,
   piecewise-linear, or unexplained by any of these? The classification must be derived from evidence,
   never from a list of known function names.

3. **Close the loop.** A diagnosed structure becomes an induced operator, which is registered in `Ω`
   and reused. `HELD_OUT_REFUTED` stops being terminal: it becomes the branch point where the creature
   spends questions to grow.

4. **Remove the dead code claim.** Whatever remains unused after wiring is deleted, not left in the
   tree looking like capability.

## Predictions — stated so they can fail

- **P1 (wiring is real).** On all seven `x mod k` instances the **real path**
  (`synthesize_or_disambiguate_skill`) reaches ≥95% held-out accuracy starting from 3 seeds, with no
  pre-collected evidence table. *Falsified if any instance refuses or scores below 95%.*
- **P2 (the refusal taught something).** `HELD_OUT_REFUTED` no longer ends the episode; the run
  diagnoses a structure and returns an organ. *Falsified if the status still appears as terminal.*
- **P3 (no second implementation).** `VersionSpace` and/or `settle` appear in the real path's call
  stack. *Falsified if the organ graph still uses only `derive_probe_space`.*
- **P4 (diagnosis is evidence, not a name list).** Given a family whose structure is *not* periodicity
  (affine, quadratic), `diagnose_failure` must not return `periodic`, and given periodic data it must.
  *Falsified if it keys on anything but the numbers.*
- **P5 (no timidity, still).** Determined problems (`x*y`, `7x-2y+12`) still crystallize. *Falsified if
  the wiring makes them refuse.*
- **P6 (cost is bounded and honest).** Questions spent to induce structure are reported, and scale with
  the structure's size, not with luck. *Falsified if the reported cost understates actual oracle calls.*

## Non-claims

- This does not make the creature sentient and I will not say it does.
- Diagnosing "periodic" recovers one class of structure. It is not general program induction, and a
  family with structure outside the diagnosed set will still refuse — which is the correct behaviour.
- `SETTLED` remains relative to the reachable probe space. `truth.achieved` false, `authority: NONE`, $0.
- Last round's numbers (700/700) described a helper that nothing called. Where they are re-measured
  this round, they will be measured **through the real path** and labelled as such.

## Why this is the deepest available layer

Last round made the creature able to *notice* its own blindness. This round makes the blindness
*actionable*: a failure to explain becomes a budgeted experiment, and the budget's return is a new
operator that did not exist before. That is the difference between a system that reports the limits of
its grammar and a system that grows past them.
