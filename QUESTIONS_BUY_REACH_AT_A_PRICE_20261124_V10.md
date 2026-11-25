# QUESTIONS BUY REACH AT A PRICE — 166 → 512 predictions, and the error rate goes 3.6% → 13.3%
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged; no model call or stored parameter this round.

---

## 1. Two measurements that had never been made

Before building anything I stopped guessing about *why* the system is silent, which nine rounds had
assumed but never counted.

**Every law is true on the class it claims.** Ten machines, 81 enumerated states, 43 laws at
support ≥ 2:

| projection | laws | true on their class | false |
|---|---|---|---|
| CARD | 14 | 14 | **0** |
| CONTENT_COUNTS | 10 | 10 | **0** |
| IDENT | 11 | 11 | **0** |
| IDENT_CONTENT_COUNTS | 8 | 8 | **0** |

**Soundness was never the problem. Width was never the problem.**

**The silence is a census, not a judgement.** Of 45 atoms across ten machines:

| | count |
|---|---|
| atoms with a two-witness law | **5** |
| atoms with laws, **all at support 1** | **40** |
| atoms with no law at all | 0 |

Of the 99 refusals on held-out transitions, **88 were `no law admits this state`** and 11 were covered.
So the learner is not refusing because it is careful — it is refusing because **40 of 45 atoms have
exactly one witness and nothing else.** Evidence is the binding term, and that is the one thing a
question can change.

## 2. The result, at three walk lengths and two seeds

| walk | A: walk only | C: + questions | probes |
|---|---|---|---|
| 40 steps | 5 predictions, 0 wrong | **96**, 25 wrong | 109 |
| 120 steps | 48, 3 wrong | **187**, 17 wrong | 209 |
| 200 steps | 113, 3 wrong | **229**, 26 wrong | 189 |
| **total** | **166, 6 wrong (3.6%)** | **512, 68 wrong (13.3%)** | **507** |

Refusals fell from **90.6% → 70.9%** of held-out transitions.

```
reach_more_than_doubles            true     (166 -> 512, 3.1x)
questions_buy_reach                true     (+346 predictions for 507 probes, 0.68 each)
questions_preserve_the_error_RATE  FALSE    (3.6% -> 13.3%)
questions_preserve_SOUNDNESS       FALSE
questions_pay_for_themselves       FALSE    (346 bought < 507 spent)
```

**Read honestly: this is the first 3× on reach in ten rounds, and it was not free.** The error rate
quadrupled. A system that says 3% wrong things about 9% of states and one that says 13% wrong things
about 29% of states are not obviously ranked; by the usual measure (correct answers per state seen) C
wins 512-68=444 against A's 166-6=160. By the standard this project has held itself to — *never claim
what you cannot verify* — A wins, because it is the only one that can say "I am never wrong when I
speak" and mean it.

Both are reported. Neither is called the answer.

## 3. Why the error rate had to rise, and it is a real mechanism

507 probes, **351 falsified and 156 confirmed**. Two thirds of single-witness laws are wrong the moment
they are tested. When a probe falsifies a law, this instrument does not delete it — it **adds the
observation to the evidence and re-learns**, which splits the class the law claimed. That produces many
narrow laws from evidence that now includes states *chosen by the learner*.

The states a learner probes are, by construction, the states nearest its current boundary — and the
held-out set is drawn from the same reachable space. So acquisition moves the boundary into the region
under test. That is not a defect to patch; it is what acquisition is, and it explains the whole trade
in one sentence:

> **A question buys coverage of the states you asked about and no others.**

The 0.68 predictions-per-probe figure is the honest price, and it is below 1 — one question buys less
than one answer.

## 4. What this changes about the plan

For nine rounds the bottleneck was described as "how do we get more laws". It is now two numbers, both
measured:

* **coverage** — 70.9% of held-out states still refused even after 507 questions;
* **precision at coverage** — 13.3% wrong once the boundary moves.

Any future mechanism has to move both at once, and the only class of mechanism not yet tried that could
do that is the one where a question is chosen to be *representative* rather than *adjacent* — i.e.
sampling that maximises disagreement with the held-out distribution instead of with the current
boundary. That is a different objective function from everything in this tree, and it is testable with
this instrument unchanged.

## 5. Verified / unverified / failed

**Verified by execution this round:**
* 43 of 43 two-witness laws are true on the class they claim. **0 false.**
* 40 of 45 atoms have laws only at support 1. **0 atoms are lawless.**
* Acquisition takes held-out reach 166 → 512 (3.1×) for 507 probes, and refusals 90.6% → 70.9%.
* 351 of 507 probes falsify the law they test — a 69% falsification rate.

**Failed, and it was my expectation:**
* "Acquisition preserves soundness." My earlier small-budget probe showed 134 predictions at 5.2%
  error and looked like a free lunch. At 507 probes across two seeds the error rate is **13.3%**.
  The small-budget result did not survive scaling, and the honest number is this one.
* `questions_pay_for_themselves` — 346 predictions bought for 507 probes. Below break-even.

**Audited from this prompt (unchanged from the last audit, re-checked):** `92b6db85`, `d6c1661a`,
`repo_component_and_cow_engine_v1`, `instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`,
`learned_skill_id`, `click@ac0e297` and the "244 verified commits" appear **only inside my own reports**
— 2 files each, both mine. None is a commit or a module in this repository.

**Blocked, logged once:** no Docker in this sandbox, so no official benchmark row can be produced here.

## 6. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 329.4 s
```

Two new instruments, 89 existing tests green, repo integrity guard PASS (17 rules). All committed on
`arena/50c05c04-brain`.

## 7. Next

The objective function, not the mechanism: select each question to **maximise disagreement with the
held-out distribution** rather than with the current boundary. If probing adjacency is what raised the
error rate from 3.6% to 13.3%, then probing representatives should raise coverage without paying that
price — and if it does not, then the trade in §2 is a law of this problem and the report will say so.
