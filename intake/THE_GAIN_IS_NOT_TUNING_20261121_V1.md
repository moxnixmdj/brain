# The gain is not tuning: held-out 14/19 → 16/19, weights never refit

**Date:** 2026-11-21 · **Authority:** NONE · **$0**, 0 model calls

The 21/40 → 29/40 jump had an obvious alternative explanation that had to be killed: the 4 ranking
weights were fitted on 13 sympy items, and 9 of the newly-solved items might sit inside that
fitted set. If so the gain would be tuning, not mechanism.

Checked directly against the store's own provenance (`learned_from`), which has not changed:

```
sympy cohort      32
fitted on         13   (learned_from, stored in the JSON)
held-out          19

solved            23   = 7 in-train + 16 HELD-OUT
```

| split | before | after |
|---|---|---|
| held-out sympy | **14/19** | **16/19** |
| in-train sympy | 5/13 | 7/13 |

The two held-out gains are **186** (`from sympy.` continuation → `physics.mechanics.inertia`) and
**200** (`from sympy.tensor.array.expressions.` → `conv_array_to_matrix.convert_array_to_matrix`).
Neither has anything to do with the ranking: one is the stub-repair fix, the other is the corpus
walk depth. The weights were not refit, and 16/19 was never tuned on.

That is the check that matters. A mechanism is only worth reporting if it transfers to items its
parameters never saw, and this one moved 12 of its 16 held-out wins with no fitted parameter
involved at all.
