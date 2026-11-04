# Pre-registration: refuse to commit when the evidence cannot distinguish

**Written before implementing. 2026-11-04 · authority NONE · `truth.achieved` false**

## The defect, read from the code

`_try_register` in the synthesizer does:

```python
if sig == target_sig:
    return expr_src          # <- first match wins, and the search stops
```

and separately dedupes the bank by **output signature over the supplied inputs**:

```python
if sig not in seen_sigs:
    seen_sigs[sig] = expr_src
```

So two candidates that agree on the supplied inputs are treated as *the same thing*. The bank
literally cannot represent "these two different programs fit the data equally well". The first one
found is returned as though it were the answer.

Measured, from the previous round: `return (x * x)` and `return (x + x)` both reproduce the three
teaching examples of `2x`. The creature returned one of them. It had no way to know it had chosen.

This is the bottleneck. Six rounds have improved the error structure around the search; the search
itself commits without knowing whether it was entitled to.

## What "the evidence cannot distinguish" means here

For a set of input/output examples and the synthesizer's grammar, a body is **admissible** iff it
reproduces every example. The evidence is **insufficient** iff more than one admissible body exists.

That is checkable without an oracle: enumerate admissible bodies, count them. If the count is 1 the
commitment is forced; if it is >1 the creature chose arbitrarily.

## Predictions (falsifiable, stated before the run)

**E1.** Three examples are usually underdetermined: for the problem set used in the previous round,
more than one admissible body exists for most of them.

**E2 (the payoff).** The `x*x` case is exactly an ambiguity, and it is visible without knowing the
answer: `x*x` and `x+x` are both admissible, so the examples cannot distinguish `2x` from `x²`. The
creature should be able to *say* this. I predict the audit failure from last round becomes a
detectable phenomenon once ambiguity is enumerated.

**E3.** Adding a disambiguating example collapses the admissible set, usually to 1. I predict one
extra example is enough for the `x*x` case.

**E4 (the honest bound).** Uniqueness is not correctness. If the true function is outside the
grammar, exactly one admissible body may exist and still be the wrong function. I predict I can
construct such a case, and I will not claim uniqueness implies truth.

**E5 (what the creature should do).** On ambiguity it should prefer the simpler body by an explicit,
stated cost and mark the answer PROVISIONAL — not silently return the first. I predict this changes
at least one answer relative to first-match, and that the change is toward the simpler hypothesis.
