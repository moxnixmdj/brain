# First principles, pass 25 — questions, evidence, and the limits of repair

Date: 2026-11-04. This report corrects the earlier
[`FIRST_PRINCIPLES_TWENTYFOUR_20261105_V1.md`](FIRST_PRINCIPLES_TWENTYFOUR_20261105_V1.md).
It describes a limited, interactive learning mechanism, not consciousness or a
claim of general semantic understanding. No independent human or system has
certified this implementation or report.

## Correction of pass 24

1. **Names do not establish a relationship.** Pass 24 treated overlap in names as
   meaningful evidence for matching functions. An intended relation with unrelated
   names was missed, and functions with shared words but distinct meanings produced
   the same apparent disagreement. A fired check establishes only disagreement
   with the *proposed* check, not the truth of its premise or which side is wrong.
2. **The S35 volume assessment was wrong.** Under ordinary volume semantics,
   `cube_volume(s) = 6*s` is not the cube volume `s**3`, and
   `box_volume(l,w,h) = l+w+h` is not the box volume `l*w*h`. Both functions in
   that fixture were wrong under its intended specification. The previous report
   incorrectly called the cube side correct. Without the specification, source
   alone does not identify either side as right.
3. **A diagonal relationship is not an off-diagonal specification.** For
   example, `w*w`, `w*h`, and `h*h` agree when `w == h`. Even if a caller asserts
   that a diagonal relationship and one reference are correct, that does not
   determine the general function.
4. **The earlier safety and learning claims were too broad.** A prior notion
   implementation executed workspace code in the caller; the current source
   model does not. Moving later checks into a namespace is an improvement, not
   independent certification of the broker or proof that all remaining repair
   paths are safe.

## What changed

* **Proposal without authority.** The source model statically interprets a
  restricted numeric AST, considers eligible narrow/wide pairs regardless of
  name, and reports a disagreement as a question. It neither executes the source
  to find questions nor assumes that equality is intended. It declines modules
  with definition-time decorators, defaults or annotations, including on
  unrelated functions. A held, fired, or declined result is a property of the
  model/check, not an authenticated specification.
* **Explicit, scoped feedback.** A caller can reject a question, confirm it,
  name one reference function, and supply answers to active queries. Test
  authorship additionally requires at least two separately supplied examples at
  distinct proposed inputs and bounded candidate agreement. The answers are
  expected to come from an external specification; reviewer names, bases, and
  supposed independence are **caller claims, not authenticated facts**. Both
  answers may be supplied by the same caller. Misleading feedback can still
  produce a misleading test.
* **Active discrimination.** Candidate expressions are obtained from the
  target and the explicitly named reference by rebinding source-expression
  parameters, rather than from a per-error-class repair table. The next input is
  chosen to distinguish surviving models when possible; another validation
  input is requested when necessary. Truncated candidate or query grids do not
  authorize bounded-agreement authorship. Peer-call equality is kept distinct
  from a directed literal expectation.
* **Experience changes priority, not permission.** Reviews of distinct questions
  update a simple signed-frequency score over name tokens, shared tokens, kind,
  and arity. Duplicate source/question evidence is counted once, contradictory
  reviews are excluded, and a question's own review does not score itself.
  These are fixed, hand-designed features and a small learned ranking, not a
  discovered semantic representation, a calibrated probability, or permission
  to edit. No review score can confirm an unseen question.
* **Measure only reported screens.** Candidate outcomes update learning only
  when the confined screen reports a specific, authoritative result. Unknown,
  unreported, timed-out, nonauthoritative and placeholder results are not
  silently counted as failures or successes. Producers are interleaved so one
  source of candidates does not monopolize the demonstrated 36-candidate
  cutoff; the cutoff still limits coverage.
* **Repair scope and publication.** A generated notion test binds its question,
  reference, target and source hash. A candidate must change only the target
  return expression and preserve the rest of the file. Ambiguous module stems
  are refused. Reviewed-notion candidates are checked in a private stage before
  the broker publishes the single target with a drift check; failed checks do
  not deliberately stage the candidate in the live workspace. These local
  checks are reported as `verified: false`, `correct: null`: they are not an
  independent verification of intended behavior. The generated test itself is
  written to the workspace, and its marker and caller metadata are not an
  authentication mechanism.
* **Feedback persistence.** The notion store respects the memory policy, uses
  distinct temporary files for writes, and exposes write errors rather than
  silently claiming to save them. It is not a multi-writer transactional store:
  simultaneous read-modify-write operations can still lose an update.

## Measurements and controls

All results below were run against the actual working tree, not a mocked
executor. Namespace-dependent tests require the broker available in this
sandbox. The fixture oracles and review labels are authored for evaluation;
they are not independent certification or a real user's authenticated feedback.

### Learning with unchanged code

The reproducible test
`test_review_priority_learns_from_feedback_without_granting_authority` reviews
four training questions: two positive and two negative. Four separate held-out
questions are left unreviewed.

| Held-out class | Before reviews | After reviews |
|---|---:|---:|
| Two fixture-positive relations | 0.0 each | 0.095238 each |
| Two fixture-negative relations | 0.0 each | -0.055556 each |

No code changed between the cold and warm scores; all held-out `review` entries
remained absent. This is a small, curated lexical/arity transfer demonstration,
not a measured real-world accuracy, false-positive rate, calibrated confidence,
or evidence that the system learned the meanings of those names. A different
name distribution or wrong feedback can reverse or degrade the ranking.

The no-review control writes no notion test or notion repair. The ambiguity
control exposes the same source to incompatible specifications and gets the same
tentative finding. Additional tests cover rejected and conflicting reviews,
identical-evidence deduplication, source-hash invalidation, insufficient or
contradictory examples, memory policy, ambiguous module stems, and truncated
search. Those controls show refusal in the tested cases, not universal safety.

### Guided repair and held-out values

Six small fixtures exercise the feedback/query/board loop, including unrelated
names, multiplication, addition, subtraction, and narrow/wide volume variants.
For each, fixture-provided examples answer the model's queries; the resulting
candidate is checked on two additional input values that were not the review
queries. **6/6** fixtures passed both held-out checks and preserved unrelated
functions. The mechanism did not autonomously discover their specifications:
the fixtures supplied the trusted reference and expected outputs.

Separately, ten ordinary board fixtures were accepted; **10/10** passed two
independent held-out values each after publication. Those ten fixture definitions
are an evaluation set, not a runtime lookup table. This is a narrow arithmetic
sample, not a whole-repository repair rate.

A real 36-candidate broker screen returned only the two reported outcomes before
its first pass. Learning kept `[(0, False), (1, True)]`, not 34 imagined
failures. A refused workspace snapshot returned placeholder passing indices; it
contributed no outcomes to learning. The tests also cover timeouts and
nonauthoritative screens.

### Test runs

```text
python3 -m pytest canonical/tests/test_reviewed_notions_and_active_queries_v1.py \
  canonical/tests/test_repair_board_heldout_v1.py -q -p no:randomly -rx
40 passed, 1 xfailed
```

The strict expected failure is intentional and important: a hostile function
can introspect and replace the in-process generalization probe's output binding.
A constant-returning candidate can thereby cause a forged positive result.
Duplicate-result and simple `print`-replacement attacks are now refused or
resisted, but they do not fix the underlying interpreter trust boundary. The
probe tests input sensitivity only; even an honest positive does **not** prove
correctness. The strict xfail documents the remaining counterexample.

Eight additional broker, operator, board, and self-model test files were run
using a separate Python virtual environment with pytest and pytest-subtests:
**79 passed, 17 subtests passed**. Four tests in the confined-measured-repair
file failed under the system interpreter because that exercise explicitly
requires a virtual environment; all 15 tests in that file passed in the venv.
The full eight-file command is:

```text
python -m pytest -q -p no:randomly \
  canonical/tests/test_operator_generalization_v1.py \
  canonical/tests/test_repair_candidate_broker_v1.py \
  canonical/tests/test_repair_candidate_broker_trusted_fixture_v1.py \
  canonical/tests/test_confined_measured_repair_v1.py \
  canonical/tests/test_a_candidate_that_fails_the_suite_is_refused_v1.py \
  canonical/tests/test_creature_posture_changes_its_choice_v1.py \
  canonical/tests/test_the_creature_runs_unattended_v1.py \
  canonical/tests/test_the_self_model_is_fed_what_the_creature_knows_v1.py
```

The same nine-file regression selection as pass 24, using the system
interpreter and `-q -p no:randomly`, changed from **23 failed / 46 passed** to
**22 failed / 47 passed**. Comparing the sorted test names found no new failing
names; `test_zero_host_exec_and_compatibility_invariants` was the one that no
longer failed. These are selected tests, not a claim that the full repository
passes. The remaining failures are:

```text
canonical/tests/test_four_wave_optimal_plan_v1.py::test_wave2_pluggy_class_method_crystallizes_and_warm_recalls_fast
canonical/tests/test_optimal_four_phase_awake_mastery_v1.py::test_phase2_byte_verified_two_step_capability_bridge_and_oracle_refusal
canonical/tests/test_optimal_four_phase_awake_mastery_v1.py::test_phase3_and_4_zero_prompt_awake_daemon_cow_guard_and_supplier_plan
canonical/tests/test_optimal_four_phase_awake_mastery_v1.py::test_phase3_mid_insertion_guard_transfer_and_coupled_two_file_zygote_repair
canonical/tests/test_optimal_four_phase_awake_mastery_v1.py::test_phase3_one_python_lesson_transfers_across_all_six_other_languages
canonical/tests/test_optimal_unified_creature_and_prc2_v1.py::OptimalUnifiedCreatureAndPrC2Tests::test_compound_cst_subtree_narrowing_cross_language_test_suite_and_suspect_line_priority
canonical/tests/test_optimal_unified_creature_and_prc2_v1.py::OptimalUnifiedCreatureAndPrC2Tests::test_optimal_pillar1_general_cst_algebra_and_auto_discovered_polyglot_cross_scope_transfer
canonical/tests/test_optimal_unified_creature_and_prc2_v1.py::OptimalUnifiedCreatureAndPrC2Tests::test_prc2_apply_time_broadening_5_of_5_and_weak_verifier_isolation
canonical/tests/test_post_066e8df_workspace_speed_and_r2_scientific_fabric_v1.py::test_phase2_r2_direct_adequacy_p3_policy_cegar_and_escape_repair_cycle
canonical/tests/test_post_066e8df_workspace_speed_and_r2_scientific_fabric_v1.py::test_phase3_sparse_symbolic_law_harmonic_science_domain_certificate_ooxml_and_capsules
canonical/tests/test_post_066e8df_workspace_speed_and_r2_scientific_fabric_v1.py::test_phase4_awake_pareto_capability_scheduler_confined_shell_and_unified_model_specialist_door
canonical/tests/test_self_expanding_awake_organism_v1.py::test_stage1_type_level_composer_macro_autonomous_v1_and_osworld_trajectory
canonical/tests/test_self_expanding_awake_organism_v1.py::test_stage3_active_mechanism_discriminator_grid_induction_and_capability_discovery
canonical/tests/test_unattended_inspector_investigation_v1.py::UnattendedInspectorInvestigationTests::test_an_existing_unfinished_catalog_goal_is_not_replaced
canonical/tests/test_unattended_inspector_investigation_v1.py::UnattendedInspectorInvestigationTests::test_new_process_resumes_the_same_unfinished_parent
canonical/tests/test_unattended_inspector_investigation_v1.py::UnattendedInspectorInvestigationTests::test_no_caller_named_goal_runs_then_resumes_without_claiming_parent
canonical/tests/test_unattended_inspector_investigation_v1.py::UnattendedInspectorInvestigationTests::test_wrong_answer_is_not_remembered_or_parent_closed
canonical/tests/test_unified_awake_cognitive_fabric_v1.py::test_stage2_unfamiliar_api_tool_planning_semantic_ambiguity_polytopes_and_lattice
canonical/tests/test_unified_awake_cognitive_fabric_v1.py::test_stage3_associative_memory_dom_grounding_perf_hotspots_and_command_repair
canonical/tests/test_unified_awake_cognitive_fabric_v1.py::test_stage4_r3_fixed_point_closure_skill_macro_and_adaptive_solver_v12
canonical/tests/test_zero_llm_awake_mastery_upgrades_v1.py::test_move2b_egraph_congruence_closed_algebraic_rule_generalization
canonical/tests/test_zero_llm_awake_mastery_upgrades_v1.py::test_move4_continuous_zero_llm_awake_agency_daemon_and_rule_expiry
```

## Operational use and unresolved boundaries

The board exposes `notion_review.store` and pending findings. Inspect them with
`python3 -m canonical.swe_kernel.notion_feedback_cli_v1 --store STORE list`.
Use `review FINDING --decision confirm --reviewer NAME --basis BASIS
--trusted-function FUNCTION`, or `--decision reject` without a reference. Run
the workspace sensor again to obtain the next plan; answer its exact proposed
arguments with `answer FINDING --args JSON_ARRAY --expected JSON_NUMBER
--reviewer NAME --basis BASIS`, then sense again. An ordinary board run may
author a test and attempt a repair once the stated gates are met. The CLI does
not authenticate a caller, source of truth, identity, or independence. Query
predictions are visible to the caller, so answers are not blinded.

The numeric hypothesis space, scan, candidate count, and finite query grid are
bounded and omit many real programs. Agreement on this finite space and two
external examples does not rule out functions outside the model. Larger
arities, large modules, imports, annotations, decorators, branching, mutable
state, and ambiguous modules can be declined. Name-token ranking remains prone
to the same semantic confounding that invalidated the former name gate.

The broker reports `carrier_qualified: false`; tests of one attempted host write
and single-file publication are not a hostile-code certification or a blanket
race-safety or multi-file atomicity guarantee. For **non-notion** repairs, the
legacy board path still writes candidate files into the live workspace before
checking and then tries to roll back on failure. That path, and any path relying
on the untrusted in-process probe, should not be treated as safe for adversarial
workspaces. A source-hash marker is a restriction, not a signature or grant of
authority. The whole-repository suite was not run.

The next first-principles step is not another table of fixes. It is to separate
trusted observation from untrusted execution, obtain authenticated or independently
checkable specifications, learn from more diverse non-curated feedback, measure
calibration and false positives on blind held-out tasks, and replace the legacy
live-staging path with a genuinely qualified transactional boundary. Until then,
this is a bounded, feedback-guided capability, not autonomous semantic knowledge.
The implementation and tests made no paid external model API calls; sandbox
compute was used. `truth.achieved` remains false.
