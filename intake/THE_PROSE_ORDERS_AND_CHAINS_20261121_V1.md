# The prose orders, the prose chains: 34/40 → 36/40

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` = `false` · **$0**, 0 model calls

---

## 0. Two shapes the grammar did not have

Both remaining solvable items needed a body that is not a single expression.

**180 — a rewriting lambda.**

```python
parse_mathematica(expr).replace(Function('F'), lambda *x: Max(*x)*Min(*x))
```

The prose states all of it: "every occurrence of the function symbol **F** is **replaced** by a
new function that … returns the **product of the maximum and the minimum** of those arguments."

| part | statement it comes from |
|---|---|
| `replace` | the inflected verb "replaced" — the same morphological allowance already made for `int`/`integer` and for plural keywords |
| `lambda *x` … `(*x)` | "those argument**s**" is plural, so the lambda takes a splat and the members are applied to a splat |
| `Max`, `Min` | "maximum", "minimum" — ranked by prefix relation, not by an arbitrary pair order |
| `Function('F')` | "the function **symbol F**" — `F` read straight out of the prose |

**189 — a three-statement chain.**

```python
System
    system = System.from_newtonian(wall)
    system.add_joints(slider, pin)
    return system.form_eoms()
```

"sets up this system using the Newtonian formulation, **adds** the **slider and pin joints**, and
**returns** the system's **equations of motion**." Construct, chain, return.

## 1. The fifth silent empty space

Item 189's stub ends:

```python
    from sympy.physics.mechanics import 
```

with the cursor **after** `import` and before the name. `parameters()` returned `[]` — the stub
did not parse — so no candidate could be built for it, exactly as with 35/31/32/186/200 last
round. That is now **five separate items** hidden by the same class of instrument fault.

The repair branch had to be written carefully: `_repaired_source` calls `rstrip()` first, which
removes the trailing space that *marks* the cursor, so the test cannot require one.
`from X import` with nothing after it is equally truncated.

The rule this project has now paid for five times:

> **An instrument that fails closed is indistinguishable from a system that knows nothing.**
> Check the reference, then check `parameters()`, before believing any zero.

## 2. What was measured and rejected

**Item 177 is not a shape problem, and the mechanism is not extended for it.**

```python
laplace_transform(eye(2), t, z, legacy_matrix=False)   # passes
laplace_transform(Matrix([[1,0],[0,1]]), t, z, legacy_matrix=False)   # FAILS
```

So the *identity-matrix instance* matters, not merely a 2×2 matrix — and `legacy_matrix=False` is a
keyword the prose never states and nothing derives. Extending a general mechanism to rescue one
item would have meant inventing knowledge for it. It stays unsolved, and the honest reason is
recorded rather than papered over.

## 3. Result

| | before | after |
|---|---|---|
| sympy | 28/32 | **30/32** |
| networkx | 6/8 | **6/8** |
| **total** | **34/40** | **36/40** |

**Held-out sympy: 17/19 → 18/19 (95%).** Weights never refit. Both 180 and 189 are held-out
items, so both gains transfer.

Time 249 s + 36 s. Zero model calls, zero network at run time. 58 tests pass.

## 4. The four that remain, with the reason each is not a mechanism failure

| item | reason | is it derivable? |
|---|---|---|
| 203 | **the prose contradicts its own test** — says DISTINCT, the hidden test wants MULTIPLICITY | no; correctly not attempted |
| 177 | needs `eye(2)` specifically *and* the unstated keyword `legacy_matrix=False` | needs knowledge; not extended for it |
| 29 | version artifact — `extrema_bounding` does not exist in networkx 3.6.1 | no |
| 27 | the keyword is `cutoff`; the prose says "number of communities set at 5" | convention, not derivation |

**Not one of the four is a general-shape failure.** Two are the benchmark disagreeing with itself
or its environment, one is unstated knowledge, one is a keyword convention.

## 5. The shape of the whole result

```
sympy, no-dependency      30/32      (93.75%)
networkx, no-dependency    6/8       (75%)
total                     36/40      (90%)

held-out sympy            18/19      (95%, weights fitted on the other 13 only)
```

Every gain this session came from making the artifact's own statements reachable — never from
storing a name, never from a model, never from a synonym table:

1. the stub's incomplete line states the vocabulary (35, 31, 32, 186, 200, 189)
2. the corpus walk must reach the depth the symbols live at (14,625 → 50,286 names)
3. a member's own docstring states its meaning (188, 194, 185)
4. a live instance states what a property hides (181, 182)
5. an inflected prose verb and a spelled-out symbol state a lambda (180)

**36/40 is still not a benchmark score.** The published 51–59% figures are on all 328 items across
26 libraries with dependency pinning; this is a 40-item two-library no-dependency subset. No
comparison is made anywhere in this project, and `truth.achieved` remains `false`.
