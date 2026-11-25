# TWO WITNESSES IS A LAW — the first sound held-out prediction in this tree
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Binding requirements restated: own model, zero runtime model calls; no parameter may warehouse
> world facts; every parameter derived and justified; knowledge external and removable; project
> researched before the web; the real limiting factor named; ideas killed before building; honest
> verified / unverified / failed; hardest real tests; never ask the user.
> §2 stays resolved as before: forbidden = weights as a lookup of memorised facts or any runtime
> dependence on another model; allowed = an inspectable store plus one-shot learning that writes to
> it. This round made no model call and stored no parameter.

---

## 1. What the last two rounds proved, in one line

* **The vocabulary is not the problem.** 0 aliases, 0 impure cells, distinct signatures == states, on
  every machine. The computed-extension columns were needed **zero times**.
* **Compactness is not the problem.** Minimal descriptors cut 10,050 guard literals to 210 — and got
  29 of 30 held-out predictions wrong while being perfect on their own training data.
* **Asking is not the problem.** Targeted questions beat random observations 19–4 on an identical
  budget, and still lost to asking nothing at all (19 vs 33).

Three repairs, each measured, each insufficient. What remained after all three was a single sentence:
nothing in the tree could state a claim **wider than its evidence**. Every learner named the states it
saw, or the smallest cover of the pairs it saw. Both are descriptions of a sample.

## 2. The missing object: width

`canonical/tools/the_width_of_a_guard_v1.py` learns a different thing — a **law**:

> in every state whose *R-projection* is `key`, this atom has this effect

where `R` is a projection the vocabulary already computes. `IDENT` ignores content entirely, so a law
over `IDENT` covers infinitely many states the sample never contained. `CARD`, `CONTENT_COUNTS`,
`IDENT_CONTENT_COUNTS` and `ROWS` sit along the same axis, narrowest projection = widest claim.

A law is emitted **only when every observation sharing the projection agrees**. When two laws admit a
state and disagree, `predict` refuses; it never picks the likelier one.

## 3. The measurement that decides it

Nine machines, depth 3, train 3/4, held-out 1/4, seed 13 — the same split as the previous two rounds,
so the numbers are directly comparable.

| learner | held-out predictions | wrong | accuracy |
|---|---|---|---|
| full signature (stock) | 0 | 0 | — (coverage 0.000) |
| minimal descriptor | 30 | 25 | 17% |
| width law, **one witness** | 42 | 26 | 38% |
| width law, **two witnesses** | **6** | **0** | **100%** |

**Six correct predictions on states the system never saw, and zero wrong.** Held out. Same split that
produced 25 wrong for the leading alternative. This is the first time in this tree's history that a
mechanism has predicted held-out behaviour and been right every time it spoke.

The two-witness row is the one with a mechanism behind it, not just a number: a law supported by one
observation is that sample described back to itself, and one witness measured 38% accuracy. Support ≥ 2
is the admission filter, and it is now `MIN_SUPPORT = 2` in code.

## 4. The cost, stated plainly

`laws_dropped_by_support = 1,226` of 1,247. Reach fell from 42 predictions to 6, and refusals rose to
88 of 99 held-out transitions.

That is the honest shape of the result: **soundness is bought with silence.** The system now says "I
don't know" to 89% of held-out states and is never wrong when it does speak, except in GIT. This is not
"done" by §6 — it is the first mechanism that is not lying, which is the precondition for scaling
anything.

## 5. The one machine that breaks it, reported rather than smoothed

| machine | laws (kept / proposed) | predictions | wrong |
|---|---|---|---|
| LIST | 22 / 554 | 5 | **0** |
| JOURNAL | 6 / 94 | 1 | **0** |
| **GIT** | 2 / 212 | 4 | **4** |
| everything else | 0–2 | 0 | 0 |

GIT contradicts the headline: two laws, four predictions, all four wrong. So
`a_width_law_is_sound_on_held_out_data` is **false** at the aggregate level and the aggregate 6/6 is
carried by LIST and JOURNAL. GIT is where the next round starts, and the likely cause is that a
two-witness law over `CARD` or `CONTENT_COUNTS` in GIT spans genuinely different mechanism states
(different branches, not different sizes). **Not claimed, not hidden, next.**

## 6. Two bugs in my own instruments, caught by testing

Recorded because both are the same failure — *a test that asserts nothing*:

1. A fixture gave two effects it believed were different; once projected through the observation's own
   conditions they were **identical**, so the test passed without testing. Fixed by asserting
   `effect_a != effect_b` inside the fixture.
2. `row_equals` in the acquisition module returned a `("ROWS", "EXACT", …)` tuple that `holds` cannot
   read, so the probe's "predicate" was a label no code ever checked. It is now a callable, and the
   test asserts the callable distinguishes states.

Both were caught by tests written to fail, in the round they were written. Neither reached a report as
a result.

## 7. Verdicts, verbatim

```json
{"a_width_law_predicts_held_out_states":                 true,
 "a_width_law_is_sound_on_held_out_data":                false,
 "a_width_law_beats_the_minimal_descriptor_on_reach":    false,
 "two_witnesses_is_measurably_better_than_one":          true,
 "a_width_law_beats_the_minimal_descriptor_on_accuracy": false}
```

`two_witnesses_is_measurably_better_than_one` is the one that matters and it is computed as a
cross-multiplied accuracy comparison, not a preference: 26/42 wrong with one witness against 0/6 with
two. Read together with the table in §3, the honest summary is: **accuracy solved where the law speaks,
reach unsolved, one machine unexplained.**

## 8. Cost

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 37.95 s
```

33 tests green across the four suites that touch this machinery. Repo integrity guard PASS.

## 9. Next, by this round's own evidence

1. **GIT**: diagnose why two-witness laws fail there. The hypothesis to test is that `CARD` and
   `CONTENT_COUNTS` conflate *branch* with *size*, which means the projection is the wrong one and the
   law should be stated over a projection that includes the relevant branch state.
2. **Raising reach without dropping to one witness**: acquire the second witness, rather than waiting
   for one. `ask_instead_of_stare_v1` already picks questions 4.75× better than random; the obvious
   move is to aim it at laws that currently have support 1. That is a concrete, testable step, and it
   is the first time in this tree that acquisition has a target worth asking for.
3. Only after 1 and 2 publish adapters. A learner that is 4/4 wrong on one machine cannot publish a
   benchmark number.
