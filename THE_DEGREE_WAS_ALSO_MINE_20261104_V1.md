# Round 30: the degree was also mine

Round 29 removed a handwritten cofactor list and replaced it with a rule. That was real. This round
found that the rule had **a list inside it**, one layer down.

## What round 29 actually achieved, stated precisely

Round 29 replaced

```python
cofactors = [x, 2x, x*x, const]     # four entries I typed
```

with differencing at lag `k`. But the replacement recovered **affine and quadratic** coefficients —
slope by division, quadratic by second difference. Two shapes. Measured 2026-11-04:

| expression | round 29 |
|---|---|
| `T(x) + x³` | `CONTRADICTORY_OR_OUT_OF_GRAMMAR` |
| `T(x) + 2ˣ` | `CONTRADICTORY_OR_OUT_OF_GRAMMAR` |

**The degree was the next thing I had typed**, and the base of an exponential would have been the one
after that. That is a *shorter* list, not no list. It fails on exactly the same principle, and it
would have kept failing on the same principle for as many rounds as I kept patching it.

## The rule, generalised

Difference `y` at lag `k` once, which kills any period-`k` table:

```
D_k(x) = y(x+k) − y(x) = s(x+k) − s(x)
```

Then **identify** what survives instead of assuming its shape.

**Polynomial.** If `s(x) = a·x^d` then `D_k` has degree `d−1`, so `d−1` unit differences leave a
constant

```
C = a · k · d!        ⇒        a = C / (k · d!)
```

The **degree is how many differences it took to flatten** — measured, not searched. Verified
independently before writing code, for `d = 2,3,4` at `k = 3` and `k = 5`: the constant came back
6, 18, 72 and 10, 30, 120, and `C/(k·d!)` recovered `a = 1` exactly every time.

**Exponential.** If `s(x) = A·rˣ` then `D_k = A·rˣ·(rᵏ − 1)`, whose consecutive **ratio is exactly
`r`**. A constant ratio names the base with no fitting, for any base.

**Neither → refuse.** That is not a fallback. It is what makes a success here distinguishable from a
lucky fit, because the shape is **named before the block is solved**.

## Measured — all 0 wrong on held-out

| expression | before | after |
|---|---|---|
| `T+x³` | refused | **solved** |
| `T+x⁴` | refused | **solved** |
| `T+x⁵` | refused | **solved** |
| `T+0.25x³` | refused | **solved** |
| `T+2ˣ` | refused | **solved** |
| `T+3ˣ` | refused | **solved** |
| `T+1.5ˣ` | refused | **solved** |
| `T+0.5ˣ` | refused | **solved** |

No regression: `T+3x`, `T+x²`, `T*2x`, `T+7` all still solve, 0/30 wrong.

## The defect I introduced in this very round, and caught

With few points the detector reported **`poly6`, `poly8`** — a degree that means nothing more than
"fewer samples than terms". A short difference sequence *always* flattens, by exhaustion.

That is **arithmetic exhausting itself, not a discovery** — the same error as round 25's budget limit
read as a statement about the grammar, and round 27's period cap read as a statement about the
language. It is evidently my characteristic failure: I mistake the edge of my instrument for the edge
of the world.

A degree now needs **two points of redundancy beyond itself** before it may be believed. Below that
the detector says nothing and the creature refuses, which is correct — the evidence genuinely cannot
yet distinguish a polynomial from an exponential.

## A nondeterminism that was not one

`T+3ˣ` gave `CONTRADICTORY` at 9 points and `DISAMBIGUATED` at 12. I assumed nondeterminism and nearly
went looking for state pollution — the same wrong hypothesis I had in round 26. It was
**evidence-dependence**: at period 3 with 9 points, differencing at lag 3 twice leaves exactly one
value, and refusing is the honest answer. The fix was not to make it deterministic; it was to make
the *requirement* explicit.

That is twice now that "it changed between runs" was actually "it depends on the evidence". Worth
recording so I stop reaching for the first explanation.

## Why this is the right layer

Round 29 asked *can this acquire a capability I did not install?* It answered: the coefficients, yes;
the algebra, no. Round 30 extends the same answer one level: **the shapes the algebra ranges over are
now also recovered rather than typed.**

Still mine, and I will keep saying it: the **decision to difference at lag `k`**, and the idea that a
table composes with a cofactor at all. Those are authorship. What is no longer mine is *which*
cofactors exist — affine, polynomial of any degree, exponential of any base, including bases and
coefficients I would never have written into a list.

`truth.achieved: false` · `authority: NONE` · $0 · no sentience claim · no external models · no
neural weights.

## Measured state

**310 passed, 26 subtests**, one pre-existing failure that fails identically on the stashed baseline.
14 new tests demanding degrees and bases never expressible before, the refusals alongside them, and
source-level guards that fail if a degree or base is typed back into the detector.
