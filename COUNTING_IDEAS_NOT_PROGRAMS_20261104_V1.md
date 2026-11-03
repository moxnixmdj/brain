# Counting Ideas, Not Programs

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

Yesterday's module reported **12 admissible bodies** for three examples of `2x` and called the answer
PROVISIONAL. That number was wrong in a way that mattered: ten of the twelve were *the same function
written differently*. The honest count was never 12.

---

## 1. The distinction the module could not draw

Two bodies are the *same explanation* if they produce the same values. Two bodies are the same
*program* only if they produce the same text. I measured programs and called them explanations.

Grouping by behaviour over the probe range:

| group | members | example |
|---|---|---|
| A | **10** | `(x / 1) + x`, `(x / 1) * 2`, `(x * 2) / 1`, `2 * (x / 1)`, … |
| B | 1 | `2 / (1 / x)` |
| C | 1 | `2 // (1 / x)` |

**12 programs → 3 explanations.** The real state of knowledge was "three ideas, one of which is
written ten ways", not "twelve ideas". Overstating the ambiguity is a failure too — it makes the
creature refuse to commit when it is entitled to.

Pre-registered in `PREREG_EXPLANATION_COUNTING_20261104_V1.md`; **9/9 findings as predicted.**

## 2. The payoff is immediate

The interrogation loop from yesterday, now counting explanations:

```
step 0: programs=12  explanations=3  PROVISIONAL  sizes=[10,1,1]   asked x=-3.5, told -7.0
step 1: programs= 3  explanations=1  DETERMINED   sizes=[3]
```

One answer, and the answer is now **forced** — every admissible program is the same function
spelled differently. That is `DETERMINED` with the honest caveat attached: the data force the
*answer*, not the *spelling*, and neither is the same as being true. The report says all three.

Before this change the same sequence ended PROVISIONAL at 3 programs, because the module could not
tell three spellings from three ideas.

---

## 3. Two bugs in the grouping, both caught by trying to break it

**Bug 1 — representation as difference.** `(2 * x)` returns `4` and `(2.0 * x)` returns `4.0`.
Using `repr` directly, those differ at every probe position, so a pure spelling difference
fragmented the grouping and every answer looked more ambiguous than it was. Fixed with a numeric
signature token — while keeping `bool` distinct, because `x > 0` returning `True` is not
`x > 0` returning `1`.

**Bug 2 — and this one was in my test, not my code.** I wrote a test asserting that
`(x // 1) * 2` and `(x * 2) / 1` were "the same, just spelled differently". It failed. They are not:
at `x = 1.5` they give `2.0` and `3.0`. The int/float confusion was real, but that pair was a genuine
behavioural difference wearing similar clothes, and using it as the example would have taught the
wrong lesson. The test now uses a pair that differs only in value spelling, and a separate test
asserts floor-division *is* a different explanation.

I had already "verified" the fix on integers only, where they agree. The probe range was the reason I
was wrong.

**Bug 3 — the probe range certifies the grouping, and it was integer-only.** I tried to construct two
bodies that agree on every integer probe and differ elsewhere. `x ** 2` and `int(x) * int(x)`: equal
at every integer in the list, and `2.25` versus `1.0` at `x = 1.5`. The range had no fractions.
Adding fractional probes fixed it — and immediately changed which witness the interrogation asks for,
from `x = -3` to `x = -3.5`.

> **A grouping claim is only as good as the range it was computed on.** The report now carries
> `grouping_basis` saying exactly how many probes and that the claim is bounded by them.

---

## 4. What this says about the creature

The capability added this round is small and precise: **it can now tell how many genuinely different
things its evidence permits, rather than how many sentences fit.** That sounds like bookkeeping. It is
not, because the two numbers have opposite failure modes:

- Overcount explanations, and the creature refuses to commit when it should (`PROVISIONAL` forever,
  asking questions whose answers it already knows).
- Undercount them, and it commits when it should not — which is the original defect, the one that
  produced `x*x` with total confidence.

Yesterday it was on the wrong side of that trade for the first reason. Both directions are errors, and
the interesting thing is that **the same probe range controls both**: too narrow, and different ideas
collapse into one (false confidence); too wide is never a problem for counting, only for truth. The
range under-counts confidence, never over-counts it, so the safe direction is a *larger* probe set —
which is the opposite of how I had been reasoning about grid size all session.

---

## 5. The honest bound

**Grouping is behavioural, not algebraic.** `(x / 1) + x` is grouped with `(x / 1) * 2` because they
agree everywhere I probed. Nothing here proves they *are* the same function; it proves they are
indistinguishable on 21 points. A pair that agrees on 21 points and differs on the 22nd would be
merged — and my own `int(x) * int(x)` construction is exactly that shape, caught only because I
thought to add fractions.

**The oracle is still the benchmark.** The value at `x = -3.5` was supplied by the harness. The
creature has learned to count its own uncertainty correctly; it has not learned to obtain the value.

**Cost still decides ties, and cost is a preference.** With explanations the tie is now between
*ideas*, which at least means something — but a cheaper correct-looking body is still preferred
without evidence.

**Non-claims.** No sentience. Pure Python over small numeric tuples; no I/O, no host execution, no
GUI. `DETERMINED` means the budget contained one explanation, never that the explanation is true.
`truth.achieved` stays false. $0 spent.

---

## 6. Ranked next moves

1. **Ask the world, not the harness.** The interrogation loop has a well-defined question format
   ("value at this input"); wire it to whatever observation surface the creature actually has, so the
   oracle is not me. This is the last piece of the loop that is still simulated.
2. **Probe selection instead of a fixed grid.** Fractions were needed and I did not know it until I
   tried to break my own grouping. Cheap version: choose probes that separate the surviving
   explanations maximally — which the code already computes for the *question*, but not for the
   *certificate*.
3. **Domain tracking instead of rejection** (carried over, still unbuilt).
4. Repair rather than discard a refuted concept; composition of invented concepts; the front door.
