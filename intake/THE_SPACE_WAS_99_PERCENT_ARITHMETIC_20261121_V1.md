# The space was 99% arithmetic — removed, and the score did not move

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

---

## 0. One measurement explained five failed experiments

For `sympy.Equality`, whose type exposes **177 attribute paths**, the generator produced:

```
APPLY        1
PATH       177
WRAP        96
LEAF         1
OP     99,725        <- 99.7% of the entire space
```

The `OP` block was `itertools.permutations(other_paths, 2) × 7 operators` = **95,823 bodies**.
Every cap in the pipeline — 600, 2500, whatever — therefore truncated the space to **arithmetic**,
and every ordering experiment in the previous four receipts was fighting that single fact:

- cheap-first reordering moved `eq.lhs - eq.rhs` 169 → 514 and lost `Matrix([first, second])`;
- lifting statements above the grid gained 33/34 and lost 187 and 192;
- quota-sampling put four of six target bodies in the first 70 and still lost two items.

None of those were ordering problems. They were all the arithmetic flood reasserting itself
through a different doorway.

## 1. The fix, and what it cost

`itertools.permutations(other_paths, 2)` is **removed**. The bounded `short[:12]` adjacent grid
already covers the real cases, because the useful members are the short ones — `lhs`, `rhs`,
`base`, `exp` — not `as_content_primitive`.

Every target body now co-exists inside the 600-candidate budget, which was previously impossible:

| item | body | position |
|---|---|---|
| 33 | `list(G.nodes)` | 12 |
| 34 | `list(G.edges)[0]` | 11 |
| 187 | `eq.lhs - eq.rhs` | 331 |
| 190 | `RigidBody(a), Particle(b)` | 100 |
| 191 | `index.free_symbols` | 82 |
| 192 | `Matrix([first, second])` | 66 |
| 199 | `n % p == 0` | 50 |

## 2. The honest result: the score did not change

| | before | after |
|---|---|---|
| sympy | 19/32 | **19/32** |
| networkx | 2/8 | **2/8** |
| total | 21/40 | **21/40** |

The space is roughly **400× smaller** and nothing was lost. That is a real simplification — the
kind the "best part is no part" rule asks for — but it is **not a capability gain**, and
reporting it as one would be dishonest.

What it does buy is headroom: with arithmetic no longer occupying 99.7% of the budget, the
remaining structural classes (nested cross-parameter reads, member calls, compositions over
literals) can be added without displacing anything, which was not true before.

## 3. Where this stands

```
sympy      19/32   no-dependency cohort
networkx    2/8    never tuned
total      21/40   42 tests passing, ~160 s, zero model calls, zero network
```

Held-out on sympy (weights fitted on 13 items, never on the remaining 19): **14/19**.

**This is not a benchmark score.** The published 51–59% figures are on all 328 items across 26
libraries with dependency pinning. A 40-item two-library no-dependency subset is easier and
smaller, and no comparison to those numbers is honest.

## 4. Next bottleneck, precisely

With the flood gone, the largest remaining class is **nested cross-parameter reads** (181, 182,
189 — `parent.frame.x`) and **member calls whose name the prose never states** (188, 194 —
`to_list`, `todok`). The first is a grammar gap with a known shape. The second is the
meaning→name convention in its pure form and is the only class in this whole chain that no
run-time derivation has ever touched.

`truth.achieved` remains `false`.
