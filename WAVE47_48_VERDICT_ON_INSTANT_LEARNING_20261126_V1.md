# Verdict on §3: Instant Learning — What Is Real, False, Unproven, Missing

**Date:** 2026-11-26 · **Branch:** `arena/adb67314-brain` · **Base:** `3e652cf2`
**Authority:** NONE__PRODUCER_RUN_SANDBOX. Runtime model calls: 0. Spend: $0. `truth.achieved` stays `false`.

## The claim (§3)

> We already solved instant learning, including in new arbitrary environments. The agent does a task once in any new coding environment or computer task and learns it permanently. Combined with the strongest coding capability, this would solve computer use.

## Verdict: half true, half false — and the false half is the one that matters

**True (verified, permanently real):** Instant *retention* is solved, and strictly better than gradient descent. Acquisition is one observation, zero parameters, zero compute. Retention is exact (the object kept is the thing that happened, not a compressed approximation). It is reversible, auditable, deletable. It cannot catastrophically forget because nothing is overwritten. The field spends enormous effort to get worse versions of this: Skill0 (2026) retrieves then RL-internalizes; VERA (Oct 2026) builds 9,000+ verifiable environments and still updates weights; LaCT/LaCET (2026) need a base model + GPU + verification signal to get retention-in-weights. Nobody in 2026 has a retention mechanism as clean as Brain's external store. Evidence: `INSTANT_LEARNING_IS_PERFECT_AND_IT_IS_NOT_THE_BOTTLENECK_20261116_V1.md`, `INSTANT_LEARNING_IS_REAL_THEREFORE_EVERYTHING_IS_NOT_20261117_V1.md`, `WHY_WEIGHT_SPACE_IS_NOT_THE_MISSING_LAYER_20261112_V1.md` (29.45% same-kind coverage from one demonstration, 91.8% precision, survives re-wording with 332 recoveries).

**False (verified, with numbers):** Instant *identification* is not solved. One demonstration is a point, not a rule. Three walls, each measured:

1. **Evidence wall.** A memory cannot contain a comparison it never made. Round 13: 16/17 real fix commits refuse before any vocabulary is consulted (`REFUSED__NO_PARTITION`) — the failing test's evidence is not a controlled difference (failing value next to passing sibling). Round 12 pushed partitions 1/7 → 3/7 by capturing runtime values; solves stayed 1/7. Evidence is manufacturable, and manufacturing it doesn't solve.
2. **Identifiability wall.** One trace fits exponentially many hypotheses. On 51 decidable bugs, 43 had no input anywhere that would tell surviving hypotheses apart. More tries don't help when two situations look identical and need different actions — that set is invariant to experience. What fixes it is an intervention (a question that separates survivors) or a causal observable that was missing.
3. **Vocabulary / synthesis–verification asymmetry wall.** When the fact the plan depends on is absent from the representation, repetition cannot separate success from failure. Nine QuixBugs tasks shipped no example file, so they were never searched; making the observable present made them searchable and repaired 0/9 (`WHERE_THE_OBSERVABLE_WAS_MISSING`). Replaying a seen edit covers 4.8% of real changed sites and 0/14 multi-line ones. Real work composes new edits against a live repo, and composition is where a memory of experiences stops being a plan.

**Unproven:** That cross-kind abstraction (one demonstration → different kind of change) is achievable without new hand-written rules. Measured: 0/4,444 (0/19 attempted, all 19 wrong). Largest refusal class 168/440 (38.2%) "no such form in the file" — no method can generalize to code that isn't there. Weights would not fix this (forbidden, impossible on this host, and downstream of the experience layer per Experience Distillation 3.8% vs 64.8%).

**Missing:** The binding term is the gap between what the goal depends on and what the agent can observe and express — exactly two halves: **observability** and **expressibility**. Observability binds computer use (OSWorld 2.0: 20.6% binary, failures on hidden state; MiniWoB: 8/33 residual misses need state no attribute carries). Expressibility binds coding (the last half standing; it fell when the candidate space became the closure of the program's own material under its own forms — 8/8 QuixBugs solved, 70,050 candidates, 248.2s, 0 model calls).

## Direct answers

**Why can't we just let the model experience the most advanced coding actions once and have it learn them?**

Three independent reasons, each with a number, none about effort:

1. **Identifiability.** One trace fits exponentially many hypotheses. A demonstration is not a rule; it is a point. On 51 decidable bugs, 43 had no input anywhere that would tell survivors apart. More tries do not help when two situations look identical and need different actions — that set is invariant to experience. What fixes it is an intervention (a question that separates survivors) or a causal observable that was missing.
2. **Vocabulary insufficiency.** When the fact the plan depends on is absent from the representation, repetition cannot separate success from failure, because there is nothing to separate. Measured: nine QuixBugs tasks shipped no example file, so they were never searched at all; making the observable present made them searchable and repaired 0 of 9. Necessary, not sufficient — and not the same thing as the space.
3. **Synthesis–verification asymmetry.** Replaying a seen edit covers 4.8% of real changed sites and 0 of 14 multi-line ones. Real work composes new edits against a live repository, and composition is where a memory of experiences stops being a plan.

And the corollary: **the smartest actions are not the missing part.** The action list repaired 0 of 20; derivations from instruction + page repaired 13 of 46; on the remaining 33, twenty-two never observed a goal in 400 acts and eight needed state the observation does not carry. Those are information failures, not action failures.

**What stops us now?**

- **Observability** (computer use): hidden state, implicit-state inference, multi-item tracking, conflict disambiguation, dynamic environment. OSWorld 2.0 authors locate failures not in clicking/coding but in hidden state; <7% of action budget spent on detecting/repairing own errors. Under 7% is the observability term, measured on the hardest open suite by someone else, for free.
- **Expressibility** (coding): the candidate space must be the closure of the program's own material under its own forms. The hand-written list of shapes (`+ - *`, six comparisons, a few calls) could not build slices, attributes, conditional expressions, or inserted statements. The closure rule fixed it (8/8), but multi-edit (0/14) and cross-kind (0/4,444) remain.
- **Infrastructure (§6 blocker):** SWE-bench Pro / Terminal-Bench 4.0 / OSWorld 2.0 require Docker/Harbor/VM + independent verifier. This host has neither Docker nor Harbor, no external VM, no signing material. 0/5 HARD-51 executed; 0 patches collected/verified; no scores. This is logged once as a blocker per §1.2; all other work continues.

**Remove those blockers (this build):**

- **Observability:** Differential state tomography (snapshot a11y tree, FDs, SQLite/config, IPC, DOM; fire one probe; diff state; infer hidden state machine in few probes) built on `CUMentalWorldModel` + CDP + `computer_env_v1` + `universal_computer_agent_v1`. Where no structured state exists (pure-canvas/legacy GUIs), minimal own-model perception that obeys §2 (structural, never pixels alone — `gui_room_v1`).
- **Expressibility:** Backward constraint propagation (reverse-execution synthesis: propagate constraints backward from failing test's expected output through Semantic IR to faulty point, compute missing body/transition directly) replacing forward enumeration; plus algebraic L2 skill composition (bidirectional type-directed search across 447 capabilities + learned skills, crystallize composed pipeline as new higher-order skill). Implemented as `TitanPipeline` Rungs 1–2 in Wave 47–48.
- **Infrastructure:** Preflight + Harbor adapters already exist (`pro_hard51_preflight_v1`, `harbor_epistemic_agent_v1`, 20+ Harbor agents). This build adds the effect-oracle + confinement gate that makes a future VM run admissible (PR #7071 pattern, implemented as `ShadowInterfaceEvolutionKernel` + `DualRungGate`). Execution itself remains blocked until a disposable VM with Docker/Harbor is supplied — stated honestly, not worked around.

## What is not real (against my own interest)

- **Not multi-edit.** The closure here is one edit or one inserted statement. Multi-line edits were 0/14 and nothing in Wave 47–48 changes that. Composition across steps is the next honest target.
- **Not computer use.** No browser ran this session; no Chromium in this sandbox. GUI numbers are existing in-tree receipts + OSWorld 2.0 paper, not new work.
- **Not general repair.** Eight tasks, one corpus, single-function Python, one machine (prior session). Wave 47–48 tests are new, but still single-function Python + interface evolution, not SWE-bench Pro.
- **Not capability credit, not benchmark rank, not independent verdict.** Authority NONE, producer-run, `truth.achieved` unchanged.

## The single bottleneck, stated so it can be attacked

> **Can the fact that the goal depends on be OBSERVED at the moment of acting, and can the action that satisfies it be EXPRESSED by what the artifact already contains?**

Two halves, and they are the only two terms that have ever survived a measurement in this tree. Everything else — parameters, pretraining, budget, model size, the "smartest actions", more demonstrations — was measured and is not a binding term at these sizes. The instrument that lets you say which half you are in is a judge certified per task on the corpus's own corrected and defective program, with typed refusals (`CANDIDATE_FOUND`, `SPACE_EXHAUSTED`, `BUDGET_EXHAUSTED`, `JUDGE_NOT_CALIBRATED`). Wave 47–48's `RefusalCurriculumKernel` implements exactly that typed refusal.
