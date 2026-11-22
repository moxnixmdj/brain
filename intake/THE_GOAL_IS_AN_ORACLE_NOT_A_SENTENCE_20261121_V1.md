# The goal is an oracle, not a sentence

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instruments:** `canonical/tools/gitchameleon_harness_v1.py`, `canonical/tools/hole_filler_v1.py`
**Benchmark:** GitChameleon 2.0, real, 328 items / 26 libraries, executable hidden tests

---

## 0. The contradiction this resolves

For two commits the instrument admitted a goal only as a predicate written by hand in a
`GOALS` dictionary. That dictionary is a part that should not exist: it is me, the engineer,
smuggling the answer in and then reporting that the system found it.

The resolution, and it is not a compromise: **in every real benchmark the goal already is an
executable check.** SWE-bench ships `fail_to_pass`. GitChameleon ships a hidden test. The
gate measures a post-state. Writing a natural-language goal and translating it into a
predicate was me *adding* a part and then having to invent the very thing the benchmark
supplies for free.

So the interface changes once, here:

> A goal is given as an oracle. The system's job is to find a call that the oracle accepts.
> Nothing in the system may contain a hand-written mapping from words to calls.

## 1. The oracle is real, and that was checked first

A harness was written and every claim below rests on it. On the 40 no-dependency
sympy/networkx items, **37/40 have an oracle that discriminates**: the stub fails and the
reference solution passes on a real interpreter. The 3 exceptions are networkx items whose
reference solution does not pass on networkx 3.6 — a version-pinning fact about the
benchmark, reported rather than hidden. `solution` is used **only** to prove the oracle
discriminates and is never read while scoring.

## 2. What the cheap, honest mechanism actually reaches: 3/40

`hole_filler_v1` derives a body from the item's own declared information — the stub's
incomplete shape, its return annotation, its parameters, the values the problem states — and
lets the oracle decide. Three strategies, no model, no stored world fact:

| strategy | derivation | solved |
|---|---|---|
| `close_expression` | stub is cut mid-call; close it with the value the problem states | 1 |
| `construct_annotated_type` | the return annotation names the class; call it with the stub's parameters | 2 |
| `forward_call` | the annotation names the symbol; forward the argument | 0 (superseded) |

**3/40 = 7.5%.** The frontier, on the whole 328-item benchmark, scores **51.2%** (o1, greedy)
to **59.4%** (Claude 4 Sonnet + RAG), with self-debugging worth a further 10–20 points. Our
number is measured on 40 items, not 328, and on the easiest library cohort — it is not
directly comparable, but the direction is unambiguous and it is not in our favour.

## 3. Why it stops there, stated precisely

The remaining 37 items need bodies such as:

```
list(G.edges)[0]
bellman_ford_predecessor_and_distance(G, source)
laplace_transform(eye(2), t, z, legacy_matrix=False)
parse_mathematica(expr).replace(Function("F"), lambda *x: Max(*x)*Min(*x))
PinJoint('pin', parent, child, parent_point=parent.frame.x, child_point=-child.frame.x)
```

Two measured facts explain the ceiling, and neither is a matter of trying harder:

1. **The stub stops declaring and starts describing.** Where the annotation names a type,
   we can construct it (that is the 2 items won). Where it names `list`, `tuple`, or `int`,
   the annotation carries no symbol and the derivation has nothing to work from.

2. **Identical prose, different answers.** Items 29 and 30 state *the same problem in
   identical words* — "Write a function that calculates the diameters' extreme distance of
   a graph" — and require `extrema_bounding(G, usebounds=True)` and
   `extrema_bounding(G, "diameter")` respectively. **The prose is not a function of the
   call, and the call is not a function of the prose.** No set of syntactic strategies can
   separate two items that read identically; only a test could, and the test only says pass
   or fail after the fact.

## 4. What this means for the constraint, stated without softening

To close that gap without a model you need one of two things:

- a **knowledge base mapping descriptions to calls** — which is exactly the memorised world
  knowledge the zero-knowledge-house constraint forbids in parameters; or
- a **search over the artifact's own surface**, driven by the test as the oracle, which
  turns `PinJoint('pin', parent, child, parent_point=parent.frame.x, ...)` into a search
  for a constructor signature, key names taken from the object's own attributes, and
  argument expressions taken from the parameters — a program-synthesis problem, not a
  lookup.

The second is legal under the constraints and is where the next unit of work must go. The
first is forbidden and would also be dishonest, because it would be the frontier's method
wearing our name.

## 5. Verified / unverified / failed

**Verified**
- The GitChameleon harness runs real items and its oracle discriminates on 37/40 no-dep items.
- A constraint-legal mechanism derives 3 of those 40 from the items' own declarations.
- Two strategies fire for real reasons, and their win conditions are understood.

**Unverified**
- Whether a search over the artifact's surface can reach the other 37. Not attempted yet; the
  item-29/30 pair suggests the oracle, not the prose, must drive the search, and that has not
  been built.
- Whether this cohort's rate predicts the full 328. It does not follow from 40 items.

**Failed**
- `GOALS`-style hand-written goals: removed as a part that should not exist.
- Reaching the items by adding syntactic forms: measured at 3/40, and the identical-prose
  pair shows why more forms cannot close it.

`truth.achieved` remains `false`. The next bottleneck is stated in §4 and is the only legal
route: **synthesis over the artifact's own surface, with the test as the oracle.**
