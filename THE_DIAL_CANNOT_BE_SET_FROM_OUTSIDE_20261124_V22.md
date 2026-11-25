# THE DIAL CANNOT BE SET FROM OUTSIDE — real code refuses 92% of itself
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project before web, web
> before building; name the real limiting factor; kill the idea before building it; verified / unverified /
> failed; hardest real tests; never ask the user. §2 resolution unchanged. No model call, no stored
> parameter.

---

## 1. The hope I was testing, and where it came from

Last round ended with a problem I could see but not solve: the vocabulary is a **dial** — more predicates
means more precision and less coverage, with a two-point Pareto front and no way to say which point is
right, because on ten synthetic machine worlds a refusal costs nothing. My proposed fix was to attach a
real price using the only real corpus here: the ~6,200 Python files in this repo.

The test: predict a function's return-shape class (`NO_RETURN` / `RETURNS_VALUE` / `MIXED`) from its own
structural shape, features carrying no names, no literals, no docstrings. Price a refusal at 1 and a wrong
prediction at *p*, then sweep *p* from 1 to 100 and ask whether the winning vocabulary is stable.

1,200 files, **7,282 functions trained, 3,538 held out, split by file** so no held-out function shares a
file with a trained one. Every subset of 9 candidate features up to size 6.

## 2. The result, and why it is not a vocabulary result

| price | cost | pred | wrong | refused | accuracy | coverage |
|---|---|---|---|---|---|---|
| 1 | 3282 | 268 | 12 | 3270 | 0.9571 | **0.0757** |
| 2 | 3294 | 268 | 12 | 3270 | 0.9571 | 0.0757 |
| 5 | 3323 | 255 | 8 | 3283 | 0.9696 | 0.0721 |
| 10 | 3354 | 224 | 4 | 3314 | 0.9825 | 0.0633 |
| 20 | 3394 | 224 | 4 | 3314 | 0.9825 | 0.0633 |
| 50 | 3472 | 116 | 1 | 3422 | 0.9915 | 0.0328 |
| 100 | 3477 | 61 | 0 | 3477 | **1.0000** | **0.0172** |

**A 100× sweep in the price of an error changes total cost by 5.9%.** At the cheapest price the learner
speaks about 7.6% of held-out functions; at the most expensive it is perfect and speaks about 1.7%. Paying
100× more to avoid an error buys 12 fewer errors and 207 more refusals.

The winning subset does change with price (5 distinct subsets, sizes 4–6), so "the optimum is stable" is
false — but it does not matter, because every candidate sits inside a 6% coverage band. **The cost model has
almost nothing to choose between.**

## 3. What this actually establishes

The dial is real (accuracy and coverage trade strictly, 0.957 → 1.000 as 0.076 → 0.017), and it is
irrelevant, because **the vocabulary covers under 8% of a real codebase regardless of how it is set.**

That is a much sharper statement of the project's standing than "coverage is 0.70 on ten machine worlds". It
means the synthetic result was not a small-world artefact of *difficulty* — it was a small-world artefact of
*scope*. Ten enumerated machine worlds have ~150 held-out transitions each and lifting covers 60–70% of
them. A real repository has 3,538 held-out functions and this vocabulary covers 268 at best.

The difference is not that code is harder to observe. It is that a code function's return shape is not
determined by its structural shape — two functions with identical `HAS_TRY`/`HAS_LOOP`/`LINES` can return
differently, and the key therefore conflicts, and the system correctly refuses. **The refusal is honest and
it is the finding**: structural keys under-determine behaviour on real code by roughly an order of
magnitude more than on the enumerated worlds.

## 4. The verdict on my own hope

*Hoped:* a real corpus would supply an externally fixed setting for the dial.
**Refuted.** The corpus resists rather than informs: it refuses so much that no price distinguishes the
options materially. Choosing a point on the dial remains a preference, and now I know *why* it must remain
one — not because I lack a cost model, but because the vocabulary's coverage is too small for the cost model
to bite.

## 5. Verified / unverified / failed

**Verified by execution:** the seven-point price table; the 5.9% cost spread across 100×; strict
accuracy/coverage trade; features carry no names or literals (a test asserts it); nested-function returns
are not misattributed.

**Failed, mine, this round:** the hypothesis that a real corpus fixes the dial externally. Also `the_winning_
vocabulary_is_the_same_at_every_price_ratio = false` — five different subsets win at seven prices.

**Unverified:** whether a *richer* key that includes dataflow (what the return expression derives from)
would raise coverage on real code. That is a different representation and I did not build it; the shape-only
feasibility is what this round measured.

**Scope honesty:** return-shape prediction is a deliberately modest real-code task. It is not SWE-bench. It
was chosen because it is the strongest real-code claim the learner can make with zero model calls and no
borrowed answers. Every number above is internal; `docker: command not found`, so no benchmark row exists
or is claimed, and nothing here is comparable to the Opus 5.5 / Muse Spark / GPT-6 figures the prompt quotes
— those are all vendor or SEAL figures for systems that spend real inference compute.

**Audited (re-checked this round, tool not prose):** 25 repo commits; 4 of 19 prompt identifiers exist as
code; **0 of 9** prompt commit hashes resolve; 6 numeric figures unverified. Receipt:
`canonical/verification/AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json`.

## 6. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 15.9 s · 1200 files, 408 subsets
```

5 new tests. Full suite across the files this work touches: green. Guard PASS (17 rules, 0 violations).

## 7. Next

One representation change has ever paid (lifting), and this round shows why it paid: it replaced
*names* with *structure*. The refusal pattern on real code says structure alone is not enough — the missing
term is **provenance**: where a value came from, not what shape the code around it has. That is a computable
relation for Python (`ast` gives the assignment and call graph), it is the same kind of object as the lifted
predicates, and it is the first candidate in twenty-two rounds that is aimed at the measured failure rather
than at a plausible one.
