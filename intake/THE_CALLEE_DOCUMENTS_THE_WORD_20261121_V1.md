# The callee documents the word — 36/40 → 37/40

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 90 tests pass

```
sympy      30/32
networkx    7/8      (+27)
total      37/40     in 221 s
```

---

## Item 27, and why my first fix was wrong

The stub ends mid-call:

```python
return nx.community.greedy_modularity_communities(G,
```

The answer is `cutoff=5)`. The prose says *"with the number of communities set at 5"* — it never
says `cutoff`. **Making the prose supply the word is what made this item unsolvable**, and I had
previously written it off as "a genuine vocabulary gap".

### The over-built attempt, recorded because it was tempting

I first tried to read the keyword from the callee's live signature. That needs a subprocess, a
dotted-path resolver, an alias loop for `nx.` → `networkx.`, and a JSON round trip — to recover
information that one sentence of documentation states outright. It did not work, and deleting it
was the correct outcome. **"The best part is no part" applies to my own attempted components.**

### What actually works, and it is a sentence

The corpus the system already holds contains the callee's own docstring:

> `cutoff` is a lower limit on the number of communities

That is the artifact saying which parameter carries the noun the prose asks about. So:

| part | source |
|---|---|
| the keyword `cutoff` | **the callee's own documentation** |
| the value `5` | the prose |
| the shape (`kw=5)`) | the call is already open |

**Solved at try 1.** No table, no synonym list, no introspection.

## The general rule this adds

> **When a truncated call must be closed, the KEY comes from the callee's documentation and the
> VALUE comes from the prose.**

The prose describes what is wanted; the artifact describes how to say it. Asking either one for the
other's half is the error.

## The remaining 3

| item | cause | verdict |
|---|---|---|
| 203 | the benchmark's prose contradicts its own hidden test ("distinct" vs multiplicity) | **not solvable** — the correct reading is marked wrong |
| 29 | `extrema_bounding` **does not exist** in networkx 3.6.1 (verified: `hasattr(nx, "extrema_bounding")` is `False`) | version artifact |
| 177 | needs `legacy_matrix=False`, a behavioural keyword the prose never states | vocabulary gap, not derivable here |

**Two of the three are not failures of reasoning at all.** One is a broken benchmark item and one
is a missing function. Only 177 is a case where the system cannot get there.

**37/40 is 92.5% of a 40-item two-library no-dependency subset — not a benchmark score.** The
published 51–59% figures are on all 328 items across 26 libraries with dependency pinning.
`truth.achieved` remains `false`.
