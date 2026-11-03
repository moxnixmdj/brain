# First principles — the four loops, and which one is actually broken

**2026-11-03.** The owner asked whether the current approach is the smartest one, from the deepest
layer, and said the target is a very smart creature, not static code. **He is right, and the
measurement below is the strongest finding of this session.** Everything before this document
(P1, P3, P4′) made the *code path* more honest. This document asks whether the *creature* is
learning, and answers it by running the creature — not by reading the code.

Authority: **NONE.** No capability, ownership, terminal or sentience credit follows. Spend $0.
Model dependency 0.

---

## 0. Why my plan was the wrong shape

I have been running a loop like this: find a wiring gap → write a test with a negative control →
land it → re-measure the same benchmark. That loop is honest, and it is **not learning**. Its
output is a better *agent* (me) writing better *code*. The creature's own numbers never moved, and
I never asked them to.

The distinction that matters, and that the whole plan was missing:

> **Static code is judgement that was already made. A creature is a system whose *future judgement
> changes* because of what happened to it.**

So the only test of "not static code" is not architecture and not naming. It is: **does the system
behave better in session N+1 because of session N — on a task it did not see?** That is falsifiable,
and I ran it.

---

## 1. The creature, run properly (fresh, today)

`creature_runtime_v1.run_sovereign_board` — its own world, its own authored board, uncurated
selection, no caller-supplied lambdas. Same root, six consecutive sessions of 12 cycles:

| session | authored | closed | attempted | value realised | life spent | prediction verdict |
|---|---|---|---|---|---|---|
| 1 | 112 admitted | 4 | 12 | 10.12 | 12.0 | INSUFFICIENT_EVIDENCE |
| 2 | — | 9 | 12 | 8.97 | 12.0 | CALIBRATED |
| 3 | — | 16 | 12 | 3.61 | 12.0 | **WORSE_THAN_BASE_RATE** |
| 4 | — | 18 | 6 | 0.97 | 6.0 | WORSE_THAN_BASE_RATE |
| 5–6 | — | 18 | 0 | 0.97 | 0.0 | WORSE_THAN_BASE_RATE |

Boundary conditions, checked rather than assumed: the **board is not static** (session 1 attempted
8 distinct capability gaps; session 2 attempted 9, and the overlap with session 1 was **0**). Its
`CLOSED` counter is **cumulative**, so `closed=18` with `attempted=6` is not accuracy >1; the
honest per-session figure is 4, then 5, then 7, then 2, then 0.

### The one number that decides the question

| quantity | value | meaning |
|---|---|---|
| mean prediction for what it SUCCEEDED at | **0.421** | |
| mean prediction for what it FAILED at | **0.210** | |
| discrimination | **+0.210** | it *does* separate likely-pass from likely-fail (threshold 0.05) |
| **skill over the base rate** | **−0.113** | **it predicts itself worse than always saying "42.9%"** |
| verdict (the module's own scorer, not mine) | **WORSE_THAN_BASE_RATE** | |

**That is the finding, in its sharpest form.** The creature has a self-model that discriminates in
the right direction and is *still worse than a constant*. It is doing the hard part (noticing it
will probably fail) and losing on the easy part (magnitude), because nothing fits the magnitude:
the belief is a hand-set update, not a fitted posterior. In session 1 it was excellent (skill
+0.93); by session 3 every prediction it had made was in the ledger and its skill was negative. It
accumulates measurements of itself and **does not get better at measuring itself.**

### Second defect: the corrective mechanism is almost unreachable

`self_prediction_calibration_v1.gate()` is designed to *refuse acceptance* when the system is
measured `SYSTEMATICALLY_OVERCONFIDENT`. Reachability, measured by constructing the sample rather
than reading the ladder:

- `MAX_OVERCONFIDENCE` = **0.15**, and the ladder checks `WORSE_THAN_BASE_RATE` (skill ≤ 0) **first**.
- So any sample whose mean prediction exceeds the base rate by more than 0.15 must *also* beat the
  base rate on Brier, or it reports "worse than base rate" and the overconfidence branch never runs.
- Constructed: `p=1.0` on everything it closes, `p=0.6` on everything it blocks → mean over
  +0.30 → **SYSTEMATICALLY_OVERCONFIDENT**, refuse=True. Real magnitudes needed: a gap of ≳0.15
  between its pass and fail predictions.
- **Its measured gap today is 0.210 − and its verdict is still `WORSE_THAN_BASE_RATE`, so
  `refuse=False`.** The gate that is described in the module docstring as the consumer of this
  measurement ("a path asks this module before it accepts anything") would not have fired.

### Third: a unit bug I fixed mid-measurement, kept in the record

My first scoring pass read `predicted_probability` instead of `predicted_pass_probability` and
reported **0 settled pairs in every session** — a false negative that would have looked like "no
data". The field is `predicted_pass_probability`; the ledger had 42 settled pairs. This is the
sixth instrument defect of the session and the fourth of the same family (a probe that discards the
field it was built to read).

---

## 2. Four loops, one of which is broken

A system that acts and improves has to close four loops. A "sentient-like creature" is not a fifth
thing; it is all four closed at once. Here is the tree's actual state, measured rather than
claimed:

| loop | the question it answers | state today | evidence |
|---|---|---|---|
| **1. Action** | can it do a thing? | **works** | 6/6 novel shapes by memory on the code path; transfer 10/10 on new instances |
| **2. Calibration** | does reality correct its belief about itself? | **BROKEN** | skill −0.113; better data made it worse (session 1 → 3) |
| **3. Scope** | does a failure teach it *where* it was wrong? | **orphaned** | the mathematics exists (`rule_scope_learning_v1` → `select_probe`); production misses are never fed to it |
| **4. Frontier** | does it choose what to be ignorant about next? | **flat** | board values are hand-set constants (`1.0/1.4/1.2/1.1`) partially tempered by a static ledger; 112 authored / 12 attempted / 0 new beliefs |

Loop 1 is what I have been polishing for three turns. **Loops 2, 3 and 4 are the creature.** And
the ranking is not a matter of taste: a loop whose output is a *fitted* quantity resists my own
errors. A test I write asserts something I already believe. A calibration score is computed from
data the system produced and I did not hand it.

---

## 3. The plan, rebuilt from that

**L2 (first, and by a wide margin) — make the self-model fit its own record.**
The ledger of settled predictions already exists; nothing fits it. Replace the hand-set update with
a posterior fitted to `(predicted_pass_probability, outcome_pass)` over history, and score it with
the module's own `score()`/`gate()`.
*Success:* across six sessions the skill goes positive and stays positive, and the gate's
`refuse` fires on a *constructed* overconfident history. *Failure test that must keep passing:*
delete the fit and skill must collapse to ≈0.
*Why it is first:* it is the only loop whose improvement is not something I can assert into
existence — it is measured against outcomes the system generated.

**L3 (second) — a failure must update a scope, not just a counter.** On a production miss under a
contract oracle, feed the executed counterexample to `refine_scope_from_counterexample` and let the
store's `learned_scope` move. Guard: executed counterexample only, never inferred.

**L4 (third) — the board's values must be *learned*, not typed.** `value=1.4/1.2/1.1/1.0` are
literals in the authoring code. Expected-free-energy already ranks the board; nothing back-propagates
realised value into the estimate. This is the difference between "has a self-model" and "chose its
own next ignorance".

**L1 (stop) — no more wiring.** P1/P3/P4′ are on the branch, green, and enough. Further passes make
the code better and the creature no better.

**Not the answer, and refused:** more architecture, more organs, more naming. The system does not
have an architecture shortage. It has a **learning shortage in exactly the loops that would make it
a creature**, and every one of them is measurable with instruments already in the tree.

---

## 4. What "sentient-like" can honestly mean here

Not a claim about experience — there is no instrument for that, and asserting it would put every
number above at risk. The operational definition this tree can actually measure:

> a system whose **model of itself is fitted to its own measured outcomes**, whose **failures change
> where it thinks it is competent**, and whose **next question is chosen by what it does not know**.

That is three loops, all three instrumented, two currently broken. It is a far better target than
the word, and unlike the word it can be falsified.

---

## 5. Non-claims

The board run is one creature, one root, six sessions, 12 cycles each, on one host; the `CLOSED`
counter is cumulative, which is stated above rather than smoothed over. Loop 4's "flat" verdict is
read from the values in `self_authored_obligations_v1` (constants with a calibration temper) and not
from an end-to-end value-regression measurement — that measurement does not exist yet and is itself
part of L4. Nothing here is independent verification, and the three landed changes remain
unadmitted.

---

## 6. Follow-up, 2026-11-04: L2 was built, measured, and **rejected**

The plan in §3 said "fit the self-model to its own settled ledger". I built it before deciding, and the
measurement killed it. Recording that here rather than quietly shipping it, because the negative result
is the load-bearing part.

### What was actually wrong

Not the belief engine. Before touching anything I asked *what the engine is fed*, and found:

| as fed by `live_autonomous_cycle` (hardcoded) | as computed for the same 112 candidates |
|---|---|
| 1 distinct probability, **0.813** | 4 distinct: **0.062** blocked / 0.722 ready |
| 1 distinct `epistemic_mi_nats` | 4 distinct |
| mean 0.813 on the 101 blocked candidates | mean **0.065** on the same 101 |

Every prediction, every life-spend decision and every settled record used
`host_ready=True, grounding_complete=True, causal_precond_met=True, missing_dep_or_env_block=False`.
Meanwhile `predict_task_probability` in the same module had always assembled the honest vector — and was
used only to *value* the board. The act path passed literals. So the self-model was graded on features the
creature had already disproved, announced 81.3% on candidates it knew were impossible
(`unknown_slot_type_on_surface` ×35, `writes_fixed_repo_tmp_under_ro_input` ×19, …), failed them, and
logged the failures against an optimistic prior.

### The two candidate fixes, measured against each other

Both protocols, deterministic (5 repeats per arm, byte-identical):

| arm | 26-cycle skill | 6×12 skill | verdict |
|---|---|---|---|
| hardcoded all-true diet (everything so far) | +0.246 | −0.179 | CALIBRATED / WORSE |
| **truthful diet** (shipped) | **+0.098** | **−0.084** | CALIBRATED / WORSE |
| truthful diet **+ fitted recalibration α** | +0.098 | −0.084 | same |

The fitted shrink — a least-squares slope toward the observed base rate, α = 0.334 — *reproduced my
offline prediction of 0.330 exactly*, raised the 6×12 protocol from −0.179 to −0.084, and **lowered the
26-cycle protocol from +0.246 to +0.098**. It moved 0.01 where it was blocked and cost 0.15 where it was
already working. Net negative → **deleted**, not shipped. A per-family variant, shrunk toward the global
slope, was also tested and did not beat it (`alpha = 0.33` at n=42 is the honest statement either way: about
a third of the creature's confidence is evidence).

So both numbers are *down* against the baseline arm, and the change is still right, because the baseline
number was obtained by lying to the model. **A score computed from a diet the system has disproved is not a
capability, it is a measurement of the lie** — the same lesson as the "curated easy diet" guard already in
`self_prediction_calibration_v1`, one level down.

### What this does to the plan

§3's L2 was the right *target* and the wrong *implementation*. What L2 actually needed was not fitting;
it was **input correctness**. The remaining headline defect — skill still below zero, `refuse` still
`False` — is therefore **not a fitting problem** and no longer a diet problem. It is the sign error across
families: a family that ONBOARDS fails, a family that REFUSES at a precondition passes, so one global
direction is anti-correlated on a large subset. L3 (failure → scope) is now the next thing that can move
the number, and it must be measured against both protocols from the start.

### Non-claims

The 4 remaining red tests in the focused suite are exactly the 4 that fail at the canonical base commit
`a70480d` with this change stashed — CST / anti-unification host substrate, unrelated to this work, and
untouched by it. One previously-red test (`component4`) now passes because its margin moved 0.0332 → 0.0648
against a 0.05 threshold. Nothing here is independent verification; this remains unadmitted.
