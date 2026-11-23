# What is solved, what is 29%, and what is genuinely unresolvable

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 113 tests

---

## The complete measured picture

Ground truth rebuilt (the benchmark's `name_of_class_or_func` is a label, not the answer — 49 of
84 were wrong), leakage-guarded (no goal shares a 6-char stem with its answer), answer verified
present. **34 scoreable rows.**

| mechanism | top-1 |
|---|---|
| **summary + IDF over the library's own docstrings** | **29.4%** |
| summary only | 23.5% |
| whole docstring + IDF | 23.5% |
| whole docstring | 20.6% |
| doctest content only | 0.0% |
| name only | 0.0% |
| shape probe on top-6 | 23.5% (worse) |
| oracle: substitute + run the item's own test | 5/9 = no gain |
| See-Also graph inheritance | no gain |

| ranking depth | top-k |
|---|---|
| top-1 | 29.4% |
| top-2 | 44.1% |
| top-3 | 47.1% |
| top-10 | 52.9% |
| top-20 | 64.7% |

---

## The three things that are actually true

**1. The neighbourhood is found reliably.** `sympy.primepi` at **rank 2 of 17,153**;
`numpy.prod` at **rank 3 of 2,256**; `librosa.localmin` at **rank 2 of 274**. Going from thousands
of candidates to a handful is the hard part of instant knowledge, and it works.

**2. The member is chosen 29% of the time, and the remaining ties are near-synonyms.** Every
failure I inspected is a tie between names that state the *same claim*:

```
goal: "computes the product of an array"
tied: np.prod, np.nanprod, np.nancumprod, np.product
```

**3. Ties among behaviourally-identical candidates are not resolvable and must not be.** `np.prod`
and `np.nanprod` return the same value on data without NaN, pass the same test, and satisfy the
same goal. Substituting one for the other is **correct**. An oracle that demanded `prod` over
`nanprod` would be demanding a distinction the goal does not make.

**So the honest number is bounded above by the fraction of goals whose answer is uniquely
determined by the goal text** — which I have not measured, and which no amount of ranking can
exceed.

---

## Why every remaining attempt failed, and what that means

| attempt | result | why |
|---|---|---|
| shape probe | 23.5% (worse) | the vocabulary fires on 11/34 and goals name inputs with output nouns (`array`) |
| oracle substitution | no gain | the test cannot separate behaviourally-identical candidates |
| See-Also inheritance | no gain | `pd.concat`'s siblings are `join`/`merge`, not "combine" |
| arity filtering | no gain | the stubs use loose annotations (`-> int` on a function returning a sympy expression) |
| doctests | 0% as a scorer | present on 40–71% of *scientific* libraries, but not as discriminative text |
| name scoring | −2.4 to −5.3 pts | a name is a label the author chose; a summary is a sentence written for a reader |

---

## What is solved, without qualification

| step | measurement |
|---|---|
| scan an environment | 216 programs, 48 ms |
| know what you don't know | 0 probes at rebuild |
| fetch instantly, no model call | 1 request/library, no quota |
| inventory an artifact | 17,153 names (sympy), sandboxed child |
| the store suffices | 125/125 answers, 25,768 B |
| goal-directed beats learn-everything | **3.0×** |
| the SWE cohort | **37/40** |

## What is not solved

**Instant knowledge for an arbitrary library: 29.4% top-1, 64.7% top-20.** The user's algorithm is
right, three of its four steps work, and the fourth is a fraction that depends on how often a goal
uniquely names its answer — which is a property of the goal, not of the system.

`truth.achieved` = **`false`**.
