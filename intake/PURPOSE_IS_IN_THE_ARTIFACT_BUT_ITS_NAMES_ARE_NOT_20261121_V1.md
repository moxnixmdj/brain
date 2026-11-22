# Purpose is in the artifact; its names are not in its surface

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instrument:** `canonical/tools/docstring_purpose_search_v1.py`
**Chain:** `THE_GOAL_IS_AN_ORACLE` (3/40) → `THE_NAME_IS_A_CONVENTION` (0/3, closed surface search) → this

---

## 0. The lead that was real

The previous receipt closed surface search with a precise reason: ranking by *name* overlap
cannot find `isprime` from "determine if n is prime", because the description does not
contain the string. It left two legal routes and named one as testable first.

The lead: **the artifact states its own purpose, in its own words, in its docstrings.**

```
isprime      "Test if n is a prime number (True) or not (False)."
primeomega   "Calculate the number of prime factors counting multiplicities for a"
primepi      "Represents the prime counting function pi(n) = the number..."
mobius       "Mobius function maps natural number to {-1, 0, 1}"
```

This is inside the artifact, free, local, and requires no network, no model, and no stored
table. It is the most honest source of purpose available under the constraints, and it works.

## 1. What it bought, measured

Ranking the artifact's 928 public names by the shared distinctive words between the item's
problem statement and each name's docstring, then submitting candidates to the item's oracle:

| instrument | cohort | solved |
|---|---|---|
| derive from declared stub information (`hole_filler`) | 40 | **3** |
| + docstring purpose ranking, with the three bug fixes below | 32 sympy | **7** |

Six of the seven now solve at **rank 1**: `jacobi_symbol`, `npartitions`, `primepi`,
`totient`, `mobius`, `is_carmichael`. `legendre_symbol` at rank 9.

### Three bugs, each of which alone zeroed the result

These are recorded because each looked exactly like a limitation of the approach:

1. **Full docstring, not 400 characters.** Truncating pushed `isprime` from rank 41 to 196.
2. **Raw shared count, not length-normalised.** Dividing by docstring length rewards terse
   docstrings and buried `isprime` at 196; raw count put five of seven in the top 3.
3. **Emit through the stub's own alias.** `totient(n)` fails; `sympy.totient(n)` passes.
   This single bug turned **seven solved items into seven failures** in one run.

A fourth, found the same way: one item's stub body is indented **one space**, not four.
Appending a four-space `pass` was a `SyntaxError`, which silently produced an empty target
name and an argument-less candidate for the whole item. The indent is now read from the stub.

## 2. Where the ceiling actually is — and it is not the ranking

Raising the candidate budget from 12 to 25 changed nothing: **7/32 either way**. So the limit
is not search depth. Asking whether the required symbol is reachable *at any depth* answers it:

| | |
|---|---|
| required symbol appears anywhere in the ranking | **7 / 22** |
| best rank for `isprime` | 52 |
| best rank for `primeomega` | 56 |
| required symbol is **not a top-level surface name at all** | **15 / 22** |

Those 15 are the ones that matter:

| item | required body | why the surface cannot contain it |
|---|---|---|
| 178 | `sympy.physics.quantum.trace.Tr(n)` | a **submodule** member, not in `dir(sympy)` |
| 186 | `inertia(...)` | reached through `sympy.physics.mechanics`, a submodule |
| 187 | `eq.lhs - eq.rhs` | an **attribute path on a parameter** |
| 188 | `poly.rep.to_list()` | a **chained attribute** on a parameter |
| 191 | `index.free_symbols` | a **property** on a parameter |
| 193 | `matrix.flat()` | a **method** on a parameter |
| 199 | `n % p == 0` | **arithmetic** over two parameters |
| 181 | `PinJoint('pin', parent, child, parent_point=parent.frame.x, ...)` | a **constructed call with fields read off the parameters** |

> **The artifact's purpose is in its docstrings, but the names that realise that purpose are
> not confined to its surface.** They live at arbitrary depth (submodules), and on the
> parameters themselves (attributes, methods, properties), and sometimes in expressions built
> from both.

## 3. The verdict on §3, final for this benchmark

**True:**
- The oracle is real and discriminating (37/40 no-dependency items).
- Purpose is recoverable from the artifact itself, and it lifts the score from 3/40 to 7/32
  with six of seven at rank 1 — a genuine, constraint-legal signal that costs 0 model calls.
- Every failure in this chain was diagnosable to a specific, mechanical cause.

**False:**
- "Scan the environment and fetch what is missing" is a complete solution. The missing thing
  is a **name at arbitrary depth or an expression over parameters**, not a fact.
- A flat surface search closes the gap: 15 of 22 required symbols are not in the surface.
- More search budget helps: 12 and 25 candidates scored identically.

**Unproven:**
- Hierarchical surface search (submodules + parameter attributes + call-chain fields) with the
  oracle as judge. This is the direct extension of what is now measured, is legal under every
  constraint, and has *not* been attempted.
- Expression synthesis over typed parameters, judged by the oracle (items 187, 191, 199).

**The real bottleneck, stated once:**
> The search space must be **everything reachable from the stub's namespace** — submodules,
  parameter attributes, chained fields, constructor keywords — and it must be **ranked by
  purpose** and **judged by the oracle**. That space is combinatorial, the oracle costs ~1 s,
  and purpose-ranking has so far only worked where the artifact repeats the problem's words.

## 4. Constraint pressure, recorded honestly

Nothing in this receipt requires violating a constraint. The purpose signal came from the
artifact, not from a table. But the measurement also shows exactly why the frontier is at
51–59% and we are at ~22% of *this* cohort: a model carries the meaning→name convention for
every library it has ever read, at every depth. We are re-deriving it at run time from
docstrings, and it works only where the docstring happens to describe the task in the task's
own words.

The legal response is not to store that convention. It is to **make the search hierarchical
and let the oracle prune**, because the oracle is the only judge that requires no knowledge.
That is the next unit of work, and it is the first one in this chain that has a measured,
non-obvious design constraint behind it: **rank by purpose, explore by structure, judge by
execution.**

`truth.achieved` remains `false`.
