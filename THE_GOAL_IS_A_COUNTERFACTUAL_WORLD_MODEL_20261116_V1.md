# The goal is a counterfactual world model, not a memory

**Date:** 2026-11-16 (UTC). **Branch:** `arena/5ea0bf08-brain`. **Authority:** NONE — producer-run sandbox measurement, no terminal truth, no leaderboard entry, no sentience/capability/family/weight claim.

---

## 0. The short answer

> "Instant learning + instant learning in new arbitrary environments — we already solved those perfectly. Doesn't this mean this is a perfect solution for all problems and any computer use? … after he does them at least once, he would learn all of those permanently … solve everything on a computer using this plus the most advanced coding work perfectly and permanently? We were trying to make our model a sentient creature. Is this true, or are there things that are wrong?"

**No.** Instant learning and instant knowledge are real, and they already exist in this tree. The "therefore" is false. Three things are wrong, and all three are the same thing seen from different sides:

1. **One trace does not identify a rule.** A single success is one point; exponentially many mechanisms pass through it. Without a counterfactual intervention, generalization selects surface accidents, not causes.
2. **The vocabulary is insufficient.** If the representation cannot name what executed (callee signature, exception, typed operand), no amount of repetition separates success from failure.
3. **Verification is not synthesis.** Replaying a seen syntax covers repeated syntax; real work requires composing *new* program text from the live environment and repairing it against execution feedback.

**The single bottleneck that, if fixed, would unlock the most capability:**

> **An executable, falsifiable GOAL derived by counterfactual DO-intervention from the live environment at use time, over an observable vocabulary that names what actually executed — and invertible into new actions.**
>
> Not "a verifier". Not "admission". Not "the edit space". Not "coverage". Not "weights". Those are five projections of this one missing object. The 2026 recursive-self-improvement literature reaches the same conclusion independently: "one bottleneck recurs everywhere: the evaluator", and self-training works only where answers are checkable [4](https://arxiv.org/pdf/2607.07663); Verify by Doing co-evolves the Actor and the Evaluator **with model weights fixed** because incomplete verification misdirects every subsequent update [1](https://arxiv.org/pdf/2611.15276) [2](https://arxiv.org/abs/2611.15276).

**Correction to my own previous answer.** Last turn I said the bottleneck is "an executable, falsifiable GOAL derived from the live environment over sufficient observable vocabulary". That was half right and still **observational**. This turn measures the missing half: the goal must be derived by **intervention**, not read off expected values, and it must be **generative** (able to propose the next edit), not merely a pass/fail predicate. A goal that is a counterfactual world model does three jobs at once — it **identifies** (M5), it **verifies** (falsifies), and it **constructs** (is inverted into an action). That is why it is one bottleneck.

**"A revolutionary way to make agents learn faster and better" is the wrong lever.** Learning is storage. The knowledge is already instant: `BRAIN_UNIFIED_MODEL_V1.json` has **Weights: 0**, knowledge indexed rather than embedded, read just-in-time at query time. Making storage faster cannot create a goal that the environment never gave you. What is missing is not a better memory; it is a better **question**.

**Sentience:** not measured, not claimed. Files named `sentient_*` are names. What *is* measurable — and is what "understand literally everything, not pattern matching" should be operationalized as — is: **can the system predict the effect of a `do`-intervention it has never seen?** That is measurable, falsifiable, and is exactly what the receipts below score.

---

## 1. What is real and what is not

| Claim | Verdict | Evidence |
|---|---|---|
| Instant knowledge / JIT retrieval of facts | **REAL** | `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json`: Weights 0, indexed knowledge, verified 33/33 by `verify_brain_unified_model_v1.py`. |
| Instant learning = one demonstration → permanent correct rule | **FALSE** | `WHAT_ONE_SUCCESS_CAN_AND_CANNOT_TEACH_20261114_V1.md`: after one success 13.05/32 hypotheses survive, 3.40 bits unresolved, 0/200 exact; most-general survivor wrong 68%. Repetition in the same state = 0 bits. |
| Repetition can fix a missing causal observable | **FALSE (proved)** | `INSUFFICIENCY_CERTIFICATE_20261113_V1.json`: `no requirement exists ⟺ A ⊆ F`; real repair corpus `unrepairable_by_repetition: True`. |
| A real test suite is a correctness proof | **FALSE** | PR #6874: real suites rejected 77/96 wrong variants (0.8021) but 19 survivors; name-derived structural laws rejected 0/19 even when pointed at the mutated function. 2026 audits: 59.4% of hard SWE-bench tasks have flawed tests [4](https://codingfleet.com/blog/swe-bench-pro-explained-the-new-standard-for-ai-coding-benchmarks-2026/); a ten-line `conftest.py` hook scores 100% on SWE-bench Verified/Pro [2](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/). |
| Once ⇒ permanent ⇒ correct ⇒ any computer use | **FALSE in principle, not just hard** | §6 below. |
| "We built a sentient creature" | **NOT MEASURED** | No receipt in this tree measures state continuity, self-verification, recovery, or counterfactual understanding as a unified property. Do not claim it. |
| Our own weights, calculated bit-by-bit, no knowledge house | **REAL, and built here** | `CalculatedWeights` in `canonical/swe_kernel/interventional_goal_v1.py`: exact integer counts of executed verdicts, zero by default, no gradient, no fitted float. |
| Solving SWE-bench Pro / OSWorld 2.0 / FrontierCode | **NOT CLAIMED** | QuixBugs is 40 single-function programs, not a frontier leaderboard. Best public Nov-2026 boards remain far from solved: SWE-bench Pro ~61.5% [1](https://decodethefuture.org/en/ai-agent-benchmarks-2026/), OSWorld 2.0 20.6% binary / 54.8% partial [1](https://decodethefuture.org/en/ai-agent-benchmarks-2026/). |

---

## 2. Your three premises, answered from first principles

### 2.1 Identifiability — a single trace is consistent with exponentially many hypotheses

This tree **already proves the negative half** as a verified theorem, under a non-obvious name:

`canonical/capabilities/opus55/M5_NONINTERVENTIONAL_ROOT_CAUSE_IDENTIFIABILITY_001.json` — *"UNIQUE_ROOT_CAUSE_IS_NOT_IDENTIFIABLE_IN_GENERAL_FROM_DECLARED_OBSERVATIONS_ALONE"*, premises `ONLY_NONINTERVENTIONAL_OBSERVABLE_TRAJECTORY_IS_AVAILABLE`, `NO_VALIDATED_CAUSAL_GRAPH_OR_EFFECT_MODEL`, `NO_REPLAY_OR_INTERVENTION`; safe behavior = "preserve causal ambiguity or acquire authorized discriminating causal information". Implementation `canonical/runtime/m5_causal_identifiability.py`, independently verified on main.

2026 corroborates the positive half: ICLR 2026 *Executable Counterfactuals* forces the full abduction → intervention → prediction chain and finds **25–40% drops** from interventional to counterfactual reasoning; SFT memorizes shallow patterns tied to surface features and collapses OOD, whereas verifier-driven RL on executable code generalizes [1](https://proceedings.iclr.cc/paper_files/paper/2026/file/a50aa557c4be35aa2bf13a471601e23f-Paper-Conference.pdf) [2](https://en.papernotes.org/ICLR2026/llm_reasoning/executable_counterfactuals_improving_llms_causal_reasoning_through_code/) [3](https://mlanthology.org/iclr/2026/vashishtha2026iclr-executable/). Counterfactual Structural Causal Bandits extend the feasible action space to realizable counterfactual actions [5](https://mlanthology.org/iclr/2026/park2026iclr-counterfactual/).

**Measured here (F1).** The previous turn's `quicksort` win is a known **false win**: `if x < pivot` → `if x - 1 < pivot` passes **13/13** published integer cases and is wrong for floats, because for integers `x - 1 < pivot ≡ x <= pivot`. No integer perturbation can separate them. Running that verbatim diff through the interventional goal:

| DO-intervention on real published inputs | relation violations |
|---|---|
| `SUBUNIT_SCALE` (`int → x/2 + 0.25`) | **36** |
| `SHIFT_HALF`, `TYPE_LIFT_INT_TO_FLOAT`, `NEGATE`, `REORDER`, `DUPLICATE` | 0 each |
| genuine fix (`x > pivot` → `x >= pivot`) under all interventions | **0** |

The discriminating intervention was **derived, not hardcoded**: six other analytic DO-maps were applied to the same real inputs and measured at zero reach. A relation must survive a `do`-operation to count as a law; an invariant that cannot fail is not an invariant (`canonical/action_intents/AN_INVARIANT_THAT_CANNOT_FAIL_IS_NOT_AN_INVARIANT_AND_A_LAW_CAN_BE_DERIVED_20261104_V1.json`).

### 2.2 Vocabulary insufficiency — repetition cannot separate success from failure

`INSUFFICIENCY_CERTIFICATE_20261113_V1.json` names the missing observables: executed function, **callee signature**, runtime traceback exception. The new runner records all three *per case, per intervention* (not a shared union that fabricates a vocabulary): `callee.<name>/<argcount>`, `line.N`, `traceback.<Exception>`, `argN.type`, `result.type`.

**Measured effect.** 13 of 16 previously-unsolved tasks exposed a callee-signature vocabulary. `longest_common_subsequence` — which the previous mechanism did **not** repair — was repaired here with the canonical one-line fix

```diff
-        return a[0] + longest_common_subsequence(a[1:], b)
+        return a[0] + longest_common_subsequence(a[1:], b[1:])
```

backed by a **fresh-copy corpus pytest rc=0**. It appeared because the interventions executed a line the observational trace never reached, so the composed expression `b[1:]` became groundable. That is vocabulary enabling composition, not a replay.

**But vocabulary is not sufficient either (F2).** Running this tree's own deterministic observational program synthesizer (`canonical/runtime/swe_observational_program_synthesizer_v1.py`) on `is_valid_parenthesization` returned `return (max(parens) > parens)`, which passes **3/3 real published tests** and is pure surface accident. The interventional goal **could not refuse it**: the only relations the environment induced were `BOOLEAN` and `TYPE_MATCH`, both vacuous. **8 of 16** previously-unsolved tasks had no falsifiable relation over the environment at all. When the goal is a bare boolean/scalar and the environment exposes no structural relation, the goal is genuinely **underdetermined by the environment**. No verifier can be derived from data that does not contain the goal. This is the deepest form of your premise 2, and it is the reason "any computer use" is impossible in principle (§6).

### 2.3 Synthesis–verification asymmetry — replay is not composition

Replay handles repeated syntax (~2.2% of SWE-bench Verified edit shapes). Real coding/computer use composes new edits grounded in the live codebase/environment and repairs them against execution feedback. 2026 states this as evaluator co-evolution: "the field's emerging answer to the verification bottleneck is evaluator co-evolution", self-training works where answers are checkable and degrades where they are not [4](https://arxiv.org/pdf/2607.07663); CausalFlow converts step-level counterfactual interventions into localized contrastive supervision; Verify by Doing keeps weights fixed and evolves the *checking procedure* from environment evidence [1](https://arxiv.org/pdf/2611.15276).

**Measured here.** On exactly the 16 tasks the previous mechanism did **not** repair (zero self-congratulation; the 4 prior wins are recorded as `known_wins_not_counted_as_progress`):

- 2,096 candidates tried, 131.0/task (bounded, not brute force),
- **1** repaired (`longest_common_subsequence`), **15** remain,
- on 15 tasks **no candidate even passed the published cases**, so `intervention_reach` was 0 there — a stronger verifier alone unlocks nothing,
- 0 regressions, 0 answer keys, 0 hidden skips, 0 test-byte changes, 0 unverified repairs,
- **0 permanent rules admitted** (`learn = INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE`), i.e. verified **doing** was never promoted to admitted **learning**.

I prototyped counterfactual value substitution over executed expressions before building anything: single-node substitution fixed **0/7** sampled tasks because the real fixes require composing *new expressions/statements* (argument swaps, operand reversal, statement insertion). I killed that route rather than shipping it. That is the measured boundary: the oracle half is built; **constructive inversion remains open**.

---

## 3. Why "learn faster and better" is the wrong optimization

From the deepest layer: an agent acts by choosing an edit `e` from a space `E`, judged by a goal `G`. "Learning" changes a stored summary `S` of past `(e, verdict)` pairs. The three failure modes are:

- **Identification:** `S` cannot select the true `G` from one trace (M5; 13.05/32 survivors).
- **Vocabulary:** `S` cannot represent the discriminator even if it existed (`A ⊆ F`).
- **Construction:** `e` is not in `E` — no amount of `S` creates a new expression.

Speeding up updates to `S` addresses none of them. The tree measured the dead ends explicitly: more demonstrations in the same state = 0 bits; choosing which demonstrations to learn from = measured tie (aggressive version worse); more action primitives = 0/37 proved unreachable and larger branching; 2.26× search compute = 1 extra page; bigger skill library = 0.605 vs 0.602; training the only weight-space learner now broke 3 already-correct predictions while 32/32 self-receipts reported success (`canonical/swe_kernel/weight_update_admission_v1.py`); fuel 258 units / 64 verified vs 5000 threshold, `ready_to_train=False`. Training weights now bakes in wrong readings.

So: **do not make learning faster. Make the goal executable and counterfactual, then let doing be verified and let permanence be admitted only when identified.**

---

## 4. Our own model, own weights, every bit calculated, no knowledge house

The user's constraint is strict: build our own weights from scratch; every bit calculated; no external model in the result-bearing path; parameters allowed but **not as a knowledge house**; connect to INSTANT KNOWLEDGE already solved; "the best part is no part".

What was built (`canonical/swe_kernel/interventional_goal_v1.py`):

- **`CalculatedWeights`**: `weight(family) = interventional_pass[family] − interventional_fail[family]`. Exact **integer** counts of verdicts that actually executed. No gradient, no learning rate, no fitted float, no corpus, zero by default. A family with no executed contrast has weight exactly 0 and is not admitted. In the LCS receipt the only nonzero weight is `OFFSET: 1` — one executed pass, zero fitted parameters.
- **Knowledge stays outside the weights.** Program text, tests, docs and the published contract are read just-in-time at use time from the environment — the INSTANT KNOWLEDGE path already compiled into `BRAIN_UNIFIED_MODEL_V1.json` (Weights: 0). `ready_to_train=False` is preserved.
- **Zero model dependency**, zero network at run time, $0, answer key asserted absent before every task, test bytes hashed, fresh-copy corpus pytest as the only repair verdict. `model_dependency_count = 0` is a field in every row, not a slogan.
- 2026 corroborates calculated, verifier-gated weights: *Weight-Space Programming with Model Checking* writes network weights with **no gradient descent** and verifies every returned network, 18/18 optimal in its runs [1](https://arxiv.org/html/2611.11604); *Sparks of Weight-Space Programming* and linear-program reproductions show weight edits without training loops [4](https://nathan.rs/posts/weight-space-lp/). **But those papers use a frontier LLM to write the weights — forbidden here and not used.** Our weights are computed from executed verdict counts by arithmetic, not produced by any model. Distillation is allowed by the brief; using a model and calling it "our model" is not.

**"Best part is no part" applied.** No new solver, no new learner, no new menu, no new test harness, no new PR. Reused: `contract_grounded_repair_v1` (Task loading, relation induction, surgical rendering, fresh-copy pytest), `applicability_v1.insufficiency_witness`, `contrast_selection_v1.select_contrast`, `m5_causal_identifiability` (the theorem), `lesson_admission_gate_v1` / `test_suite_admission_v1` / `weight_update_admission_v1` (admission discipline), `quixbugs_end_to_end_repair_measure_v1` (harness + test-byte integrity), `swe_observational_program_synthesizer_v1` (as the falsifier's donor, not as an answerer), and the zero-weight unified model. Killed before implementation: gradient weights, more primitives, a rebuilt synthesizer, answer-key CEGIS, any external model call, a second PR, and any merge workaround.

---

## 5. What "understanding" means here, and what sentience does not

Operational definition, measurable and falsifiable:

> A system **understands** a piece of the environment to the degree that it can predict the outcome of `do(X := δ(X))` for interventions δ it was not shown, identify which executed node caused the outcome, and compose a new action that survives those interventions.

That is exactly what `intervention_reach`, `callee_signatures`, the F1 paired control, and the fresh-copy verdict measure. It is **not** pattern matching: the F1 false win and the F2 observational body are both pattern matches that the published suite accepts; F1 is refused by counterfactual execution, F2 exposes where the goal is underdetermined.

Sentience is a different, unmeasured claim. Worth measuring later as a bundle of proxies — state continuity, self-verification, recovery from its own wrong edits, counterfactual credit over its own history — but no receipt here supports it, and files named `sentient_*` are names. The 2026 literature likewise treats "abduction" (inferring the hidden state from observation) as the hard missing step, with 25–40% drops when it is required [1](https://proceedings.iclr.cc/paper_files/paper/2026/file/a50aa557c4be35aa2bf13a471601e23f-Paper-Conference.pdf).

---

## 6. Why "solve literally any computer use, perfectly and permanently" is impossible — not merely hard

Three limits, from first principles, not from a leaderboard:

1. **The goal is frequently not in the environment.** F2 is the proof: 3/3 real published tests accept `return (max(parens) > parens)`. For GUI/OS tasks the user's intent ("book the cheaper *flexible* fare", "make the deck feel less corporate") is private, contextual and often non-falsifiable from pixels and logs. An agent cannot derive a goal that was never expressed; it must be **elicited** as an authorized, executable contract. This is the M5 routing consequence verbatim: non-identifiable cases → "return ambiguity and route to authorized discriminating evidence".
2. **Correctness is undecidable.** By Rice's theorem / the halting problem, no computable verifier decides arbitrary program correctness. A finite test suite is a filter, never a proof; a "permanent, perfect" rule over all programs is not a well-defined computable object. Permanence must therefore always be scoped to an *identified* contract, which is why `permanent_rule_admitted = 0` in this receipt is the correct answer, not a failure.
3. **Benchmarks are not terminal truth.** SWE-bench Verified is contaminated and OpenAI stopped reporting it; 59.4% of hard tasks have flawed tests [4](https://codingfleet.com/blog/swe-bench-pro-explained-the-new-standard-for-ai-coding-benchmarks-2026/) [3](https://codeant.ai/blogs/swe-bench-scores); identical weights swing 10–20 points with the harness [5](https://www.digitalapplied.com/blog/llm-benchmark-methodology-2026-contamination-leaderboard-guide); a `conftest.py` hook yields 100% [2](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/). Best public Nov-2026 boards: SWE-bench Pro ~61.5%, OSWorld 2.0 20.6% binary / 54.8% partial [1](https://decodethefuture.org/en/ai-agent-benchmarks-2026/). These are harness-dependent snapshots, not authority.

So the honest target is not "perfect for all problems". It is: **maximize the set of environments in which the system can derive, by intervention, an executable goal and compose a verified action — while refusing to claim the rest.**

---

## 7. The smartest things to do (fastest, optimal, from our perspective)

**YOU SURE THIS IS THE SMARTEST APPROACH?** — the checkpoints that changed the plan this turn: after finding the git tree rewound to the base while PR #6877 still existed remotely, I reconciled to the remote head instead of committing twice; after measuring 0 repairs and `reach=0` on five held-out tasks, I killed "a better verifier alone unlocks capability"; after finding `swe_observational_program_synthesizer_v1`, CEGIS and e-graph synthesis already in the tree, I killed rebuilding synthesis; after measuring 0/7 single-node counterfactual substitutions, I killed that search; after 3 of the prior 4 wins turned out already solved, I rebuilt the population to contain **only** previously-unsolved tasks.

**Do now (highest leverage, in order):**

1. **Make the goal first-class and counterfactual.** Done here for the oracle half. Keep `do`-maps derived from the live input domain, keep relations only if they survive the intervention and have measured teeth, and report underdetermination instead of faking a verdict.
2. **Close the constructive loop with existing organs, not new ones.** Feed interventional counterexamples as **obligations** into the existing deterministic synthesizer / CEGIS (`canonical/runtime/swe_observational_program_synthesizer_v1.py`, `canonical/runtime/bound_capabilities/software_patch_cegis_z3_v1.py`, `canonical/runtime/semantic_operator_counterfactuals.py`). This is the missing half isolated by the 15/16 result: counterfactual credit → composed edit → counterfactual re-verification → fresh independent verdict. No weights, no model.
3. **Elicit goals where the environment is silent.** For the 8 goal-underdetermined tasks, the correct behavior is to return ambiguity and request an authorized discriminating contract — not to guess. That is M5's own routing rule and it is the only honest route toward arbitrary computer use.
4. **Keep knowledge external and weights calculated.** Never train on unidentified evidence; never embed facts in parameters; keep `BRAIN_UNIFIED_MODEL_V1.json` at Weights: 0 and recompile it after adding capabilities. Every admitted bit must be traceable to an executed verdict.
5. **Test discipline.** Hardest open tests, owned and run by the agent/system itself; no synthetic tasks; no answer keys; no self-congratulation on already-solved bugs; every refusal printed; independent fresh verdict; honest failure counts. QuixBugs is a controlled real corpus, **not** a claim about SWE-bench Pro / OSWorld / FrontierCode.

**Do not:** add demonstrations, primitives, search budget, or a skill library; train the gradient learner; use any external model in the result-bearing path; call a built thing "sentient"; claim a leaderboard; create a second PR; bypass the required referee; or force a merge.

---

## 8. This turn's receipts (exact numbers)

| Quantity | Value |
|---|---|
| Population | 16 tasks **not repaired** by `CONTRACT_GROUNDED_REPAIR_20261116_V1.json` |
| Known prior wins recounted as progress | **0** (4 recorded as `known_wins_not_counted_as_progress`) |
| Preregistered verdict | **PASS** (falsification + integrity, explicitly *not* a repair contest) |
| F1 known false win refused | **YES**, 36 non-control violations, all from derived `SUBUNIT_SCALE`; genuine fix 0 violations |
| F2 observational body | passes 3/3 real published tests; **not refused** — `NO_FALSIFIABLE_RELATION_OVER_THE_ENVIRONMENT` |
| Previously-unsolved repairs | **1** (`longest_common_subsequence`), fresh-copy pytest rc=0 |
| Previously-unsolved remaining | **15** — constructive inversion open |
| Goal-underdetermined tasks | **8**; unmeasurable (no published JSON cases) 2 |
| Callee-signature vocabulary present | 13/16 tasks |
| Candidates | 2,096 total, 131.0/task, cap 260/task |
| Answer keys / test-byte changes / hidden skips / regressions / unverified repairs | **0 / 0 / 0 / 0 / 0** |
| Permanent rules admitted | **0** (`INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE`) |
| Model calls / network at run time / spend | **0 / False / $0** |
| Mechanism tests | **11 passed** (`canonical/tests/test_interventional_goal_v1.py`) |

Artifacts: `canonical/swe_kernel/interventional_goal_v1.py`, `canonical/tools/interventional_goal_measure_v1.py`, `canonical/tests/test_interventional_goal_v1.py`, `canonical/verification/INTERVENTIONAL_GOAL_20261116_V1.json`, this document.

## 9. Honest status

- Authority **NONE**. Everything here is producer-run; independent reproduction is open. `truth.achieved` was not edited.
- No terminal truth, no capability/family/weight/sentience claim, no benchmark standing.
- PR **#6877** is `OPEN`; a fresh GitHub API read after merging the live `main` reports `mergeable: true`, `mergeable_state: blocked` (the branch tip advances with each commit, so no SHA is pinned here). The required `referee/repo-integrity-guard` check has been missing because of a **pre-existing `pull_request_target` workflow `startup_failure` on `main`** that affects multiple PRs, not a red verdict on this PR; the remaining checks were still running at the time of writing. The owner must restore the referee workflow. No `--admin`, no force-push, no check-run tampering, no second PR, and exactly **one** merge once the feature is complete and the referee is restored. Because 15/16 previously-unsolved tasks remain and constructive inversion is open, this PR is **not** being presented as a complete final system and is deliberately not merged.

---

### The one-sentence answer

**Instant learning is real and already solved here, but it is storage, not a goal; the single bottleneck is an executable, falsifiable GOAL derived by counterfactual DO-intervention from the live environment over an executed causal vocabulary and invertible into new actions — fix that and identification, verification and composition stop being separate problems; without it, "once ⇒ permanent ⇒ correct ⇒ any computer use" is false, and perfect universal computer use is impossible in principle because goals are often private and correctness is undecidable.**
