# Your Agent Is Never Taught — Because It Waits for Accidents Instead of Running Experiments

**`OBSERVATIONAL_POOL_IS_EMPTY_BY_CONSTRUCTION_20261116_V1`** · 2026-11-16

## The question this answers

*What is the single bottleneck that, if fixed, would unlock the most capability?*

Last session priced a failure: one failure kills `2^k` hypotheses, where `k` is the number of
shared candidates the failure **kept**. So a near miss — keeps almost everything — is worth half
the hypothesis space, while a dramatic failure is worth almost nothing. The most informative
evidence in the world is the *nearly correct* attempt.

That immediately raises a harder question, and it is the one this session answers:

> **Can the system CONSTRUCT a near miss, or can it only WAIT for one to show up?**

Waiting is observation. Constructing is intervention. Everything depends on which one the tree can
actually do — and I measured it.

## What I found, in one table

Using the tree's own exact counter (`applicability_v1.count_survivors`) on the tree's own real
corpus — `|A| = 23`, two recorded failures — every hypothesis space is `2^23 = 8,388,608`.

| evidence | eliminated | share of the space |
|---|---:|---:|
| **the whole real corpus** — 2 actual failures | **8** | 0.0001 % |
| one dramatic failure (keeps 3) | 8 | 0.0001 % |
| **one reachable near miss (keeps 22)** | **4,194,304** | **50 %** |

**One near miss is worth 524,288× everything the real corpus ever taught us.** The corpus did not
teach nothing. It taught `8 out of 8,388,608`.

## Why — and it is not a tuning problem

This is the part that matters, because it means no amount of better ranking fixes it.

The tree's selector, `contrast_selection_v1`, is *deliberately* observational. Its own docstring:
the candidate pool is **"ONLY states that have actually been observed, plus the state the caller is
in right now"**, and the module **"never invents a world."** That refusal is principled — it cites
the measured failure mode of proposing queries outside what the system can actually reach.

But it has a consequence nobody had priced:

> **If the pool does not CONTAIN a discriminating state, selecting optimally from it is worth
> exactly zero.**

And the pool does not contain one. Real failures are dramatic: they drop most of the shared facts at
once, so they keep only a handful and every one of them is worth `2^3`. The tree already measured
this directly — the enumeration receipt recorded the selector returning `NO_INFORMATIVE_STATE` on
that very corpus, with `survivors_before = 8,388,600`. **Zero information, from a perfect selector,
on real evidence.**

**The pool is not badly ranked. It is badly populated.** Those are different problems and they have
different fixes. Better ranking of a pool of dramatic failures is worthless — it is sorting an empty
drawer more neatly.

## The fix is not "rank harder." It is "construct the neighbour."

The near miss that halves the space is not exotic. It is the most natural experiment imaginable:

> **Take something that worked. Remove exactly one of the facts it required. Try again.**

That attempt keeps 22 of 23 and eliminates `2^22` — half the entire hypothesis space — for one
interaction. This is the difference the causal literature names precisely: observationally
equivalent models need not agree under intervention, *because interventions create inputs that never
occur in observational data* (arXiv 2609.32247; and the classic result that no amount of observation
resolves a confounder that one intervention settles).

The agent that **runs experiments on its own plan** learns at `2^k`. The agent that **waits to see
what happens** learns at `2^3`. Same learner. Same arithmetic. The gap is entirely in who chooses
the evidence.

## The one thing that made this true and could break it

An intervention is only admissible if the state is **reachable and certifiable**. This is exactly
why the tree should NOT simply start inventing states, and it already has the component that
governs this: `certified_reached_escape_state_constructor_v2`, which binds every row that can
support certified progress to a content-addressed receipt from a separately supplied verifier, and
explicitly *"grants no terminal authority."*

So the honest ordering is:

1. **Make the near miss DISTINCT** — free, arithmetic only. (The real corpus wasted a query: its two
   failures dropped the same facts, so the second bought 7 hypotheses instead of 8. Fixing that
   costs nothing and was never done.)
2. **Make the near miss REACHABLE** — this costs machinery, and the constructor is the gate.
3. **Only then** prefer intervention over observation.

Step 1 is free and was missed. Step 2 is the bottleneck.

## So: is this a revolutionary way for agents to learn faster?

**Partly — and the part that is real is narrower and more useful than the sweeping version.**

Real: the learning rate from experience is set almost entirely by the *information content of the
evidence selected*, and that is a designed quantity, not a fixed property of the environment. A
system that chooses near misses learns ~500,000× faster than one that accepts whatever failures
happen to occur, at identical cost per interaction. That is a genuine, mechanically-explainable
speedup and it is why the ceiling is high.

Not real, yet: this tree cannot yet do it. It observes. The capability gap is one component —
`construct a reachable, certifiable state one fact away from a success` — and I am not going to
claim it exists before it is measured against the constructor.

Wrong, in the strongest form: it is not that agents "learn faster" in some general sense. An agent
that cannot construct a near miss learns *nothing* from experience, no matter how many trajectories
it collects — which is precisely the measured result that a frozen-context memory agent "can look up
what it has seen but cannot learn from it" (TMEM, arXiv 2606.04536), and the reason a blind retry is
worth 2.7 steps of information (AgentLens, arXiv 2605.12925). Volume is not the lever. **Selection
is.**

## The bottleneck, stated exactly

> **The system can only SELECT evidence. It cannot yet CONSTRUCT it.** Every improvement available
> from better ranking of observed states has already been taken — the selector is exact and returns
> `NO_INFORMATIVE_STATE` on real data. The remaining capability is behind one door: *make a state
> that is one fact away from a success, and certify that it is reachable.*

That is what I will build next — against the constructor, not instead of it.

## Reproduce

```bash
python3 canonical/tools/observational_pool_is_empty_by_construction_v1.py \
        canonical/verification/OBSERVATIONAL_POOL_IS_EMPTY_BY_CONSTRUCTION_20261116_V1.json

/tmp/v4/bin/python -m pytest \
        canonical/tests/test_observational_pool_is_empty_by_construction_v1.py -q   # 10 passed
```

## Instrument limits — stated plainly

- **This is arithmetic, not evidence about the world.** Counts come from the tree's own
  `count_survivors`; they say what a hypothesis space contains, not what any real agent will do.
- **`|A| = 23, D_i = [20, 20]` is one corpus**, taken from a merged receipt. It is not a distribution.
- **The 524,288× is a ratio between two sizes of hypothesis space**, not a measured learning-curve
  speedup. No agent was run. No task was attempted.
- **The realizability gate is declared, not measured here** (`status: NOT_MEASURED_HERE`). Whether a
  near miss can actually be constructed in this tree is the open question this document does *not*
  answer, and the next instrument must.
- **A mistake I made and corrected in this session:** a draft read `D_i` as the *kept* set and
  claimed the corpus was already interventional (4×, not 524,288×). The live counter refutes it —
  `count_survivors(A, [D1, D2])` with `|D_i| = 20` returns `2^23 − 8`, exactly as the receipt says.
  The test `test_D_is_the_dropped_set_not_the_kept_set` now prevents that misreading from shipping.

*Authority: `NONE__PRODUCER_RUN_COMPUTATION_OVER_EXISTING_COUNTER`. $0. No model used to produce
any number above.*
