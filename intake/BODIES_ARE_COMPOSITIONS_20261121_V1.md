# Bodies are compositions — 15/32 on the full sympy cohort

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instruments:** `canonical/tools/body_grammar_v1.py`, `batched_oracle_v1.py`, `shape_and_synonym_v1.py`
**Chain:** … → `ONE_HANGING_CANDIDATE_COSTS_THE_ITEM` (11/13 held-out) → this

---

## 0. The mistake I had been making

I had been treating the unsolved items as **vocabulary** problems — the name shares no word
with the prose. That was wrong, and measuring it showed why.

Items 176–192 need:

```
eq.lhs - eq.rhs                          attribute path, then arithmetic
matrix.rep.to_list()                     chained attribute path
DFT(n).as_explicit()                     application, then method
Matrix([first, second])                  a list built from the parameters
RigidBody(a), Particle(b)                a tuple of two applications
PinJoint('pin', parent, child,
         parent_point=parent.frame.x)    keyword arguments read off the parameters
```

**Not one of these is `symbol(a, b)`.** No ordering of name applications can produce them,
which is exactly why every unit of extra ranking effort returned nothing. The space was
wrong — for the second time in this chain, and this time structurally rather than
statistically.

## 1. The grammar

The smallest set of compositions covering every shape observed, each derived only from the
stub's own declaration:

| kind | example |
|---|---|
| `LEAF` | `n` |
| `PATH` | `index.free_symbols`, `poly.rep.to_list()` |
| `OP` | `eq.lhs - eq.rhs` |
| `APPLY` | `Matrix([first, second])` |
| `PREDICATE` | `n % p == 0` |
| `METHOD` | `DFT(n).as_explicit()` |
| `KWARGS` | `PinJoint(`'`pin`'`, parent, child, parent_point=parent.frame.x)` |

## 2. Four bugs, each of which alone returned zero

Every one was found by measuring *where the correct body sits in the generated space*, not
by reading code:

1. **Ordering inside the space.** `sympy.Equality` exposes **117** attribute paths. With the
   combinatorial block first, a 600-candidate cap was exhausted before `eq.lhs - eq.rhs`
   (position **169**). Ordering is not cosmetic here; getting it wrong means zero.
2. **Name length is a proxy for API primitiveness.** `lhs` and `rhs` are the 3rd and 4th
   *shortest* of 117 members; `as_content_primitive` is the longest and no problem asks for
   it. Sorting by length moved `lhs`/`rhs` inside the budget.
3. **Properties are not methods.** `index.free_symbols` sat at position **136 of 212** by
   length, because it is 12 characters among many shorter method names. As a *property* —
   readable without a call, the cheapest possible body — it belongs at position 50.
4. **"Stated" symbols were junk.** Tokenising the prose and keeping every word that matched a
   module member produced **`two`** and **`second`** for item 192 — English words that happen
   to be corpus members. Those consumed the budget the real symbol needed. Stated symbols are
   now derived from the stub's **own imports and annotations**, which is where `Matrix` is
   actually named.

That third measurement is the general lesson: **cheapness is a better ordering signal than
size.** A property read, a leaf, a single attribute are all one trial each and should be
tried before anything constructed.

## 3. Two judge bugs found the same way

- **The per-candidate and worker timeouts were chosen independently.** 60 candidates × 3 s is
  180 s of allowance; with a 120 s worker budget, *every* verdict became `worker_timeout`,
  including the correct one. The per-candidate allowance is now **derived** from the budget.
- A single hanging candidate (`sympy.ntheory.prime(n)` searching for the nth prime) had
  previously destroyed a whole item; `signal.alarm` bounds it per candidate.

## 4. Result

| instrument | full sympy cohort (32) |
|---|---|
| goal as an executable check | 3/40 (different cohort) |
| store ranking + shape + stated + squash | 12/32 |
| **+ composition grammar** | **15/32** |

```
179  sympy.core.preorder_traversal(expr)
187  eq.lhs - eq.rhs                       <- OP
192  Matrix([first, second])               <- APPLY
193  list(sympy.matrices.Matrix(matrix))
195  sympy.core.bottom_up(expr, lambda x: x.doit())
196  sympy.core.use(expr, lambda x: x.doit())
197  sympy.external.gmpy.is_square(n)
198  sympy.ntheory.isprime(n)
199  n % p == 0                             <- PREDICATE
201  sympy.external.gmpy.jacobi(a, n)
202  sympy.ntheory.npartitions(n)
204  sympy.functions.primepi(n)
205  sympy.functions.totient(n)
206  sympy.functions.mobius(n)
207  sympy.external.gmpy.legendre(a, n)
```

**220 s for the whole cohort**, median item under 3 s.

## 5. The remaining 17, classified

- **194 `todok`**, **183 `is_carmichael`**, **184 `divisor_sigma`**, **185 `to_int`**,
  **188 `to_list`** — vocabulary. The name shares no word with the prose.
- **176 `DFT(n).as_explicit()`**, **177 `laplace_transform(eye(2), t, z, legacy_matrix=False)`**,
  **180 `parse_mathematica(...).replace(...)`** — the *shape* is a composition the grammar does
  not yet admit (a matrix built from a literal, a keyword the prose never states).
- **181/182 `PinJoint(...)`**, **189 `System`**, **190 `RigidBody/Particle`** — object
  construction with cross-parameter attribute reads. The KWARGS rule exists but the values are
  nested (`parent.frame.x`) two levels below what `attribute_paths` reaches.
- **186 `inertia(...)`** — needs a **relative-import path** (`physics.mechanics`), not a
  namespace attribute.
- **191 `index.free_symbols`** — in the space at position 50 and *passes alone*, but every batch
  containing it returns `worker_timeout`. The candidate set is genuinely too expensive for the
  budget; this is now a *throughput* limitation, not a search or ranking one.
- **203** — benchmark defect, must not be tuned for.

`truth.achieved` remains `false`. 15/32 is 47% of a 32-item no-dependency sympy cohort — not a
benchmark score, and not comparable to the 51–59% frontier figures on the full 328.
