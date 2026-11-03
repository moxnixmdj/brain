# Two Programs That Mean the Same Thing

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

This is the fourth attempt at the user's question — *is this the smartest approach?* — and the
first one that changed my mind about something I wrote down yesterday rather than adding a
mechanism on top.

---

## 0. What I said yesterday, and what was wrong with it

Yesterday's writeup ended with a limit stated as a fact:

> It can **reuse** what it wrote. It cannot **notice that two different programs mean the same
> thing.**

The second clause was true. The *diagnosis* attached to it — that the organ needs literal shared
syntax, full stop — was incomplete in a way that mattered, and I only found out by building the
thing that was supposed to fix it. Admitting a concept has **two** gates in sequence:

1. **a shared-subtree gate** — the same canonicalised subtree must appear at ≥ 2 sites;
2. **a compression gate** — the induced definition must pay for itself, in bytes (`ΔB_exec < 0`)
   and under the exact Stitch node law `(k−1)·|E| − (k+1)·arity − (k+2) > 0`.

Yesterday I measured gate 1 failing and called it "the limit". Gate 2 was invisible because my
probe corpora were pairs. Measured today, for the 9-node concept `max(a,b) − min(a,b)` with arity 2:

| sites | stitch law | verdict |
|---|---|---|
| 2 | −1 | REJECT |
| 4 | +11 | pass |
| 11 | +53 | pass |

So for a two-program corpus, gate 2 was **already** fatal no matter how perfect the syntax match.
My "shared syntax" probe could not distinguish "needs syntax" from "needs syntax *and* volume".
That is the same instrument error as the `10**6` penalty constant and the confounded GROWN arm:
**the answer was in the design, not the data.** Yesterday also claimed the `signed_distance` rung
was a real test of semantics; it was not — `abs` is native to the synthesizer's bank, so a concept
built from `abs` has zero headroom and could never show a gain. I removed that claim.

---

## 1. The mechanism

`canonical/swe_kernel/semantic_unification_v1.py` (new). It finds pairs of **structurally
distinct** expressions from **different** programs that agree on a probe vector of
`(0,1,2,3,5,−1,−3,7,10)`, and returns the correspondence with witness values. It uses the
repository's own zero-`exec` evaluator (`eval_pure_ast_expr`) — a match is an observation, not a
claim about algebra. A disagreement anywhere vetoes the pair. Agreement is necessary, never
sufficient, and the asymmetry is deliberate: a false "different" costs one missed concept, a false
"same" injects a wrong concept into the grammar that every later program inherits.

| pair | as written | result |
|---|---|---|
| `max(p,q) − min(p,q)` vs `abs(s−t)` | no shared syntax | **1 correspondence, EXACT, 81/81 probes** |
| `(p+q)/2.0` vs `s/2.0 + t/2.0` | no shared syntax | **1, EXACT** |
| `100.0*p/q` vs `(p/q)*100.0` | no shared syntax | 1, **UP_TO_REPRESENTATION** (13/81 differ by 1 ulp) |
| `max(0.0,min(1.0,p))` vs the ternary chain | no shared syntax | 1, UP_TO_REPRESENTATION |
| `p*q` vs `s+t` | unrelated | **0** |
| `p > q` vs `s−t` | bool vs number | **0** |

---

## 2. Three bugs in my own instrument, all found by the traps I planted

I want these on the record because each one would have produced a confident wrong answer.

1. **Variable renaming passed as meaning.** `p` and `s` "agreed on 9 probes" — because both were
   bound to the same probe value. Two *unrelated* programs (`p*q` vs `s+t`) reported four
   correspondences. Fix: a correspondence must involve structure (an operator or a call), or it is
   just renaming.
2. **Float representation passed as difference.** `100.0*p/q` vs `(p/q)*100.0` disagreed in 13 of
   81 probes by one unit in the last place — float multiplication is not associative. My exact
   `repr` comparator called that a semantic difference. Fix: graded verdict
   `EXACT` / `REPRESENTATION` (1e-12 relative) / `DISAGREE`, recorded per pair rather than hidden.
3. **`int` vs `float` passed as difference.** `0.0` vs `0` killed the clamped-interval match. Fix:
   numeric coercion — with `bool` explicitly excluded, since `True == 1` in Python and a comparison
   result silently standing in for a number is exactly the false positive I was trying to avoid.

Plus a direction bug in the bridge: I renamed the wrong side, so the needle never appeared and
every trial honestly reported `REWRITE_CHANGED_NOTHING`. The instrumentation said "nothing
happened" and I nearly believed it.

---

## 3. Does it buy anything? Three arms, swept over corpus size

`canonical/tools/semantic_join_benchmark_v1.py` (new, re-runnable, `--json`). One concept that is
genuinely absent from the bank — a clamped normalisation — taught from programs written one way,
the same programs with half re-spelled, and the same corpus with the second half **rewritten
through a verified correspondence**.

```
sites per spelling: 4
arm                admitted  library   held-out   median ms
all_one_spelling          2        2       1/2       352.7
two_spellings             1        1       1/2       349.1
bridged                   2        2       1/2       355.7
  concept_is_learnable               YES
  join_increases_admission           YES
  join_fully_restores_control        YES
  join_improves_held_out_reach       no
```

At 6 and 8 sites per spelling, each spelling amortises its own definition and all three arms
admit 3 concepts — the join has nothing to repair. Below ~4 sites nothing amortises at all.

**What the join actually does:** it makes one concept cover a corpus written two ways, so a thin
corpus does not pay twice for the same idea. **What it does not do:** it does not improve held-out
reach, at any corpus size — and the reason is structural, not a tuning problem. A concept is a
*callable*: once it exists, the synthesizer can emit `concept_ab12(x, y)` in a program of either
spelling, because the concept's body is a single expression the search never has to re-derive.
Re-spelling was never what blocked synthesis. It blocked **learning**.

That is the real correction to yesterday. "It cannot notice two programs mean the same thing" was
right about the corpus and wrong about the consequence: fixing it buys compactness and one fewer
paid definition, not new reach.

---

## 4. Where the reach does come from — and the limit I still cannot explain

The genuine reach gain measured yesterday (clamped-interval problems, 4/5 → 5/5, 2.9× faster)
came from the concept existing at all, not from any equivalence. But re-testing the
`signed_distance` rung today gave **no reach gain at any weight (3–6)**, and the reason is that
`abs` is native: `|a−b| + 5` was already reachable without a concept. So that rung measured
nothing and yesterday's numbers for it should not be quoted as support.

The honest state of the reach claim:

- **clamped normalisation** — the concept carries information the bank lacks (a clamp applied
  before dividing). Reach gain measured. Not native.
- **signed distance** — `abs` and `max`/`min` are native. No headroom. Nothing to learn.
- **held-out + 0.5** — still 1/2 in every arm, including with the grown library. I do not have an
  explanation for this that I trust, so I am not going to write one. It is the open question.

---

## 5. What this does and does not say about a sentient-like creature

The user's actual target is a creature, not a benchmark. So, plainly:

**What got stronger.** There is now a mechanism that takes two pieces of knowledge that *look*
unrelated and recognises they are the same piece of knowledge. That is a real cognitive primitive —
analogy — and it is measured, not asserted: 81/81 probe agreement on a pair with no shared syntax,
with three traps that must stay silent and do.

**What did not.** Recognition is not understanding. The mechanism compares values on a finite
probe vector I chose; it has no notion of *why* the two expressions agree, cannot construct an
algebraic argument, and would accept a pair that agrees everywhere I looked and diverges where I
did not. It found the analogy; it cannot explain it. And the analogy did not make the creature
able to *do* anything it could not already do — it made it cheaper, which is why the held-out
column refuses to move.

**Non-claims.** No sentience. No credit. Pure Python over small numeric tuples; no I/O, no host
execution, no GUI; nothing here bears on reaching a shell or a browser, which remain gated.
`truth.achieved` stays false. $0 spent.

---

## 6. Ranked next moves

1. **Explain the 1/2.** The held-out `+ 0.5` case is a concrete, bounded mystery: the concept
   exists, the search can call it, and it still does not reach. Either the bank's weight accounting
   is wrong, or the reach threshold is higher than I measured. This is the only item where I have a
   result I cannot account for, which makes it the most informative thing to do next.
2. **Composition of invented concepts** — two-away problems, still untested. This is the only route
   to compounding-on-compounding.
3. **Concept invention on the primary path.** It still lives behind a cognitive-core buffer, not the
   front door. A mechanism that only runs in a benchmark is not part of the creature.
4. Backlog. Still last.
