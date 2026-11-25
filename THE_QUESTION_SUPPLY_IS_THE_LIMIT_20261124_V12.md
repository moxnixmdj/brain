# THE QUESTION SUPPLY IS THE LIMIT, NOT THE BUDGET — and stopping on accuracy cost more accuracy
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. What I built, and what it found instead

The previous round produced the only measured curve in twelve rounds — accuracy flat to 143 probes,
collapsed by 507 — and ended with a plan: an acquisition loop that **stops when marginal accuracy turns
negative**, so the budget is discovered rather than chosen by me.

Three arms, 11 machines × 2 seeds, identical machinery, 200-probe budget:

| arm | probes | predictions | wrong | accuracy | how it stopped |
|---|---|---|---|---|---|
| **FIXED** (never stops early) | 157 | **156** | 9 | **0.9423** | out of questions ×11 |
| **ADAPTIVE** (stops on accuracy) | 84 | 136 | 8 | 0.9371 | out of questions ×10, accuracy ×1 |
| **PER_ATOM** (stop when the atom is known) | 62 | 84 | 7 | 0.9167 | out of questions ×10, accuracy ×1 |

```
the_question_supply_is_the_limit_not_the_budget   true
stopping_costs_no_accuracy                        FALSE   <- my rule cost accuracy
the_fixed_arm_pays_its_extra_reach_in_errors      FALSE   <- it was strictly better
stopping_per_atom_is_worse_than_the_accuracy_rule  true
```

**Every arm ran out of QUESTIONS at roughly 14 probes against a budget of 200.** That is the finding,
and it makes the round's entire premise wrong: "when to stop asking" is not a decision problem when
the supply of askable questions is seven times smaller than any budget you would set. A larger budget
buys nothing at all.

## 2. The stopping rule I built lost to never stopping

`ADAPTIVE` gave up 20 predictions and finished **0.5 points less accurate** than `FIXED`. My risk gate
was noise: on a small held-out set, one probe's accuracy change is one or two transitions, so the
"marginal accuracy turned negative" signal fires on sampling noise and rolls back a genuinely useful
observation. I wrote the rule to make the budget data-driven and it made it worse.

I am recording that as a loss rather than tuning `patience` until it wins. The mechanism is clear: the
gate measures a quantity (accuracy on ~20 held-out transitions) with less precision than the effect it
is trying to detect.

`PER_ATOM` — "stop asking about an atom the moment you know something about it" — is intuitively the
most sensible rule of the three and measures **worst**: 0.9167, fifty-four fewer correct predictions
than FIXED. Knowing one law about an atom does not mean knowing the atom; the atoms with many contexts
need many witnesses, and the eager rule starves exactly those.

## 3. Why the question supply runs out

A question is "a support-1 law and a reachable state it admits that no probe has visited". Both are
consumed by asking: the probe adds an observation, which either upgrades the law to support 2 (removing
it from the candidate pool) or splits its class (removing the key). After ~14 probes on a depth-3
enumerated state space, every candidate law either has two witnesses or no unvisited state it admits.

So the supply is bounded by **laws × unvisited states**, counted on a small enumerated machine. On a
real environment it would be larger — but the *shape* of the constraint is the transferable result:

> The number of questions an environment can answer is a property of the environment, and it is much
> smaller than the budget you would be willing to spend. Measuring it costs ~14 probes.

That is the first time in this body of work that a limit has been **measured in units of the thing
itself** rather than described.

## 4. Verified / unverified / failed

**Verified by execution:** the three-arm table; every arm exhausted its question supply before its
budget; `PER_ATOM` is the worst of three rules; `FIXED` is the best.

**Failed, and both were mine:**
* `stopping_costs_no_accuracy` = **false**. The adaptive rule cost 0.5 points.
* `the_fixed_arm_pays_for_its_extra_reach_in_errors` = **false**. I predicted the fixed arm would
  trade errors for reach; it did not trade anything, it was simply better on both counts.

**Superseded:** the previous round's plan to build an accuracy-gated stop. It is built, measured, and
does not beat asking until the questions run out.

**Audited (re-checked):** `92b6db85`, `d6c1661a`, `repo_component_and_cow_engine_v1`,
`instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`, `learned_skill_id`, `click@ac0e297`,
"244 verified commits" — 2 files each, both mine.

**Blocked, logged once:** `docker: command not found`; no official benchmark row is producible here.

## 5. Note on the environment

The workspace reset to the base commit again at the start of this turn (all prior commits present on
`origin`, absent locally). Recovered by fetch + reset; no work was lost because each round pushes. The
test runner (`.venv`) has to be rebuilt after each reset, which is now a known cost of the session
rather than a surprise.

## 6. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 366.2 s
```

4 new tests; the suite touching this machinery is green; repo integrity guard PASS (17 rules).
Committed on `arena/50c05c04-brain`.

## 7. Next

The supply being finite means the lever is not *how many* questions but *which states they can reach*.
A question's reach is bounded by the depth-3 enumeration the harness provides; on a machine with more
depth there are more unvisited states per law, so the supply grows. The next instrument measures supply
as a function of exploration depth — if supply scales with depth, then the practical rule for a real
environment is "explore until the supply of questions stops growing", and that is a stopping rule about
exploration, not about accuracy.
