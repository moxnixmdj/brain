# The Premise Is the Sense

**`THE_PREMISE_IS_THE_SENSE_20261116_V1`** · 2026-11-16 · branch `arena/8bc45da6-brain`

## Your claim, and the exact place it breaks

> *"Give our model the smartest actions once, let it experience them once, and it learns them
> permanently. Then we solve everything on a computer."*

Half of that is true and already built. Half is false, and **the false half is not a matter of
effort — it is a counting argument.** I did not answer this from memory: this tree measured it on a
real git repository two days ago (`ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.md`,
1,680 real transitions, nothing truncated), and an October 2026 formal-semantics study of frontier
agents found the same thing from the outside.

**True:** one verified experience can be stored perfectly and permanently, and applied again inside
a typed interface with a mechanical check. That is real, it is built, and it is genuinely rare.

**False:** that one experience teaches the *environment*. A demonstration is three transitions. The
environment is 168 states. Storing three transitions — in weights, in a store, anywhere — does not
turn them into 168. On task A the single most charitable demonstration that exists licenses
**112 of 168** states. On task C, **56 of 168**.

**False, and this is the sharper one:** that *more* tries close the gap. The undecidable set is
**invariant to experience**. If two situations look identical and need different actions, no policy
keyed on that appearance can be right on both — however many times you visit them. Trying again
teaches you *which* perceptions are undecidable, which is valuable, but it is not the lesson the
claim asserts.

**And sentience:** not measured, not supported, not required. The only in-tree proxy — *does
experience change competence on new problems* — is negative. Asserting it spends every real number
this tree has.

## The real bottleneck, in one sentence

The tree already named it:

> **Whether the fact the plan depends on is OBSERVABLE AT THE MOMENT OF ACTING.**

Not the store. Not the parameters. Not the plan. Not the speed. That one thing — and every number
moves with it and with nothing else.

Frontier agents fail exactly there. A 2026 formal-semantics study measured that **46–64% of plans
for solvable tasks contain an inapplicable action, and those account for 89% of failed episodes**;
precondition violations terminate 66–68% of solvable episodes under every architecture, and
*"agents change the state far more often than they inspect it."* Reflexion and critic architectures
do not fix it. That is the same bottleneck, measured from the opposite side, by someone with nothing
to gain from agreeing with us.

## What nobody had done, and what I did

The tree's own answer was *"spend on senses, not on demonstrations"* — correct — but it then
**hand-listed four sense vocabularies** and compared them. That answers *"is a rich sense better than
a poor one"* (always yes). It does not answer the question that actually decides the architecture:

> **Which facts must be read before running this plan, and what do they cost?**

That is exactly solvable and the tree already owns the solver: `k6_decision_refinement_compiler_v1`,
which enumerates every subset of candidate discriminators and therefore returns the **provably**
minimum-cost sufficient set — not a greedy guess. I reduced the question to its contract:

- a plan is **one choice**: `RUN+CONFIRM` where it reaches the goal, `REFUSE` where it does not;
- two states may share a perception **only if they agree on that choice** — otherwise the agent is
  looking at two different situations, deciding one thing, and is wrong in one of them;
- so the minimal sufficient sense is the minimum-cost fact set making every perception cell
  decision-consistent.

I verified that compiler against an **independently written brute force**. They agree on both tasks.

## The result

| task | minimal sufficient sense | cost | instead of | cost |
|---|---|---:|---|---:|
| A — committed & clean | **`unstaged`** | **1** | status+content(all)+staged | 11 |
| C — committed & `b.txt` still `one` | **`content:b.txt`** | **1** | status+content(all)+staged | 11 |

**One tool call makes the agent's own decision fully decidable. Eleven were being spent.** At the
minimal sense there are **0 undecidable states** on both tasks.

And the part that inverts the obvious instinct:

| sense | cost | task C sufficient? | undecidable states |
|---|---:|---|---:|
| status | 6 | **NO** | **24** |
| status + content(a.txt) | 7 | **NO** | **16** |
| status + content(all) | 10 | yes | 0 |
| **`content:b.txt` alone** | **1** | **yes** | **0** |

**More sensing was never the answer. The RIGHT sensing was.** Reading six status facts buys nothing
for task C; reading one file settles it. The premise of this plan lives in `b.txt`, so that is the
only thing worth reading.

These undecidable counts — 24, 16, 0 — **reproduce the basin document's published table exactly**,
measured by a different instrument. `test_undecidable_counts_reproduce_the_published_basin_table`
pins that agreement so the two can never silently diverge.

## "You sure this is the smartest approach?" — what I killed first

- **I did not build a new learner.** One exists; the failure is evidence, not learning.
- **I did not build a new selector.** It is exact and already returns zero on real data.
- **I did not require weight training.** Files-not-backdoors: the decision is a computed threshold,
  every bit of it derived, and the same rule applies to pixels — read the premise, refuse on
  mismatch.
- **I did not re-derive the basin measurement.** I reused its world, plans, goals and definitions,
  and cross-checked against its published numbers.
- **I did not let the optimiser cheat.** Without a postcondition, "always refuse" satisfies
  sufficiency with one fact and solves nothing. I found that by running it, and the formulation now
  includes `CONFIRM` so the empty policy cannot win. The degenerate answer is printed alongside the
  real one rather than hidden.

## What this means for the goal

**Am I right that this is a revolutionary way to make agents learn faster?** Partly — and the true
version is more useful than the sweeping one.

The learning rate from experience is set by **the information content of what you read before
acting**, and that is a *designed* quantity. A system that reads the premise learns from one
experience *safely*; a system that does not learns from one experience *sometimes*, silently, and
calls the failures noise. Volume is not the lever. **Reading the decisive fact is.**

**Is computer use solved by "do it once"?** No. It is solved by *"read exactly the premise, run,
confirm, and refuse when the premise fails"* — and then one experience is worth having. That is the
difference between silent failure and a refusal, and it is measurable, exact, and cheap.

**The single bottleneck:** *the premise.* Make the decisive fact observable and priced. Everything
downstream — reuse, permanence, compounding, transfer — is gated on it. This module prices it
exactly: one call, not eleven, and the answer is derived from the goal rather than chosen by hand.

## Where this goes next

1. **Per-fact pricing in the acting loop.** Before any plan runs, compute the minimal sufficient
   sense for *its* postcondition and read only that. This is a threshold computed from the goal, not
   a learned behaviour — it transfers to any environment where the premise can be read at all.
2. **Refuse is a first-class outcome.** A refusal is a correct answer and must be recorded as one.
   Silent failure is the enemy; the tree measured 31.1% of replays corrupt with no error raised.
3. **Then, and only then, permanence.** Storing a guarded plan is worth doing; storing an unguarded
   one is storing a gamble.

## Reproduce

```bash
python3 canonical/swe_kernel/the_premise_is_the_sense_v1.py \
        canonical/verification/THE_PREMISE_IS_THE_SENSE_20261116_V1.json
/tmp/v4/bin/python -m pytest canonical/tests/test_the_premise_is_the_sense_v1.py -q   # 12 passed
```

## Instrument limits — stated plainly

- **One environment, one action hand, three tasks.** A real `git` repository, not a GUI; 168
  semantic states reachable by ten actions. This is not a distribution and not a benchmark.
- **Costs are tool calls**, a defensible proxy for latency and context, not a measured wall-clock.
- **Sufficiency is relative to the plan.** A different plan has a different premise and therefore a
  different minimal sense. The method is general; these numbers are not.
- **A refusal-only policy is degenerate** and is reported as such, not hidden.
- **No capability credit, no benchmark rank, no independent verification.** Authority
  `NONE__PRODUCER_RUN`. $0, zero model calls, zero network calls at run time.
- **Nothing here claims sentience**, and nothing here would change if it did.

*Reused unchanged and not rebuilt: `k6_decision_refinement_compiler_v1.py`,
`one_demonstration_basin_v1.py`, and the merge receipt `a_failure_is_worth_two_to_the_keys_kept`
(#6906) and pool receipt (#6911).*
