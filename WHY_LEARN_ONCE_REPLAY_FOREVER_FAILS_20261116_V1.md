# Why "learn once, replay forever, anywhere" fails — and the exact part of it that is true

**Answer in one line.** "Do it once → learned permanently → replay anywhere" is true about *capture* and
false about *action*: a demonstration yields a decision procedure plus a premise, while what gets
replayed is a plan that is only valid on the state it was proved on. Measured on this repository: the
operation stayed legal after a change in **228 of 228** two-step compositions, the recorded plan was
valid in **106 of 228 (46.5%)**, and **71 of 228 (31.1%)** replays produced a file that still parses
while keeping the very binding the operation claimed to have removed. Every one of the 106 correct
replays had zero drift between proof and replay. The permanent thing is the *method*; the disposable
thing is the *plan*.

---

## 1. What was asked, and what was actually measured

The claim has three separable parts, and each fails for a different reason. Three of those failures are
already measured in this tree; this document adds the fourth.

| failure mode | what it predicts | where it was measured | result |
|---|---|---|---|
| identifiability | one trace ⇒ exponentially many hypotheses | `ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.json` | one demonstration: precision **0.069**, **297 dangerous errors of 319**; two chosen observations: precision **1.000**, 0 dangerous errors, recall 0.455; random observations: identified in **0 of 12** seeds |
| vocabulary insufficiency | the premise may not be expressible in the facts at hand | same receipt, `SEPARATION_IMPOSSIBLE` | **18** blocking sites share all 9 facts and still differ; the missing observable is named: *the rewrite-equality proof itself* |
| synthesis–verification asymmetry | replay covers only what was already derived | `ONE_DEMONSTRATION_REACH_20261116_V1.json` | the learned inline operation reaches **5.3%** of sites as-is, **86.3%** once composed with rename, **45.8%** combined; two identically-learned actions differ **16×** in reach |
| **state drift** | a plan is a function of the state, not of the operation | **this document**, `ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json` | **122 of 228 (53.5%)** recorded plans stale; **71 (31.1%)** silently corrupt; **106 of 106** correct replays had zero drift |

The new instrument (`canonical/swe_kernel/action_replay_under_change_v1.py`) contains no model. It finds
real sites where the bundle's own learned `inline` operation actually performs — by running it, not by
pattern-matching the source — and then takes **ordered pairs** of those sites inside the same real file.
That is the charitable case for replay: both steps are known to apply, so the pair is a genuine
composition rather than a guess about applicability. For each pair it records three separate facts:

* did step A apply to the original file (so the pair is a legitimate composition at all);
* does step B still apply to the file **after** A — i.e. did the change destroy B's *premise*;
* does B's **plan** (the `difflib` line replacements B's own realization produced, replayed by line
  index onto the changed file) reproduce what applying B live to the changed file produces.

The third question is what "replay forever" means operationally — in a code file and in a GUI window
alike: re-issue a recorded action sequence onto a state that has moved.

**Receipt** (`canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json`): 4 independent
samples over `canonical/**/*.py`, corpus `sha256 dbfd2a3d…3cf6` (5,562 files, commit `c3a4c75e`), 509 eligible sites, **228 ordered pairs
in 62 files**:

| what the replay did | pairs | share |
|---|---|---|
| reproduced the live edit exactly (`REPLAY_MATCHES_LIVE`) | **106** | 46.5% |
| produced text that does not compile (`REPLAY_DOES_NOT_PARSE`) | **47** | 20.6% |
| **compiled, and still binds the name the edit claimed to remove** (`SILENT_CORRUPTION`) | **71** | **31.1%** |
| compiled, edit landed, but not what live produced (`REPLAY_DIFFERS_BUT_HOLDS`) | 4 | 1.8% |

Per-sample staleness: 35/60, 30/60, 27/60, 30/60 — 45–58% across four independent samples. The rate is a
property of the population, not of one lucky sample.

---

## 2. The law the numbers give

**Drift decides replay; legality does not.** In all 228 pairs the operation was legal on the changed
file — that is what makes the pair replayable — so legality survived the change **228 of 228**. What did
not survive was the plan's addressing. Every correct replay had `drift = 0`, i.e. the earlier step
changed nothing at or above the lines the plan addresses: **106 of 106**. Drift zero is *necessary* and
not *sufficient*: of the 122 stale replays, 118 had drift ≠ 0 and **4 had drift 0**, because a plan can
also be stale for reasons line numbers do not capture (a same-shaped edit landing on a different
statement).

The sharpest witness is a single file with the same two variables in both orders
(`canonical/capabilities/internalized/causal_falsification/agent_replay_v1/agent_replay/stats.py`):

| order | status | drift |
|---|---|---|
| `bootstrap_diff_interval.high` **then** `wilson_interval.high` | `REPLAY_MATCHES_LIVE` | 0 |
| `wilson_interval.high` **then** `bootstrap_diff_interval.high` | `SILENT_CORRUPTION` | −33 |

This is not a corner: **28 of the 62 files** in the sample contain both a replay that matches live and a
replay that silently corrupts. Composition is not commutative in *safety* — nothing about the operations
changed, only which lines the second plan addressed.

A learned action is therefore not a macro. It is a **decision procedure plus a premise**, and only a
proof run on the state in hand licenses acting on that state.

The silent class is the dangerous one. In the corruption witnesses the replay leaves the original
binding in place **and** inserts the inlined statement where the plan expected it — the file parses, the
work happens twice, and the operation's own sentence ("this binding is gone") is false. A test that
imports the module, or that reads the program's exit code, passes. The 2026 SWE evidence reports the
same class from the other side: **29.0%** of *passing* SWE-bench Verified patches retain code the human
deletion removed, and a deletion-check retrofit drops resolution **63.2% → 41.9%** (Guard-and-Go).

---

## 3. What is real

* **Capture is cheap, permanent, and worth it.** A demonstration does yield a permanent, reusable
  *object*: the operation's decision procedure, its premise, and its cost. Storing it is bytes; the
  instruments in this tree acquire and re-verify such an object for **0 model calls and $0**. Nothing
  about "learn once" is wrong at the level of storage.
* **Abstractions transfer; recordings do not.** STAIR (2026) reuses *hierarchical plans* and lifts
  Lingxi to **81.2%** and **79.2%**, while raw unabstracted trajectory reuse transfers "substantially
  worse". This branch's reach receipt says the same in one number: inline alone reaches 5.3% of sites,
  inline composed with the *abstract* rename reaches 86.3%.
* **A proof, once found, is a forever-valid fact about the class it quantifies over.** The gate receipt
  (`LEARNED_SKILL_VERDICT_20261116_V1.json`) shows that a condition which is *checked* (witness +
  sentence + scope) accepts **4/4** true cases and **12/12** impostors, while conditions that are merely
  *remembered* accept the impostors (`stdout_equals` 0/4 and 0/12). Permanence belongs to the verifier,
  not to the plan.
* **Composition is available; only the record is not.** In these 228 pairs the second operation remained
  legal every single time. A system that re-decides gets both steps; a system that replays gets one step
  and, 53.5% of the time, a stale file.

## 4. What is false

* **"One demonstration identifies the action."** False with a number: precision 0.069, 297 dangerous
  errors of 319 held-out sites, and a deliberately *empty* requirement survives a single point. The
  failure is structural: one example is consistent with ~10^100 programs in the programming-by-example
  literature, and exact program equivalence is undecidable.
* **"Learned permanently" as *authority to act*.** False: a learned condition may **veto**, never
  **license**. Licensing is the proof's job. Every measured arm where a learned rule was allowed to
  license produced dangerous errors; the arms where it only vetoed produced none.
* **"Replay anywhere."** False at 53.5% staleness and false *silently* at 31.1%. A changed file, a
  changed window, a changed database row and a mid-run human edit are the same phenomenon. SWE-Touch
  (Aug 2026) measures the human-edit version: injecting a plausible mid-run repo edit cuts resolve by
  **7.7 points** across 9 models, and **63.3%** of flipped runs end in *Retained Conflict* — the agent
  never re-reads the region that changed. **59.0%** of real SWE-chat sessions contain exactly such edits.
  An agent that replays is structurally unable to notice them.
* **"Anywhere" includes computer use.** OSWorld 2.0 (2026) puts binary success at **44.3%** over a median
  workflow of ~318 tool calls; at a per-step reliability of 0.995 a 318-step workflow succeeds about
  **0.20** of the time. A replayed action sequence inherits *every* step's premise; a re-decided one
  inherits only the premises it re-checks. The dominant OSWorld-2.0 failure modes — dropping a
  constraint, missing information that appears mid-task, guessing instead of asking, skipping
  verification — are premise failures, not knowledge failures.
* **"Advanced SWE" as replay.** Pure replay covers 2.2% of SWE-bench Verified, and the uncovered part is
  what decides the score: real tasks need new edits grounded in the live environment. Even the *location*
  half is hard — right file >92% but right lines only 44.6–51.6% — and refactoring benchmarks top out
  near 41%.
* **"Learn from the trajectory."** A SWE-bench Verified trajectory averages 48.4K tokens over 40 steps,
  and 22–30% of it can be dropped while *raising* Pass% to 66.5. Most of a recording is waste, so
  "learn the trajectory" mostly learns noise. Learn the abstraction; discard the trace.

---

## 5. The single bottleneck

Not capture, not storage, not retrieval, not speed: **the premise, re-proved on the live state's
observables.** All four failures are that one bottleneck seen from four sides:

1. *Identifiability* — the premise cannot be inferred from one point (0.069 precision).
2. *Vocabulary insufficiency* — the premise may not be expressible in the facts at hand (18 sites; the
   missing observable named).
3. *Synthesis–verification asymmetry* — the premise of a *new* edit cannot be read off a stored one
   (5.3% vs 86.3% reach).
4. *State drift* — the premise that was proved is a premise *about a state* (53.5% stale, 31.1% silent).

**The system must decide, per instance, whether the premise holds, and that decision needs an
observation the representation contains.** Where the observation exists, learning buys speed: it ranks
what to check and vetoes what is certainly wrong. Where it does not, learning buys nothing — and the
certificate must say so out loud instead of guessing.

---

## 6. Architecture consequence

**Re-decide → prove → act.** A learned action ships as three things, never as a recording:

* the **decision procedure** (what to do, parameterised — `inline(function, variable)`);
* the **premise** (what must be true of the state, as a predicate over observables);
* the **cost** (what checking and acting will take).

At execution: evaluate the premise **on the state in hand**, run the proof, apply the realization the
proof produces, then re-read the result and check the *sentence* the operation claims (`edit_landed` in
this instrument: the binding is gone). A recorded plan is at most a **hint** that saves search; it never
carries authority, and it is validated by the postcondition rather than by its provenance.

For composition, the second step's premise must be re-checked against the **effect** of the first step,
not against the state the first step was learned on. That is exactly what these 228 pairs test, and it is
where a 46.5% success rate becomes 100%: legality is available in 228 of 228 pairs; only the addressing
failed.

Weights carry exactly three decisions and no knowledge: **which observation to take next** (expected
information gain, `contrast_selection_v1`), **which observable is missing** when the insufficiency
certificate fires, and **the features of the premise predictor** — which may veto, never license.

---

## 7. Verdict and the next four falsifiable moves

**Verdict.** "Do it once → learned permanently → replay anywhere" does **not** solve computer use or
advanced SWE. It covers a real and useful sub-class: actions whose premise is decidable from observables
the representation has, applied to states that have not moved under the plan. That sub-class is bounded
by measurement, not opinion — 46.5% of honest compositions here, 2.2% of SWE-bench Verified for pure
replay, ~44% binary on OSWorld 2.0 for the best re-deciding agents. The true and more useful statement
is the weaker one: **learn the method once, prove the premise every time, and let the plan be
disposable.**

1. **Drift-invalidation, measured.** Fingerprint the region a plan touches and refuse the replay when it
   changed. Falsifier: it must remove the 118 drift-≠0 stalenesses *and* must not be sold as complete —
   the 4 zero-drift stale cases survive it by construction.
2. **Postcondition as the only door.** Refuse to count any application whose claimed sentence
   (`edit_landed`) is false, and re-run these 228 pairs. Target: silent corruptions 31.1% → 0 with no
   loss of legality. Falsifier: a case whose postcondition passes and whose file is still wrong — that
   case proves the *sentence*, not the check, is the weak link.
3. **Premise re-check on the effect, not on the record.** Re-run the protocol with the second premise
   evaluated against step A's *effect*. Falsifier: any pair where the re-check passes and the live
   application then fails its postcondition.
4. **Human-edit injection, our own.** Imitate SWE-Touch on our own suite: inject a plausible mid-run edit
   and require the agent to re-read the touched region before acting. Falsifier: any run that accepts a
   plan whose region changed, or reports a patch as resolved while it retains code the deletion removed
   (the Guard-and-Go check).

Each move is a measurement with a kill condition, and none of them adds a parameter, a store or a
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
