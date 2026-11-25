# ONE EXPERIENCE, EVERY CONSEQUENCE

**Date** 2026-11-24 · **Branch** `arena/50c05c04-brain` · **Schema** `BRAIN_ONE_EXPERIENCE_EVERY_CONSEQUENCE_V1`
**Receipt** `canonical/verification/ONE_EXPERIENCE_EVERY_CONSEQUENCE_20261124_V1.json`
**Kernel** `canonical/swe_kernel/safe_action_model_v1.py` · **Instrument** `canonical/tools/one_experience_every_consequence_v1.py`
**Tests** 40 passing across three rounds · **Guard** 17 rules, 0 violations
**Cost** 0 model calls, 0 stored parameters, 0 network · 147 s · 9 machines · 27 problems · 1,571 transitions

---

## §0 Requirements read, and the §2 contradiction resolved

Bound by: own weights only, **zero model calls at runtime**, zero knowledge house (no memorized
world facts in parameters; every parameter computed and justified), knowledge from the project's
instant-knowledge store rather than weights, nothing borrowed presented as ours, hardest real
problems as tests, never stop, never ask, "best part is no part", research before building.

**The contradiction, resolved and then improved by evidence.** *Forbidden:* parameters as a lookup
of world facts; any runtime dependency on another model. *Allowed:* an external, inspectable,
editable store the system computes with, plus learning that writes to it from one experience.

This round changes the boundary **toward more safety, not more permission.** What the system stores
here is neither a fact nor a policy: it is a set of **constraints, each carrying the single
observation that licensed it**, and the planner may only act where the constraint admits the state.
The test the mission proposed — *knowledge outside the weights, addable and removable without
retraining* — is met exactly: deleting one transition deletes exactly one operator, and the
surviving table remains sound. That is stronger than the mission's test, so it is adopted.

---

## §1 Research findings

### 1.1 In this project (exhaustive, including non-obvious names)

* `canonical/swe_kernel/canonical_frame_v1.py` — the 5 relation frames; the only reader of a
  machine state. Reused, not rebuilt.
* `canonical/tools/frames_that_cross_machines_v1.py` — 9 real machines, 4 reused + 5 new.
* `canonical/swe_kernel/partial_order_planner_v1.py` — **my previous round**, the induce-then-plan
  kernel this round supersedes as the planning core.
* Composition family that already exists and is **not** failing: `proved_composition_v1`,
  `effect_contract_composition_v1`, `composition_verification_v1`, `plans_compose_v1`,
  `compose_a_host_never_seen_v1`, `hierarchical_skill_library_v1`, `operand_invention_v1`,
  `egraph_and_deductive_synthesizer_v1`.
* Grep counts that matter: `sample complexity` **0 files**, `action model` **1 file**,
  `held out` 189 files but almost all are unrelated benchmarks. The words this round is built on
  were absent from the tree. That is why it went to the literature.

Two files named in the requested execution sequence — `typed_invention_v1.py`,
`epistemic_scan_acquire_compress_v1.py` — **do not exist** in this repository, and neither does
commit `209bbc6c`. They were not invented.

### 1.2 In the literature (what changed the design)

* **SAM / N-SAM / N-SAM\*** (arXiv 2312.10705). "Safe" = every plan the learned model admits is
  consistent with the real system. N-SAM\* is **provably sample-complexity optimal** and includes an
  action **from a single observation** without losing safety. The same line of work proves the
  negative: **non-trivial safe models with conditional effects may need exponentially many samples**
  (Conditional-SAM, arXiv 2403.15251).
* **SAM+** — safe learning from partially observable observations.
* **LOCM / NSAM / lifted STRIPS from traces** (arXiv 2411.14995) — 5 traces of a few hundred actions
  per domain, learning types from argument positions.
* **OSWorld 2.0** — 108 long-horizon tasks, ~318 tool calls; best binary success 20.6%. Failure modes
  are implicit state, multi-item tracking, and trusting one's own summary over the environment.

**Why this mattered:** my previous round induced operators from whatever the sweep happened to see,
then let a planner cite them anywhere the guard matched. That is exactly an **unsafe** action model,
and its 8 refuted plans are the measured cost. The frontier's answer is not more data; it is the
safety property, and safety is what makes one observation enough to act on.

---

## §2 §3 verdict: what is real, what is not, and the real bottleneck

**Real, with numbers.**

| claim | evidence |
|---|---|
| A table learned from **one execution per atom** never predicted wrongly | 0 wrong, held-out transitions, 9 machines |
| The previous round's induction is unsafe | **32** wrong predictions on the same held-out sets |
| Safe one-shot plans execute and hold | **6** verified plans from one experience per atom |
| One experience buys **almost no reach** | 0 predictions on 101 held-out transitions; 21 refusals |
| My "refutation test" generalizer is unsound | 2 predictions, 2 wrong; 4/4 wrong under fire — **not shipped** |

**False or unproven.**

* "Do it once and it learns it permanently" is **half true**. *Soundly* it learns the consequence of
  that exact step, and can act on it. It does **not** generalize from it: at one observation the
  guard that keeps it sound is a description of the state it came from, so the operator applies
  essentially nowhere new.
* Generalization by probing was my own idea this round and it **failed**. One probe per dropped
  literal tests one state while the claim is about a region. Recorded, guarded by a test, and
  labelled unsound in the module.
* Anything resembling the mission's aspiration (arbitrary new environments, GUI, browser, hardest
  SWE) is **untouched** by this round. No benchmark was run and none is claimed.

**The real bottleneck, from first principles.** Not planning, not search, not the vocabulary — those
are measured and adequate. The bottleneck is **the number of *varied* observations per action**.
Safety forces the model to be narrow; reach forces it to be wide; evidence is the only thing that
widens it without losing safety. So the limiting factor is the *acquisition policy*: which states to
put the machine into so that each new observation buys the most admissible operators.

That reframes the mission's question. It is not "learn everything" or "learn goal-directed" — it is
**choose the next observation to maximise admissible reach per execution**. And it makes the
mission's own idea (scan, diff what you know against what you must know, fetch or probe the
difference) the right shape, but with a different objective than "know everything": one execution
should be worth the most *reach*.

---

## §3 The single plan, and rejected ideas

**Plan.** Build the safe core (induced from observations, refusing rather than guessing), measure 1-
vs 5- vs 10-shot against the previous round's induction on identical held-out data, then and only
then attempt reach — by evidence first, by probe second, and report the probe failure.

**Rejected, with reasons.**

| rejected | why |
|---|---|
| Learn the vocabulary too (relations as well as conditions) | The frame already separates states: 0 aliased groups on JOURNAL, VAULT, LIST. Building a learner for a component that is not failing is waste. |
| Ingest `--help` text, man pages, or the web into the store | Not measurable inside a *measured* environment: it would put unverified text behind a safety property that currently rests on execution. The right place for it is a different layer, and mixing them would destroy the one guarantee this round achieved. |
| CEGIS / backward program synthesis (the "reverse execution" idea) | Prerequisite is a safe model of the effect; that is what this round built. Doing synthesis first would be building on sand — and the repo already has `egraph_and_deductive_synthesizer_v1`, which is not the bottleneck. |
| Typed skill algebra over 447 capabilities | The composition family already exists (`proved_composition_v1`, `effect_contract_composition_v1`) and is not failing. Adding a type system would be a part with no measured defect behind it. |
| Adversarial self-play over the failure corpus | With 27 problems and no held-out protocol it would be a demo. The honest version needs a refutation loop that is *sound*, and this round showed the sound core does not generalize yet. |
| Generalization by "the goal needs it, so assume it" | That is precisely the unsafe move that produced 32 wrong predictions. It is now a forbidden pattern in the module, not a heuristic. |
| Keep the probe generalizer because the idea is attractive | It was measured unsound. Keeping it would be the exact failure mode this project exists to avoid. |

---

## §4 What was built

### 4.1 `safe_action_model_v1.py`

* `Observation` — one executed step. The unit of learning and the unit of proof.
* `specific_table` — one operator per `(atom, pre-state)`; guard = **every** condition true before.
  Deterministic-or-excluded: an atom with two effects from one pre-state is `CONFLICTED` and
  dropped, never averaged. Operators are **merged by guard**, because two states the vocabulary
  cannot tell apart are, to the model, the same state — without that merge the table was
  **ambiguous with itself** and refused everything it knew.
* `generalize` — drops a guard literal only when a *different observation* of the same atom shows the
  same effect. No witness, no drop.
* `apply` — three outcomes: applies, refuses (unobserved state), refuses (ambiguous). No fourth.
* `check_against_truth`, `generalization_under_fire` — the second **executes**.
* `generalize_by_probe` — kept, documented as measured-unsound, and never used to claim reach.

### 4.2 `one_experience_every_consequence_v1.py`

Nine machines, held-out transitions, 1/5/10-shot against the previous induction, three planners,
every plan forked and executed, verdicts computed from the receipt rather than written in prose.

---

## §5 Results

### 5.1 Prediction over 9 machines

| learner | predictions | **WRONG** | refused | sound |
|---|---|---|---|---|
| safe, **1 observation per atom** | 0 | **0** | 101 | ✅ |
| safe, 5 per atom | 0 | **0** | 101 | ✅ |
| safe, 10 per atom | 0 | **0** | 101 | ✅ |
| **previous round's induction** | 34 | **32** | 67 | ❌ |
| probe-generalized (mine) | 2 | **2** | 99 | ❌ |

The zero-prediction column is the finding, not a gap: a guard that names a whole state admits no
*other* state, so no held-out transition is covered. It is the sound-and-narrow point the theory
predicts, reported instead of engineered away.

### 5.2 Generalization under fire (a guard literal dropped, then executed)

| method | tested | right | **wrong** |
|---|---|---|---|
| evidence-based (positive witness) | 0 | 0 | 0 |
| probe-based (mine) | 4 | 0 | **4** |
| previous round's induction | 75 | 1 | **74** |

### 5.3 Planning (27 conjunctive problems)

| planner | verified plans | refusals |
|---|---|---|
| safe, one-shot | **6** | 21 |
| safe, ten-shot | **7** | 20 |
| forward search (control) | 24 | — |

Safe one-shot solves a quarter of what exhaustive search does, from **one execution per atom**, and
every one of its plans was executed and held. The refusals are the price of the guarantee, counted.

---

## §6 What this does not show

* **No benchmark.** No SWE-bench, Terminal-Bench, or OSWorld run. Nothing here is a benchmark score.
* **No GUI, no browser, no vision.** The sandbox has no browser and none was claimed.
* **No cross-environment transfer yet.** Operators are per-machine.
* **One experience is enough to be *right*, not enough to be *broad*.** That is the sentence this
  round can defend and the previous ones could not.
* The probe generalizer is a failure and is labelled one in the code and in the receipt.

---

## §7 The next bottleneck, and the plan for it

**Bottleneck: the acquisition policy.** Reach per execution is what is missing, and it is a choice
of *which states to visit*, not a better learner.

1. **Targeted observation**: choose the next probe state to maximise the number of guard literals a
   new observation can license. This is the missing piece, and it turns "one experience" into "one
   *well-chosen* experience" — the mission's idea, with an objective that is measurable.
2. **Probe budget that scales with the region claimed**: the failure this round showed precisely is
   one test for a region-sized claim. The fix is a size-aware budget, and it is testable against the
   same held-out protocol.
3. **Cross-machine carried guards**: the frame's vocabulary already crosses machines; carrying the
   *guards* rather than the vocabulary is the composition this round still owes.
