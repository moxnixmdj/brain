# The store carries the convention, and it reproduces without re-learning

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instrument:** `canonical/tools/learned_ranking_store_v1.py` (9 tests, all passing)
**Chain:** … → `A_LEARNED_RANKING_TRANSFERS` (7/13 held-out) → this

---

## 0. What was owed

`A_LEARNED_RANKING_TRANSFERS` established one transferable object: **four floats over four
computed features**, fitted on 13 items, solving 7 of 13 held-out items. Its own follow-up
showed feature *discovery* is not the win (one feature → 5/13), so the object to persist is
the narrow one: four floats.

The user's instant-knowledge claim, narrowed to something measurable, is this:

> Knowledge acquired in one session, externalised as data, **reproduces the same behaviour in
> a later process without being re-learned.**

That is what this receipt measures.

## 1. The store

`learned_ranking_store_v1` keeps the weights in plain JSON outside the code:

```json
{"schema": "BRAIN_LEARNED_RANKING_STORE_V1",
 "entries": {"weights": {"features": ["coverage","doc_overlap","stub_hit","depth"],
                         "weights": {"coverage":1.0,"doc_overlap":1.0,"stub_hit":0.0,"depth":1.0},
                         "learned_from": ["176","177","178","179","180","181","182",
                                          "183","184","185","188","190","192"]}}}
```

**554 bytes.** Inspectable, editable, deletable. The features themselves are never stored —
they are pure functions of the name, the problem text, the docstring and the stub name.

## 2. The measurement

| step | result |
|---|---|
| session 1: fit weights on 13 items | 9/13 on train |
| session 1: save to JSON | 554 bytes |
| session 1: rank the 13 held-out items | 7/13 in top 10 |
| **session 2: fresh process, load store, fit nothing** | **7/13 in top 10 — identical** |
| session 2: solve through the benchmark's own hidden tests | **7/13 solved** |

Solved from the store alone, with no per-item logic:

```
197  sympy.external.gmpy.is_square(n)
201  sympy.functions.jacobi_symbol(a, n)
202  sympy.ntheory.npartitions(n)
204  sympy.functions.primepi(n)
205  sympy.functions.totient(n)
206  sympy.functions.mobius(n)
207  sympy.functions.legendre_symbol(a, n)
```

## 3. Deletion is real, and failure is closed

A remembered thing that cannot be removed is not knowledge, it is a weight. Tested:

- `delete` removes the entry; the reloaded store yields all-zero weights;
- a store with no weights **ranks nothing** (`rank` returns `[]`) rather than falling back to
  a default — it fails closed, it does not silently guess;
- a corrupted store degrades to "no weights" instead of raising mid-run;
- a test asserts the store contains **no names and no facts** — only weights and provenance.

## 4. What this establishes, and what it does not

**True:**
- A convention learned in one session is externalised to 554 bytes and **reproduces the
  identical held-out result in a fresh process without re-learning**.
- It solves 7 of 13 held-out items through the benchmark's own hidden tests.
- The stored object contains no names and no world facts; the features are recomputed each
  time from the artifact and the problem text.
- It is deletable, and deletion provably removes the behaviour.

**Not established — and this matters more than the success:**
- **7/13 is 53.8% of a 13-item held-out half of a 26-item sympy sub-cohort.** It is not a
  benchmark score and must not be compared to the 51–59% frontier figures, which are on the
  full 328-item benchmark. The only honest statement is that this sub-cohort number is in the
  neighbourhood of those figures, on an easier and much smaller problem set.
- **One library.** sympy only. Not networkx, not the other 24.
- **The store does not yet persist across environments.** It persists across *processes*. The
  §6 claim needs it to persist across *sessions in unseen environments*, which requires the
  environment to supply the feedback that the benchmark's hidden tests are supplying here.
- **13 items fit weights; 13 measured them.** That is a small sample. Six held-out items still
  fail, and they fail in the known way: names whose words appear nowhere in the problem
  (`todok`), or symbols whose purpose the prose does not state.

## 5. Where this leaves the plan

The chain now has a shape:

| receipt | mechanism | result |
|---|---|---|
| `THE_GOAL_IS_AN_ORACLE` | the goal is an executable check | 3/40 |
| `THE_NAME_IS_A_CONVENTION` | flat surface search | closed: 15/22 symbols not in the surface |
| `PURPOSE_IS_IN_THE_ARTIFACT` | rank by the artifact's own docstrings | 7/32 |
| `STRUCTURE_WITHOUT_PURPOSE` | structured space + cheap oracle | 8/32; oracle 9–50× faster |
| `A_LEARNED_RANKING_TRANSFERS` | fit four weights, measure held-out | **7/13 held-out** |
| this | externalise the weights, reproduce without learning | **7/13 from 554 bytes** |

The next unit is forced by the last open gap and is not a search problem:

> The feedback signal. Every result above is supervised by the benchmark's hidden tests. In an
> unseen environment there is no hidden test — there is an environment that either does what
> was wanted or does not. **The mechanism that converts environmental outcome into the
> pass/fail signal the fit needs is the actual missing part**, and it is the same part §6
> needs for GUIs, browsers and unseen software.

`truth.achieved` remains `false`.
