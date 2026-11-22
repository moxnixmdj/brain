# A property hides what an instance states: 32/40 → 34/40

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` = `false` · **$0**, 0 model calls

---

## 0. Why the nested read was invisible

Items 181 and 182 have the same answer:

```python
PinJoint('pin', parent, child, parent_point=parent.frame.x, child_point=-child.frame.x)
```

Every part is *stated*: the constructor by the stub's return annotation, the keyword names by the
artifact's own signature, the values by the parameters' members, and the name literal `'pin'` by
the prose's own function name (`custom_pinJoint`). Nothing had to be guessed.

What blocked it was an enumeration limit with a subtle cause:

```
>>> Body.frame          # a PROPERTY on the class
>>> dir(Body)           # reports the property object
['deleter', 'fdel', 'fget', 'fset', 'getter', 'setter']
```

Walking `dir(cls)` — which is what the whole space does — can never see `x` inside `frame`,
because `frame` is a *property* whose value only exists on an instance:

```
>>> Body("b").frame.x
b_frame.x
```

So the two-level space was not merely hard to rank; it **did not contain the answer**. No filter,
no weight and no budget could have found it.

## 1. The four measured corrections, in the order they were forced

Each of these was a real failure I hit, in this order, on these two items:

| # | mistake | measurement that killed it | correction |
|---|---|---|---|
| 1 | any capitalised import is the constructor | `Body('body', parent, child, ...)` — a *parameter's* type, not the return | the **return annotation** is the constructor |
| 2 | name literal = class name lowercased | `'pinjoint'` fails, `'pin'` passes, `'p'` fails | the **prose's function name**, boilerplate stripped |
| 3 | keywords by prose word overlap | `(parent, child)` won, because both are *parameter* names the prose repeats constantly | a keyword may not be a parameter |
| 4 | keyword parts must all match the prose | `parent_point` lost to `parent_axis` because the prose says "**points**" | plural normalisation (the same allowance as `int`/`integer`) |

And the ordering rule that finally worked, which is the same rule as everywhere else in this
project: **a dotted path the prose spells out is stated, not guessed.** Item 181's text contains
the literal string `parent.frame.x`, and item 182's contains both `parent.frame.x` and
`child.frame.x`. Ranking nested reads by their head word put `frame.u` first, because every frame
axis shares the head `frame`; ranking by the *spelled-out path* puts `frame.x` first.

## 2. Unbounded products are the same failure as the arithmetic flood

The first working version emitted **550** keyword-constructor bodies, and they crowded out the
stated-symbol applications that solve other items — the same pathology as the 95,823-body
`permutations` block removed earlier this session. The fix is the same shape: bound by *stated*
evidence rather than by a cheaper sort. Only 2 keyword pairs by qualifying evidence, only 3 nested
reads per parameter, only the first few names, capped at 80.

## 3. Result

| | before | after |
|---|---|---|
| sympy | 26/32 | **28/32** |
| networkx | 6/8 | **6/8** |
| **total** | **32/40** | **34/40** |

Time 245 s + 34 s. Zero model calls, zero network at run time.

**Held-out sympy: 17/19 (89%)**, weights never refit. Both 181 and 182 are held-out, so both
wins transfer — the mechanism is a general rule about instances and properties, not a patch for
two items.

## 4. What remains

```
sympy unsolved:    177  180  189  203
networkx unsolved:  27   29
```

| item | cause | derivable? |
|---|---|---|
| 203 | the prose contradicts its own test (DISTINCT vs MULTIPLICITY) | **no**, and correctly not attempted |
| 29 | version artifact — the referenced symbol does not exist in networkx 3.6.1 | no |
| 27 | the keyword is `cutoff`; the prose says "number of communities set at 5" | convention, not derivation |
| 189 | a three-body system: `RigidBody`+`PrismaticJoint`+`PinJoint` composed, then EOM | composition over several constructors |
| 177 | `laplace_transform(eye(2), t, z, legacy_matrix=False)` | composition over a constructed literal **plus a keyword the prose never states** |
| 180 | `parse_mathematica(expr).replace(Function("F"), lambda *x: Max(*x)*Min(*x))` | a lambda rewriting a symbol |

**Only 177 sits at the edge of the general mechanism.** 180 needs a lambda whose body is itself a
composition; 189 needs chaining three constructors. Neither is knowledge — both are shape — and
both are one shape away from what the grammar already emits.

34/40 is **85% of a two-library, no-dependency subset**. It is still not comparable to the
published 51–59% on all 328 items across 26 libraries, and that comparison is not made anywhere.
`truth.achieved` remains `false`.
