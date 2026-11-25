# THE OBJECTIVE CHANGE BOUGHT NOTHING — and that is the useful result
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. What I predicted, and what happened

Last round ended with a specific claim: the error cost of acquisition was caused by **the objective**.
Adjacent probing moves the decision boundary into the region under test, so the fix is to probe
*representatively* — maximising disagreement with the distribution the system will be tested on rather
than with its own current boundary.

Measured, 11 machines × 2 seeds × 30-probe budget, scored on held-out transitions:

| arm | predictions | wrong | correct | accuracy | probes |
|---|---|---|---|---|---|
| A — walk only | 70 | 5 | 65 | 0.929 | 0 |
| **ADJACENT** (last round's rule) | **154** | 10 | **144** | **0.935** | 147 |
| **REPRESENTATIVE** (this round's rule) | **154** | 10 | **144** | **0.935** | 143 |
| RANDOM (control) | 113 | 6 | 107 | 0.947 | 70 |

```
representative_beats_adjacent_on_correct   false   <- my prediction, refuted
representative_beats_asking_nothing        true    (+79 correct predictions)
```

**The two selection rules are indistinguishable — identical reach, identical error count, and 143
versus 147 probes.** The objective change bought nothing, and the reason is structural rather than
statistical: both rules draw from the same admissible set (states a support-1 law admits and no probe
has visited), and once a probe removes its own state from that set, the choice of *which* admissible
state to visit first barely matters. A test now asserts exactly this overlap on the minimal case, so
it cannot be quietly re-litigated.

## 2. The finding that survived, and it is better than the one I wanted

Last round's headline was: *acquisition triples reach and the error rate rises 3.6% → 13.3%.*

This round, at 30 probes per machine instead of 507 across the corpus, **the error rate does not rise
at all**: 0.935 accuracy against the walk-only baseline's 0.929, with 2.2× the reach.

> **The cost of a question is not a fixed price. It is a function of how many you ask per state.**

At 507 probes the boundary gets moved into the test region repeatedly and accuracy collapses to 87%.
At 143 probes it does not move far enough to hurt, and reach more than doubles for free. That is a
curve, not a trade-off, and it is the first actionable result about budget in eleven rounds:

```
probes per machine     accuracy      reach
        0              0.929          70
      143              0.935         154     <- free
      507 (corpus)     0.867         512     <- paid for
```

## 3. What this means for the plan, stated without optimism

* **Acquisition pays up to a budget and then overfits.** The instrument now has that budget measured;
  the next version should stop when marginal accuracy turns negative rather than at a fixed count.
* **Selection policy is not the lever.** Two principled rules and a random control all land within
  1.8 points of each other on accuracy. Spending more effort on *which* state to probe is wasted.
* **Coverage is still 70%+ refused** even in the best arm. Questions buy reach; they do not buy
  understanding, and nothing in eleven rounds has changed that.

## 4. Verified / unverified / failed

**Verified by execution:** the four-arm table above, on 11 machines and two seeds; the structural
overlap of the two rules (asserted); accuracy at a 143-probe budget is statistically indistinguishable
from walk-only while reach is 2.2×.

**Failed, and it was mine:** `representative_beats_adjacent_on_correct` = **false**. The objective was
not the defect. I am recording this rather than re-running with a budget that would have flattered it.

**Superseded:** last round's framing that acquisition "costs 3.7× accuracy" is only true at ~500
probes. The corrected statement is in §2.

**Audited (re-checked this round):** `92b6db85`, `d6c1661a`, `repo_component_and_cow_engine_v1`,
`instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`, `learned_skill_id`, `click@ac0e297`,
"244 verified commits" — each appears in exactly **2 files, both of them mine**. None is a commit or a
module here.

**Blocked, logged once:** `docker: command not found`. No official benchmark row can be published from
this sandbox. This remains the only item outside my control.

## 5. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 134.9 s
```

4 new tests, all green; 89 existing tests green; repo integrity guard PASS (17 rules, 0 violations).
Committed on `arena/50c05c04-brain`.

## 6. Next

Stop choosing questions better and start choosing when to stop: an acquisition loop that halts when
marginal accuracy turns negative. That is measurable with the instrument already built, it is the only
curve in this body of work with a known shape, and it is what makes a budgeted learner usable on an
environment it cannot enumerate.
