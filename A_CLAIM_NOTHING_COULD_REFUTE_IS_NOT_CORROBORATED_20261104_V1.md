# A claim nothing could have refuted is not corroborated — round 26

**Date:** 2026-11-04
**Status:** `truth.achieved: false` · `authority: NONE` · $0 · no sentience claim · no external models · no neural weights

---

## What round 25 left on the table

Round 25 fixed two things one layer below inference: **senses** (the probe space was a diagonal, and
crashed on any container) and **budget** (four call sites searched at 64–80 and then spoke about the
grammar). It recorded one defect as the next round's question, with an `xfail` to make its fix loud:

    x*x + y over three points  ->  (4.5*x0) + (-0.5*x1) + -0.5
    at (10, 20):   claimed 34.5,   truth 120

That body is WRONG on every input it was not shown, and it was **CRYSTALLISED**. So this round's
question was why, and the first hypothesis — a weak search — is false. `x*x + y` and `x + y` both fit
those three points *perfectly*. So does a plane. Three observations exactly determine the three
parameters of an affine fit, which means the body has **zero residual on zero leftover data**.

Zero residual with nothing left over is not corroboration. It is the definition of a curve drawn
through three points.

## The defect, stated as a single sentence

The crystallizer asked **"does it fit?"** and accepted the answer. It never asked **"could this have
been wrong?"**

That is round 25's defect wearing different clothes:

| round | the overstatement | what was missing |
|---|---|---|
| 25 | "no candidate" — from a search that had not finished | proof the search was exhaustive |
| 26 | "crystallised" — of a claim nothing had tested | proof the evidence could refute it |

Both are a confidence asserted beyond what was actually established. Round 25's lived in a budget;
this one lives in degrees of freedom.

## The mechanism: refutability from evidence alone

`canonical/runtime/refutability_v1.py`. Withhold one observation, fit the rest, and ask whether the fit
still predicts the point it never saw. If it does, that point was a **prediction**, and disagreement
would have been a **refutation**. If nothing predicts anything, the claim has absorbed its evidence and
said nothing about the world.

    REFUTABLE       the evidence could have caught the claim being wrong
    NOT_REFUTABLE   the claim absorbed its evidence and predicted nothing beyond it
    TOO_FEW_POINTS  the evidence is structurally incapable of testing a claim this general

The third verdict is not a cop-out, it is the finding. With `n <= parameters` the question has no
answer, and reporting that as either success or failure would be inventing one. That is exactly where
`x*x + y` over three points sits.

Measured separation:

| case | verdict | |
|---|---|---|
| `x*x` over 20 points | REFUTABLE 20/20 | |
| `x mod 4` over 8 points | REFUTABLE 8/8 | |
| `T(x)+x` over 9 points | REFUTABLE 9/9 | |
| `len(x)` over 3 lists | REFUTABLE 3/3 | |
| `sorted(x)` over 3 lists | REFUTABLE 3/3 | |
| `x^3` over 20 points | NOT_REFUTABLE 0/20 | memorisation |
| `x*x + y` over 3 points | TOO_FEW_POINTS | **the headline case** |
| affine over 3 points | TOO_FEW_POINTS | indistinguishable from the above |

Note the last two rows. They are not two cases. They are **one case with two answers**, which is why
neither may be called settled.

The gate sits *after* disambiguation, on the whole accumulated evidence, because everything above it
may have bought tests from an oracle — and a claim that correctly predicted an answer it had not been
shown has been tested by the strongest instrument available. Refusing that would discard the one
thing that actually happened.

## Why this is reuse, not new machinery

The tree already contained the instrument: `generalization_check_v1.classify(body, params, withheld)`
holds points back and requires agreement, calling it `OVERFIT` instead of "solved". **Seven modules
use it.** Its own docstring says that any reach number reported without it is an upper bound.

The crystallizer — the one place that grants permanence — did not use it at all.

So the honest description of this round is not "a new capability was built". It is: **the creature had
a test it was not applying at the moment it decided what to believe.**

## The uncomfortable part: the instrument was wrong five times

Every single failure while building this was the *measuring device*, not the reasoner. Each one
presented as a finding:

1. **Vacuous test.** Withhold a point, fit on two, require prediction — of a 3-parameter family. It
   failed for *every* law, including `x+y`. A test that fails everything measures nothing.
2. **Unusable API.** Called `_solve_multilinear`, which returns an *expression string*, then tried to
   call it. Everything read as 0.
3. **Backwards degrees of freedom.** Condition inverted; a defect became invisible.
4. **Narrower than the audited.** The auditor used the organ graph's candidate generator (constant,
   projection, affine, table) while `sorted(x)` and `len(x)` are reachable only through the
   observational synthesizer. A testable law was reported NOT_REFUTABLE. **An auditor narrower than
   the synthesizer certifies only what it already understands.**
5. **Five more mechanical ones**, each of which looked like science: a sandbox without `sorted` scored
   a correct body as OVERFIT; `_split_body` treated `def run` as a helper and left an empty outer body
   (three separate times); `out` was re-initialised, silently discarding every body the new branch had
   just validated; `_SynthBody` was routed through `_safe_eval_candidate`, which cannot evaluate it, so
   all its predictions read as failures; a doubled `return` from wrapping a statement body as an
   expression.

**That is the deepest finding of the round.** A creature whose instruments are narrower or more
fragile than its reasoner does not discover its own blindness — it reports the blindness as a
property of the world. Round 22's "the concept library is inert", round 24's "the grammar is the
limit", and round 25's "the rewind" were all this error in different costumes, and this round
produced five more before the instrument was trustworthy.

## What the creature now does differently

- A claim that no evidence could have refuted is returned as `PROVISIONAL_UNTESTABLE_CLAIM`. The body
  is still handed back and is still exact — provisionality is not uselessness — but it is **not
  registered as settled knowledge**.
- `DISAMBIGUATED_AND_CRYSTALLIZED` is no longer said when there was nothing to separate; that case
  reports `SOLE_HYPOTHESIS_CRYSTALLIZED`. The word DISAMBIGUATED was asserting a discrimination the
  caller could not verify had happened.
- Every crystallised answer now carries its `refutability` report, so the claim and the evidence that
  licenses it travel together.

## Regression status

- New suite `test_a_claim_nothing_could_refute_is_not_corroborated_v1.py`: **15 passed**.
- 22-suite regression: **291 passed, 20 subtests**, one pre-existing failure
  (`test_a_fallback_is_held_to_the_same_evidence_v1`) that fails identically on the stashed baseline.
- **No capability lost**: round 24's compositions `T+x`, `T−x`, `T*x`, `T+x²` remain **0/150** wrong
  on held out; round 25's `x*y+1`, `2*x*y`, `x*y`, `x+y` all exact when tested.
- Three tests were updated rather than repaired, and each update states the measurement that forced it:
  `test_determined_problems_still_crystallize`, its twin in the settlement suite, and the level-1
  bootstrap test. All three asserted that a three-point fit should be settled — the exact claim this
  round falsifies.
- The round-25 `xfail` now **passes as expected-to-fail for the right reason**: the wrong affine body is
  no longer called a law.

## Not done

- **P4 of round 25 (the 4× table-evidence constant) remains open.** Recorded, not rushed.
- **Refutability is not yet used to decide HOW MANY points to buy.** The module can say
  TOO_FEW_POINTS; the creature does not yet treat that as a shopping list. That is the obvious next
  move and it is not claimed here.

## The thesis handed forward

Round 25: the creature was better at answering than at perceiving.
Round 26: **the creature was better at reasoning than at checking, and its checking apparatus was the
least trustworthy thing it owned.**

A creature that cannot tell "I could not have been wrong" apart from "I was right" will accumulate
false confidence at exactly the rate it learns. `truth.achieved` is still **false** — but the creature
now knows, in a way a caller can audit, which of its own answers it was ever in a position to doubt.

---

# Part 2: what is DERIVED and what is merely CHOSEN

The first half of this round made a claim stop being permanent when nothing tested it. That is
protective, and protective alone is not enough — it also *cost* a capability: three-point fits used to
be answered and now refuse. So this half asks the question that actually distinguishes a living system
from a careful one:

> **which of my numbers are theorems, and which are preferences I have been reporting as theorems?**

## The 4× constant was justified by a false sentence

`settlement_v1.table_evidence_requirement(period, factor=4)` carried this docstring:

> the block must be at most a quarter of the evidence, **which is what separates an induction from a
> restatement**

That is a claim, so it can be measured. Requirement `k·p`, signal truly periodic for `T` cycles and
then breaking:

| requirement | false tables accepted when |
|---|---|
| `2p` | `T ∈ {2,3,4,5,6,7}` |
| `3p` | `T ∈ {3,4,5,6,7}` |
| `4p` | `T ∈ {4,5,6,7}` |
| `6p` | `T ∈ {6,7}` |

**A false table is accepted exactly when `T ≥ k`, for every `k` and every `p`.** No finite multiple
removes the failure; raising `k` slides the boundary and buys nothing categorical. So `4` does not
separate induction from restatement. It refuses tables from signals that broke before the fourth
cycle, and that is all it does.

The number is now written as what it is — `2·period` (the only derivable part: every residue seen
twice means one real repeat) **plus a stated repeat policy**, exported through
`table_requirement_policy()`, whose `status` field begins `POLICY, NOT THEOREM`. The numeric value is
unchanged, so nothing regressed; what changed is that the tree no longer asserts something false.

**This is the discipline the round is about, applied to a docstring instead of a program.** A false
sentence in a justification is the same defect as a false claim in an organ: it licenses belief that
evidence did not earn.

## A deliberate negative result: the experiment planner is worse than what it replaced

The obvious next step after `TOO_FEW_POINTS` is to *buy the missing evidence*, and the deficit is
computable: an arity-`a` fit needs `a + 2` observations, so the plan is exact. `plan_probes` computes
it, and on a three-point affine it correctly says **one more observation**.

It also ranks candidate probes by how many surviving pairs disagree at them, which sounds strictly
better than a fixed grid. **It is not, and I shipped it before checking.**

For `x // 7` over seeds 1..5 it bought probes at `-1`, `-10`, `-11` — every one negative, every one
where all candidates agree — and never visited `x ≥ 8`, where `x // 8` and `x // 7` actually differ.
The creature crystallised `x // 8`, **wrong at 37, 100 and 999**. The old code did not have this
failure: its probe space starts at −40 and sweeps far enough to reach the separating region.

So the wiring is **reverted**. The decision path keeps the space that demonstrably separates, the
computed deficit is used only when it is *larger* than the default, and `plan_probes` is retained as an
**advisory report** with its limitation stated in the source. Its ranking was not better; it was
untested, and the first test falsified it.

This is recorded rather than quietly removed because a tree that only records its wins is a tree that
cannot tell the difference between progress and motion.

## What the two halves together say

| | asks | can be derived? |
|---|---|---|
| refutability | did this evidence constrain the claim? | yes — degrees of freedom |
| table requirement | have I seen enough repeats to trust it? | **no** — a tolerance |
| probe deficit | how many more observations? | yes — `arity + 2 − n` |
| probe *choice* | which observations? | **not yet** — the naive ranking lost to a sweep |

Two of four are theorems. Two are not, and the tree now says which is which instead of implying all
four were discovered.

## The correction this forces on the guard

The action intent carried `canonical_base_commit` as a hand-maintained field, which went stale three
times in one session as main advanced — I re-based it twice and was about to do it a third time. That
is exactly the static artefact this project is supposed to be replacing: a derived value maintained by
hand, which fails by going stale rather than by being wrong.

Recorded here rather than papered over: **re-basing is a treadmill, not a fix.** The field should be
computed from the base the guard already has, and until it is, every merge makes the intent lie by one
commit.

## Measured

- `x // 7`, `x^3`, `2^x` from seeds 1..5: **identical to baseline** (refuted / out-of-grammar). The
  planner revert removed the only observed false positive.
- `table_evidence_requirement(3) = 12`, `(10) = 40` — unchanged, so no capability moved.
- Refutability on 8 cases: correct separation, including `x^3` NOT_REFUTABLE as memorisation.
- 97 passed, 1 xfailed across the five suites that touch this subsystem.

`truth.achieved: false`. What is true: the creature can now distinguish a claim it tested from one it
merely fitted, and the tree can distinguish a number it derived from one it chose.
