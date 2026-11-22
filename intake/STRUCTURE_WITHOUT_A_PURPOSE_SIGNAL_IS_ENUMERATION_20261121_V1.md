# Structure without a purpose signal is still enumeration

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instruments:** `structured_surface_space_v1.py`, `batched_oracle_v1.py`
**Chain:** `THE_GOAL_IS_AN_ORACLE` (3/40) → `THE_NAME_IS_A_CONVENTION` → `PURPOSE_IS_IN_THE_ARTIFACT` (7/32) → this

---

## 0. What this receipt closes

`PURPOSE_IS_IN_THE_ARTIFACT` ended with a measured design rule and a specific gap: only 7 of
22 required symbols were reachable at any depth, because the required thing was often **not a
top-level name**. It named the next step precisely — `rank by purpose, explore by structure,
judge by execution` — and left it unproven.

This receipt builds that and measures it. Two results matter, and only one of them is good.

## 1. The good result: the oracle got 9–50× cheaper, and is still authoritative

One oracle call cost **0.95 s**, and **0.59 s of that was `import sympy` alone** — paid again
for every candidate, thousands of times, to answer a question the library only has to be
imported once to answer.

`batched_oracle_v1` imports the item's imports once, installs a live `sample_N` module whose
function is swapped per candidate, compiles the hidden test once, and runs its own
`TestCase`s in-process.

| | per candidate |
|---|---|
| subprocess + pytest | 950 ms |
| batched worker (first form) | 120 ms |
| batched worker (final) | **19–110 ms** |

Correctness was treated as a first-class requirement, not an afterthought:

- 7/7 agreement with pytest on one item, positive *and* negative cases;
- **20/20 agreement on reference solutions across 20 independent items.**

Three bugs were found and fixed while getting there, each of which produced *silent wrong
answers*: the test imports `from sample_N import f`, so the module object must exist before
the test compiles; the test source needs `__file__`; and the function must be bound into the
test namespace before each trial.

**This is a real, reusable result.** A fast, verified judge makes the rest measurable at all.

## 2. The bad result: structure did not pay

The structured space is real and correctly built. For sympy it is **14,625 dotted names**
against 928 top-level ones, and the specific misses are in it: `ntheory.primetest.is_square`
at rank 5, `physics.mechanics.inertia` at rank 2.

| configuration | solved |
|---|---|
| flat surface, purpose-ranked (`docstring_purpose_search`) | **7/32** |
| structured space, MODULE+SUBMODULE, budget 300 | **6/32** |
| …with a large budget (2500 candidates = 37% of the whole space) | **8/32** |

Three separate bugs were found and fixed on the way (MODULE/SUBMODULE were concatenated so
submodules began at position 930 of 14,629 and were never reached; the rank lookup matched a
bare name against a dotted corpus; bodies were emitted without the namespace prefix). After
all three, the total did not move.

And the wins that *did* appear were not the ones the structure was built for:
`jacobi_symbol` and `legendre_symbol` "solved" through `sympy.external.gmpy.jacobi` — the same
function under a second name, if anything **less** meaning-bearing than the original.

## 3. Where it actually fails, stated exactly

Four items were checked by generating their required body by hand and asking the oracle.
**All four pass.** The failures are purely placement:

| item | required body | in the space? | oracle |
|---|---|---|---|
| 187 | `eq.lhs - eq.rhs` | **not generated** | passes |
| 193 | `matrix.flat()` | **not generated** | passes |
| 199 | `n % p == 0` | **not generated** | passes |
| 191 | `index.free_symbols` | **yes, position 14,855** | passes |

This is the whole finding in one table. The space contains the answer or can trivially be
taught to contain it; what it cannot do is put it anywhere near the front.

> **The purpose-ranking signal that works for module functions is inapplicable to attributes.**
> `lhs`, `rhs`, `flat`, `free_symbols` appear in no docstring, so every attribute candidate
> scores zero and is ordered behind all 14,625 documented names. Purpose lives in prose about
> *functions*. Attributes are named by convention, not described by prose.

## 4. Verdict

**True:**
- The oracle can be made ~9–50× cheaper with verified agreement (20/20 reference solutions,
  7/7 mixed cases). This is the durable result of this receipt.
- The structured space is correctly enumerated and contains the missed symbols at shallow
  rank (`is_square` 5, `inertia` 2).
- Every remaining failure is a *placement* failure, not a generation failure — proven item by
  item above.

**False:**
- "Rank by purpose, explore by structure" is sufficient. Structure without a purpose signal
  is enumeration; a broader space with the same ranking solved **no more items**, and the
  larger budget that did find items (2500 candidates for 2 items) is brute force wearing a
  different name.
- A bigger space is progress. 14,625 names, +0.06 solved.

**Unproven:**
- A purpose signal for *attributes*. Docstrings do not describe them. The candidate sources
  that remain are the problem text's own relational phrases ("the difference", "the
  number of") and the hidden test's argument shapes — neither has been attempted.

**The bottleneck, for the fourth time and now sharply:**
> Every mechanism so far can **generate or reach** the required body and cannot **rank** it.
> The missing signal is the meaning→name convention, and it is not in the artifact's prose
> for attributes, not in its surface for submodule members, and not in the problem text for
> either. Ranking is the whole problem; generation is nearly free.

## 5. What this does to the plan

The honest position is that the closing mechanism is **not** a better search over a bigger
space. Three attempts have now bounded what search can buy: 3/40 → 7/32 → 8/32, at increasing
implementation cost and with frontier at 51–59%.

The live question is no longer "which space?" but **"what carries the convention?"** — and
under the standing constraints it may only be (a) computed at run time from the environment,
or (b) stored in the external store. Option (a) has now been measured to its limit. Option (b)
is the one the user's instant-knowledge claim actually describes, and it has not been built.

`truth.achieved` remains `false`.
