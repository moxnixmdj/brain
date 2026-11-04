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
