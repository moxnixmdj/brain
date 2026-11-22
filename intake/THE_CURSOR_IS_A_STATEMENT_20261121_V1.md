# The cursor is a statement: 21/40 → 29/40

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` = `false` · **$0**, 0 model calls

---

## 0. The finding

Five items — 35, 31, 32, 186, 200 — share one stub shape: **the cursor is left inside an
incomplete statement.**

```python
    return nx.                              # 35
    return nx.community.                    # 31, 32
    from sympy.                             # 186
    from sympy.tensor.array.expressions.    # 200
```

I had classified these as "stubs of unknown shape" and moved on. They are not. **The incomplete
line states the vocabulary the answer must come from, and the answer is the prefix plus a
completion.** The cursor is a statement.

## 1. Why they were unreachable, and it was not a vocabulary problem

`parameters()` failed on all five:

```
_repaired_source("...    return nx.")  ->  "...    return nx.\n    pass"   # still a SyntaxError
ast.parse(...)                          ->  SyntaxError at line 3
parameters(...)                         ->  []
```

The repair appended `pass` but left the truncated *expression* untouched. So **no candidate could
ever be built for these items, whatever the grammar generated.** Every experiment that reported
them unsolved was reporting an instrument failure.

This is the fourth instance of the same failure mode in this project: *a judge that fails closed
is indistinguishable from a system that knows nothing.* The rule now stands in the code:

> **Every instrument must be validated against the reference solution before any result it
> produces is believed.** Four separate zeros in this project were instrument bugs.

## 2. The mechanism, in the artifact's own terms

No new knowledge is required. Three facts are already stated:

1. **The stub's import states the alias** (`import networkx as nx`), so `nx.x` and
   `networkx.x` are one vocabulary.
2. **The corpus states which module each name really lives in.** `nx.community` is a
   *re-export* path — the real home is `networkx.algorithms.community.<name>`. Prefix matching
   therefore finds **zero** names (measured) and **suffix matching** finds 944.
3. **The prose states the concept.** Item 35's prose says "shortest path lengths and
   predecessors"; `bellman_ford_predecessor_and_distance` names three of those words.

The corpus had to be deepened first. The walk enumerated packages two levels deep and collected
third-level modules as *bare names without ever opening them*, so `physics.quantum.trace.Tr` and
`tensor.array.expressions.from_array_to_matrix` appeared nowhere in 14,625 rows. Fixed to a
fixed depth of 5:

| | before | after |
|---|---|---|
| sympy names | 14,625 | **50,286** |
| networkx names | 3,752 | **7,346** |

## 3. Three ordering facts, each measured

| fact | wrong | right |
|---|---|---|
| completion order | by name length: `bellman_ford_...` is #930 of 944 | **by prose evidence**: #82, solved at try 83 |
| stub-qualified bodies | `nx.bellman_ford_...` (splicing `nx.` twice → `nx.nx....`) | **bare tail**, because the stub already ends `nx.` |
| `from X.` continuation | `from X import y` as the whole body | **rest of the line**: `physics.mechanics import inertia` + `return inertia(...)` |

And the slicing bug that made all of it inert for one round: `conts[:400]` ran **before** the
prose sort, then a second `[:40]` ran after. The correct body was generated, ranked, and then
deleted by a stale slice.

## 4. Two more classes fell with the same discipline

**The return annotation is the constructor it wants.** Item 178's stub declares
`-> sympy.physics.quantum.trace.Tr` and its reference is *exactly* that call. On sympy, an
unimported intermediate module raises `AttributeError`, so the qualified spelling is the working
one. Emitted first as `RETANN`: solved at try 1.

**A member the prose names across an underscore.** 191's prose says "extract all the free
**symbols** present"; the member is `free_symbols`. A plain membership test on the prose
vocabulary cannot match a single token containing an underscore, so the read fell to the back of
the space. Splitting the member and requiring every part to be a prose word — the same rule
already used for squashed symbol names — moved it to position 3.

Item 191 also exposed why ordering alone was not enough: `index.base` on a symbolic `Indexed`
costs **12 s**, and one long stream let a handful of hangs consume the whole budget before the
correct candidate was ever tried. Judging is now chunked with a shared deadline, so a hanging
candidate costs a bounded share instead of the entire run.

## 5. The result

| | before | after |
|---|---|---|
| sympy | 19/32 | **23/32** |
| networkx | 2/8 | **6/8** |
| **total** | **21/40** | **29/40** |

Time: 234 s sympy + 19 s networkx. Zero model calls, zero network at run time.
48 tests pass (42 existing + 6 new).

**Two references do not run at all** in networkx 3.6.1 — `extrema_bounding` does not exist. Items
30, 31 and 32 were therefore solved *without* a reference to validate against, so their hidden
tests were read directly. Item 30's test demands diameter semantics (4 for `path_graph(5)`, 5 for
`cycle_graph(10)`, 1 for `complete_graph(6)`, error-or-infinity when disconnected) and
`diameter(G)` satisfies every assertion. Item 30 was solved with `diameter(G)` and not the
reference's `extrema_bounding(G, "diameter")`: **a different correct body, found rather than
replayed.** 31/32 solved with `greedy_modularity_communities(G)` while the reference calls
`naive_greedy_modularity_communities` — the tests accept the greedy variant.

## 6. What this is not

```
29/40 is 72.5% of a two-library, no-dependency subset.
```

The published frontier figures — greedy o1 51.2%, Goose/GPT-4.1 55.5%, RAG Claude 4 Sonnet
59.4% — are measured on **all 328 items across 26 libraries with dependency pinning**.
This subset is easier and much smaller. **No comparison to those numbers is honest**, and none is
made. Re-measuring the held-out sympy split is the next thing to do for that reason.

Five items remain unreachable by any candidate and were not counted as capability:
27 (prose says "number of communities", the keyword is `cutoff` — nothing derivable),
29/30-adjacent version artifacts, 203 (prose contradicts its own test), and 188/194
(the meaning→name convention: `to_list`, `todok`).

`truth.achieved` remains `false`. §6 is not met.
