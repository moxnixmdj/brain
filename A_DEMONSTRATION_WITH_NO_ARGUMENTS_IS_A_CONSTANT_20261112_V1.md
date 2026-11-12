# A demonstration with no arguments is a constant

**2026-11-12.** Base `05c9d45f`. Branch `arena/d3d05f45-brain`. Round 17.

Round 16 ended with a plan: deepen the 296 verified experiences by re-running each **k = 8 times with
fresh inputs**. That plan has an assumption, and this round tested it instead of building on it.

```
verification records                     296
  module-path ids (...auto.v1)            294
  declared registry capabilities            2
  other                                     2
arguments after the script path           {'0': 296}
verified experiences with any argument       0
curated registry capabilities              145
  of those, independently verified           1
```

**Every verified experience passes zero arguments.** There is no input space. Running it eight times
produces the same point eight times: depth in count, no depth in information. And the population being
verified is not the population of skills — 294 of the 296 are module paths verified as "this module
still runs", while the 145 curated capabilities are almost entirely outside the verified set.

## What this says about the question

> *Give it the most advanced actions, let it try each once, and it keeps them forever.*

The premise hides a word. "Try once" only means something if the try has **inputs** — an instance drawn
from a task's input distribution. A zero-argument execution is not a task; it is a constant. Learning
from it can only memorise that constant, and the tree has now counted 296 of exactly that.

This is the third time the same structure has appeared, each time one layer deeper:

| layer | what was measured | result |
|---|---|---|
| the edit learner (round 13) | one showing vs two | literal `product == None` → `?1 == None`; 1 of 4 → 4 of 4 |
| the benchmark record (round 14) | harness vs weights on unseen tasks | no harness gain; weights `S_held = 0.29` vs `S_seen = 0.57` |
| the evidence base (rounds 16–17) | 296 independently verified experiences | zero arguments, so zero instances to generalise over |

Each layer says the same thing in its own vocabulary: **generalisation is bought with variation, and
variation has to be constructed. It is never a by-product of repetition.**

## The fix, named and deliberately not shipped

`canonical/runtime/capability_receipt_lane_v1.py :: declared_probe_args()` already fills every
`${input.*}` placeholder of a declared capability. It fills each with a **constant** — the capability
id for free text, one content-addressed sink for paths — so instance *k* is instance 1 by
construction.

The change is about six lines: derive those values from `(capability_id, module_sha, instance_index)`
and record the index in the receipt so `--verify` replays the same instance.

I did not make it, and that is the round's judgement call, not an omission:

* that module produces **all 296 attestations**; a blind edit could invalidate them;
* the CI lane that would prove the change is correct **does not run in this sandbox**;
* the standing law is to kill a candidate before implementing it when it can break what it feeds.

Naming it with the exact function, the exact change and the exact reason it is unsafe to ship blind is
worth more than six lines merged on hope. **The next session that can run the workflow should make this
change and nothing else**, then re-verify.

## What this costs the story so far

It removes the last version of the optimistic plan that survived. Not "we have solved instant learning"
— we have solved *permanence*, in three independent ways, and this repo holds the receipts for it. What
has never been solved, anywhere in the 2026 record or in this tree, is **variation**: the thing that
turns one experience into a distribution a held-out split can test.

For "any computer use, solved", that is the whole remaining problem, and it is now stated in a form
that can be built: give every capability an instance index, fill its inputs from it, run k instances,
split by instance, and let nothing into the corpus that a second identity did not reproduce.

## Receipts

```
python3 input_space_census_20261112.py
python3 -m pytest -q canonical/tests/test_input_space_census_v1.py        6 passed
```

## Non-claims

Counts only; it does not judge whether the 296 verified modules were worth verifying, and it does not
claim the input-space fix works — it has not been run. One module in the verified set does overlap the
registry; that is a single point, not coverage. Reads evidence and the registry, writes nothing,
`truth.achieved` false, $0, zero model dependency.
