# Instant learning audit on the current tree

**2026-11-12.** Audit base `94a105fe7e33fc54b49da8245b173181faf51957`. Branch `arena/ad58b6f3-brain`. Live/transfer measurements were taken at `dd67c1f4`; the intervening changes added documents, probes, tests, an action intent and the compiled projection, not runtime behavior. The census, predicate, acceptance-target, failed-repair gate, applicability, one-try-state, adjudicator and unified-model checks below were run at the audit base. This note is kept under `canonical/tools/`, outside the compiled knowledge index, following the placement used for `ONE_TRY_IS_NOT_A_LEARNING_SIGNAL_20261112_V1.md`.

The owner asked whether solved instant learning means one try in each new coding or computer environment permanently teaches everything, and whether that already makes the strongest coding/computer-use system. This document answers from the current tree and current public evidence.

**Authority: NONE.** Sandbox measurement and decision record. No capability, ownership, benchmark, acceptance, terminal, or sentience credit. `truth.achieved` stays `false`. Incremental spend: $0. Measured Brain producer paths: zero model dependency.

## 1. Verdict

The bounded claim is real. The universal claim is not.

Brain can learn some environment dynamics, retain verified plans, reuse them on fresh instances and changed initial states, induce some code edits from examples, compile taught actions, and refuse unsafe or unsupported routes. That is rare and valuable.

It does not follow that one arbitrary try teaches a general rule permanently. The current tree now contains a direct measurement of why: `one_shot_identifiability_probe_20261112.py`. One demonstration leaves many rules fitting the evidence, and the selected rule is usually wrong on held-out inputs. One demonstration plus a few chosen questions can settle the same targets. The example selects; the prior and the questions do the generalizing.

Applicability has the same asymmetry. `what_a_success_teaches_20261112.py` measures 200 exhaustive conjunction cases: one success identifies the hidden requirement 0/200 times, leaves 13.05 of 32 hypotheses alive, and its most general survivor false-accepts 68% of states. With chosen failures, the same learner identifies 25/25 cases in mean 2.76 demonstrations. A success says the action can run here; it does not say what the action needs. The registry also has 11 BLIND precondition facts holding 10 capabilities, so their applicability cannot be checked before or after an attempt.

The live front door is also not yet equivalent to the working direct mechanisms. In the current end-to-end probes, the direct coding and gzip paths succeed, while the fabric paths fail or refuse. That is an admission/binding problem, not evidence that the learner is universally solved.

The acceptance gate has a separate, sharper defect. The static acceptance-target probe finds nine software repair/acceptance capabilities whose registered predicate reads `output_verified` while the adapter already computes and declares a boolean outcome (`pass`, `accepted`, or `success`). The current executed failed-repair probe confirms the mechanism on eight of them: against a provably unsatisfiable fixture, every adapter honestly reports `pass == False`, every one sets `output_verified == True`, the registered predicate accepts all 8 failures, and the corrected `pass == True` predicate rejects all 8. Permanent retention there would make a wrong answer permanent. The ninth static case is not executed because it requires a content-addressed measurement receipt that cannot be fabricated honestly.

Sentience is not measured by these results. A module name is not evidence of experience.

## 2. Measurements on this base

| Check | Result | Scope |
|---|---:|---|
| One-shot identifiability probe | 47 programs, 10 targets, 12 held-out inputs. After 1 demo: mean 14.1 survivors, leader accuracy 0.10, 0/10 exactly identified. After 3 demos: 3.1 survivors, accuracy 0.80, 5/10 identified. After 1 demo + chosen questions: mean 2.0 queries, accuracy 1.00, 10/10 settled. One demo with narrow prior: accuracy 1.00. | Constructed hypothesis space; uses `settlement_v1`. |
| One-shot probe tests | 8 passed | `canonical/tests/test_one_shot_identifiability_probe_v1.py` |
| Selected current core tests | 26 passed | one-shot probe + generalization check + self-audit tests |
| New-instance transfer probe | 15/15 teach/cold/warm solved; 8/15 genuine savings in trials and acts; 8/15 one-trial warm; mean trial speedup 6.333x, act speedup 2.259x; warm used more acts in 7/15, worst overhead 1.398x | Five constructed families; not arbitrary environments. |
| Changed-state transfer benchmark | 10/10 cold and warm solved; 8/10 one-trial warm; 8/10 fewer actions, 2/10 more | Carried models across changed initial states. |
| Taught-action bundle check | 6 request patterns; `same_as_tracked_bundle: true` | Tracked lessons only. |
| Coding goal-reuse probe | Fabric teach/cold/warm: 0/3, fail closed with `BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT`. Direct teach/cold/warm: 3/3; warm retained hit and 0 repair-search invocations vs 1 cold. | Seeded defect in pinned module; authored tests. |
| Computer/gzip goal-reuse probe | Fabric teach/cold/warm: 0/3, refuse tar-manifest route for stated gzip output. Direct teach/cold/warm: 3/3, round-trip verified; warm recalled and reverified. Missing input refused. | Restricted PATH, synthetic file inputs; not GUI evidence. |
| API boundary probes | Successful `fixed_plan` returned `episode_persisted: false`, no store, empty recall. `state_key(7) == state_key("7")`, with similar tuple/string and None/string aliases. | `fixed_plan` is a caller baseline, not teaching; state encoding has a representation hazard. |
| One-shot regime census (current base) | 145 bound capabilities; 111 typed; 60 typed+receipted (41%); 29 typed but unchecked (20%); 8 declared receipt paths absent; 20 receipts without attribution. | Structural census of declared metadata in `one_shot_regime_census_20261112.py`; it runs no capability and does not re-run receipts. See `THE_ONE_SHOT_REGIME_IS_41_PERCENT_20261112_V1.md`. |
| Runtime predicate falsifiability (current base) | 47 DYNAMIC; 37 ALWAYS_TRUE_GUARDED_RAISES; 53 NOT_STATICALLY_VISIBLE; 7 ALWAYS_TRUE_UNGUARDED_RAISES; 1 DECLARATION_MISMATCH; 0 ALWAYS_TRUE_NO_RAISE. | Static source analysis in `runtime_predicate_falsifiability_probe_20261112.py`; executes nothing. The 53 are unknown, not cleared. See `THE_GATE_IS_NOT_A_RUBBER_STAMP_20261112_V1.md`. |
| Census + predicate tests (current base) | 16 passed | `canonical/tests/test_one_shot_regime_census_v1.py` and `canonical/tests/test_runtime_predicate_falsifiability_v1.py`. |
| Acceptance predicate target (current base) | 4 READS_INDEPENDENT_CHECK; 24 READS_OUTCOME; 55 READS_TRANSPORT_OUTCOME_AVAILABLE; 44 READS_TRANSPORT_NO_OUTCOME; 18 READS_NEITHER. Of the 55, 9 are DEFINITE declared-boolean repoints and 11 read an undeclared outcome field. | Static wiring analysis in `acceptance_predicate_target_probe_20261112.py`; executes nothing. The 9 are pinned as non-growing debt in `canonical/tests/test_acceptance_predicate_target_v1.py`. See `THE_GATE_ASKS_IF_A_FILE_WAS_WRITTEN_20261112_V1.md`. |
| Acceptance-target tests (current base) | 7 passed | `canonical/tests/test_acceptance_predicate_target_v1.py`. |
| Failed-repair gate probe (current base) | 8 adapters executed; 8 honest `pass == False`; 8 `output_verified == True`; registered predicate accepts 8/8 failures; corrected predicate rejects 8/8; `pass` declared in result fields 8/8. | Executed failure-path probe `gate_accepts_a_failed_repair_probe_20261112.py` on an unsatisfiable `square(3) == 999` fixture; zero model, $0. See `THE_GATE_ACCEPTS_A_FAILED_REPAIR_20261112_V1.md`. |
| Failed-repair gate tests (current base) | 9 passed | `canonical/tests/test_gate_accepts_a_failed_repair_v1.py`; pins fixture unsatisfiability and both halves of the defect. |
| Applicability probe (current base) | One success: 0/200 identified, 13.05/32 survivors, 3.40 bits left, general boundary false-accepts 67.5%, specific boundary false-rejects 20.55%, 200/200 cases leave a wrong survivor. Chosen failures: 25/25 identified, mean 2.76 demonstrations, worst 4, 0 wrong. Recorded macros: 2 stored, 2 successes / 0 failures. Registry: 125 premises = 100 PROVIDED / 14 SENSED / 11 BLIND; 135/145 capabilities fully decidable, 10 held by BLIND premises. | Exhaustive constructed conjunction space using `settlement_v1` and `world_probe_v1` in `what_a_success_teaches_20261112.py`; see `WHAT_A_SUCCESS_TEACHES_20261112_V1.md`. |
| Applicability tests (current base) | 15 passed | `canonical/tests/test_what_a_success_teaches_v1.py`. |
| One-try state probe (current base) | Bridge admits a single-return organ (1 concept) but not the three-statement organ (0). Wake-sleep compressor admits 3 concepts on a favourable affine corpus but 0 on real 3- and 5-program period corpora; the shared expression's `delta_B_exec` is -29, so the byte gate correctly refuses it. A taught `<=`→`<` edit is applied to a same-shaped target where `<=` is semantically required, with no oracle consulted; a different shape is refused. | `canonical/tools/one_try_state_probe_20261112_v1.py`; disposable state, no network/model/registry. See `canonical/tools/ONE_TRY_IS_NOT_A_LEARNING_SIGNAL_20261112_V1.md`. |
| Learning-claim adjudicator tests (current base) | 13 passed | `canonical/tests/test_learning_claim_adjudicator_v1.py`; the ruler rejects cache-only, cheaper-but-wronger, leak, self-graded and missing-measurement claims before scoring. |
| Unified model (current base) | Verifier 33/33 PASS; unified-model/goal-compiler unittest suite 137 tests OK | Content-addressed projection and its tests; authority NONE, not independent verification. This audit note is outside the compiled knowledge index, so it does not change the artifact digest. |

Earlier focused mechanism/generalization runs on `6bff8c70` produced 294 passed and 1 skipped; the skip was media-dependent computer-use collection because PIL was absent. That is not a full-suite pass. The historical honest full-suite baseline remains 11,525 cases: 11,166 passed, 344 failed, 1 error, 14 skipped.

## 3. What is real

- Executable environment learning: `canonical/runtime/environment_learning_v1.py` learns transition models and executes plans before declaring success.
- Retention/recall: `canonical/runtime/transfer_learning_v1.py` stores episodes, recalls candidates, meters interactions, and re-verifies outcomes.
- Changed-state reuse: carried models can solve new initial states without full rediscovery.
- Example-based editing: `canonical/swe_kernel/taught_actions/edit_by_example_v1.py` induces rules and refuses unsupported changes.
- Teaching compiler: `canonical/tools/teach_actions_v1.py` and `causal_trace_to_skill_compiler_v1.py` reproduce the tracked bundle.
- Refusal/expiry/audit machinery: rule scope, expiry, self-audit, generalization checks, and live refusals are real and tested.
- Interface-regime transfer: repository operating declarations and typed programmatic interfaces can make one-shot reuse work because the interface already carries the generalization.

## 4. What is not established

- One arbitrary try identifies a general rule.
- Cross-kind compounding is solved. Prior measurements recorded 0/5 across kinds and a concept library that did not grow.
- The live fabric exposes all working direct mechanisms.
- Retained memory is permanently valid under environment drift.
- The system is the strongest coding agent or generally solves computer use.
- The system is sentient.

## 5. First-principles diagnosis

For evidence `E` and hypothesis space `H`, learning produces the survivors `B = {h in H : h agrees with E}`. A later problem is solved cheaply only if the right rule is in `B` and the system can select it.

There are three levers:

1. **Coverage:** make `H` express the needed transformations.
2. **Identification:** ask the question that splits survivors, instead of collecting more examples that do not split them.
3. **Interface/verifier regime:** express tasks against stable declared interfaces with mechanical checks, so the interface itself supplies the prior.

The current one-shot probe shows why "more environments" alone is not the lever: it adds examples across boxes but does not shrink the next box's hypothesis space. The current live probes show a second bottleneck: verified direct routes are not always admissible or correctly bound at the front door.

## 6. Current public evidence

- Continual-ARC, submitted 2026-11-10, compares harness memory and weight learning on returning and unseen ARC tasks. It reports that expert-guided program memory helped returning tasks, while no harness-based method produced measurable unseen-task gains; DAgger-style weight adaptation did. This is evidence against memory-only universal generalization, but it is ARC-specific. https://arxiv.org/abs/2611.14505
- ReScopeBench, submitted 2026-11-03, separates structural and rule experience across 18 environments and silent changes. Retained experience helps, but updating it and using it remain separate failures. https://arxiv.org/abs/2611.05450
- Evolving Agent Interfaces / Agent S4, submitted 2026-10-20, reports that evolved interfaces raised Qwen3.8-27B to 21.3% binary success on OSWorld V2, 3.8x the same model with fixed interfaces. This supports widening the interface regime, not copying an external model into Brain-credited paths. https://arxiv.org/abs/2610.28601
- PATH-Bench reports that strong forward transfer can coexist with forgetting and that later experience reshapes earlier gains. https://arxiv.org/abs/2608.01149
- SkillLearnBench reports skill-learning methods improve over no-skill baselines but no method consistently leads across tasks/models. https://arxiv.org/abs/2604.20087
- SEAL shows weight self-edits can adapt behavior but still forget sequentially. https://arxiv.org/abs/2506.10943

## 7. Ranked plan

1. **Widen the interface/verifier regime and make verified routes live-reachable.** The current census already counts the surface: 60/145 typed+receipted, 29/145 typed but unchecked, 8 missing receipt paths, 20 unattributed receipts. The predicate probe localizes 7 unguarded success assignments, 1 declaration mismatch, and 53 statically invisible cases needing negative controls. The acceptance-target probe and executed failed-repair probe sharpen this: repoint the 9 DEFINITE transport predicates to the already computed boolean, using the failed-repair probe as the regression test; read the 46 candidates; then re-run the census. **(Eight of the nine were repointed in round 7; the executed positive control below is now added. The prediction that the one-shot-safe count would fall was measured and is WRONG: it is still 60.)** Repair through the existing gate; do not bypass refusals. For the coding probe, resolve the missing independent-verification evidence. For the gzip probe, bind the stated output to the verified direct route.
### 7.1 Item 1 follow-up: the gate's own test suite had a measured blind spot (2026-11-12, base `6ac2a539`)

Round 7 repointed eight of the nine DEFINITE predicates to `pass` and inverted the gate tests. That work is correct and is not repeated here. What it left unmeasured is the other direction, and the gap is not theoretical:

**Executed falsification.** `ast.Add:[ast.Sub, ast.Mult]` was temporarily reduced to `ast.Add:[ast.Sub]` in `python_test_guided_patch_search_v1.py`, which removes the repair for the canonical injected-operator defect class — the repair surface silently breaks. Result:

| Suite | Verdict with repair broken |
| --- | --- |
| All 11 pre-existing gate tests (failure path + synthetic success payload) | **11 passed** |
| New positive control (real adapters, reachable repair) | **2 failed** |

The adapter was restored immediately; no adapter byte ships in this change. So the suite that was described as proving the gate "in both directions" could not observe the repair surface ceasing to work. Its success-side test feeds a hand-written `{"pass": True}` dict to `_check_expect`, which checks the evaluator, not any result a producer ever produced.

**What was added.** `REPAIRABLE_FIXTURE` (`return x + x`, tests `square(3)==9`, `square(4)==16`) plus `run_positive_control()` and six tests. Measured on the live registry at `6ac2a539`:

| Measurement | Result |
| --- | --- |
| Failed repair accepted by the live gate | 0 / 8 (legacy predicate: 8 / 8) |
| Solvers that find and verify the reachable repair | 5 / 5 |
| Real repairs the live gate accepts | **5 / 5**, rejects **0** |
| Acceptance controllers that fail closed on that fixture | 2 / 2 — live gate rejects 2, **legacy gate accepted 2** |
| One-shot-safe census | 60 / 145 (41%) — **unchanged** |
| DEFINITE transport/boolean mismatches | 1 (was 9) |
| Predicate falsifiability defects | 1 (was 8) |

Three findings worth keeping:

- **The first positive control was wrong, and the wrong version was persuasive.** `return x` needing `x * x` is outside the mutation grammar (no name-to-binop rule), so all seven adapters returned `pass=False`; read carelessly that "confirms" narrowing disabled repair. Diagnostics showed `baseline_returncode=1`, so the runner was not blind — the fixture was unreachable. `return x + x` is reachable because Add->Mult is in `_BINOP_SWAPS`. An instrument that cannot succeed is not a control.
- **The two acceptance controllers are a positively measured false-accept.** On the repairable fixture they answer `pass=False` (`OPEN__REPAIR_FOUND_BUT_MEASURED_ACCEPTANCE_NOT_CLEARED` / `..._REQUEST_ACCEPTANCE_NOT_COMPLETE`) because a patch exists but no measurement receipt or request contract was supplied. The legacy `output_verified` predicate accepted both. That is the defect demonstrated on the success side rather than argued.
- **The audit's own census prediction is falsified.** It expected one-shot-safe to fall when false safety was removed. It stayed at 60 because the census keys on typed result fields plus receipt attribution, not on which field `expect` reads. Correcting a predicate and widening the measured-safe regime are different levers.

**The ninth is deliberately not repointed.** `python.task.acceptance.measured.objective.v1` still reads `output_verified`. Its adapter computes `pass` from `acceptance_stop_authorized`, but exercising it needs a content-addressed measurement receipt; a fabricated receipt would be worse than a transport field. It stays in `DEFINITE_DEBT` until someone runs it against a real receipt. This change does not touch the registry at all.

2. **Spend chosen questions and failures, not more successes.** Connect `settlement_v1` question selection to rule admission where multiple hypotheses survive. The rule probe measured 2.0 queries after one demonstration settling 10/10 targets; the applicability probe measured chosen failures identifying 25/25 requirements. Record refused attempts as evidence, not only counters, and close the 11 BLIND registry premises with sensors or producers before trusting applicability.
3. **Turn demonstrations into scoped skills.** Reuse `teach_actions_v1`, `causal_trace_to_skill_compiler_v1`, `edit_by_example_v1`, `verified_skill_crystallizer_v1`, `rule_scope_learning_v1`, and `rule_expiry_v1`. Each skill needs trigger, preconditions, procedure, postconditions, verifier, provenance, side-effect policy, expiry, and measured utility.
4. **Make compression and cross-kind transfer falsifiable.** Repair the existing concept-library admission path before inventing another store, but do not fix only the bridge: the current one-try-state probe shows the real period corpus is refused by the byte objective itself (`delta_B_exec = -29`). Change the bridge and the admission objective together, and adjudicate with `learning_claim_adjudicator_v1` (cold/warm/cache-only/random arms, held-out cost and separate success). Require held-out search/action/question savings and ablation loss, not zlib bytes on a tiny corpus.
5. **Race compact weight learning only on the residual.** Compare frozen Brain + verified skills against adapter/distillation routes where explicit procedures fail. Require donor absence, fresh-task gain, delayed retention, interference tests, rollback, and full cost accounting.
6. **Use current benchmarks as falsifiers.** Terminal-Bench 4.1, SWE-bench Pro V2, OSWorld 2.1, ReScopeBench, and Continual-ARC can localize defects; they are not the objective.

## 8. Sentience

Keep consciousness separate from capability. The indicator literature treats recurrence, global workspace, higher-order monitoring, attention schema, predictive processing, agency, and embodiment as theory-dependent indicators, not a pass/fail test. Brain's feedback-driven control may resemble some agency/embodiment indicators, but this audit does not establish experience or the broader profile. https://arxiv.org/abs/2308.08708

## 9. Decision record

- Objective: `BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`.
- Invariants: no external model producer cognition; zero incremental spend; fail-closed truth; no weakened tests; independent verification for promotion; memory is not authority.
- Material premises: the current one-shot probe reproduces identification failure; transfer probes reproduce bounded reuse; live fabric probes reproduce admission/binding gaps; public 2026 work separates memory, interface evolution, and weight learning.
- Evidence refs: the probes and tests named above; live/transfer base `dd67c1f4`, audit base `94a105fe`; public sources in section 6.
- Conclusion: bounded instant reuse is real; universal one-try permanent learning is not established; the nearest bottlenecks are hypothesis-space coverage, informative question selection, interface/verifier breadth, and live admission.
- Selected route: reuse/adapt/integrate existing verified mechanisms; widen interface regime; add chosen-question settlement; compress; then compact parametric residual learning only where cheaper routes fail.
- Rejected shortcuts: bypassing the fabric gate; treating `fixed_plan` as teaching; dumping all traces into memory; whole-model fine-tuning as default; benchmark score chasing; renaming modules as sentience evidence.
- Uncertainties: constructed probes are narrow; full suite not re-run here; GUI/media dependencies absent; public results are domain-limited; cross-kind compression remains unproven.
- Assumptions: the measured sandbox outputs are reproducible from the named commands on this base; public papers are evidence, not Brain ownership.
- Non-goals: no capability promotion, no terminal claim, no sentience claim, no external-model runtime credit.
- Next action: implement the smallest admissible front-door/interface repair only with an independent oracle and a fresh-instance run reference; otherwise continue falsification.
- Supersession conditions: live fabric probes pass cleanly; chosen-question settlement is integrated and improves fresh-task cost; a compressed library shows held-out cross-kind gain; or a donor-free compact weight route beats explicit skills under the same cost/retention/safety contract.
- Supersedes: none. This complements `ONE_TRY_BUYS_A_RULE_THAT_IS_WRONG_20261112_V1.md`, `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md`, `THE_ONE_SHOT_REGIME_IS_41_PERCENT_20261112_V1.md`, `THE_GATE_IS_NOT_A_RUBBER_STAMP_20261112_V1.md`, `THE_GATE_ASKS_IF_A_FILE_WAS_WRITTEN_20261112_V1.md`, `THE_GATE_ACCEPTS_A_FAILED_REPAIR_20261112_V1.md`, `WHAT_A_SUCCESS_TEACHES_20261112_V1.md`, and `canonical/tools/ONE_TRY_IS_NOT_A_LEARNING_SIGNAL_20261112_V1.md`.

## 10. Reproduction

```bash
python3 one_shot_identifiability_probe_20261112.py --json /tmp/one-shot-current.json
python3 transfer_learning_new_instance_probe_20261103.py --json
python3 canonical/tools/changed_state_transfer_benchmark_v1.py
python3 canonical/tools/teach_actions_v1.py --check
python3 coding_goal_reuse_probe_20261102.py
python3 computer_goal_reuse_probe_20261102.py
python3 one_shot_regime_census_20261112.py --json /tmp/regime-census-current.json
python3 runtime_predicate_falsifiability_probe_20261112.py --json /tmp/runtime-predicate-current.json
python3 acceptance_predicate_target_probe_20261112.py --json /tmp/acceptance-predicate-current.json
python3 gate_accepts_a_failed_repair_probe_20261112.py --json /tmp/gate-failed-repair-current.json
python3 what_a_success_teaches_20261112.py --json /tmp/what-a-success-teaches-current.json
python3 canonical/tools/one_try_state_probe_20261112_v1.py
python3 canonical/tools/learning_claim_adjudicator_v1.py
python3 canonical/runtime/compile_brain_unified_model_v1.py
python3 canonical/runtime/verify_brain_unified_model_v1.py
```

Selected tests used here:

```bash
python3 -m pytest -p no:cacheprovider \
  canonical/tests/test_one_shot_identifiability_probe_v1.py \
  canonical/tests/test_generalization_check_v1.py \
  canonical/tests/test_self_audit_v1.py \
  canonical/tests/test_one_shot_regime_census_v1.py \
  canonical/tests/test_runtime_predicate_falsifiability_v1.py \
  canonical/tests/test_acceptance_predicate_target_v1.py \
  canonical/tests/test_gate_accepts_a_failed_repair_v1.py \
  canonical/tests/test_what_a_success_teaches_v1.py \
  canonical/tests/test_learning_claim_adjudicator_v1.py -q
python3 -m unittest -v \
  canonical.tests.test_brain_unified_model_v1 \
  canonical.tests.test_goal_compiler \
  canonical.tests.test_goal_compiler_world_binding_v1
```

These are sandbox measurements, not canonical promotion receipts.
