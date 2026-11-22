# Two libraries, two judge bugs, and an honest generalisation number

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Tests:** 42 passing

---

## 0. The first real generalisation test, and what it taught

Everything in this chain was measured on sympy. Networkx is the honest test: **8 no-dependency
items, none of it tuned on.** The first run scored **0/8**.

That was not a capability result. It was two instrument bugs:

1. **The hidden tests import differently.** sympy tests do `from sample_N import f`; networkx
   tests do `import sample_N` and then call `sample_N.f(...)`. My worker installed a mock module
   carrying only the bare function, so `from ... import f` worked and `sample_N.f` did not.
   Every networkx item returned `worker_failed`.
2. **`_module_name` only matched `from sample_N import`.** Fixed to accept `import sample_N`.

After both fixes, `list(G.nodes)` and `list(G.edges)[0]` pass in isolation.

## 1. The generation gap

Passing in isolation is not the same as being found. Both bodies are **a member of the
parameter read and wrapped**, and the member name (`nodes`, `edges`) is not a module-level
symbol — no symbol surface can reach it. The declared type states it, though.

One rule was added, and only one: emit `list(param.member)` and `list(param.member)[0]` for
the shortest members the declared type exposes, placed **before** any arithmetic.

| library | before | after |
|---|---|---|
| sympy | 19/32 | **19/32** (no regression) |
| networkx | 0/8 | **2/8** |

Item 33 solved with `list(G.adj)` — a **different correct body** from the reference's
`list(G.nodes)`. That is the strongest single piece of evidence in this chain that the mechanism
is not replaying: it found an answer the benchmark author did not write.

## 2. What I tried and rejected, with measurements

I attempted five separate orderings of the composition space. Each traded one item for another,
and I recorded why rather than keeping whichever looked best:

| attempt | result |
|---|---|
| cheap-first reordering by kind | `eq.lhs - eq.rhs` 169 → 514; `Matrix([first, second])` **lost** |
| lift statements above the offset grid | 33/34 gained, 187 and 192 **lost** |
| quota-sample the combinatorial kinds | statements near front, but APPLY cut before generation |
| hoist WRAP to the front | 33/34 at position 11, 192 absent *in my harness only* |
| hoist APPLY | no change — 192 was never broken; my harness omitted `stated_symbols` |

The measured cause of all five: **`OP` is 99,725 of 100,000 generated bodies** for a type with
177 attribute paths. Any cap truncates the space to arithmetic. The honest fix is to quota-sample
combinatorial kinds *at generation time*, which I prototyped and measured — it put four of six
target bodies in the first 70 — but it cost 187 and 192 when combined, so it is not in the tree.

**This is the clearest remaining design problem in the chain**, and it is now precisely stated:
the space is dominated by a kind that is almost never the answer.

## 3. Where the numbers actually stand

| cohort | solved | of |
|---|---|---|
| sympy, no-dependency | 19 | 32 |
| networkx, no-dependency | 2 | 8 |
| **total** | **21** | **40** |

Held-out split on sympy (weights fitted on 13 items, never on the rest): **14/19**.

**None of this is a benchmark score.** The published 51–59% figures are measured on all 328
items across 26 libraries with dependency pinning. A 40-item no-dependency two-library subset is
a different, easier, much smaller distribution, and no comparison to those figures is honest.

## 4. The 19 unsolved, classified

| class | items |
|---|---|
| benchmark defect (prose contradicts its own test) | 203 |
| version artifact (`extrema_bounding` does not exist in networkx 3.6.1) | 29, 30 |
| needs a nested cross-parameter read (`parent.frame.x`) | 181, 182, 189 |
| member call whose name the prose never states | 188, 194 |
| composition over a constructed literal | 177, 180 |
| open-call stub (mid-call, missing argument list) | 27, 31, 32 |
| relative-import path | 186 |
| unclassified | 178, 185, 191, 200, 35 |

Only **188, 194, 185 (and arguably 178)** are the meaning→name convention in its pure form. The
rest are structural gaps in the grammar, known shapes, or benchmark artifacts.

`truth.achieved` remains `false`. The next bottleneck is the one measured in §2: **the body
space is dominated by arithmetic, and the answer is almost never arithmetic.** Quota-sampling at
generation time is the fix, and it needs to be done without displacing the statements.
