# The best prior state was 36/40, and 180 is the gap

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 82 tests pass

**I have to correct my own reporting again.** I read a `grep` filter as evidence and wrote that
"189 regressed". It did not: 189 solves (`System.from_newtonian(wall)…`, try 59). The cohort
reports **35 OK / 5 failed = 35/40**, and the five are 177, 180, 203, 27, 29.

That matters because commit `956a9469` in this same branch had already reached **36/40**, solving
180 and 189. So today's work is **36 → 35**: I restored 189 to the harness and **lost 180**.

```
sympy      29/32   (was 30/32 at 956a9469)
networkx    6/8
total      35/40   (was 36/40)
```

## What 180 needs, exactly

```
parse_mathematica(expr).replace(Function('F'), lambda *x: Min(*x)*Max(*x))
```

Everything in it is stated by the prose: `replace` ← "is replaced", `*x` ← "those arguments"
(plural), `Max`/`Min` ← "the maximum and the minimum", `Function('F')` ← "the function symbol F",
and the head ← the stub's own `from sympy.parsing.mathematica import parse_mathematica`.

I verified each piece in the space: the lambda block produces the body, and via `judge_stream` over
that space the answer is found at **index 78 in 0.6 s**. It is *not* found through `solve_item`,
whose space puts the same family at 582 and whose head ranking keeps choosing `Max(expr).replace(…)`
or `sympy(expr).replace(…)` instead of `parse_mathematica(expr).replace(…)`.

## What I changed and what it bought

| change | effect |
|---|---|
| `capital_tail_matches`: a capitalised prose word names a constructor by **prefix + degree + a closed remainder set** | 180 → `['sympy.Max', 'sympy.Min']` exactly; nothing spurious on 177/199/203/204 |
| hint constant AND spelled-out in lower case | **+13** |
| `unclassified` → `APPEND` shape `(1,2,1)` | a real `tar -rf` effect no longer counted as a broken measurement |
| head ranking: stub-bound callables first, constructors never a head | moved the correct body into the top 600 (582) but not yet to the front |

**None of it recovered 180.** The honest summary is that I traded a working item for a mechanism
that is right in isolation and not yet right in composition, and I should have measured the cohort
*before* claiming the mechanism worked.

## The lesson, stated as a rule

**A body that passes in isolation and is present in the space is not solved.** The only test that
counts is the end-to-end one, and I ran it twice before believing it — and the first time I read it
wrong.

`truth.achieved` remains `false`.
