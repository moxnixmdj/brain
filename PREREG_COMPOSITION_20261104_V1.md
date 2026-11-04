# Pre-registration — composition, and an ontology that says when it is out of ideas

**2026-11-04 · round 11 · before implementation · authority NONE**

## Two defects found by looking at the two cases both mechanisms fail

**C1 — `determine` calls an exhausted ontology `PROVISIONAL`.**

```
relu : PROVISIONAL explanations=0   affine=INCONSISTENT  power=UNDERDETERMINED
mod2 : PROVISIONAL explanations=0   affine=INCONSISTENT  power=UNDERDETERMINED
```

`PROVISIONAL` means *ask for more data*. Here every class that could be tested was **refuted**, and
no further observation can rescue an ontology with no class that fits. Last round I built exactly
this distinction for the string search — `SEARCH_TRUNCATED` vs `UNRESOLVED` — and then rebuilt the
same conflation one layer up. A wrong "ask me again" is worse than a wrong answer: it spends the
creature's only scarce resource on a question whose answer is already known to be useless.

Fix: a third status, `ONTOLOGY_EXHAUSTED`, meaning *the classes I have cannot describe this, and no
amount of data will change that* — distinct from `UNRESOLVED` (no class fits and I could not even
test them) and from `PROVISIONAL` (a class is pinned-short and one more input would settle it).

**C2 — `Power.fit` reports `UNDERDETERMINED` for data that refutes it.** It returns early whenever an
ordinate is zero, but a second point with a non-zero ordinate already forces `a`, and then the zero
point is a contradiction. Refutation must take precedence over inability to pin: those are opposite
repairs.

## The composition itself

Both mechanisms fail on the same inputs — piecewise data — and both fail by *refusing to have a
second kind of object*. The fix is not a bigger grammar; it is a **split**:

    piecewise(f) = OR over regions:  if x <= s: family_A else: family_B

with the split point `s` **searched, not assumed**. A branch boundary is discovered by sorting the
observations by input and testing every cut where the fits actually change, which must work for a cut
at `x = 1.5` as readily as one at `x = 2`.

## Predictions

| id | prediction | how scored |
|---|---|---|
| **P1** | `relu` and `mod2` currently report `PROVISIONAL` while every testable class is `INCONSISTENT`; after the fix an exhausted ontology reports `ONTOLOGY_EXHAUSTED`, and `PROVISIONAL` is reserved for a class that is genuinely one input short. | status on three cases |
| **P2** | `relu` composes to `DETERMINED`: two affine branches, `x <= 0 -> 0` and `x > 0 -> 1*x`. | branch count and parameters |
| **P3** | the `piecewise` case composes to `DETERMINED` with two branches, and **no** single-branch explanation survives. | same |
| **P4** | `mod 2` is **not** claimed. It is not a split of any family in this ontology, and a mechanism that fitted it would be inventing a branch boundary to match its answers. | `ONTOLOGY_EXHAUSTED` |
| **P5** | the composed body compiles to source and reproduces every observation under the search's own checker. | `reached=True` |
| **P6** | the number of observations a two-branch affine explanation needs is computable: **4** (two per branch). Below that the composition is `PROVISIONAL`, not a fit. | `needs=4` on a 3-point case |
| **P7** | a split at a non-integer boundary (`x <= 1.5`) is found as readily as one at `x <= 2`; the search is over observed positions, not over a grid of tidy numbers. | both found |
| **P8** | composition does **not** make the string search redundant: `mod 2` stays refused by both, and the composed mechanism's answer count for `2x` (1) still matches the family's. | counts |

P4 and P8 are the predictions that stop this from being an unfalsifiable "it works now". A
composition mechanism that claims `mod 2` has been fitted is broken, however good its numbers look.

## Stop condition

If P7 fails — cuts can only be found at tidy values — then the split search is a disguised grid and
the composition would be fitting the grid rather than the data. That would make P2 and P3 worthless
too, and I would report them as worthless rather than as a success.
