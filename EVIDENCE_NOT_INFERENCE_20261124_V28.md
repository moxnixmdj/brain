# EVIDENCE, NOT INFERENCE — the store binds to reality and cannot tell you what will matter
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project then web; name the
> real limiting factor; kill the idea before building it; verified / unverified / failed; hardest real
> tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The test I set myself, and the answer

V27 proved **binding**: flipping two recorded contrasts broke six real tests with a clean identity control.
Binding is not prediction. So: split the 49-entry store by function, learn from one half, predict which
held-out contrast will move a test — *before* running it.

40 contrasts considered, 28 with ground truth from intervention, **4 of 28 (14%) moved an outcome.**

| rule (scored on held-out functions) | accuracy | sensitivity | precision |
|---|---|---|---|
| learned single signal (`function_has_raise_ast`) | 0.7857 | **0.00** | 0.00 |
| always "does not matter" | 0.7857 | 0.00 | 0.00 |
| **STATIC: `at_position`** | 0.5000 | **1.00** | **0.30** |
| majority-class baseline | 0.7857 | — | — |

**The learned rule flags nothing.** It predicts "does not matter" on every row and ties the majority
classifier exactly. The one-line static rule is the only rule that catches any positive — 3 of 3 — and its
precision of 0.30 makes it useless to act on.

So the answer to the question is **no**: the store carries evidence, not inference. It can tell you what
*happened* and it cannot tell you what *will matter*. Saying that plainly is the deliverable.

## 2. I reproduced V25 in my own evaluation code, one round later

The first version of the metric reported the best signal at **0.7857 on held-out functions** and set
`the_store_can_predict_which_contrast_matters: true`. That number was the majority class.

V25 was the report where accuracy 1.0000 turned out to equal "always pass" at equal coverage, with zero
failures predicted. I wrote it, and one round later I built an evaluator that made exactly the same mistake —
because accuracy is the convenient number to compute and sensitivity is the one that carries the meaning.

**Third time in this project.** Mean-of-ratios coverage hid zero-prediction runs (V21); a selection objective
disagreed with its own price table (V23); a summary-line comparator was contaminated by wall-clock strings
(V27). The pattern is stable and worth naming as a standing rule:

> **The most convenient number to compare is usually not the one that carries the meaning.** Accuracy without
> a class breakdown, a summary line without its timings stripped, a mean of ratios without the denominators —
> each is a measurement that looks finished and is not.

`score()` now returns sensitivity, precision and the majority-class baseline together, and a test fails if a
future version drops them.

## 3. The honest state of the whole project, eight rounds

| finding | status | evidence |
|---|---|---|
| lifting moves coverage 0.126 → ~0.70 on ten machine worlds | verified, scope-limited | V16 |
| syntactic vocabulary transfers across codebases | verified | 0.9796 vs 0.9896, V24 |
| vocabulary predicts test outcome | **failed** | = "always pass" at equal coverage, 0 failures predicted, V25 |
| cross-machine law transfer (lifted or not) | **failed** | 42/50 wrong, V15/V16 |
| guards · saturating questions · accuracy-gated stopping | **failed** | V18, V20, V21 |
| behavioural entries earned by execution | verified | 49 entries, 22 raise-contrasts, all replayable, V26 |
| **entries bind to real outcomes under intervention** | **verified** | 2 of 4 move 6 tests, clean control, V27 |
| **entries predict which contrast matters** | **failed** | sensitivity 0.00, V28 |
| any benchmark row | **not producible** | `docker: command not found` |

What this adds up to, without decoration: this system can *learn a true thing about what code does* (earned,
replayable, binding) and it cannot yet *reason from what it learned to what it has not run*. That is the
difference between a memory and a model, and it is where the work actually stands.

## 4. Verified / unverified / failed

**Verified by execution:** 40 contrasts, 28 with intervention ground truth, 4 positive; learned rule
sensitivity 0.00 and majority-class tie; static rule sensitivity 1.00 at precision 0.30; every intervention
run passed its identity control before being counted.

**Failed, mine, this round:** the evaluation metric itself — a majority-class tie reported as a predictive
success, corrected within the round.

**Unverified:** whether a rule using more than one signal (a conjunction over `at_position`, `side_changes`,
arity) could lift precision above 0.5. With 4 positives I would be fitting noise; the honest statement is
that the sample cannot decide it, and I am not going to grow the sample until the metric is trustworthy.

**Not publishable:** any benchmark row. Nothing here is a claim about SWE-bench Pro, Terminal-Bench 4.0, or
OSWorld 2.0, and no comparison to any frontier model is made. The prompt's figures for those remain
unreproducible from this sandbox and are not repeated as if measured.

## 5. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 446.5 s (40 interventions x 3 runs)
```

4 new tests, including one that fails if sensitivity or the majority baseline is ever dropped from the score.
Guard PASS (17 rules).

## 6. Next

The metric is the bottleneck before the sample size is. The next round builds the evaluator this project
should have had ten rounds ago: every instrument reports accuracy, sensitivity, precision and its
majority-class baseline as a four-tuple, with a repo-wide guard that fails any new receipt whose headline
number lacks them. That is not a result — it is removing a recurring instrument defect, and three measured
misreads in eight rounds makes it the highest-value thing left that does not require Docker.
