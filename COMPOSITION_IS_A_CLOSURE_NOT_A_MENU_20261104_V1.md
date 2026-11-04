# COMPOSITION IS A CLOSURE, NOT A MENU

2026-11-04, round 24 result. For
`PREREG_THE_LIBRARY_THAT_NOBODY_READS_AND_THE_CLOSURE_THAT_REPLACES_IT_20261104_V1.md`.
Base `72e27486`. `truth.achieved` false, `authority: NONE`, `$0`.

Predictions: **P1, P2, P3, P4, P5 all PASS** — with one correction to round 22's diagnosis and one
of my own tests overturned by a result I did not expect.

---

## 1. First, round 22 was wrong and this is the correction

Round 22's note claimed: *"the concept library receives zero concepts because the bridge admits only
single-`return` bodies, so nothing accumulates."*

Re-measured on round 23's searched organs:

```
concepts before: 0
  P=3  concepts=1
  P=5  concepts=2
  P=7  concepts=3
```

**The bridge fires. Concepts are admitted.** Round 22 described a symptom that round 23 happened to
remove, not the reason the creature fails to improve. I am recording that as a wrong diagnosis rather
than quietly re-planning around it.

## 2. The real finding: the library is admissible and inert

With three learned tables in `G_t`, on the same shape:

| task | cold | after periods 3, 5, 7 are in the library |
|---|---|---|
| `T(x) + x` | REFUSED | **REFUSED** |
| `2*T(x) - 1` | 6/6 | 6/6 |
| `T(x) * x` | REFUSED | **REFUSED** |
| `T(x) + U(x)` | 6/6 (writer) | 6/6 |

Identical. And the compounding test is flat for a reason no library can fix:

```
period-12 cold : 2 questions
period-12 warm : 2 questions
```

2 is the information floor — one observation per block entry. Round 23 already reached it, so **cost can
no longer measure learning**: a library that made a floor-cost problem cheaper could only do so by
knowing the world for free. The question has to be asked as *expressiveness*, and by that measure the
library bought nothing.

## 3. What actually changed: one rule instead of N nodes

The refusal above is the defect: `T(x)+x` is a composition, no single node describes it, and adding one
node per composition would rebuild the menu one level up.

The fix is a **closure rule**: pick a combining operation and a basis co-factor, **invert the operation**,
and ask whether the residual is constant per residue. If it is, the table's block has been solved out of
the data. Depth 1, three operations, four co-factors, every candidate still filtered by the existing
version space.

## 4. Measured

**Cold — writers disabled, empty library, search only:**

| task | status | organ | held-out (37 inputs never shown) | questions |
|---|---|---|---|---|
| `T(x) + x` | DISAMBIGUATED_AND_CRYSTALLIZED | `composed_table_3_add_x` | **37/37** | 3 |
| `T(x) - x` | DISAMBIGUATED_AND_CRYSTALLIZED | `composed_table_3_sub_x` | **37/37** | 3 |
| `T(x) * x` | DISAMBIGUATED_AND_CRYSTALLIZED | `composed_table_3_mul_x` | **37/37** | 3 |
| `T(x) + x*x` | DISAMBIGUATED_AND_CRYSTALLIZED | `composed_table_3_add_x2` | **37/37** | 3 |

All four were **refused before this change, cold and warm**.

**Through the live executor** on a booted `Creature`:

```
plus-x : DISAMBIGUATED_AND_CRYSTALLIZED  composed_table_3_add_x  q=3  answers [6.0, 507.0, 998.0] exact
times-x: DISAMBIGUATED_AND_CRYSTALLIZED  composed_table_3_mul_x  q=3  answers [-7.0, 3500.0, -2000.0] exact
```

**P3 — false positives, 15 adversarial cases.** Nearly-periodic, piecewise, noisy, and random
functions, plus genuine periodics. **Zero false claims.** Everything claimed was exact on held-out
inputs; everything not claimed refused.

**P4 — bounded.** Candidate count 28–31 (7× a bare period task) regardless of period; generation
~5 ms, and it does not grow with the period (P=12 produces 8 candidates, fewer than P=3).

## 5. The result that overturned my own test

Round 23's suite asserted `x*x` must be **refused**. It now solves it:

```
def run(x0):
    return ((((0.0, 0.0,))[int(math.floor(x0)) - math.floor(math.floor(x0) / 2) * 2]) + (x0 * x0))
```

`T_2 = [0, 0]` plus `x²` is exactly `x²`, and it is **exact at x = 10⁶**. That is a correct solution, not
a cheat, so the test was asserting the creature is worse than it is. I replaced the name-based assertion
with the invariant that actually matters:

> **whatever is claimed must be exact on held-out inputs, for any corpus.**

Checking names is a proxy; checking answers is the property. `x³`, `floor(x/7)`, `2^x`, random mappings
and the piecewise/noisy cases still refuse.

## 6. Honest limits

- **The closure is a design decision, not emergence.** One rule instead of N nodes is strictly less
  static. It is not the creature inventing its language, and I said in the pre-registration that I would
  not call it that.
- **Depth 1 only.** `T(x)+T'(x)` is not covered by this rule; it happened to be solved by the period
  writer for `T(x)+U(x)`. Nested composition is outside what was built.
- **The co-factors are a small hand-picked basis** (x, 2x, x², constant). Composition over a small basis
  is not general capability, and the basis being small is what makes the claim modest.
- **Nothing compounds across separate problems**, and §2 explains why cost is no longer the measure. This
  round did not change that.
- **The concept library remains inert** — it accumulates and nothing reads it. Wiring it in without
  evidence that it helps would be decoration. Recorded in a test so the choice is visible rather than
  forgotten.
- `truth.achieved` false, `authority: NONE`, $0, no sentience claim, no external models, no neural
  weights, no dynamic code execution in result-bearing modules.

## 7. Receipts

```
canonical/tests/test_composition_is_a_closure_not_a_menu_v1.py              9 passed
canonical/tests/test_the_grammar_can_find_what_no_writer_knew_v1.py        10 passed
regression set (12 suites)                                       190 passed, 25 subtests
```

Every behavioural claim above comes from `synthesize_or_disambiguate_skill` with `growth_enabled=False`,
or from `sovereign_perform` on a booted `Creature`.
