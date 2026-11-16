# Why "learn once, replay forever, anywhere" fails — and the exact part of it that is true

**Answer in one line.** "Do it once → learned permanently → replay anywhere" is true about *capture* and
false about *action*: what a demonstration yields is a decision procedure plus a premise, and what
gets replayed is a plan that is only valid on the state it was proved on. Measured on this repository:
the operation stayed legal after a change in **230 of 230** two-step compositions, the recorded plan
was valid in **114 of 230 (49.6%)**, and **43 of 230 (18.7%)** replays produced a file that still
parses while quietly keeping the binding the operation claimed to have removed. Every one of the 114
correct replays had zero drift between proof and replay. So the permanent thing is the *method*; the
disposable thing is the *plan*.

---

## 1. What was asked, and what was actually measured

The claim under test has three separable parts, and each has to be measured against a different
failure. This document covers the fourth and last one — **state drift between proof and replay** — on
top of the three already measured in this branch's history:

| failure mode | what it predicts | where it was measured | result |
|---|---|---|---|
| identifiability | one trace ⇒ exponentially many hypotheses | `ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.json` | one demonstration: precision **0.069**, **297 dangerous errors of 319**; two chosen observations: precision **1.000**, 0 dangerous errors, recall 0.455; random observations: identified in **0 of 12** seeds |
| vocabulary insufficiency | the premise may not be expressible in the facts the system has | same receipt, `SEPARATION_IMPOSSIBLE` | **18** blocking sites share all 9 facts and still differ; the missing observable is named: *the rewrite-equality proof itself* |
| synthesis–verification asymmetry | replay covers only what was already derived | `ONE_DEMONSTRATION_REACH_20261116_V1.json` | the learned inline operation reaches **5.3%** of sites as-is, **86.3%** once rename is composed, **45.8%** combined; two identically-learned actions differ **16×** in reach |
| **state drift** | a plan is a function of the state, not of the operation | **this document**, `ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json` | **116 of 230 (50.4%)** recorded plans are stale; **43 (18.7%)** are silently corrupt; **114 of 114** correct replays had zero drift |

The new instrument (`canonical/swe_kernel/action_replay_under_change_v1.py`) has no model in it. It
finds real sites where the bundle's own learned `inline` operation actually performs (by running it,
not by pattern-matching the source), then takes **ordered pairs** of those sites in the same real file
— the charitable case for replay, because both steps are known to apply and the pair is a genuine
composition. For each pair it records three separate facts:

* does step A apply to the original file (so the pair is a legitimate composition at all);
* does step B still apply to the file **after** A — i.e. did the change destroy B's *premise*;
* does B's **plan** (the `difflib` line replacements B's own realization produced, replayed by line
  index onto the changed file) reproduce what applying B live to the changed file produces.

The third question is what "replay forever" means operationally, in a code file and in a GUI window
alike: re-issue the recorded action sequence onto a state that has moved.

**Receipt** (`canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json`), 4 independent
samples over `canonical/**/*.py`, corpus `sha256 03de2d51…b3315`, 546 eligible sites in 128 files, **230
ordered pairs in 57 files**:

| what the replay did | pairs | share |
|---|---|---|
| reproduced the live edit exactly (`REPLAY_MATCHES_LIVE`) | **114** | 49.6% |
| produced text that does not compile (`REPLAY_DOES_NOT_PARSE`) | **71** | 30.9% |
| **produced text that compiles and still binds the name the edit claimed to remove** (`SILENT_CORRUPTION`) | **43** | **18.7%** |
| compiled, edit landed, but not what live produced (`REPLAY_DIFFERS_BUT_HOLDS`) | 2 | 0.9% |

Per-sample staleness: 33/60, 32/60, 26/60, 25/60 — the rate is stable across samples
(42–55%), and it is a property of the population, not of one lucky sample.

---

## 2. The law the numbers give

**Drift decides replay, not legality.** In all 230 pairs the operation was legal on the changed file
(that is what makes the pair replayable) — legality survived the change **230 of 230**. What did not
survive was the plan's addressing. Every correct replay had `drift = 0`, i.e. the earlier step changed
nothing at or above the lines the plan addresses; **114 of 114**. Drift zero is *necessary*: of the 116
stale replays, 113 had drift ≠ 0 and only 3 had drift 0 — so zero drift is **not sufficient**, because a
plan can also be stale for reasons line numbers do not capture (a same-shaped edit landing on a
different statement).

The sharpest witness is one file with the same two operations in both orders
(`canonical/runtime/generic_goal_tool_effect_planner_v2.py`):

| order | status | drift |
|---|---|---|
| `build_planning_problem.later_required` **then** `_resource_overlap.right` | `REPLAY_MATCHES_LIVE` | 0 |
| `_resource_overlap.right` **then** `build_planning_problem.later_required` | `REPLAY_DOES_NOT_PARSE` | −313 |

Composition is not commutative in *safety*. Nothing about the two operations changed; the order
changed which lines the second plan addressed. A learned action is therefore not a macro. It is a
**decision procedure plus a premise**, and only a proof run on the state in hand licenses acting on
that state.

And the silent class is the dangerous one. In the corruption witness, the replay leaves the original
`rows = candidate_map.get(...)` binding in place **and** inserts the inlined `for` header — the file
parses, the loop runs twice over the same list, and the operation's own sentence ("this binding is
gone") is false. A test that only imports the module, or only checks the program's exit code, passes.
This is the same failure class the 2026 SWE evidence reports from the other direction: **29.0%** of
*passing* SWE-bench Verified patches retain code the human deletion removed, and a deletion-check
retrofit drops resolution **63.2% → 41.9%** (Guard-and-Go, Aug 2026).

---

## 3. What is real

* **Capture is cheap, permanent, and worth it.** A demonstration does yield a permanent, reusable
  *object*: the operation's decision procedure, its premise, and its cost. Storing it is bytes; the
  instruments in this tree cost **0 model calls and $0** to acquire and to re-verify. Nothing about
  "learn once" is wrong at the level of storage.
* **Abstractions transfer; recordings do not.** STAIR (2026) reuses *hierarchical plans* and lifts
  Lingxi to **81.2%** and **79.2%**, while unabstracted trajectory reuse transfers "substantially
  worse". This branch's reach receipt says the same thing in one number: inline alone reaches 5.3% of
  sites, inline composed with the *abstract* rename reaches 86.3%.
* **A proof, once found, is a forever-valid fact about the class it quantifies over.** The gate receipt
  (`LEARNED_SKILL_VERDICT_20261116_V1.json`) shows a learned condition that is *checked* (witness +
  sentence + scope) accepts **4/4** true and **12/12** impostors, while conditions that are merely
  *remembered* accept the impostors (`stdout_equals` 0/4 and 0/12). Permanence belongs to the
  verifier, not to the plan.
* **Composition works when the second premise is re-checked against the first step's effect.** In these
  230 pairs the second operation remained legal every time — i.e. the *composition* is available; a
  system that re-decides gets both steps, and a system that replays gets one step and a corrupt file.

## 4. What is false

* **"One demonstration identifies the action."** False with a number: precision 0.069, 297 dangerous
  errors out of 319 held-out sites, and a deliberately *empty* requirement survives one point. This is
  the identifiability problem and it is structural — one example is consistent with ~10^100 programs in
  the programming-by-example literature, and exact equivalence of programs is undecidable.
* **"Learned permanently" as *authority to act*.** False: a learned condition may **veto**, never
  **license**. Licensing is the proof's job. Every measured arm where a learned rule was allowed to
  license produced dangerous errors; the arms where it only vetoed produced none.
* **"Replay anywhere."** False at 50.4% staleness, and false *silently* at 18.7%. The plan is bound to
  the state; a changed file, a changed window, a changed database row, a mid-run human edit are the same
  phenomenon. SWE-Touch (Aug 2026) measures the human-edit version: injecting a plausible mid-run repo
  edit cuts resolve by **7.7 points** across 9 models and **63.3%** of flipped runs end in *Retained
  Conflict* — the agent never re-read the region that changed. **59.0%** of real SWE-chat sessions contain
  exactly such edits. An agent that replays is structurally unable to see them.
* **"Anywhere" includes computer use.** OSWorld 2.0 (2026) puts binary success at **44.3%** with a median
  workflow of ~318 tool calls; at a per-step reliability of 0.995 a 318-step workflow succeeds
  **0.20** of the time. A replayed action sequence inherits *every* step's premise; a re-decided one
  only inherits the ones it re-checks. The dominant OSWorld-2.0 failure modes — dropping a constraint,
  missing information that appears mid-task, guessing instead of asking, skipping verification — are
  all premise failures, not knowledge failures.
* **"Advanced SWE" as replay.** Replay covers 2.2% of SWE-bench Verified, and the part it does not cover
  is the part that decides the score: real tasks need new edits grounded in the live environment. Even
  the *location* half is hard (right file >92%, right lines 44.6–51.6%) and refactoring benchmarks top
  out around 41%.
* **"Learn from the trajectory."** A SWE-bench trajectory averages 48.4K tokens / 40 steps and 22–30% of
  it can be dropped while *raising* Pass% to 66.5 — most of a recording is waste, so "learn the
  trajectory" mostly learns noise. Learn the abstraction, discard the trace.

---

## 5. The single bottleneck

Not capture, not storage, not retrieval, not speed. **The premise, re-proved on the live state's
observables.** Everything else is downstream and cheap; this one thing is what all four failures are
about:

1. *Identifiability* — the premise cannot be inferred from one point (0.069 precision).
2. *Vocabulary insufficiency* — the premise may not be expressible in the facts at hand (18 sites, the
   missing observable named).
3. *Synthesis–verification asymmetry* — the premise of a *new* edit cannot be read off a stored one
   (5.3% vs 86.3% reach).
4. *State drift* — the premise that was proved is a premise *about a state* (50.4% stale, 18.7% silent).

They are one bottleneck seen from four sides: **the system must decide, per instance, whether the
premise holds — and that decision needs an observation the representation contains.** Where the
observation exists, learning buys speed (it ranks what to check, and vetoes what is certainly wrong).
Where it does not exist, learning buys nothing and the certificate must say so out loud.

---

## 6. Architecture consequence

**Re-decide → prove → act.** A learned action ships as three things, never as a recording:

* the **decision procedure** (what to do, parameterised — `inline(function, variable)`);
* the **premise** (what must be true of the state, as a predicate over observables);
* the **cost** (what checking and doing will take).

At execution: evaluate the premise **on the state in hand**, run the proof, apply the realization the
proof produces, then re-read the result and check the *sentence* the operation claims (`edit_landed`
in this instrument: the binding is gone). The recorded plan is at most a **hint** that saves search; it
never carries authority, and it is validated by the postcondition, not by its provenance.

For composition: the second step's premise must be re-checked against the **effect** of the first step,
not against the state the first step was learned on. This is exactly what the 230 pairs test, and it is
where a 49.6% success rate turns into 100% — because the 230 of 230 legality is available, and only the
addressing failed.

Weights carry exactly three decisions and no knowledge: **which observation to take next** (expected
information gain, `contrast_selection_v1`), **which observable is missing** when the insufficiency
certificate fires, and **the features of the premise predictor** — which may veto, never license.

---

## 7. Verdict and the next four falsifiable moves

**Verdict.** "Do it once → learned permanently → replay anywhere" does **not** solve computer use or
advanced SWE. It solves a real and useful sub-class: actions whose premise is decidable from observables
the representation has, applied to states that have not moved under the plan. That sub-class is bounded
by measurement, not by opinion: 49.6% of honest compositions here, 2.2% of SWE-bench Verified for pure
replay, ~44% binary on OSWorld 2.0 for the best re-deciding agents. The true statement is the weaker,
more useful one: **learn the method once, prove the premise every time, and let the plan be disposable.**

1. **Drift-invalidation, measured.** Fingerprint the region a plan touches; refuse the replay when the
   fingerprint changed. Falsifier: it must remove the 113 drift-≠0 stalenesses *and* not be sold as
   complete — the 3 drift-0 stale cases survive it by construction. Target: silent corruptions 18.7% → 0
   by making every replay postcondition-checked, with the fingerprint only as a speed filter.
2. **Premise re-check on the effect, not on the record.** Re-run the 230-pair protocol with the second
   premise evaluated against step A's *effect* (this run already shows 230/230 legality is available).
   Falsifier: any pair where the re-check passes and the live application then fails its postcondition.
3. **Name the missing observable, then add it.** The `SEPARATION_IMPOSSIBLE` certificate says the missing
   fact is the rewrite-equality proof itself. Add exactly that observable and re-measure recall against
   the 0.455 obtained from `first_computed ∧ read_once`. Falsifier: recall rises while dangerous errors
   stay 0 — if dangerous errors rise, the fact was not the missing one.
4. **Human-edit injection, our own.** Imitate SWE-Touch on our own suite: inject a plausible mid-run edit
   and require the agent to re-read the touched region before acting. Falsifier: any run that accepts a
   plan whose region fingerprint changed; any run reported as resolved whose patch retains code the
   deletion removed (the Guard-and-Go check).

Each move is a measurement with a kill condition, and none of them adds a parameter, a store, or a
retrieval index. The best part is no part.

---

## Reproduce

```bash
python3 canonical/swe_kernel/action_replay_under_change_v1.py \
  --pattern 'canonical/**/*.py' --pairs 60 --candidates 1400 --samples 4 \
  --json canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json
python3 -m pytest canonical/tests/test_action_replay_under_change_v1.py
```

Authority is `NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT`: producer-run, 0 model calls, $0, no benchmark or
terminal credit claimed. Independent verification remains open.
