# Separation is still the bottleneck — after one run, one invariance, and one new environment

**2026-11-16 · branch `arena/5ea0bf08-brain` · integrated base `b6f847e8973244b337ca880c20ed2638551fe337` · authority NONE · producer-run sandbox · $0 · zero external model calls**

This is a fresh answer to the repeated owner prompt, not a continuation note. I re-read the instruction literally, searched the project by **effect and intent** (including non-obvious names), re-checked the latest 2026 web research, and asked at each step: **YOU SURE THIS THE SMARTEST APPROACH?** The answer below integrates the newest `main` measurements (#6892 and the later one-move #6893) once; it does not chase further `main` moves.

Supersedes on the single-bottleneck question: `THE_GOAL_IS_A_COUNTERFACTUAL_WORLD_MODEL_20261116_V1.md`, `THE_GOAL_IS_THE_BOTTLENECK_20261116_V1.md`, `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md`. It also corrects the previous version of this note, which said the 24/40 union was "not one composed run": `main` has now measured that run.

Artifacts: `canonical/action_intents/SEPARATION_IS_THE_BOTTLENECK_20261116_V1.json`, `canonical/tools/proof_carrying_counterfactual_union_v1.py`, `canonical/tests/test_proof_carrying_counterfactual_union_v1.py`, `canonical/verification/PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json`.

---

## 0. The answer in one paragraph

**No.** Instant storage and one-shot actions do not solve all computer use or all software engineering; this is not a sentient creature, not a perfect model, not a terminal truth, and not a revolution in the claimed "anything on a computer" sense. What is real: a content-addressed **zero-weight instant-knowledge model** built from this repository's own calculated artifacts (no external model, no gradient, no knowledge house), permanent storage of verified experience, a **24 / 40** repair result now measured in **one run under the corpus's own `pytest`**, one α-invariance that turns **0 / 304** literal survivors into **4 / 384** accepted survivors without moving the capability ceiling, an exact inclusion–extraction decision over **8,388,600** survivors in **0.000 s**, a zero-experience browser census now at **66 / 130** with zero regressions, and a four-machine new-environment cost law that moves learning cost from *per request* to *per environment* but still refuses **3 / 16** requests. The single bottleneck is still **separation**: an invariant-closed, failure-assembled hypothesis space that contains the truth, paired with a computable causal observation that splits it and an independent verifier that can read the split. One demonstration supplies **content**; an invariance supplies **reach**; a causal observation supplies **identification**; none of the three can be manufactured by more demonstrations, a longer action list, more environments, more search, or weights added now. The smartest move is therefore **no new part**: reuse the already-existing decision/composition organs, bind the newest receipts to the audit, recompile the zero-weight model, and merge once only when the referee is green.

---

## 1. First principles: why "once, permanently, anything on a computer" cannot follow

Let `H` be the hypothesis space the system can construct, `I` the invariances it already holds, `O` the observations it can execute, and `V` the independent verdict that reads them. A one-shot trace `t` can become permanent **storage**; it becomes capability only when all of the following hold:

```
∃ h* ∈ H(I, failure_evidence)          the truth is representable
∧ ∃ o ∈ O  : o(h*) ≠ o(h′)            some computable observation splits it
∧ V(o, h*) is independent/affordable    the split is actually readable
```

If any factor is zero, more demonstrations, more environments, more compute, and more "advanced actions" multiply by zero. This is not an opinion: in 23 real program spaces one demonstration leaves a median **1,037** survivors (**10.018 bits**); on **479** real sites one success licenses **0** requirements and would act wrongly on **297 / 319** held-out sites (precision **0.069**); two *chosen* observations reach precision **1.000** with **0** dangerous errors; **12** random sequences identify **0**; **7 / 23** tasks with no repair in the space were unrescuable by any number of questions. Rice-style undecidability and finite-evaluation Goodhart limits mean no fixed verifier can certify arbitrary semantic intent from a passing trace [1](https://arxiv.org/html/2607.07663v1), [2](https://arxiv.org/html/2610.24206), [3](https://arxiv.org/html/2610.11464v1).

A demonstrated action is also **an operation plus a premise**, not a bare command. On four real machines, **5 / 18** atoms change effect between `TARGET_ABSENT` and `TARGET_EXISTS`, **17 / 36 (47.2%)** cells are inert, and **4** atoms ignore their argument entirely. The correct unit is `(atom × state class)`, not "action". A single trace is one cell of that table.

**"Best part is no part" is the engineering law applied here.** The tree already owns the constructive, interventional, identification, admission, planning, composition, environment-learning, and proof-obligation organs under non-obvious names. `WHERE_THE_SOLUTIONS_LIVE_20261101_V1.md` says the quiet truth: *"The decision layer is not missing. It is unwired from the computer-use layer."* Rebuilding a learner, verifier, or weight house would add a part that the measurements say cannot supply `H`, `I`, `O`, or `V`.

---

## 2. What changed since the previous answer (read by effect, not by filename)

| hidden-under-a-name mechanism | measured effect | receipt |
|---|---|---|
| `composed_repair_one_run_v1.py` + `grammar_closed_repair_v1.py` + `synthesized_expression_from_the_failure_v1.py` + recorded replay | **first one-run, one-judge composition**: 41 files / 40 bugs, **24 / 40 repaired in 387.8 s**. Synthesis won 3 at ~0.2 s; rewrite families 15; recorded learned replay 6. The projected 24/40 is now a measurement, not arithmetic. **Capability gain over the re-judged union: 0.** | `COMPOSED_REPAIR_ONE_RUN_20261116_V1.json`, `ONE_RUN_THREE_VOCABULARIES_ONE_JUDGE_20261116_V1.md` |
| `arm_learned_from_its_own_verified_repairs_v1.py` + `induced_edit_basis_v1.py` α-canonicalization | **literal preconditions**: 23 tasks fired, 304 candidates, **0** survived examples, **0** judged, **0** repaired. **α-canonical preconditions**: 28 fired, 384 candidates, **4** survived, **4** judged, **4** repaired. One demonstration repaired **15 / 24** of its own bug, **15 / 24** after bound-name renaming, and **5** distinct other bugs across 333 pairs / 39 targets. **Capability gain: 0**; it is a 129× cost win on `mergesort`. | `ARM_LEARNED_IN_ONE_RUN_20261116_V1.json`, `WHAT_ONE_VERIFIED_REPAIR_TRAVELS_20261116_V1.json`, `THE_INVARIANCE_IS_THE_REACH_20261116_V1.md` |
| `applicability_v1.py` + `contrast_selection_v1.py` inclusion–extraction | exact survivor count **8,388,600 = 2^23−8**; brute force **1.37 s**, inclusion–extraction **0.000 s**; **5,058** exhaustive equality checks, **120** seeded learn trials, **120** selector-equivalence cases; separable and inseparable cases return `AMBIGUOUS 2^20` / `INCONSISTENT 0`. No capability or benchmark credit claimed. | `THE_LEARNER_DECIDES_PAST_THE_ENUMERATION_WALL_20261116_V1.md`, `DECIDE_PAST_THE_ENUMERATION_WALL_20261116_V1.json` |
| `implied_ending_v1.py` + `picker_answer_v1.py` + `miniwob_contract_arm_arm_v1.py` | zero-experience, zero-search, zero-reward browser census **52 → 66 / 130** at seed 1060 (**+14**, 50.77%), replicated **47→56** and **49→57**, **0** regressions, **0** parameters. Of the remaining 64 pages, **17** are `EXECUTED_AND_LOST` and the rest are honest refusals; the sentence did not have to say "submit" because the contract supplied the missing end state. | `THE_SENTENCE_DID_NOT_HAVE_TO_SAY_SUBMIT_20261116_V1.json` |
| `instant_learning_in_a_new_environment_v1.py` + existing planner/composer organs | four real machines (filesystem, git, tarball, sqlite) with **18** opaque atoms / **36** `(atom, state)` cells. Active measurement: **29** adaptation trials, **13 / 16** requests solved, **44** total trials, **1.0** trial/request after adaptation. Demonstration: **11 / 16**, **34** trials, **2.125**/request. Break-even **25.78** requests total / **6.44** per machine. Shuffled atom labels/order: measuring agent still **13 / 16** machine-by-machine, demonstrator moves to **12 / 16** and **46** trials. Remaining refusals are surface expressivity (`GIT REPLACE`, `GIT REMOVE`) and composition (`TARBALL REPLACE`). | `INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json`, `INSTANT_LEARNING_SHUFFLED_CONTROL_20261116_V1.json`, `THE_PRICE_OF_A_NEW_ENVIRONMENT_20261116_V1.md` |

The earlier evidence is unchanged and still binding: **0 / 9** no-JSON tasks repaired when their own test files became the observable; **3** screen-accepted candidates refused by the published `pytest`; **100** held-out HumanEvalFix bugs with **51** test-passing candidates, **43** `UNSEPARATED`, majority vote wrong **3 / 5**, chosen question **8 / 8** with **0** regressions; PR #6887 re-judged **16 / 20** claimed learned-arm repairs with **4** not reconstructible; corrected earlier browser census **52 / 130**, **51** refused, **27** executed-and-lost, **0** regressions; **24 / 40** verified union with **16** hard-open tasks (**8** example-searchable, **8** no-JSON).

---

## 3. Is it revolutionary? Is it sentient? Is it permanent?

**Revolutionary in the narrow, measured sense only.** The new-environment result changes the *currency* of adaptation from `O(requests × demonstrations)` to `O(machines × adaptation) + O(requests)`: after ~6.4 requests per machine, every later request costs one trial instead of ~2.1, and the shuffled control shows the measuring agent's solved set no longer depends on the luck of action ordering. That is a real removal of luck and a real cost-law change. It is convergent with 2026 work that explicitly explores an environment's unit functions before transfer [4](https://arxiv.org/html/2603.07978) and with evidence that surface-specific rankings invert across platforms [5](https://arxiv.org/html/2606.06560v1). It is **not** "all computer use solved": the tax is per machine, a general computer has unboundedly many machines, and **3 / 16** requests remain refused by expressivity/composition.

**Not revolutionary in the claimed sense.** The architecture — frozen/zero weights, execution feedback, evaluator co-evolution, counterexample-guided synthesis, hardened grading — is the 2026 consensus shape, not a break from it [1](https://arxiv.org/html/2607.07663v1), [6](https://arxiv.org/abs/2611.15276), [7](https://arxiv.org/html/2605.16142), [2](https://arxiv.org/html/2610.24206). This tree is ahead in refusal discipline and behind frontier systems in measured capability. The best 2026 continual-learning exam still clears only **47.7%** of levels and all five levels in **23.3%** of tasks [8](https://arxiv.org/html/2610.33956); harness persistence alone does not gain on unseen tasks [9](https://arxiv.org/html/2611.14505); weight-based routes that do gain require a frozen teacher and verified trajectories, i.e. an external model the owner forbids [10](https://arxiv.org/html/2610.05303). Web consensus is evidence, not authority: the owner explicitly rejected following a weights/conventional-pretraining consensus, and the zero-weight model below is the calculated alternative.

**Not sentient, not measured as sentient, not required.** The only in-tree proxy — does experience change competence on a new problem — is negative outside the premise/invariance already held. No sentience claim, no terminal truth, no capability/family/weight claim, no benchmark/leaderboard entry. `truth.achieved` stays `false`.

**Permanent storage, not a permanent rule.** One verified experience is content-addressed and reusable; one demonstration leaves ~10 bits unresolved. α-renaming is a theorem of λ-calculus, not a fact learned from the demonstration. "Show it once and it knows it permanently" is true **only for everything the representation already quotients out**; it is false for everything else, and showing adds instances, not invariances.

---

## 4. The single bottleneck, sharpened

The standing answer was **separation**. The newest measurements split it along its real seam without replacing it:

> **Capability = (a hypothesis space that contains the truth) × (an invariance set that gives one demonstration reach) × (a causal observation that splits the survivors) × (an independent verifier that can read the split).**

- **Size of `H` = vocabulary.** Three composed vocabularies reach **24 / 40** and stop; **16** tasks remain hard-open. No fixed vocabulary covers them. A fourth hand-written family, more search, or the hidden CEGIS instrument (0 / 5 calibration, 0 / 3 open) was measured dead.
- **Reach per demonstration = invariant set `I`.** Literal preconditions fire 304 times and win 0; α-canonical preconditions fire 384 times and win 4, but all 4 are already-repaired tasks. One invariance multiplies reach, not vocabulary.
- **Readability of the split = `O` + `V`.** The operation proof (~55 ms) decides 18 static-observable-identical sites; the corpus `pytest` is the only repair judge; a fast screen lied on 3 no-JSON candidates; majority vote among test-passing candidates is not identification; self-evolved verifiers collapse without an anchored outer reference [3](https://arxiv.org/html/2610.11464v1).
- **Composition/addressing is a symptom, not a second bottleneck.** The new-environment refusals need a composer over measured `(precondition, effect)` operators. That composer already exists under non-obvious names: `capability_planner.py`, `generic_goal_tool_effect_planner_v1.py`, `capability_composer_v1.py`, `verified_skill_macro_planner_v1.py`, `explicit_recovery_planner.py`, `environment_learning_v1.py`, `predicate_world_abstraction_v1.py`, `operator_semantics_v1.py`, `hierarchical_skill_library_v1.py`. Wiring them to win the single measured `TARBALL REPLACE` refusal would be an ordinary **+1 / 16**, exactly the incremental gain the owner told us to kill. The ultimate next unit is **a new invariance or vocabulary derived from one specific failure, plus a causal observation that separates it** — not another demonstration, action, environment, or weight.

The 2026 literature lands on the same conjunction from different sides: verifier reliability is the recurring bottleneck [1](https://arxiv.org/html/2607.07663v1); active tool-based verification co-evolves Actor and Evaluator without external feedback [6](https://arxiv.org/abs/2611.15276); counterexample-guided synthesis needs a checkable property and an actionable witness [7](https://arxiv.org/html/2605.16142); world models hurt unless used for multi-hypothesis counterfactual discrimination rather than confirmation [11](https://arxiv.org/html/2601.03905v2); experience is not automatically reliable knowledge until verifier evidence supports, contradicts, replaces, or retires each claim [12](https://arxiv.org/html/2610.34043). Every one is a **separation** mechanism, not a "learn once" mechanism.

---

## 5. What is real, and what is not

| claim | verdict | measured basis |
|---|---|---|
| zero-weight own model with instant knowledge | **real, bounded** | content-addressed `BRAIN_UNIFIED_MODEL_V1.json` compiled from this tree; **0** weights, **0** gradients, **0** external model calls, **0** network calls at run time; every bit is a calculated artifact, not a knowledge house |
| one experience stored permanently | **real** | verified skill/repair records are reusable; 275 verified applications, 0 damaged in 600 |
| one experience becomes a correct general rule | **false** | 10.018 bits survive; 0 licensed requirements; precision 0.069 / 297 of 319 dangerous held-out errors |
| one run, one judge reaches 24 / 40 | **real** | 41 files, 40 bugs, 24 repaired in 387.8 s under the corpus `pytest`; 16 hard-open |
| α-invariance unlocks new capability | **false** | 4 / 4 accepted candidates, all on already-repaired tasks; capability gain **0** |
| exact inclusion–extraction past 2^23 enumeration wall is a learner | **false** | exact counting/selector decision; no hypothesis created, no capability or benchmark credit |
| zero experience solves 66 / 130 pages | **real, bounded** | 52→66 at seed 1060, replicated +9 / +8, 0 regressions, 0 parameters; 64 pages still unsolved with honest refusal census |
| instant learning in a new arbitrary environment is solved | **false** | it is a cost law: 29 adaptation trials, 13 / 16 solved, break-even ~6.4 requests/machine, 3 composition/expressivity refusals |
| "the smartest actions once" solves computer use | **false** | action list 0 / 20, one learned kind 1–2 / 20, one learned vocabulary 16 / 40, three composed vocabularies 24 / 40; no arm exceeds half alone |
| more demonstrations / environments / compute / action lists buys coverage | **false** | 2.5× compute bought 1 page in 37; 0 / 10 new kinds; repeated observation separates nothing |
| majority vote / fast screen / stored stdout verdict is identification | **false** | vote wrong 3 / 5; screen accepted 3 corpus-failing candidates; stdout accepted 4 / 4 do-nothing programs |
| all computer use + most advanced SWE solved | **false** | 16 / 40 real local tasks hard-open; frontier long-horizon boards far from complete; graders themselves repaired [2](https://arxiv.org/html/2610.24206), [8](https://arxiv.org/html/2610.33956) |
| sentient creature / terminal truth / revolutionary capability claim | **not measured, not claimed** | Authority NONE; competence-change proxy negative outside held invariances; `truth.achieved=false` |

---

## 6. Bad, dumb, ordinary, and incremental approaches killed before implementation

1. **Another learner or verifier.** Exhaustive effect/intent search found the capture, constructive, interventional, identification, admission, planning, composition, environment-learning, and proof-obligation organs already in the tree. A new one duplicates a part and cannot supply `H`, `I`, `O`, or `V`.
2. **Weights now / conventional pre-training / distillation from an external model.** The owner forbids using a model and claiming it was built; ASCENT-style persistent weights need a frozen teacher and full next-token distributions [10](https://arxiv.org/html/2610.05303). No parameter was added here.
3. **More demonstrations, more environments, larger action lists, more search budget, bigger skill libraries.** All measured dead or reduced to a per-environment cost law. Repetition of the same observation separates nothing.
4. **A fourth hand-written vocabulary, vocabulary-by-guessing, structure/name-derived laws, mutation score as proof, model-judgment verifier, hidden CEGIS.** 0 / 19 survivors, 0.000 mutation score, 0 / 5 calibration, 0 / 3 open probes. Do not ship an all-zero open-task run.
5. **Counting a one-run composition, α-invariance, exact decision, browser gain, or cost law as new capability.** The audit now reads all five and credits **0** new repairs.
6. **Wiring the existing composer for the one `TARBALL REPLACE` refusal.** +1 / 16 is ordinary incremental work; the owner asked for the ultimate mechanism, not self-congratulation.
7. **Re-testing known wins / synthetic tasks / screen-only passes / unreconstructible claims.** The audit starts from the **16** hard-open published tasks and ignores contaminated arms.
8. **Merging ten times, `--admin`, force-push, duplicate PR, workflow/check-run tampering, merge over red or missing referee.** Refused. One merge only after complete + green.

**YOU SURE THIS THE SMARTEST APPROACH?** Yes: every cheaper route is either already present under a non-obvious name or measured zero; the only non-duplicating complete feature left in this prompt is the proof-carrying, evidence-bound answer + audit that kills the false quantifier and names the next causal unit. Adding a part would violate "the best part is no part".

---

## 7. What was built in this branch

No new learner, verifier, action, vocabulary, weight, or external model. The complete feature is the **integrated, falsifiable answer + audit**:

- `SEPARATION_IS_THE_BOTTLENECK_20261116_V1.md` — this document.
- `canonical/action_intents/SEPARATION_IS_THE_BOTTLENECK_20261116_V1.json` — one action intent, `COMPOSE`, authority NONE, capability/terminal credit 0, base bound to `b6f847e…`, lease/route/stop unchanged.
- `canonical/tools/proof_carrying_counterfactual_union_v1.py` + test + receipt — now reads the one-run, invariance, exact-decision, browser, and four-machine evidence by effect; indexes **existing** decision/composition organs; keeps the hard-open population at **16**; asserts **0** capability credit for reach/cost/evidence wins.
- `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` — recompiled from the merged tree, zero weights, content-addressed; not hand-edited across the merge conflict.
- One merge into `main` only when every required check, including `brain-referee/repo-integrity-guard`, is green.

This does **not** register capability, solve computer use, prove correctness, claim independent verification, or authorize a second merge.

---

## 8. Hardest-open-test integrity and honest test report

- Corpus: real public QuixBugs pinned at `4257f44b0ff1181dedaedee6a447e133219fcebf`; **40** published `pytest` task files; no synthetic tasks; answer keys absent from the fresh task copy; no model or network at run time; $0. The audit tool reads measured receipts and real test-file names; it does **not** execute tasks or re-test known wins. New `main` receipts are producer-run with the same zero-model / zero-network discipline.
- New audit: `real_tasks=40 repaired_union=24 hard_open=16 example_searchable_open=8 unmeasurable=8 audit_pass=True`; one-run `24/40` under one judge measured; invariance `0 → 4 accepted` with **0** new tasks; exact decision `2^23−8` with **0** credit; browser `66/130` with **0** regressions; new environment `13/16` with **3** honest refusals.
- New audit tests: **11 passed**. Selected related suites on the final merged tree: **35** test files, **429 passed, 10 failed, 5 subtests passed, 285.56 s**. The **10** failures are pre-existing on a clean `git archive origin/main`: **9** `capability_composer_v1` live-registry drift failures (153 registered capabilities vs the test's 68-capability snapshot) and **1** `unified_cognitive_fabric` authority-blob drift failure. They reproduce on `main`, are not caused by this branch, and are not hidden or silently repaired.
- Model verifier: **33 / 33** after the final recompile of the content-addressed zero-weight model from the merged tree. Repo integrity guard: **17 rules / 0 violations**. `git diff --check`: clean. The trusted load-bearing admission and drift/goal-hierarchy gates are run from the trusted base before the single merge; no merge over a red or missing referee.
- `compileall` is **not clean** on this `main`: **5** pre-existing syntax errors reproduce on a clean `git archive origin/main` — three under `canonical/capabilities/internalized/professional_work/stirrup_247f24d/` and the two earlier `canonical/runtime/livebench_legacy_predecessor_compiler_audit_v1.py` / `canonical/runtime/osworld_v21_app_policy_overlay_v1.py` files. None is touched by this branch. They are reported, not hidden.
- Authority **NONE**. Producer-run, one sandbox. Independent reproduction open. No terminal truth, no capability/family/weight claim, no sentience claim, no benchmark/leaderboard entry. The assistant built and ran the current checks because the owner is not technical and the agent is not yet capable; only the agent/system being built may take the future hardest-open tests.
- Authority **NONE**. Producer-run, one sandbox. Independent reproduction open. No terminal truth, no capability/family/weight claim, no sentience claim, no benchmark/leaderboard entry. The assistant built and ran the current checks because the owner is not technical and the agent is not yet capable; only the agent/system being built may take the future hardest-open tests.

---

## 9. 2026 sources used (evidence, not authority)

- Recursive Self-Improvement survey, 1,250 papers: verifier hierarchy and evaluator bottleneck [1](https://arxiv.org/html/2607.07663v1).
- Verify by Doing, 11 Nov 2026: Actor/Evaluator co-evolution, active tool-based verification, frozen weights [6](https://arxiv.org/abs/2611.15276).
- SWE-Bench Pro V2: 480 / 731 tasks repaired/retired, scrubbed git history, clean-container grading [2](https://arxiv.org/html/2610.24206).
- Continual Learning Exam: best frontier system 47.7% of levels, 23.3% full ladders [8](https://arxiv.org/html/2610.33956).
- Continual-ARC, 11 Nov 2026: harness persistence does not gain on unseen tasks; weight-based DAgger does [9](https://arxiv.org/html/2611.14505).
- ASCENT: one verifier-accepted trajectory into persistent LoRA only via frozen-teacher hindsight self-distillation [10](https://arxiv.org/html/2610.05303).
- Who Verifies the Verifier?: anchored reference set required; vacuous always-pass grader still trains skills [3](https://arxiv.org/html/2610.11464v1).
- KEEL: verifier evidence supports/contradicts/replaces/retires skill claims [12](https://arxiv.org/html/2610.34043).
- OSExpert: explicit unit-function exploration needed for unseen-UI transfer; current agents 0–10% without it [4](https://arxiv.org/html/2603.07978).
- MacArena: Linux→macOS rank inversion >26.5 points; surface does not transfer [5](https://arxiv.org/html/2606.06560v1).
- Property-guided CEGIS: concrete counterexamples, ~7.4× fewer calls, requires checkable property [7](https://arxiv.org/html/2605.16142).
- World models as foresight tools: multi-hypothesis counterfactuals, not confirmation rollouts [11](https://arxiv.org/html/2601.03905v2).
- Rice theorem / finite-evaluation Goodhart boundary: formal verification is relative to a specification; no fixed universally faithful verifier for arbitrary semantic intent.
