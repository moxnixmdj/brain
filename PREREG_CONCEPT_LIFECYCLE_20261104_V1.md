# Pre-registration: a concept library that can be wrong about itself

**Written before implementing. 2026-11-04 · authority NONE · `truth.achieved` false**

## What was measured (already, before any change)

1. `record_concept_outcome(cid, helped=False)` is **never called anywhere in the codebase**.
2. The synthesizer calls `record_concept_outcome(cid, helped=True)` for every concept helper it
   materialises into a returned body — at the moment the body is emitted, which is *before* anyone
   knows whether the body is right. So `verified_hits` records emissions, not verifications.
3. `log_prior = log1p(verified_hits * 2 + corpus_sites + 1)`. No term can lower it. Measured: 50
   recorded failures left it unchanged at 2.8904.
4. The synthesizer only ever sees the **top 16** concepts (`ordered_concepts[:16]`), ordered by
   `log_prior`. Measured: injecting 20 concepts whose only advantage is a higher `corpus_sites`
   filled all 16 slots — 16 junk, 0 real — and generalising reach fell from **2/2 to 0/2**.

So the organ accumulates and never revises. Its history is a ratchet, and a wrong concept that
simply *survives* crowds out a right one. This is the structural reason the system cannot stop
being static: nothing it learns can be demoted or retired by its own record.

## The change under test

- `verified_hits` may only rise on an outcome someone could check, not on emission.
- A concept gains `disconfirmations`, which lower `log_prior`.
- A concept with `disconfirmations >= 3` and `verified_hits == 0` is **retired**: not offered to
  new searches.

## Predictions (falsifiable, stated before the run)

**P1.** After ≥ 3 disconfirmations with 0 verified hits, the junk concept is no longer offered, and
the top-16 window contains real concepts again.

**P2.** Emitting a body no longer increments `verified_hits`. The forged junk concept's
`verified_hits` stays 0 regardless of how many bodies mention it.

**P3 (the important one).** With 20 junk concepts present and **no** disconfirmation, reach stays at
**0/2**. Recovery happens only when disconfirming evidence is supplied.

> P3 is what separates *learning* from *forgetting*. If reach recovers without any evidence — on a
> timer, on a use count, on recency — then the mechanism is decaying, not learning, and it must be
> reported as decay. I predict no recovery without evidence.

**P4.** Retiring a concept must not corrupt previously emitted bodies: `callable_map()` still
resolves a retired concept's callable, so nothing that was already built breaks.
