# THE VOCABULARY HAS A PRICE, AND TWO PREDICATES ARE FREE
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The currency, defined before measuring

Lifting is the only mechanism in twenty rounds that ever moved coverage, and it was never optimised. So
this round prices the vocabulary itself: hold the walk at 120, add one predicate at a time, and record

```
reach_gained = predictions(with) - predictions(without)
wrong_added  = wrong(with)       - wrong(without)
price        = wrong_added / max(1, reach_gained)
```

Every added predicate can only make a key *more specific* (keys are conjunctions of satisfied
predicates), so a predicate can never create a law — only split one. A good split keeps both pieces true
and covers states the whole did not; a bad split makes the pieces disagree and the system refuses. That is
what the price measures.

## 2. The single-predicate table

| predicate added | reach | errors | price |
|---|---|---|---|
| `IDENT_SORTED` | **+2** | **0** | **0.0** |
| `HAS_REPEATED_IDENT_LENGTH` | **+2** | **0** | **0.0** |
| `CONTENT_SORTED` | −9 | −6 | — (loses reach, saves errors) |
| `ROWS_1`, `HAS_MANY_ROWS` | 0 | 0 | — (inert: their states already match a key) |

Two predicates buy reach at **zero** price. One trades 9 predictions away for 6 fewer errors. Two are
inert. That is the first time in this project a vocabulary change has been *priced* rather than argued
for, and it immediately shows the four categories a feature can be in.

## 3. The trap, and getting out of it

The best of all 1,023 subsets scores **0.9167 accuracy / 0.6689 coverage** against a 0.828 / 0.520
baseline. That number is worthless: it was selected on the same held-out transitions it is scored on, and
it is exactly the defect that produced the retracted V13 result.

So: **leave-one-machine-out.** Choose the subset using nine machines, then score it on the tenth.

| | predictions | wrong | accuracy | coverage |
|---|---|---|---|---|
| baseline vocabulary | 77 | 16 | **0.828** | **0.520** |
| selected subset | 93 | 12 | **0.886** | **0.628** |

**+5.8 accuracy points and +10.8 coverage points on a machine the choice had never seen.** The gain is
real and it is out-of-sample.

## 4. What is *not* a finding

The subset itself. Five of ten folds choose
`{CONTENT_SORTED, HAS_MANY_ROWS, HAS_REPEATED_IDENT_LENGTH, ROWS_3}`, two choose a variant with
`ALL_CONTENT_UNIQUE`, and three choose something else. Only `CONTENT_SORTED` appears in all ten.

So the honest statement is: **the vocabulary is improvable, the improvement is measurable out-of-sample,
and it does not pin down a particular subset.** Saying "these four predicates are the answer" would be
reading a 5-of-10 vote as a consensus. What carries the gain is not one subset — it is that the space of
conjunctions contains strictly better points than the five predicated I had been using, and a
leave-one-out estimate proves it without pretending to have found *the* point.

## 5. Where this leaves twenty rounds

| result | status |
|---|---|
| un-lifted laws: 0.126 coverage | superseded |
| **lifting: 0.70 (subset) / 0.628 (fixed split) for zero extra evidence** | **verified** |
| predicted vocabulary choice, out-of-sample: +5.8 accuracy, +10.8 coverage | **verified** |
| 11× the walk buys +0.155 coverage, yield per transition falling 7.5× | verified |
| selection policy among questions: a wash across three rules | verified |
| transfer by alignment, un-lifted or lifted | **failed** |
| guards for declining atoms | **failed** |
| accuracy-gated stopping | **failed** |
| `questions ~ states**0.41` with precision collapsing | **retracted** (vocabulary leak) |

One mechanism has ever paid, and it has now paid twice: **change what the learner can say, not how much
it hears.**

## 6. Verified / unverified / failed

**Verified by execution:** the single-predicate price table; the out-of-sample subset gain; the in-sample
number as an explicitly labelled upper bound; the instability of the chosen subset (5/10 folds).

**Unverified:** that this generalises beyond ten small machine worlds and ten candidate predicates. The
leave-one-out estimate is honest about *these* machines; it says nothing about a real filesystem or a real
repository, and I have no way to test that here.

**Not publishable:** any benchmark row — `docker: command not found`, logged once. Every number in this
series is an internal measurement; none is a claim about SWE-bench, Terminal-Bench, OSWorld, or any
external harness.

**Audited (re-checked):** `92b6db85`, `d6c1661a`, `repo_component_and_cow_engine_v1`,
`instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`, `learned_skill_id`, `click@ac0e297`,
"244 verified commits" — 2 files each, both mine; none is a commit or module in this repo.

## 7. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 161.0 s · 1023 subsets x 11 folds
```

4 new tests, including one that fails if the in-sample number is ever reported without its
out-of-sample counterpart. Guard PASS (17 rules).

## 8. Next

Two predicates are free and the conjunction space is worth more than the five I chose by hand. The next
instrument should ask where the conjunctions *stop* paying: increase the candidate predicate set to
include structural facts the relation vocabulary can already compute (ordering, prefix relations,
cardinality of ident sets) and measure the out-of-sample price curve as the set grows. The prediction to
beat is that the gain per added predicate falls, and the round that can quantify "how much vocabulary is
enough" has the thing this project has never had — a stopping rule for **representation**, derived rather
than declared.
