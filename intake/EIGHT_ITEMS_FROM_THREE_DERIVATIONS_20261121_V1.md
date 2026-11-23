# Eight items from three derivations — 21/40 → 29/40

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

| | before | after |
|---|---|---|
| sympy | 19/32 | **23/32** |
| networkx | 2/8 | **6/8** |
| total | 21/40 | **29/40** |

New: 178, 186, 191, 200, 30, 31, 32, 35. **No regressions.** 42 + 7 tests pass. Cohort time 253 s.

---

## The limiting factor was not the grammar

Five items (35, 31, 32, 186, 200) were labelled "open-call stubs, out of scope by construction".
That was wrong, and the reason it was wrong is worth stating precisely:

```
stub:      def f(G:nx.Graph, source:int) -> list:\n    return nx.
repair:    ... return nx.\n    pass          <- still a SyntaxError
result:    parameters() == []  and  annotation_spec() == {}
```

`_repaired_source` balanced brackets and appended `pass`, but a **truncated expression** is not
a bracket problem. `ast.parse` failed, `parameters()` returned `[]`, so `compositions()` was
called with **no arguments and no types**. Those five items were unreachable for every candidate
the system could ever generate — no grammar change could have touched them.

The fix is one rule: a trailing `return X.` or `from X.` is a truncated expression and loses its
final character. A bare `from X` is *never* legal Python, so it becomes a placeholder import
(the real import is what the body supplies).

## The three derivations

**1. The stub's incomplete line states which continuation is missing.**

`return nx.` states a vocabulary. The stub's own `import networkx as nx` states the alias, so
`nx.` and `networkx.` are the same namespace — that is a statement, not knowledge. `nx.community.`
is a *re-export* path with **zero** names under it in the corpus; the real home is
`networkx.algorithms.community.*`, so matching has to be on the path **suffix**. The body is the
**bare** tail, because the oracle splices `starting_code + body` and `nx.tail` would produce
`return nx.nx.tail`.

`from sympy.` states an import continuation. The corpus already knows each member's **full dotted
path**, so `conv_array_to_matrix import convert_array_to_matrix` (item 200) — a module name this
project never contained — is read off the artifact's own layout.

**2. The return annotation is the constructor it wants.** Item 178 declares
`-> sympy.physics.quantum.trace.Tr` and its reference is *exactly* that, spelled out. On sympy an
unimported intermediate module raises AttributeError, so the qualified call is the only passing
form. Emitted first, because an annotation is a statement.

**3. A member named in prose across an underscore is stated.** The prose says "extract all the
free **symbols**"; the member is `free_symbols`. A plain membership test never matched, so the
read fell behind 50 candidates — and `index.base` on a symbolic Indexed **hangs for 12 s**, so
those 50 exhausted the worker and `free_symbols` was never tried. Splitting the member on
underscores and requiring every part to be a prose word is the same rule already used for
squashed symbol names (`isprime`), applied to members. 191 now solves at try **3**.

## Two more measured facts, both about budgets

- **A hanging candidate starves a single stream.** One stream of 600 on item 191 timed out at
  300 s without reaching position 50. Judging in chunks recovers it.
- **A chunk budget that is re-granted is not a budget.** `min(per_chunk*4, oracle_timeout)`
  evaluates to the full timeout every time; `per_body_seconds*chunk + 5` lets one hanging chunk
  eat the whole deadline. The bound has to be the per-body allowance times the chunk, with the
  deadline shared across chunks.

## The remaining 11, classified honestly

| cause | items | note |
|---|---|---|
| benchmark defect | 203 | the correct reading is marked wrong; not solvable by construction |
| vocabulary gap in the prose | 27, 185 | "number of communities" → `cutoff`; "integer representation" → `to_int` |
| nested read / constructor over four parameters | 181, 182, 186*, 189 | |
| composition over a constructed literal | 177, 180 | |
| member named only by meaning | 188, 194 | "dictionary-of-keys" → `todok` |
| version artifact | 29 | `extrema_bounding` absent from networkx 3.6.1 |

\*186 solved. 30 solved as `diameter(G)` — a **different correct body** from the reference, found
not replayed.

**29/40 is 72.5% of a 40-item two-library no-dependency subset. It is not a benchmark score**
and is not comparable to the published 51–59% on all 328 items across 26 libraries.

`truth.achieved` remains `false`.
