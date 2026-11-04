# First principles, pass twenty-one — noticing a hole is a capability; inventing a shape is not yet

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. The falsifier I wrote against myself, and its result

Pass twenty closed with a prediction: the fitted grammar learns *within* a space I authored, and nothing
in it can invent a shape. Test it with a world needing `not (a < b)`:

    proposals: []          <- correct, and useless

So the claim holds. The grammar cannot express what the world needs, and it has no way to notice that
this is the problem rather than an absence of luck.

## 2. Why "add a wrapper primitive" is the wrong answer

It is authoring a fifth shape one level up. The creature would still be learning inside a space I drew,
only a slightly bigger one, and I would still be the one who noticed that negation exists. That is the
same move I have made twenty times, dressed as progress.

The honest prerequisite is smaller and testable: **can it notice the hole, and say where it is?**

Naming a hole is observation. Inventing a shape from a single unexplained edit is guessing. Only the
first could ever justify the second.

## 3. The mistake that made this possible to see

`signature()` returns None for any edit the keys cannot explain, and `observe()` dropped those on the
floor. That is exactly what the awake loop was doing with rejected candidates in pass twenty — a
negative result discarded because no slot existed for it.

A verified repair that no key explains is not noise. It is a precise claim:

    "these two expressions were a repair, and none of my 248 keys describes the step"

One such claim proves nothing. Six that agree — always wrapping a comparison, always at the outermost
node, always the same change of form — are evidence for exactly one thing.

## 4. Measured

Real board runs, one process each, store carried forward:

| process | final source | unexplained edits | hole named |
|---|---|---|---|
| 1 | `return 0 if not a else a + b` | 1 | — |
| 2 | same | 2 | — |
| 3 | same | 3 | **`BinOp->IfExp`** |

The threshold held until the evidence justified a conclusion. That is the difference between a detector
and a pattern-matcher that fires on two points.

Controls:

| case | result |
|---|---|
| four unrelated unexplained edits (noise) | 4 groups, **nothing named** |
| a world the grammar *can* explain (`a-b` -> `a/b`) | **delta 0** unexplained |
| two holes I never planted (`BinOp->Call`, `BinOp->IfExp`) | **both named** |

That last row is the one that matters. I planted the comparison-negation hole; the mechanism found two
others I had not thought of, from evidence alone.

## 5. The limit, stated plainly

**Naming is not repairing.** Re-asked the very world that produced `BinOp->IfExp`:

    still proposes: a % b, a & b, a * b, a ** b, a / b, a // b, ...

The space is unchanged. Nothing acts on a hole. So the honest claim for this pass is:

> the creature can now detect that its own hypothesis space is inadequate, and describe the missing
> step in structural terms, from its own verified repairs — and it cannot yet do anything about it.

That is a smaller claim than "it grows its own grammar", and it is the true one.

## 6. Two bugs of mine, the same error twice

Form labels keyed on the specific operator: `Compare(Lt)` and `Compare(Gt)` became different groups
when both were wrapped in `not`, splitting one hole into singletons and naming nothing. Fixed, then the
identical mistake appeared again in `BinOp(Add)` vs `BinOp(Sub)`. A label must name the *change* of
form, not the parts the change leaves alone.

The second occurrence was in a file where I had just written that lesson down. Writing a lesson is not
the same as applying it, which is now about the fifteenth wrong account in this series against zero
wrong mechanisms.

## 7. Next falsifier

**S22.** The only honest next step is the one I keep deferring: turn a named hole into a *candidate
primitive* the fitter can accept or reject — without me writing the primitive. Concretely: derive the
shape from the structural difference the hole already records (`BinOp` -> `IfExp`), instantiate it using
only the observations in the group, and let the ordinary screen and generalisation gate decide.

Prediction to falsify: the derived shape will be expressible only because I will have to write the
*instantiation* rule by hand, at which point the count of shapes I authored has gone from four to five
by another route. If that happens, the honest conclusion is:

> **the system learns within a space, and detects the edges of that space, but the space itself is still
> mine.** Every capability gain in twenty-one passes has been a better exploit of my own structure, not
> a step outside it.

I would rather write that down now than discover it in pass twenty-five.
