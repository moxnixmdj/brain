# Nobody Was Ever Predicting

**2026-11-04 · round 14 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0**

Thirteen rounds of machinery. I checked, for the first time, whether any of it predicts data it has
not seen.

```
grep -rn "held.out|holdout|prequential|predict_next|unseen" \
     evidence_demand_v1 observation_refutation_v1 hypothesis_classes_v1 \
     vocabulary_induction_v1 discovered_tests_v1
→ one hit, in a docstring, describing a third test I wrote
```

**Zero held-out evaluation.** Every number this session — 12 programs, 3 explanations, 9/9, 10/10,
42/45 — was a *fit*. `DETERMINED` was being read as a property of the hypothesis. It is a property of
the observations plus an unstated assumption about how the world continues.

---

## 1. What the measurement did to my own confidence

With a truth function and genuinely held-out points, the accumulated machinery scores **42/45**. That
is better than I expected and it is also the least interesting number here, because the three failures
are all one thing:

```
mod 2, trained on three points   → NO HYPOTHESIS, then wrong or absent on the fourth
relu, trained only on x >= 0     → "return x"   predicts -5 → -5      truth 0
floor(y = x), trained on integers → "return x"  predicts 0.5 → 0.5    truth 0.0
```

Both of the last two are `DETERMINED`. Both are exactly right on everything they were shown. Both are
wrong everywhere outside it, and **no report field said which inputs the hypothesis had been checked
over** — `compose` returns `['authority','branches','fits','interpretation','needs','split_at',
'status','why']` and not one of those is a domain.

The creature was not failing to predict. It was failing to distinguish predicting from extrapolating,
which is worse, because it looks like success.

---

## 2. And the harness lied first

My first held-out run returned **0/45**. Every case, every size. Catastrophic — and I suspected the
instrument before the creature, which is the rule that has earned its place this session. It was the
instrument, twice over:

```
_compile_body(body, ["x"])((3.0,))   →  (3.0, 3.0)     "2 * (3.0,)" is tuple repetition
_compile_body(body, ["x"])(3.0)      →  6.0            correct
```

I made the scalar/tuple mistake in *both* directions while writing the measurement, and both times it
failed silently: a tuple argument turned a correct `return 2 * x` into `(3.0, 3.0)`, which compares
unequal to `6.0` and reads as a wrong prediction. That is the fifth input-shape disagreement this
session and it is now guarded explicitly in the new module rather than assumed.

---

## 3. What is now reported

**The domain of verification**, attached to every hypothesis and every prediction:

```
2x on 0..2     domain=[0, 2]     x=100  →  EXTRAPOLATION
3x+1 on 0..2   domain=[0, 2]     x=1    →  INSIDE
relu on -2..3  domain=[-2, 3]
```

**Prequential accuracy** — the only test needing no oracle at all. Build from the first k
observations, check the k+1-th:

```
2x       5 tested  0 refuted  survived all
3x+1     5 tested  0 refuted  survived all
mod 2    7 tested  1 refuted  died at k=2
x*x      5 tested  1 refuted  died at k=2
```

An affine hypothesis on `mod 2` or `x*x` dies on the very next observation, and the creature could have
known that at the time, from data it already had. **A `DETERMINED` that dies on the next point was
premature, and no truth function is needed to see it.** That is the version of this test the creature
can run on itself.

---

## 4. One prediction failed, and it failed informatively

D1 said `relu` on `{0,1,2}` would have a simpler rival (`y = x`) making the fit under-written. **There
is no rival**, because on that interval `relu` *is* `y = x` — the affine class already returns the
simplest member. I predicted a comparison that had nothing to compare.

Then the fix made it worse before it made it honest: allowing rivals fitted to *subsets* of the data,
every hypothesis became under-written by a constant fitted to a single point —

```
2x    under-written at 1/2     3x+1  under-written at 1/2     relu  under-written at 1/2
```

— which is the pre-registered stop condition, hit exactly. The one-point constant is the same
**degrees-of-freedom** failure that `mod 2` composing into two memorised constants hit in round 11 and
that the period-6 noise explanation hit in round 12. Third time. Constrained against it, the rival
check finds nothing at all, in any case.

So the honest result is a **negative one**: constrained to avoid degeneracy, the rival check cannot
distinguish a well-supported hypothesis from a truth the ontology cannot express. It is reported, and
its docstring and its test both say that absence of a rival is a statement about the **ontology**, not
about the world.

---

## 5. Why this is the deepest available move

The pattern across fourteen rounds is now unmistakable. Each round fixed a real defect, and each fix
was another way of being careful *inside* a language whose primitives I chose. The checks multiplied:
grouping, coverage, ontology exhaustion, degrees of freedom, refutation, domain. Every one of them is a
check on internal consistency, and **internal consistency cannot be tested from inside** — which is
precisely why a fit score can be made arbitrarily convincing while the thing is wrong.

Held-out prediction is the only measurement in this whole session that can fail while the machinery
believes it is right, and it is now the first thing reported rather than an afterthought. That is
worth more than the previous three rounds combined, and it took twenty lines to ask.

**Non-claims.** No sentience. `42/45` is interpolation on five toy functions with a truth function; it
is not generalisation. The domain report bounds a claim, it does not support one. Prequential refutation
says a hypothesis died, not that a better one exists. The rival check is a negative result and is
labelled as one. `truth.achieved` false. $0.

---

## 6. Ranked next moves

1. **Make prequential the primary metric of every module**, not a report field. `demand_evidence`,
   `compose`, `recover` should each be scored on how often their output survives the next real
   observation, and a `DETERMINED` that dies there should be counted as an error rather than a
   surprise. That is the only number in this repository that can go down when the machinery fools
   itself.
2. **Decompose domain failure.** `relu` on `x >= 0` is unlearnable in principle — the data contains no
   information about the other side. Distinguish that from `floor`, where a *probe at a fractional
   input* would settle it immediately. One is an absence of data; the other is an absence of curiosity,
   and only the second is a defect.
3. **The degrees-of-freedom rule has now been rediscovered three times** (rounds 11, 12, 14). It should
   live in one place and be impossible to bypass, not be re-derived per module.
4. Persist the record across processes; feed induced bodies into `demand_evidence`; the front door.
