# A stated type is evidence, not a verdict: 31/40 → 32/40

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` = `false` · **$0**, 0 model calls

---

## 0. The item, and why the guide mechanism missed it

185 declares `(K: FiniteField, a: FiniteField) -> int` and its answer is `K.to_int(a)`. The prose
says "converts the field element into its corresponding **integer** representation".

Two things were broken, both instrument-level:

**`_sample` returned the class, not an instance.** The reader resolved the annotation and called
it with no arguments. `FiniteField()` raises `TypeError` — it needs a modulus — so the reader
produced **zero guides** and the item looked like an empty space. It now tries seven *stated*
instantiations (`()` , `(6)`, `(2)`, `(0)`, `(1)`, `("x")`, `(())`), because the type's own
signature says it takes one argument and a small integer is the only value these constructors
take.

**The gate deleted the answer before scoring it.** `if not overlap: continue` — and `to_int`
shares **no prose word** with the problem. The prose says "integer", never "int". The gate is now
"any stated evidence", where the declared return type is independent evidence.

## 1. The hard part: one annotation in this cohort is WRONG

| item | declared return | actual answer returns |
|---|---|---|
| 188 | `list[int]` | `to_list()` → list ✅ |
| **194** | `list[int]` | **`todok()` → dict ❌** |
| 185 | `int` | `to_int()` → int ✅ |

I spent five rounds oscillating between two rules, because **194 and 185 demand opposite
things**:

- letting the type *outrank* meaning puts `tolist` above `todok` → loses 194;
- letting the type *add nothing* drops `to_int` for zero prose overlap → loses 185.

The resolution is not a compromise weight. It is that **the two items are separated by where the
evidence comes from**:

```
188/194  the PROSE states the meaning; the annotation may be wrong  -> prose meaning wins
185      the PROSE never states the type; the annotation is the only statement  -> type admits
```

So the type is worth at most **6** (name 3 + stated form 3) against **4 per prose overlap word**:
a member whose guide states two prose words always beats one that only matches the annotation,
and a member with *zero* prose overlap can still enter on the type alone.

Three further rules, each forced by a measurement:

1. **Specificity is capped at one overlap unit.** `to_int`'s guide has four words the prose never
   says, and an uncapped penalty buried it beneath `from_sympy`.
2. **`from_<X>` producing a type that is not the declared one is a stated contradiction.** Given
   `-> int`, `from_sympy` returns a SymPy object — the member's own name says so. `from_list`
   given `-> list` is consistent and keeps only the small inversion penalty, so 188 keeps it
   available.
3. **One decision point.** A second "preference sort" after the weighted score silently undid the
   weighting. That is the same failure mode as every other bug in this file: two places deciding
   one thing.

## 2. Result

| | before | after |
|---|---|---|
| sympy | 25/32 | **26/32** |
| networkx | 6/8 | **6/8** |
| **total** | **31/40** | **32/40** |

No regressions. Held-out unchanged at **17/19** — 185 is a *train* item, so it does not inflate
the held-out figure, and the held-out wins for 188/194 were banked in the previous commit.

The five tests in this change are regression guards, not decoration: writing
`test_declared_return_type_outranks_prose_overlap` is what caught the oscillation, because the
test encodes the *reason* (the annotation is the least noisy statement) rather than the outcome.

## 3. Remaining, all grammar rather than knowledge

```
sympy unsolved:  177 180 181 182 189 203
networkx unsolved: 27 29
```

| item | cause | knowledge needed |
|---|---|---|
| 181 182 | `PinJoint('p', parent, child, parent_point=parent.frame.x, child_point=-child.frame.x)` — a nested attribute read as a keyword argument | **none** |
| 177 180 189 | composition over a constructed literal (`eye(2)`, `Max(*a)*Min(*a)`, a three-body system) | **none** |
| 203 | the prose contradicts its own test — unsolvable, correctly not attempted | — |
| 27 | the keyword is `cutoff`, the prose says "number of communities" | convention |
| 29 | version artifact — the symbol does not exist in networkx 3.6.1 | — |

**181/182 are now the clearest target in the whole set**: the answer is one constructor call whose
keyword arguments are nested attribute reads, both halves already in the space. That is the last
purely-mechanical class.

32/40 is 80% of a two-library, no-dependency subset — **not comparable** to the published 51–59%
on all 328 items across 26 libraries. `truth.achieved` remains `false`.
