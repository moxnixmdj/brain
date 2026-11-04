# PRE-REGISTRATION — *The grammar can only express what a writer already knows*

2026-11-04, V1, round 23. Written **before** implementation, after measuring.
Base `499f731c1b` (= `origin/main`, round 21 merged). Authority `NONE`, `truth.achieved` false, $0.

---

## What this round measured first

Round 21 merged access. Round 22's note said the next defect was that "nothing is ever compressed" and
proposed library learning. Before building that, I measured the layer *above* it — and the correction
changes the plan.

### Measurement 1 — the general grammar cannot find the program that the writer emits

A period-3 block `[-2, 5, 1]` with 5 examples, asked of `_generate_candidate_expressions` alone
(growth disabled, so no writer, no structure diagnosis):

```
general grammar result: NO_CONSISTENT_HYPOTHESIS | ok= False
```

The successful program — `_block[int(x0) - int(x0/n)*n]` — is not in the reachable expression space.
It is **written** by `synthesize_table_organ`. Everything the creature "can do" about repeating
structures is a code path, not a search result.

This is the precise meaning of "static code" in this project: not a lookup table of answers, but a
**grammar whose reachable shapes are only those a writer was already written for**.

### Measurement 2 — the writer's bodies are identical, so library learning would learn one concept

```
induced_period_table_3  body=['Assign','Assign','Return']  -> return _block[int(math.floor(x0) - ...)]
induced_period_table_5  body=['Assign','Assign','Return']  -> return _block[int(math.floor(x0) - ...)]
induced_period_table_7  body=['Assign','Assign','Return']  -> return _block[int(math.floor(x0) - ...)]
```

Identical apart from the literal. So round 22's proposed "admit multi-statement bodies" would admit
three copies of one concept. Compression would then correctly find exactly one thing: *"this skeleton
is shared"*. One round of compression over a corpus of one skeleton is not a compounding library.

### Measurement 3 — a hardcoded organ is not a primitive

I registered an organ implementing the period-3 table as a grammar token, then asked for period 4:

```
with a table token in the grammar: NO_CONSISTENT_HYPOTHESIS
```

Of course: the token hardcodes period 3. A primitive that already knows the answer cannot be searched
with. What the grammar lacks is not a *token*, it is a **parametric node** — a table constructor whose
period and block are variables to be *solved*, not literals to be *emitted*.

### Measurement 4 — the cost floor, stated correctly

| structure | current evidence requirement | confirmed floor (2P) | ratio |
|---|---|---|---|
| period 3 | 12 | 6 | 2.0× |
| period 7 | 28 | 14 | 2.0× |
| period 30 | 120 | 60 | 2.0× |

`table_evidence_requirement(P) = 4P` is a constant, not a derivation. Confirming an unknown period needs
one full cycle to repeat (~2P). The remaining factor of 2 is slack, not structure. **No policy can go
below P observations** — the block has P free values and unseen residues are unknowable. So the probe
*cannot* be optimised into learning; only the constant can be tightened roughly 2×.

## The thesis, in one line

> The creature is static not because it fails to learn, but because **everything it can express was
> already named by a writer**. Learning over a language that cannot express the answer is not learning;
> it is recall of the author's foresight.

## What I will build

**A parametric table node in the general grammar.** Not a new writer: a constructor
`T(x, k, b0..b_{k-1})` that `_generate_candidate_expressions` can *propose*, with `k` and the block
derived from the evidence it already has, and which then competes in the existing version space on
equal terms with projections, affine forms and inlined organs.

The writer `synthesize_table_organ` should then become reachable **through search** rather than being
the only route. Concretely: with `growth_enabled=False` — no writer, no structure diagnosis — a
period-3 and a period-4 block must both be found by the grammar.

## Predictions — stated so they can fail

- **P1 (search reaches the shape).** With writers disabled, the general grammar returns a consistent
  hypothesis for a period-3 block, exact on held-out inputs never shown.
- **P2 (it generalises across periods).** The same, for periods 4, 5 and 7, from three examples each —
  no per-period code, no new writer per structure.
- **P3 (the writer becomes redundant for this class).** For those inputs, enabling growth cannot make
  the answer *better* than the searched one; if it differs at all, both must be exact on held-out.
- **P4 (no regression).** Every existing route and every previously-merged suite behaves as before,
  including the refusal of `x*x` and `x^3`, which must still refuse.
- **P5 (honest evidence accounting).** The number of observations stays a stated function of the
  structure, and the reported question count still matches what was asked.

**Explicitly NOT predicted:** that this makes the creature generally capable, or that anything
compounds across work items. The cost floor above says per-problem cost cannot compound for this class.
If I later claim otherwise, this paragraph is the record that I pre-registered it as false.

## Non-claims

- A parametric node is still **hand-designed**. This replaces one writer with one grammar rule. It is
  strictly less static (one rule instead of N writers, and the parameters are searched) but it is not
  "the creature invented its own language". The honest description is: *a smaller, parametric basis
  that search can compose*, not emergence.
- No sentience claim. `truth.achieved` false. `authority: NONE`. $0. No external models, no neural
  weights, no dynamic code execution in result-bearing modules.

## Why this is deeper than round 22's plan

Round 22 would have strengthened the machinery for compressing what writers emit — but the writers emit
one program shape, so there is nothing to compress into. The layer that governs everything downstream is
the **expressible set**. Widening it parametrically is the difference between a system that can be given
more capability and one that can search for it.
