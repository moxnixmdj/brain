"""Unified Epistemic Portfolio & Multi-Organ Runtime Spine (`K3 = 0`) — v1.

Unifies the Brain's previously stranded zero-model repair, tomography, CEGIS,
active-automata, version-space, contract-refusal, compression-gain, and
environment-discovery organs behind a single deterministic (`model_calls == 0`,
`parameters_stored == 0`) execution engine for `UnifiedModel`.

Core architectural mechanisms:
  1. `UNIFIED_ORGAN_MANIFEST` & `organ_portfolio_status()`:
     Runtime-verifies and wires 18 specialized organs across `canonical/swe_kernel`
     and `canonical/runtime` into the unified runtime surface.
  2. `ZeroOverheadLineMonitor`:
     PEP 669 `sys.monitoring` one-shot `DISABLE` line coverage on Python 3.12+
     with repo-scoped frame-filtered `sys.settrace` fallback on Python 3.11.
  3. `WarmCoWForkScreener`:
     POSIX `os.fork()` Copy-on-Write batch candidate verifier using hardlinked
     ephemeral overlays, post-fork RNG reseeding, module-cache eviction via
     `sys.modules.pop(...)` + `importlib.invalidate_caches()`, and OS-level fd
     silencing (~5-15 ms/candidate vs ~800 ms cold subprocesses).
  4. `MultiSignalCausalLocalizer` + `CodePlanObligationZipper`:
     Bottom-up traceback walker + AST `pytest.raises` / assertion callee import
     resolver + proactive multi-file symbol/arity change-impact obligation DAG.
  5. `FirstPrinciplesMorphismSynthesizer`:
     Domain-independent PL/AST/Lexer repair morphisms (use-before-init & eager
     `__init__` -> lazy `@property` lift, regex/lexer boundary algebra, ASCII
     pre-guards before Unicode case-folding, `DictComp` first-wins vs last-wins
     order duals, `str`-vs-`Iterable` homomorphism guards, error-accumulating
     parser partial-result continuation, and scope-aware call-arg substitution).
  6. `WholeSliceMutantKillingGate`:
     Hard precision gate requiring full enclosing test-file verification
     (`previously_passing_broken == 0` and all target failures resolved), plus
     differential separating-witness & MDL (`compression_gain_v1`) tie-breaking
     when multiple patches survive visible tests.
  7. `EStitchSemanticSkillStore` & `ActiveSymbolicMealyLearner`:
     Alpha-normalized Region-SSA equational anti-unification with bi-temporal
     validity and MDL/surprise gating, plus active $L^\\#$ separating-word Mealy
     machine learning built on `minimal_experiment_v1`.
"""
from __future__ import annotations

import ast
import concurrent.futures
import copy
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import random
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "BRAIN_UNIFIED_EPISTEMIC_PORTFOLIO_V1"

# ---------------------------------------------------------------------------
# 1. UNIFIED ORGAN MANIFEST & PORTFOLIO INTROSPECTION
# ---------------------------------------------------------------------------

UNIFIED_ORGAN_MANIFEST: tuple[dict[str, Any], ...] = (
    {
        "organ_id": "swe.metamorphic_habitation_zipper",
        "module": "canonical.swe_kernel.metamorphic_habitation_zipper_v1",
        "entrypoints": ("repair_repo_unified_zero_model",),
        "role": "zero_model_ast_habitation_and_call_zipper",
    },
    {
        "organ_id": "swe.reverse_tomography_algebra",
        "module": "canonical.swe_kernel.reverse_tomography_algebra_v1",
        "entrypoints": (
            "synthesize_regex_refinement_patches",
            "synthesize_boundary_norm_prelude_patches",
            "synthesize_dataflow_shadow_subst_patches",
            "extract_multi_stmt_tree_morphism",
        ),
        "role": "backward_value_witness_inversion_and_affine_synthesis",
    },
    {
        "organ_id": "swe.causal_cegis_inventor",
        "module": "canonical.swe_kernel.causal_cegis_inventor_v1",
        "entrypoints": ("CausalCEGISInventor", "synthesize_obsegraph_branch_repairs"),
        "role": "observational_equivalence_u_ir_bottom_up_cegis",
    },
    {
        "organ_id": "swe.residual_wall_closers",
        "module": "canonical.swe_kernel.residual_wall_closers_v1",
        "entrypoints": ("ResidualWallCloser", "apply_edits"),
        "role": "whitebox_contract_and_sibling_callsite_mining",
    },
    {
        "organ_id": "swe.environment_broker",
        "module": "canonical.swe_kernel.the_environment_broker_v1",
        "entrypoints": ("detect_layout", "declared_test_commands"),
        "role": "zero_prior_polyglot_layout_and_test_command_discovery",
    },
    {
        "organ_id": "swe.c_asan_cegis_repair",
        "module": "canonical.swe_kernel.c_asan_cegis_repair_v1",
        "entrypoints": ("repair_c_repo_asan_cegis",),
        "role": "polyglot_c_cpp_asan_ubsan_cegis_repair",
    },
    {
        "organ_id": "swe.js_causal_cegis_repair",
        "module": "canonical.swe_kernel.js_causal_cegis_repair_v1",
        "entrypoints": ("repair_js_repo_causal_cegis",),
        "role": "polyglot_js_ts_v8_causal_cegis_repair",
    },
    {
        "organ_id": "swe.angelic_lens_cow_repair",
        "module": "canonical.swe_kernel.angelic_lens_cow_repair_v1",
        "entrypoints": ("repair_git_repo_from_pytest", "repair_issue_only_green_repo_cow"),
        "role": "angelic_trace_lens_and_green_metamorphic_cow_repair",
    },
    {
        "organ_id": "swe.compression_gain",
        "module": "canonical.swe_kernel.compression_gain_v1",
        "entrypoints": ("description_bytes", "admit_corpus_abstraction", "derive_probe_domain"),
        "role": "mdl_description_length_and_boundary_probe_domain",
    },
    {
        "organ_id": "runtime.composer_route",
        "module": "canonical.runtime.composer_route_v1",
        "entrypoints": ("route", "execute_chain"),
        "role": "typed_multi_step_capability_chain_composer",
    },
    {
        "organ_id": "runtime.declared_input_derivation",
        "module": "canonical.runtime.declared_input_derivation_v1",
        "entrypoints": ("derive",),
        "role": "artifact_fact_extraction_for_unbound_capability_slots",
    },
    {
        "organ_id": "runtime.instruction_contract",
        "module": "canonical.runtime.instruction_contract_v1",
        "entrypoints": ("compile_contract", "check_contract"),
        "role": "natural_language_postcondition_contract_compiler",
    },
    {
        "organ_id": "runtime.refusal_as_specification",
        "module": "canonical.runtime.a_refusal_is_a_specification_v1",
        "entrypoints": ("read_refusal", "repair_in_world"),
        "role": "diagnostic_stderr_refusal_to_world_repair_compiler",
    },
    {
        "organ_id": "runtime.demonstration_version_space",
        "module": "canonical.runtime.demonstration_version_space_v1",
        "entrypoints": ("VersionSpaceSkill", "build_arm", "evaluate"),
        "role": "few_shot_version_space_program_algebra",
    },
    {
        "organ_id": "runtime.minimal_experiment",
        "module": "canonical.runtime.minimal_experiment_v1",
        "entrypoints": ("make_machine", "separating_word", "minimal_consistent_machine", "rank_experiments"),
        "role": "active_mealy_separating_word_experiment_synthesizer",
    },
    {
        "organ_id": "runtime.evidence_demand",
        "module": "canonical.runtime.evidence_demand_v1",
        "entrypoints": ("demand_evidence", "what_would_settle_it", "group_by_behaviour"),
        "role": "observational_equivalence_partition_and_witness_demand",
    },
    {
        "organ_id": "runtime.tool_census",
        "module": "canonical.runtime.tool_census_v1",
        "entrypoints": ("census", "census_many", "parse_contract"),
        "role": "live_environment_cli_and_module_affordance_census",
    },
    {
        "organ_id": "bound.python_counterfactual_spec_repair",
        "module": "canonical.runtime.bound_capabilities.python_counterfactual_spec_repair_v1",
        "entrypoints": ("run",),
        "role": "counterfactual_value_probe_expression_synthesizer",
    },
    {
        "organ_id": "swe.causal_swe_repair",
        "module": "canonical.swe_kernel.causal_swe_repair_v1",
        "entrypoints": ("repair_worktree", "synthesize_candidates"),
        "role": "def_use_relational_zipper_and_causal_swe_repair",
    },
    {
        "organ_id": "swe.assertion_operand_tomography",
        "module": "canonical.swe_kernel.assertion_operand_tomography_v1",
        "entrypoints": ("instrument", "capture"),
        "role": "failing_assertion_live_operand_value_tomography",
    },
    {
        "organ_id": "tools.assertion_localisation",
        "module": "canonical.tools.assertion_localisation_v1",
        "entrypoints": ("localise", "failing_assertion"),
        "role": "assertion_symbol_and_literal_index_localizer",
    },
    {
        "organ_id": "tools.assertion_demand_grammar",
        "module": "canonical.tools.the_assertion_is_the_demand_v1",
        "entrypoints": ("assert_form", "conditional_productions", "guard_productions"),
        "role": "zero_leakage_assertion_demand_and_guard_production_grammar",
    },
    {
        "organ_id": "tools.relation_from_failing_run",
        "module": "canonical.tools.the_relation_is_read_from_the_failing_run_v1",
        "entrypoints": ("sites_in", "instrument", "demanded_values", "relations_for", "apply_edit"),
        "role": "single_run_live_value_to_demanded_relation_abducer",
    },
    {
        "organ_id": "tools.force_the_value_and_see",
        "module": "canonical.tools.force_the_value_and_see_v1",
        "entrypoints": ("instrument", "run_case", "expressions_at"),
        "role": "angelic_in_frame_value_forcing_and_expression_synthesizer",
    },
    {
        "organ_id": "swe.what_the_condition_wants",
        "module": "canonical.swe_kernel.what_the_condition_wants_v1",
        "entrypoints": ("harvest", "what_the_condition_wants"),
        "role": "branch_predicate_demanded_operand_reader",
    },
    {
        "organ_id": "swe.witness_inversion",
        "module": "canonical.swe_kernel.witness_inversion_v1",
        "entrypoints": ("invert", "grammar_candidates", "apply_expression", "localize_by_angelic_perturbation"),
        "role": "live_frame_return_witness_evaluation_inverter",
    },
    {
        "organ_id": "swe.operand_invention",
        "module": "canonical.swe_kernel.operand_invention_v1",
        "entrypoints": ("operands", "conditions", "separating_terms", "differential"),
        "role": "scope_vocabulary_and_differential_operand_inventor",
    },
    {
        "organ_id": "swe.interventional_goal",
        "module": "canonical.swe_kernel.interventional_goal_v1",
        "entrypoints": ("intervene", "CalculatedWeights"),
        "role": "causal_do_intervention_goal_and_false_win_detector",
    },
    {
        "organ_id": "runtime.systematic_exploration",
        "module": "canonical.runtime.systematic_exploration_v1",
        "entrypoints": ("explore_to_goal", "drive"),
        "role": "zero_instruction_state_graph_explorer_without_revisit_waste",
    },
    {
        "organ_id": "tools.refusal_curriculum",
        "module": "canonical.tools.the_refusal_is_the_curriculum_v1",
        "entrypoints": ("read_demand", "parse_rows", "headings_of"),
        "role": "one_visit_environment_refusal_to_axiom_compiler",
    },
    {
        "organ_id": "runtime.instruction_policy",
        "module": "canonical.runtime.instruction_policy_v1",
        "entrypoints": ("first_action", "ContractArm", "order_for_execution"),
        "role": "time_zero_instruction_to_action_policy_with_zero_reward",
    },
    {
        "organ_id": "runtime.aimed_action",
        "module": "canonical.runtime.aimed_action_v1",
        "entrypoints": ("aimed_actions", "rule_of"),
        "role": "page_derived_structural_and_geometric_action_generator",
    },
    {
        "organ_id": "swe.interface_action_grammar",
        "module": "canonical.swe_kernel.interface_action_grammar_v1",
        "entrypoints": ("A11yEnvironment", "GUIWorkflowMemory", "solve_gui_goal", "CLIGrammarMemory", "solve_cli_need"),
        "role": "zero_vlm_accessibility_tree_and_cli_grammar_solver",
    },
    {
        "organ_id": "swe.patch_verdict_amplification",
        "module": "canonical.swe_kernel.patch_verdict_amplification_v1",
        "entrypoints": ("prepare_laws", "laws_against_prepared", "amplify"),
        "role": "test_independent_api_law_verdict_amplifier",
    },
    {
        "organ_id": "swe.metamorphic_laws",
        "module": "canonical.swe_kernel.metamorphic_laws_v1",
        "entrypoints": ("check_canonicality", "check_round_trip", "check_idempotence"),
        "role": "canonicality_round_trip_and_idempotence_law_checker",
    },
    {
        "organ_id": "swe.repair_version_space_selection",
        "module": "canonical.swe_kernel.repair_version_space_selection_v1",
        "entrypoints": ("partition", "diagnose", "maximum_elimination", "ask_until_settled"),
        "role": "maximum_elimination_version_space_repair_selector",
    },
    {
        "organ_id": "runtime.edit_kind_learning",
        "module": "canonical.runtime.edit_kind_learning_v1",
        "entrypoints": ("operators_of", "fits", "built"),
        "role": "open_ast_hole_operator_anti_unifier_and_applier",
    },
    {
        "organ_id": "swe.weights_from_scratch",
        "module": "canonical.swe_kernel.weights_from_scratch_v1",
        "entrypoints": ("CalculatedState", "connect_instant_knowledge"),
        "role": "calculated_online_fast_parameters_with_zero_stored_weights",
    },
    {
        "organ_id": "swe.composition_verification",
        "module": "canonical.swe_kernel.composition_verification_v1",
        "entrypoints": ("sense_chain", "generate_compositions", "admit_composition"),
        "role": "non_interfering_skill_chain_composition_verifier",
    },
    {
        "organ_id": "tools.guide_as_test_suite",
        "module": "canonical.tools.the_guide_is_a_test_suite_v1",
        "entrypoints": ("fenced_blocks", "docstring_blocks", "transcripts"),
        "role": "executable_docstring_and_markdown_transcript_harvester",
    },
    {
        "organ_id": "swe.cow_angelic_zygote",
        "module": "canonical.swe_kernel.cow_angelic_zygote_v1",
        "entrypoints": ("PytestCoWZygoteServer", "synthesize_algebraic_differential_repairs", "synthesize_angelic_separating_guards"),
        "role": "in_memory_cow_zygote_algebraic_and_angelic_guard_synthesizer",
    },
    {
        "organ_id": "swe.repo_native_component_mining",
        "module": "canonical.swe_kernel.repo_native_component_mining_v1",
        "entrypoints": ("package_modules", "symbols"),
        "role": "cross_module_repo_native_component_and_symbol_miner",
    },
    {
        "organ_id": "swe.incremental_semantic_graph",
        "module": "canonical.swe_kernel.incremental_semantic_graph_v1",
        "entrypoints": (
            "IncrementalSemanticGraph",
            "SymbolRowSQLiteCache",
            "localize_symptom_and_impacted_tests",
            "query_impacted_tests",
        ),
        "role": "content_sha256_incremental_delta_semantic_symbol_and_import_graph",
    },
    {
        "organ_id": "tools.machine_is_the_definition",
        "module": "canonical.tools.the_machine_is_the_definition_v1",
        "entrypoints": ("define", "learn_a_form", "candidates"),
        "role": "lazy_verified_command_and_environment_definition_index",
    },
    {
        "organ_id": "swe.spec_contract_synthesis",
        "module": "canonical.swe_kernel.spec_contract_synthesis_v1",
        "entrypoints": (
            "mine_exception_contracts",
            "synthesize_spec_guards",
            "synthesize_frame_containments",
            "mine_postcondition_contracts",
        ),
        "role": "pytest_raises_exception_guard_and_escape_frame_contract_synthesizer",
    },
    {
        "organ_id": "swe.causal_nexus",
        "module": "canonical.swe_kernel.causal_nexus_v1",
        "entrypoints": (
            "extract_value_obligations",
            "infer_transducer",
            "invert_lens",
            "differential_boundary_scan",
        ),
        "role": "value_obligation_extractor_and_symmetric_fst_lens_inverter",
    },
    {
        "organ_id": "swe.frontier_unified_engine",
        "module": "canonical.swe_kernel.frontier_unified_engine_v1",
        "entrypoints": ("synthesize_fst_lens", "compute_ast_structural_fingerprint"),
        "role": "bidirectional_fst_codec_lens_and_ast_fingerprint_synthesizer",
    },
    {
        "organ_id": "swe.semantic_causal_engine",
        "module": "canonical.swe_kernel.semantic_causal_engine_v1",
        "entrypoints": ("build_project_cpg", "ProjectCPG"),
        "role": "localized_code_property_graph_and_site_splicer",
    },
    {
        "organ_id": "swe.first_principles_mental_cegis",
        "module": "canonical.swe_kernel.first_principles_mental_cegis_v1",
        "entrypoints": (
            "ProgramStateMentalModel",
            "synthesize_expressions_bottom_up",
            "synthesize_discriminating_predicates",
        ),
        "role": "in_memory_contrastive_state_bottom_up_expression_cegis",
    },
    {
        "organ_id": "swe.taught_edit_by_example",
        "module": "canonical.swe_kernel.taught_actions.edit_by_example_v1",
        "entrypoints": ("edit_by_example", "learn_all", "repeated"),
        "role": "one_shot_before_after_ast_refactor_and_lesson_generalizer",
    },
    {
        "organ_id": "swe.polyglot_build_ci_engine",
        "module": "canonical.swe_kernel.polyglot_build_ci_engine_v1",
        "entrypoints": (
            "rust_repair_and_verify",
            "go_repair_and_verify",
            "ts_repair_and_verify",
            "cpp_transform_and_verify",
            "java_transform_and_verify",
        ),
        "role": "polyglot_rust_go_ts_cpp_java_ast_cst_repair_and_build_verifier",
    },
    {
        "organ_id": "tools.aimed_edits_from_failure",
        "module": "canonical.tools.aimed_edits_from_the_program_and_the_failure_v1",
        "entrypoints": ("commuted", "space_builder", "inserted"),
        "role": "program_and_failure_derived_aimed_ast_edit_generator",
    },
    {
        "organ_id": "tools.same_guard_discriminator",
        "module": "canonical.tools.the_same_guard_twice_is_the_discriminator_v1",
        "entrypoints": ("instrument_module", "predicate_candidates", "refine_guard"),
        "role": "repeated_branch_execution_occurrence_discriminator",
    },
    {
        "organ_id": "swe.distinction_creation",
        "module": "canonical.swe_kernel.distinction_creation_v1",
        "entrypoints": ("synthesise_guard", "branch_from_outcomes"),
        "role": "positive_negative_outcome_separating_guard_creator",
    },
    {
        "organ_id": "bound.python_review_diff_mutation_gate",
        "module": "canonical.runtime.bound_capabilities.python_review_diff_mutation_gate",
        "entrypoints": ("run",),
        "role": "changed_line_behavioural_ast_mutant_killing_oracle",
    },
    {
        "organ_id": "swe.specification_from_structure",
        "module": "canonical.swe_kernel.specification_from_structure_v1",
        "entrypoints": ("derive", "public_functions", "confirm_and_judge"),
        "role": "zero_test_structural_idempotence_roundtrip_and_stdlib_law_oracle",
    },
    {
        "organ_id": "runtime.verifier_falsification",
        "module": "canonical.runtime.verifier_falsification_v1",
        "entrypoints": ("run",),
        "role": "meta_verifier_vacuity_and_false_accept_falsifier",
    },
    {
        "organ_id": "runtime.osworld_zero_model_policy",
        "module": "canonical.runtime.osworld_v21_zero_model_policy_v1",
        "entrypoints": ("ZeroModelOSWorldPolicy", "parse_a11y_nodes", "decode_png_to_rgb"),
        "role": "zero_vlm_a11y_and_pure_canvas_differential_gui_policy",
    },
    {
        "organ_id": "swe.universal_computer_agent",
        "module": "canonical.swe_kernel.universal_computer_agent_v1",
        "entrypoints": (
            "extract_canvas_regions",
            "diff_framebuffers",
            "compute_petri_dominator_cut_vertices",
            "calculate_separating_projection",
        ),
        "role": "framebuffer_region_tomography_and_petri_dominator_cut_checkpointing",
    },
    {
        "organ_id": "tools.guide_is_action_grammar",
        "module": "canonical.tools.the_guide_is_an_action_grammar_v1",
        "entrypoints": ("admissible", "compile_step", "execute_path"),
        "role": "documentation_derived_typed_cli_and_artifact_action_grammar",
    },
    {
        "organ_id": "tools.goal_is_trace_quotient",
        "module": "canonical.tools.the_goal_is_a_quotient_of_the_trace_v1",
        "entrypoints": ("derived_generators", "enumerate_lattice", "coarsest"),
        "role": "unknown_goal_coarsest_sufficient_trace_quotient_lattice_solver",
    },
    {
        "organ_id": "tools.action_effect_provenance",
        "module": "canonical.tools.an_actions_effect_is_a_provenance_map_v1",
        "entrypoints": ("infer", "predict", "explain"),
        "role": "black_box_command_effect_provenance_rule_abducer_and_predictor",
    },
    {
        "organ_id": "runtime.hypothesis_classes",
        "module": "canonical.runtime.hypothesis_classes_v1",
        "entrypoints": ("fit_all", "determine", "question_for", "compose_and_verify"),
        "role": "slotted_functional_and_piecewise_hypothesis_fitter_with_active_queries",
    },
    {
        "organ_id": "runtime.vocabulary_induction",
        "module": "canonical.runtime.vocabulary_induction_v1",
        "entrypoints": ("Ontology", "recover_vocabulary", "induce", "encounter"),
        "role": "closed_form_non_forgetting_concept_and_vocabulary_ontology_inducer",
    },
    {
        "organ_id": "swe.guarded_meaning_ir",
        "module": "canonical.swe_kernel.guarded_meaning_ir_v1",
        "entrypoints": ("SemiPersistentEGraph", "lower_python", "anti_unify", "terms_equal"),
        "role": "guarded_region_ssa_meaning_ir_and_undo_log_colored_egraph",
    },
    {
        "organ_id": "swe.executable_simulator_mental_model",
        "module": "canonical.swe_kernel.executable_simulator_mental_model_v1",
        "entrypoints": (
            "simulate_python_fast",
            "abstract_analyze_function",
            "forward_backward_prunes_candidate",
            "EnvironmentMentalModel",
        ),
        "role": "microsecond_in_ram_concrete_and_forward_backward_abstract_pruning_simulator",
    },
    {
        "organ_id": "swe.angelic_cegis_repair",
        "module": "canonical.swe_kernel.angelic_cegis_repair_v1",
        "entrypoints": (
            "splice_ast_node",
            "get_node_source",
            "synthesize_angelic_condition",
            "synthesize_failure_demand_patches",
        ),
        "role": "sub_0_1ms_byte_span_ast_splicer_and_angelic_branch_condition_synthesizer",
    },
    {
        "organ_id": "swe.angelic_oe_synthesizer",
        "module": "canonical.swe_kernel.angelic_oe_synthesizer_v1",
        "entrypoints": ("synthesize_oe_expression", "synthesize_causal_structural_patches"),
        "role": "value_space_angelic_spec_and_bottom_up_observational_equivalence_synthesizer",
    },
    {
        "organ_id": "swe.differential_witness_inversion",
        "module": "canonical.swe_kernel.differential_witness_inversion_v1",
        "entrypoints": (
            "synthesize_live_differential_witness_repairs",
            "synthesize_live_differential_witness_repairs_in_ram",
        ),
        "role": "live_frame_differential_witness_inverter_and_dunder_homomorphism_synthesizer",
    },
    {
        "organ_id": "swe.petri_cow_splicing_engine",
        "module": "canonical.swe_kernel.petri_cow_splicing_engine_v1",
        "entrypoints": (
            "RepoNativePetriMiner",
            "BackwardWitnessAndDualSplicer",
            "ParallelCoWWorldTomographer",
            "AdmissionFilteredSkillStore",
        ),
        "role": "repo_native_petri_type_miner_and_parallel_cow_world_tomographer",
    },
    {
        "organ_id": "swe.tree_sitter_cst_skill_skeleton",
        "module": "canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1",
        "entrypoints": ("compile_rule_to_cst_skeleton", "iter_cst_skeleton_candidates", "render_canonical_expr"),
        "role": "seven_language_tree_sitter_cst_anti_unifier_and_cross_language_skill_compiler",
    },
    {
        "organ_id": "swe.egraph_and_deductive_synthesizer",
        "module": "canonical.swe_kernel.egraph_and_deductive_synthesizer_v1",
        "entrypoints": ("EGraph", "egraph_optimize_function", "author_verified_tests", "propose_egraph_algebraic_rewrites"),
        "role": "equality_saturation_optimizer_and_mutant_killing_verified_test_author",
    },
    {
        "organ_id": "swe.induced_edit_basis",
        "module": "canonical.swe_kernel.induced_edit_basis_v1",
        "entrypoints": ("induce_templates", "candidates_from_templates", "induce_node_templates", "candidates_from_node_templates"),
        "role": "contextual_ast_edit_basis_and_insertion_template_inducer",
    },
    {
        "organ_id": "tools.rejected_value_producer",
        "module": "canonical.tools.the_value_that_was_rejected_had_a_producer_v1",
        "entrypoints": ("rejected_value", "fix_functions"),
        "role": "rejected_assertion_value_backward_dynamic_producer_localizer",
    },
    {
        "organ_id": "tools.failing_run_names_expression",
        "module": "canonical.tools.the_failing_run_names_the_expression_v1",
        "entrypoints": ("blame_from_messages", "blame", "guard_span", "derived_candidates"),
        "role": "formatted_failure_message_expression_blame_and_guard_deriver",
    },
    {
        "organ_id": "tools.demand_learned_from_run",
        "module": "canonical.tools.the_demand_is_learned_from_the_run_v1",
        "entrypoints": ("guard_sites", "learn", "compile_rule", "replace"),
        "role": "contrastive_run_feature_demand_predicate_learner",
    },
    {
        "organ_id": "tools.grammar_closed_repair",
        "module": "canonical.tools.grammar_closed_repair_v1",
        "entrypoints": ("atoms_of", "candidate_texts", "operator_swaps", "replace_at"),
        "role": "program_own_grammar_closed_atom_and_operator_synthesizer",
    },
    {
        "organ_id": "swe.demonstration_sufficiency",
        "module": "canonical.swe_kernel.demonstration_sufficiency_v1",
        "entrypoints": ("signature", "space", "experiment_table", "sufficiency", "decide"),
        "role": "decidable_one_shot_demonstration_sufficiency_and_experiment_gate",
    },
    {
        "organ_id": "swe.rule_scope_learning",
        "module": "canonical.swe_kernel.rule_scope_learning_v1",
        "entrypoints": ("learn_scope", "synthesize_diagnostic_probes", "calibrate_rule_scope"),
        "role": "diagnostic_boundary_probe_rule_generality_scope_calibrator",
    },
    {
        "organ_id": "swe.proved_composition",
        "module": "canonical.swe_kernel.proved_composition_v1",
        "entrypoints": ("ProvedOperation", "compose", "rule_op", "structural_proof"),
        "role": "premise_survival_and_proof_survival_skill_chain_composer",
    },
    {
        "organ_id": "swe.verified_skill_crystallizer",
        "module": "canonical.swe_kernel.verified_skill_crystallizer_v1",
        "entrypoints": (
            "anti_unify_code_rule",
            "iter_crystallized_code_rule_candidates",
            "apply_crystallized_code_rule",
            "VerifiedSkillStore",
        ),
        "role": "holed_token_and_ast_skill_crystallizer_with_mutated_twin_verification",
    },
    {
        "organ_id": "swe.concept_library",
        "module": "canonical.swe_kernel.concept_library_v1",
        "entrypoints": (
            "eval_pure_ast_expr",
            "eval_pure_ast_function",
            "higher_order_plotkin_lgg",
            "canonicalize_ast_via_egraph",
            "CompoundingConceptLibrary",
        ),
        "role": "sub_ms_pure_ast_evaluator_and_higher_order_plotkin_lgg_concept_library",
    },
    {
        "organ_id": "swe.meta_circular_organ_graph",
        "module": "canonical.swe_kernel.meta_circular_organ_graph_v1",
        "entrypoints": ("verify_pure_organ_ast", "compile_organ_namespace", "make_organ", "synthesize_discriminating_input"),
        "role": "exec_free_pure_ast_meta_circular_compounding_organ_graph",
    },
    {
        "organ_id": "runtime.settlement",
        "module": "canonical.runtime.settlement_v1",
        "entrypoints": ("VersionSpace", "settle", "derive_probe_space", "diagnose_structure"),
        "role": "epistemic_version_space_settlement_and_premature_lockin_guard",
    },
    {
        "organ_id": "runtime.transfer_learning",
        "module": "canonical.runtime.transfer_learning_v1",
        "entrypoints": ("fingerprint", "similarity", "walk_carried_model", "remember", "recall"),
        "role": "cross_environment_structural_transition_fingerprint_transfer",
    },
    {
        "organ_id": "tools.right_question_is_experiment",
        "module": "canonical.tools.the_right_question_is_an_experiment_v1",
        "entrypoints": ("extract_claims", "evaluate_claim", "induce_signatures", "compose_plan"),
        "role": "prose_claim_to_minimal_discriminating_witness_experiment_compiler",
    },
    {
        "organ_id": "tools.precondition_not_in_trace",
        "module": "canonical.tools.the_precondition_is_not_in_the_trace_v1",
        "entrypoints": ("sense", "verdict", "exact_precondition"),
        "role": "hidden_world_precondition_abducer_beyond_visible_action_traces",
    },
    {
        "organ_id": "swe.computer_use_agent",
        "module": "canonical.swe_kernel.computer_use_agent_v1",
        "entrypoints": ("ComputerUseAgent", "StandingFactsLedger", "find_articulation_subgoals", "synthesize_state_key"),
        "role": "calculated_state_key_and_articulation_subgoal_computer_use_agent",
    },
    {
        "organ_id": "swe.executable_mental_model",
        "module": "canonical.swe_kernel.executable_mental_model_v1",
        "entrypoints": ("perceive_environment_state", "RelationalWorldSimulator", "check_goal_satisfied"),
        "role": "five_layer_dom_canvas_sqlite_git_file_differential_world_simulator",
    },
    {
        "organ_id": "runtime.computer_env",
        "module": "canonical.runtime.computer_env_v1",
        "entrypoints": ("ComputerEnv", "ground_dom_or_browser_surface", "perform_chain", "discover"),
        "role": "sandboxed_cli_and_dom_surface_affordance_environment",
    },
    {
        "organ_id": "swe.partial_order_planner",
        "module": "canonical.swe_kernel.partial_order_planner_v1",
        "entrypoints": ("Operator", "Plan", "plan", "induce_conditional_operators", "execute"),
        "role": "causal_link_partial_order_planner_and_conditional_operator_inducer",
    },
    {
        "organ_id": "swe.credit_assignment",
        "module": "canonical.swe_kernel.credit_assignment_v1",
        "entrypoints": ("CreditAssignment", "sense_trace", "generate_counterfactuals", "identify_credit", "admit_credit"),
        "role": "counterfactual_trajectory_rollout_step_credit_attributor",
    },
    {
        "organ_id": "tools.guide_is_key_table",
        "module": "canonical.tools.the_guide_is_a_key_table_v1",
        "entrypoints": ("table_rows", "posterior", "bits_remaining", "choose"),
        "role": "cli_help_key_table_entropy_splitting_posterior_solver",
    },
    {
        "organ_id": "tools.repertoire_is_query",
        "module": "canonical.tools.the_repertoire_is_a_query_v1",
        "entrypoints": ("catalogue", "subcommands_of", "options_of", "bm25"),
        "role": "live_machine_command_repertoire_indexer_and_bm25_retriever",
    },
    {
        "organ_id": "tools.goal_is_discriminator",
        "module": "canonical.tools.the_goal_is_a_discriminator_v1",
        "entrypoints": ("terms_from", "minimal_discriminators", "learn", "plan_under"),
        "role": "minimal_state_predicate_goal_discriminator_and_planner",
    },
    {
        "organ_id": "tools.frame_crosses_machine",
        "module": "canonical.tools.the_frame_crosses_the_machine_v1",
        "entrypoints": ("execute", "slots_of", "goals_of", "hypothesis_space", "agrees"),
        "role": "cross_machine_invariant_frame_slot_and_goal_transfer_engine",
    },
)


def organ_portfolio_status() -> dict[str, Any]:
    """Probe and report live importability & callable bindings across all 18 unified organs."""
    rows: list[dict[str, Any]] = []
    ready_count = 0
    for spec in UNIFIED_ORGAN_MANIFEST:
        mod_name = str(spec["module"])
        eps = tuple(spec["entrypoints"])
        ok = False
        missing_eps: list[str] = []
        err: str | None = None
        try:
            mod = importlib.import_module(mod_name)
            for ep in eps:
                if not callable(getattr(mod, ep, None)):
                    missing_eps.append(ep)
            ok = len(missing_eps) == 0
        except Exception as exc:
            err = f"{type(exc).__name__}:{exc}"
        if ok:
            ready_count += 1
        rows.append(
            {
                "organ_id": spec["organ_id"],
                "module": mod_name,
                "entrypoints": list(eps),
                "role": spec["role"],
                "ready": ok,
                "missing_entrypoints": missing_eps,
                "error": err,
            }
        )
    return {
        "schema": SCHEMA,
        "total_organs": len(UNIFIED_ORGAN_MANIFEST),
        "ready_organs": ready_count,
        "all_ready": ready_count == len(UNIFIED_ORGAN_MANIFEST),
        "organs": rows,
        "model_calls": 0,
        "parameters_stored": 0,
    }


# ---------------------------------------------------------------------------
# 2. ZERO-OVERHEAD COVERAGE / LINE MONITOR (PEP 669 `sys.monitoring` + 3.11 FALLBACK)
# ---------------------------------------------------------------------------


class ZeroOverheadLineMonitor:
    """Near-zero-overhead repo-scoped line hit recorder.

    Uses PEP 669 `sys.monitoring` with one-shot `DISABLE` per `(code, line)` when
    running on Python 3.12+, and falls back to a frame-filtered `sys.settrace` hook
    that immediately returns `None` on non-repository frames on Python 3.11.
    """

    def __init__(self, repo_root: pathlib.Path, *, exclude_tests: bool = True) -> None:
        self.repo_root = str(repo_root.resolve())
        self.exclude_tests = exclude_tests
        self.hits: set[tuple[str, int]] = set()
        self._backend = "none"
        self._tool_id: int | None = None
        self._prev_trace: Any = None

    def _rel_if_tracked(self, filename: str) -> str | None:
        if not filename or not filename.startswith(self.repo_root):
            return None
        rel = filename[len(self.repo_root) :].lstrip("/\\").replace("\\", "/")
        if not rel.endswith(".py"):
            return None
        if self.exclude_tests:
            base = rel.rsplit("/", 1)[-1]
            if rel.startswith("tests/") or "/tests/" in rel or base.startswith("test_") or base.endswith("_test.py"):
                return None
        return rel

    def __enter__(self) -> "ZeroOverheadLineMonitor":
        mon = getattr(sys, "monitoring", None)
        if mon is not None:
            for tid in range(5, 0, -1):
                try:
                    if mon.get_tool(tid) is None:
                        mon.use_tool_id(tid, "brain_epistemic_line_monitor")
                        self._tool_id = tid
                        break
                except Exception:
                    continue
        if self._tool_id is not None and mon is not None:
            self._backend = "sys.monitoring"
            disable_tok = mon.DISABLE

            def _on_line(code: Any, line_number: int) -> Any:
                rel = self._rel_if_tracked(getattr(code, "co_filename", ""))
                if rel is not None:
                    self.hits.add((rel, int(line_number)))
                return disable_tok

            mon.register_callback(self._tool_id, mon.events.LINE, _on_line)
            mon.set_events(self._tool_id, mon.events.LINE)
        else:
            self._backend = "sys.settrace_filtered"
            self._prev_trace = sys.gettrace()
            code_visits: dict[Any, int] = {}

            def _local_trace(frame: Any, event: str, arg: Any) -> Any:
                if event == "line":
                    rel = self._rel_if_tracked(frame.f_code.co_filename)
                    if rel is not None:
                        self.hits.add((rel, int(frame.f_lineno)))
                return _local_trace

            def _global_trace(frame: Any, event: str, arg: Any) -> Any:
                if event != "call":
                    return None
                code = frame.f_code
                cnt = code_visits.get(code, 0)
                if cnt >= 6:
                    return None
                if self._rel_if_tracked(code.co_filename) is None:
                    code_visits[code] = 999
                    return None
                code_visits[code] = cnt + 1
                return _local_trace

            sys.settrace(_global_trace)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        mon = getattr(sys, "monitoring", None)
        if self._backend == "sys.monitoring" and self._tool_id is not None and mon is not None:
            try:
                mon.set_events(self._tool_id, 0)
                mon.register_callback(self._tool_id, mon.events.LINE, None)
                mon.free_tool_id(self._tool_id)
            except Exception:
                pass
            self._tool_id = None
        elif self._backend == "sys.settrace_filtered":
            sys.settrace(self._prev_trace)

    @property
    def backend(self) -> str:
        return self._backend


# ---------------------------------------------------------------------------
# 3. PYTHON / PYTEST / UNITTEST TEST EXECUTION & COW ZYGOTE FORK SCREENER
# ---------------------------------------------------------------------------


def _has_pytest() -> bool:
    return importlib.util.find_spec("pytest") is not None


def _pythonpath_for_repo(repo_dir: pathlib.Path) -> str:
    src_dir = repo_dir / "src"
    parts = [str(src_dir), str(repo_dir)] if src_dir.is_dir() else [str(repo_dir)]
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


def enclosing_test_files(repo_dir: pathlib.Path, targets: Sequence[str]) -> list[str]:
    """Extract deduplicated enclosing test file paths from pytest node IDs."""
    files: list[str] = []
    for raw in targets:
        file_part = str(raw).split("::", 1)[0].strip()
        if not file_part:
            continue
        cand = (repo_dir / file_part).resolve()
        if cand.is_file():
            rel = cand.relative_to(repo_dir.resolve()).as_posix()
            if rel not in files:
                files.append(rel)
        elif cand.is_dir():
            for tf in sorted(cand.rglob("test_*.py"))[:8]:
                rel = tf.relative_to(repo_dir.resolve()).as_posix()
                if rel not in files:
                    files.append(rel)
    return files


def run_test_targets_subprocess(
    repo_dir: pathlib.Path,
    targets: Sequence[str],
    *,
    timeout_s: float = 15.0,
    verbose: bool = True,
) -> dict[str, Any]:
    """Run pytest (or stdlib unittest fallback) in an isolated subprocess and parse counts/nodes."""
    env = {
        **os.environ,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONPATH": _pythonpath_for_repo(repo_dir),
    }
    t0 = time.perf_counter()
    if _has_pytest():
        flags = ["-v", "--tb=short", "-p", "no:cacheprovider", "-o", "addopts="] if verbose else ["-q", "--tb=short", "-p", "no:cacheprovider", "-o", "addopts="]
        cmd = [sys.executable, "-m", "pytest", *flags, *targets]
        try:
            proc = subprocess.run(cmd, cwd=str(repo_dir), env=env, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired as exc:
            out = ((exc.stdout or "") if isinstance(exc.stdout, str) else "") + "\n" + ((exc.stderr or "") if isinstance(exc.stderr, str) else "")
            return {
                "status": "TIMEOUT",
                "returncode": 124,
                "passed": 0,
                "failed": 1,
                "errors": 0,
                "failing_nodes": [],
                "passing_nodes": [],
                "output": out,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            }
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if proc.returncode == 4 and "conftest" in out and ("ModuleNotFoundError" in out or "ImportError" in out):
            cmd2 = [sys.executable, "-m", "pytest", *flags, "--noconftest", *targets]
            try:
                proc = subprocess.run(cmd2, cwd=str(repo_dir), env=env, capture_output=True, text=True, timeout=timeout_s)
                out = (proc.stdout or "") + "\n" + (proc.stderr or "")
            except subprocess.TimeoutExpired:
                return {
                    "status": "TIMEOUT",
                    "returncode": 124,
                    "passed": 0,
                    "failed": 1,
                    "errors": 0,
                    "failing_nodes": [],
                    "passing_nodes": [],
                    "output": out,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                }
        failing_nodes: list[str] = []
        passing_nodes: list[str] = []
        for m in re.finditer(r"^(\S+::[^\n]+?)\s+(FAILED|PASSED|ERROR)\b", out, flags=re.M):
            nid, st = m.group(1).strip(), m.group(2)
            if st in ("FAILED", "ERROR"):
                if nid not in failing_nodes:
                    failing_nodes.append(nid)
            elif st == "PASSED":
                if nid not in passing_nodes:
                    passing_nodes.append(nid)
        m_pass = re.search(r"(\d+)\s+passed", out)
        m_fail = re.search(r"(\d+)\s+failed", out)
        m_err = re.search(r"(\d+)\s+errors?\b", out)
        passed = int(m_pass.group(1)) if m_pass else len(passing_nodes)
        failed = int(m_fail.group(1)) if m_fail else len(failing_nodes)
        errors = int(m_err.group(1)) if m_err else 0
        return {
            "status": "OK" if proc.returncode == 0 else "FAILED",
            "returncode": proc.returncode,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "failing_nodes": failing_nodes,
            "passing_nodes": passing_nodes,
            "output": out,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    # Stdlib `unittest` fallback when `pytest` is absent (e.g. bare `/usr/bin/python3`)
    ut_files = enclosing_test_files(repo_dir, targets)
    cmd = [sys.executable, "-m", "unittest", "-v", *(ut_files if ut_files else ["discover"])]
    try:
        proc = subprocess.run(cmd, cwd=str(repo_dir), env=env, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "returncode": 124,
            "passed": 0,
            "failed": 1,
            "errors": 0,
            "failing_nodes": [],
            "passing_nodes": [],
            "output": "",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    m_ran = re.search(r"Ran\s+(\d+)\s+tests?", out)
    total_ran = int(m_ran.group(1)) if m_ran else 0
    m_fail = re.search(r"failures=(\d+)", out)
    m_err = re.search(r"errors=(\d+)", out)
    failed = int(m_fail.group(1)) if m_fail else (1 if proc.returncode != 0 and total_ran == 0 else 0)
    errors = int(m_err.group(1)) if m_err else 0
    passed = max(0, total_ran - failed - errors)
    failing_nodes = []
    for m_uf in re.finditer(r"^(?:FAIL|ERROR):\s+(\S+)\s+\(([^)]+)\)", out, flags=re.M):
        failing_nodes.append(f"{m_uf.group(2)}::{m_uf.group(1)}")
    return {
        "status": "OK" if proc.returncode == 0 else "FAILED",
        "returncode": proc.returncode,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "failing_nodes": failing_nodes,
        "passing_nodes": [],
        "output": out,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


def _hardlink_or_copy(src: str, dst: str) -> None:
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def create_hardlinked_overlay(repo_dir: pathlib.Path, tmp_parent: pathlib.Path, tag: str) -> pathlib.Path:
    """Create a sub-millisecond hardlinked mirror of `repo_dir` (excluding `.git`/`__pycache__`)."""
    dest = tmp_parent / tag
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache", ".tox", ".venv")
    shutil.copytree(repo_dir, dest, copy_function=_hardlink_or_copy, ignore=ignore)
    return dest


def write_unlinked_patch(overlay_dir: pathlib.Path, patched_files: Mapping[str, str]) -> None:
    """Unlink hardlinked inodes BEFORE writing candidate contents so `repo_dir` is never mutated."""
    for rel_path, content in patched_files.items():
        target = overlay_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            target.unlink()
        target.write_text(content, encoding="utf-8")


def build_rel_to_module_map(repo_dir: pathlib.Path) -> dict[str, tuple[str, str, bool]]:
    """Map `rel_path` -> `(dotted_module_name, abs_file_path, is_package)` for zero-copy in-RAM module overrides."""
    repo_abs = repo_dir.resolve()
    has_src = (repo_abs / "src").is_dir()
    out: dict[str, tuple[str, str, bool]] = {}
    for py in repo_abs.rglob("*.py"):
        if any(part in (".git", "__pycache__", ".tox", ".venv", "build", "dist") for part in py.parts):
            continue
        rel = py.relative_to(repo_abs).as_posix()
        name = py.name
        if rel.startswith("tests/") or "/tests/" in rel or name.startswith("test_") or name.endswith("_test.py") or name == "setup.py":
            continue
        mod_rel = rel[4:] if (has_src and rel.startswith("src/")) else rel
        parts = list(pathlib.PurePosixPath(mod_rel).with_suffix("").parts)
        is_pkg = bool(parts and parts[-1] == "__init__")
        if is_pkg:
            parts = parts[:-1]
        if not parts or not all(p.isidentifier() for p in parts):
            continue
        out[rel] = (".".join(parts), str(py.resolve()), is_pkg)
    return out


class _InMemoryModuleOverrideLoader(importlib.abc.InspectLoader):
    """Compiles and executes patched module source directly from RAM without touching disk."""

    def __init__(
        self,
        fullname: str,
        origin_path: str,
        source_text: str,
        is_pkg: bool,
        injected_globals: Mapping[str, Any] | None = None,
    ) -> None:
        self.fullname = fullname
        self.origin_path = origin_path
        self.source_text = source_text
        self.is_pkg = is_pkg
        self.injected_globals = dict(injected_globals or {})

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:
        return None

    def get_source(self, fullname: str) -> str:
        return self.source_text

    def get_code(self, fullname: str) -> Any:
        return compile(self.source_text, self.origin_path, "exec", dont_inherit=True)

    def is_package(self, fullname: str) -> bool:
        return self.is_pkg

    def exec_module(self, module: Any) -> None:
        module.__file__ = self.origin_path
        if self.is_pkg:
            pkg_dir = str(pathlib.Path(self.origin_path).parent)
            module.__path__ = [pkg_dir]
        for gk, gv in self.injected_globals.items():
            module.__dict__[gk] = gv
        code = self.get_code(self.fullname)
        exec(code, module.__dict__)  # noqa: S102 -- confined CoW child executing repo module


class _InMemoryModuleOverrideFinder(importlib.abc.MetaPathFinder):
    """Zero-copy `sys.meta_path` finder serving candidate module patches from memory in CoW children."""

    def __init__(
        self,
        overrides: Mapping[str, tuple[str, str, bool]],
        injected_globals: Mapping[str, Any] | None = None,
    ) -> None:
        # `overrides`: `dotted_mod_name -> (abs_origin_path, patched_source_str, is_pkg)`
        self._overrides = dict(overrides)
        self._injected = dict(injected_globals or {})

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: Any = None,
    ) -> importlib.machinery.ModuleSpec | None:
        entry = self._overrides.get(fullname)
        if entry is None:
            return None
        origin_path, src_txt, is_pkg = entry
        loader = _InMemoryModuleOverrideLoader(fullname, origin_path, src_txt, is_pkg, self._injected)
        spec = importlib.machinery.ModuleSpec(fullname, loader, origin=origin_path, is_package=is_pkg)
        if is_pkg:
            spec.submodule_search_locations = [str(pathlib.Path(origin_path).parent)]
        return spec


def _evict_repo_and_test_modules(pkg_roots: Sequence[str], extra_dotted: Sequence[str] = ()) -> None:
    """Cleanly evict target repo and test modules in a forked child via `sys.modules.pop`."""
    roots = set(pkg_roots) | {d.split(".", 1)[0] for d in extra_dotted if d}
    for mod_key in list(sys.modules):
        if mod_key in ("conftest",) or mod_key.startswith(("tests", "test_")) or mod_key.endswith("_test"):
            sys.modules.pop(mod_key, None)
            continue
        for pkg in roots:
            if mod_key == pkg or mod_key.startswith(pkg + "."):
                sys.modules.pop(mod_key, None)
                break


def _fork_pipe_write_all(w_fd: int, payload: bytes) -> None:
    """Write an arbitrarily large byte payload across an OS pipe without partial-write truncation."""
    view = memoryview(payload)
    sent = 0
    total = len(payload)
    while sent < total:
        n = os.write(w_fd, view[sent:])
        if n <= 0:
            break
        sent += n


def _fork_wait_and_drain(pid: int, r_fd: int, timeout_s: float) -> tuple[bytes, bool]:
    """Simultaneously drain `r_fd` and reap `pid` so >64KB pipe payloads never deadlock."""
    chunks: list[bytes] = []
    eof = False
    reaped = False
    timed_out = False
    deadline = time.perf_counter() + max(0.05, timeout_s)
    try:
        while not (reaped and eof):
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                timed_out = True
                break
            if not eof:
                ready, _, _ = select.select([r_fd], [], [], min(0.005, max(0.0005, remaining)))
                if ready:
                    buf = os.read(r_fd, 65536)
                    if buf:
                        chunks.append(buf)
                    else:
                        eof = True
            else:
                time.sleep(0.001)
            if not reaped:
                try:
                    done_pid, _ = os.waitpid(pid, os.WNOHANG)
                    if done_pid == pid:
                        reaped = True
                except ChildProcessError:
                    reaped = True
        if timed_out and not reaped:
            try:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
            except OSError:
                pass
        if not timed_out and not eof:
            while True:
                buf = os.read(r_fd, 65536)
                if not buf:
                    break
                chunks.append(buf)
    finally:
        try:
            os.close(r_fd)
        except OSError:
            pass
    return b"".join(chunks), timed_out


def run_test_targets_fast(
    repo_dir: pathlib.Path,
    targets: Sequence[str],
    *,
    timeout_s: float = 15.0,
    verbose: bool = True,
    module_overrides: Mapping[str, tuple[str, str, bool]] | None = None,
    collect_line_hits: bool = False,
    maxfail: int = 0,
) -> dict[str, Any]:
    """Zero-cold-start CoW-forked `pytest` runner (~50-110 ms vs ~800 ms subprocess).

    Pre-imports `pytest` in the parent process and forks a Copy-on-Write worker
    collecting structured node verdicts via a lightweight in-RAM plugin, optionally
    mounting `module_overrides` via `_InMemoryModuleOverrideFinder` with zero disk I/O.
    Automatically falls back to `run_test_targets_subprocess` when multi-threaded or
    when `pytest` is absent.
    """
    if not hasattr(os, "fork") or threading.active_count() > 1 or not _has_pytest():
        if module_overrides:
            # Materialize into a temporary overlay only on non-fork / threaded fallback
            with tempfile.TemporaryDirectory(prefix="brain_fast_fb_") as tmp_s:
                ov = create_hardlinked_overlay(repo_dir, pathlib.Path(tmp_s), "work")
                repo_abs = repo_dir.resolve()
                rel_patches = {
                    pathlib.Path(orig_p).resolve().relative_to(repo_abs).as_posix(): src_s
                    for _mn, (orig_p, src_s, _isp) in module_overrides.items()
                }
                write_unlinked_patch(ov, rel_patches)
                return run_test_targets_subprocess(ov, targets, timeout_s=timeout_s, verbose=verbose)
        return run_test_targets_subprocess(repo_dir, targets, timeout_s=timeout_s, verbose=verbose)

    import pytest as _preloaded_pytest  # noqa: F401

    repo_abs = repo_dir.resolve()
    pkg_roots = WarmCoWForkScreener._discover_top_packages(repo_abs)
    t0 = time.perf_counter()
    r_fd, w_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r_fd)
        payload = b"{}"
        try:
            random.seed((os.getpid() ^ time.time_ns()) & 0xFFFFFFFF)
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
            os.close(devnull)
            os.chdir(str(repo_abs))
            _evict_repo_and_test_modules(pkg_roots, list(module_overrides or ()))
            if module_overrides:
                sys.meta_path.insert(0, _InMemoryModuleOverrideFinder(module_overrides))
            if (repo_abs / "src").is_dir():
                if str(repo_abs) not in sys.path:
                    sys.path.insert(0, str(repo_abs))
                if str(repo_abs / "src") not in sys.path:
                    sys.path.insert(0, str(repo_abs / "src"))
            elif str(repo_abs) not in sys.path:
                sys.path.insert(0, str(repo_abs))
            importlib.invalidate_caches()
            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            import pytest

            failing_nodes: list[str] = []
            passing_nodes: list[str] = []
            crash_chunks: list[str] = []
            counts = {"passed": 0, "failed": 0, "errors": 0}
            failing_item_objs: list[Any] = []
            line_hits: list[tuple[str, int]] = []
            rejected_assertions: list[dict[str, str]] = []
            producer_provenance: list[dict[str, Any]] = []
            live_rejected_objs: list[Any] = []

            class _FastCollector:
                def pytest_collection_modifyitems(self, session: Any, config: Any, items: list[Any]) -> None:
                    # Lossless diversity-first bottom-up permutation ONLY when `maxfail > 0` on large suites:
                    # visits first+last case of each distinct `originalname` from bottom of file to top (~40ms)
                    # before sweeping remaining parametrized permutations, cutting 5,400-item `init_run` 4.6s -> ~0.13s!
                    if maxfail > 0 and len(items) > 160:
                        seen_first: set[str] = set()
                        seen_second: set[str] = set()
                        front: list[Any] = []
                        rest: list[Any] = []
                        for it in reversed(items):
                            key = f"{getattr(it, 'fspath', '')}::{getattr(it, 'originalname', None) or it.name}"
                            if key not in seen_first:
                                seen_first.add(key)
                                front.append(it)
                            elif key not in seen_second:
                                seen_second.add(key)
                                front.append(it)
                            else:
                                rest.append(it)
                        items[:] = front + rest

                def pytest_assertrepr_compare(self, config: Any, op: str, left: Any, right: Any) -> None:
                    if len(rejected_assertions) < 6:
                        try:
                            rejected_assertions.append(
                                {
                                    "op": str(op),
                                    "left_repr": repr(left)[:240],
                                    "right_repr": repr(right)[:240],
                                    "left_type": type(left).__name__,
                                    "right_type": type(right).__name__,
                                }
                            )
                            if left is not None and not isinstance(left, bool):
                                live_rejected_objs.append(left)
                        except Exception:
                            pass
                    return None

                def pytest_runtest_makereport(self, item: Any, call: Any) -> None:
                    if getattr(call, "when", "") == "call" and getattr(call, "excinfo", None) is not None:
                        if len(failing_item_objs) < 4:
                            failing_item_objs.append(item)

                def pytest_runtest_logreport(self, report: Any) -> None:
                    when = getattr(report, "when", "")
                    nid = str(getattr(report, "nodeid", "")).strip()
                    if when == "call":
                        if report.passed:
                            counts["passed"] += 1
                            if verbose and len(passing_nodes) < 400:
                                passing_nodes.append(nid)
                        elif report.failed:
                            counts["failed"] += 1
                            if nid and nid not in failing_nodes:
                                failing_nodes.append(nid)
                            if len(crash_chunks) < 12:
                                crash_chunks.append(f"{nid} FAILED\n{getattr(report, 'longreprtext', '')[-1800:]}")
                    elif report.failed and when in ("setup", "teardown"):
                        counts["errors"] += 1
                        if nid and nid not in failing_nodes:
                            failing_nodes.append(nid)
                        if len(crash_chunks) < 12:
                            crash_chunks.append(f"{nid} ERROR\n{getattr(report, 'longreprtext', '')[-1200:]}")

                def pytest_collectreport(self, report: Any) -> None:
                    if report.failed and len(crash_chunks) < 8:
                        counts["errors"] += 1
                        crash_chunks.append(str(getattr(report, "longreprtext", ""))[-1500:])

                def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> None:
                    # Capture exact failing-only dynamic line hits + rejected-value return producer (`<1 ms`, 0 extra forks!)
                    if collect_line_hits and failing_item_objs and not line_hits:
                        try:
                            from _pytest.runner import runtestprotocol

                            repo_prefix = str(repo_abs) + os.sep
                            want_reprs = {d["left_repr"] for d in rejected_assertions if d.get("left_repr") not in ("True", "False", "None", "")}
                            ret_events: list[dict[str, Any]] = []

                            def _prod_trace(frame: Any, event: str, arg: Any) -> Any:
                                fn_file = frame.f_code.co_filename
                                if not fn_file or not fn_file.startswith(repo_prefix):
                                    return None
                                rel_p = fn_file[len(repo_prefix) :].replace("\\", "/")
                                base_p = rel_p.rsplit("/", 1)[-1]
                                if rel_p.startswith("tests/") or "/tests/" in rel_p or base_p.startswith("test_") or base_p.endswith("_test.py"):
                                    return None
                                if event == "return" and len(ret_events) < 256:
                                    matched = False
                                    for r_obj in live_rejected_objs[:4]:
                                        try:
                                            if arg is r_obj or (type(arg) is type(r_obj) and arg == r_obj):
                                                matched = True
                                                break
                                        except Exception:
                                            pass
                                    if not matched and want_reprs:
                                        try:
                                            if repr(arg)[:240] in want_reprs:
                                                matched = True
                                        except Exception:
                                            pass
                                    if matched:
                                        ret_events.append(
                                            {
                                                "rel_file": rel_p,
                                                "func": frame.f_code.co_name,
                                                "line": int(frame.f_lineno),
                                            }
                                        )
                                return _prod_trace

                            with ZeroOverheadLineMonitor(repo_abs, exclude_tests=True) as mon:
                                prev_t = sys.gettrace()
                                if want_reprs or live_rejected_objs:
                                    sys.settrace(_prod_trace)
                                try:
                                    runtestprotocol(failing_item_objs[0], nextitem=None, log=False)
                                finally:
                                    if want_reprs or live_rejected_objs:
                                        sys.settrace(prev_t)
                            line_hits.extend(sorted(mon.hits)[:800])
                            if ret_events:
                                # Latest matching return in repo is the direct boundary producer (`the_value_that_was_rejected_had_a_producer_v1`)
                                seen_pr: set[tuple[str, str, int]] = set()
                                for ev in reversed(ret_events):
                                    k_pr = (ev["rel_file"], ev["func"], ev["line"])
                                    if k_pr not in seen_pr:
                                        seen_pr.add(k_pr)
                                        producer_provenance.append(ev)
                                        if len(producer_provenance) >= 6:
                                            break
                        except Exception:
                            pass

            argv = ["-q", "--tb=short", "--no-header", "-p", "no:cacheprovider", "-o", "addopts="]
            if maxfail > 0:
                argv.append(f"--maxfail={maxfail}")
            argv.extend(targets)
            rc_raw = pytest.main(argv, plugins=[_FastCollector()])
            if collect_line_hits and failing_nodes and not line_hits:
                with ZeroOverheadLineMonitor(repo_abs, exclude_tests=True) as mon2:
                    pytest.main(["-q", "--tb=no", "--no-header", "-p", "no:cacheprovider", "-o", "addopts=", failing_nodes[0]])
                line_hits = sorted(mon2.hits)[:800]
            rc_int = int(getattr(rc_raw, "value", rc_raw))
            payload = json.dumps(
                {
                    "status": "OK" if rc_int == 0 else "FAILED",
                    "returncode": rc_int,
                    "passed": counts["passed"],
                    "failed": counts["failed"],
                    "errors": counts["errors"],
                    "failing_nodes": failing_nodes,
                    "passing_nodes": passing_nodes,
                    "output": "\n".join(crash_chunks),
                    "line_hits": line_hits,
                    "line_hits_failing_only": True,
                    "rejected_assertions": rejected_assertions,
                    "producer_provenance": producer_provenance,
                }
            ).encode("utf-8")
        except BaseException as exc:
            payload = json.dumps(
                {
                    "status": "FAILED",
                    "returncode": 2,
                    "passed": 0,
                    "failed": 1,
                    "errors": 1,
                    "failing_nodes": [],
                    "passing_nodes": [],
                    "output": f"{type(exc).__name__}: {exc}",
                    "line_hits": [],
                }
            ).encode("utf-8")
        finally:
            try:
                _fork_pipe_write_all(w_fd, payload)
                os.close(w_fd)
            except OSError:
                pass
            os._exit(0)

    os.close(w_fd)
    raw_bytes, timed_out = _fork_wait_and_drain(pid, r_fd, timeout_s)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    if timed_out:
        return {
            "status": "TIMEOUT",
            "returncode": 124,
            "passed": 0,
            "failed": 1,
            "errors": 0,
            "failing_nodes": [],
            "passing_nodes": [],
            "output": "",
            "line_hits": [],
            "elapsed_ms": elapsed_ms,
        }
    try:
        res = json.loads(raw_bytes.decode("utf-8") or "{}")
    except Exception:
        res = {}
    if not res or (res.get("returncode") == 4 and "conftest" in str(res.get("output", "")).lower() and not module_overrides):
        return run_test_targets_subprocess(repo_dir, targets, timeout_s=timeout_s, verbose=verbose)
    res["elapsed_ms"] = elapsed_ms
    return res


@dataclass(frozen=True)
class CandidatePatch:
    patch_id: str
    family: str
    patched_files: dict[str, str]
    description: str = ""
    mdl_delta_bytes: int = 0


class WarmCoWForkScreener:
    """Zero-Copy In-RAM Copy-on-Write (`os.fork()`) parallel candidate screener.

    Eliminates per-candidate `shutil.copytree` directory trees and disk writes:
    when all `patched_files` map to Python modules (`build_rel_to_module_map`),
    each forked child mounts `_InMemoryModuleOverrideFinder` in RAM and runs
    `pytest.main(["-x", ...])` directly against the read-only `repo_dir` (~3-8 ms
    amortized per candidate). Non-module patches fall back to hardlinked overlays.
    """

    def __init__(self, repo_dir: pathlib.Path, fast_targets: Sequence[str], *, per_candidate_timeout_s: float = 3.5) -> None:
        self.repo_dir = repo_dir.resolve()
        self.fast_targets = list(fast_targets)
        self.per_candidate_timeout_s = per_candidate_timeout_s
        self._pkg_roots = self._discover_top_packages(self.repo_dir)
        self._rel_to_mod = build_rel_to_module_map(self.repo_dir)
        self.last_partial_survivors: list[CandidatePatch] = []

    @staticmethod
    def _discover_top_packages(repo_dir: pathlib.Path) -> tuple[str, ...]:
        roots: set[str] = set()
        search_bases = [repo_dir / "src", repo_dir] if (repo_dir / "src").is_dir() else [repo_dir]
        for base in search_bases:
            if not base.is_dir():
                continue
            for entry in base.iterdir():
                if entry.name.startswith((".", "test", "docs", "build", "dist")):
                    continue
                if entry.is_dir() and (entry / "__init__.py").is_file():
                    roots.add(entry.name)
                elif entry.is_file() and entry.suffix == ".py" and entry.stem != "setup":
                    roots.add(entry.stem)
        return tuple(sorted(roots))

    def to_module_overrides(self, patched_files: Mapping[str, str]) -> dict[str, tuple[str, str, bool]] | None:
        """Convert `{rel_path: source}` into `_InMemoryModuleOverrideFinder` map if all files are Python modules."""
        if not patched_files:
            return None
        overrides: dict[str, tuple[str, str, bool]] = {}
        for rel_p, content in patched_files.items():
            norm_rel = rel_p.replace("\\", "/").lstrip("/")
            info = self._rel_to_mod.get(norm_rel)
            if info is None:
                return None
            mod_name, abs_orig, is_pkg = info
            overrides[mod_name] = (abs_orig, content, is_pkg)
        return overrides

    def _screen_bytecode_zygote_hot_swap(
        self,
        hot_items: Sequence[tuple[int, CandidatePatch, dict[str, tuple[str, str, bool]]]],
        target_nodeid: str,
        *,
        budget_s: float,
    ) -> list[int] | None:
        """Evaluate `hot_items` in a single live `pytest_runtestloop` CoW Zygote child (~2.5 ms/cand total).

        Collects `target_nodeid` ONCE, snapshots touched repo modules + cross-module imported symbol
        aliases, swaps compiled `__code__` / class attributes / module constants per candidate, runs
        `runtestprotocol(item, log=False)` (~0.4 ms), and restores module state cleanly in `finally:`.
        Returns surviving candidate indices, or `None` if collection could not bind `target_nodeid`.
        """
        if not hot_items or not target_nodeid:
            return []
        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            payload = b"null"
            try:
                random.seed((os.getpid() ^ time.time_ns()) & 0xFFFFFFFF)
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)
                os.close(devnull)
                os.chdir(str(self.repo_dir))
                touched_mods = sorted({mn for _, _, ov in hot_items for mn in ov})
                _evict_repo_and_test_modules(self._pkg_roots, touched_mods)
                if (self.repo_dir / "src").is_dir():
                    if str(self.repo_dir) not in sys.path:
                        sys.path.insert(0, str(self.repo_dir))
                    if str(self.repo_dir / "src") not in sys.path:
                        sys.path.insert(0, str(self.repo_dir / "src"))
                elif str(self.repo_dir) not in sys.path:
                    sys.path.insert(0, str(self.repo_dir))
                importlib.invalidate_caches()
                os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
                import pytest
                from _pytest.runner import runtestprotocol

                class _CandTimeout(BaseException):
                    pass

                def _on_alarm(_signum: int, _frame: Any) -> None:
                    raise _CandTimeout()

                prev_sig = signal.signal(signal.SIGALRM, _on_alarm)
                per_t = max(0.15, min(0.95, self.per_candidate_timeout_s))
                child_deadline = time.perf_counter() + max(0.5, budget_s)
                passed_indices: list[int] = []
                collected_ok = {"ok": False}
                outer_pkg_roots = tuple(self._pkg_roots)
                skip_descr = (types.MemberDescriptorType, types.GetSetDescriptorType)

                class _HotZygoteLoop:
                    def pytest_runtestloop(self, session: Any) -> bool:
                        live_items = list(session.items or ())
                        if not live_items:
                            return True
                        pkg_prefixes = outer_pkg_roots + ("tests", "test_", "conftest")
                        for mn in touched_mods:
                            importlib.import_module(mn)

                        # Pre-compile all override `PyCodeObject`s ONCE in Zygote parent before `os.fork()` (CoW zero-parse workers!)
                        precompiled_items: list[tuple[int, dict[str, tuple[str, types.CodeType, bool]]]] = []
                        for c_idx_p, _cand_p, ov_map_p in hot_items:
                            comp_map: dict[str, tuple[str, types.CodeType, bool]] = {}
                            ok_comp = True
                            for mn_p, (abs_p, src_p, is_pkg_p) in ov_map_p.items():
                                try:
                                    comp_map[mn_p] = (abs_p, compile(src_p, abs_p, "exec", dont_inherit=True), is_pkg_p)
                                except SyntaxError:
                                    ok_comp = False
                                    break
                            if ok_comp:
                                precompiled_items.append((c_idx_p, comp_map))

                        def _apply_override_in_grandchild(ov_map: Mapping[str, tuple[str, types.CodeType, bool]]) -> None:
                            for mn, (abs_orig, c_code, is_pkg) in ov_map.items():
                                m_obj = importlib.import_module(mn)
                                o_dict = dict(m_obj.__dict__)
                                base_ns = {
                                    "__name__": m_obj.__name__,
                                    "__file__": abs_orig,
                                    "__package__": m_obj.__package__,
                                    "__loader__": getattr(m_obj, "__loader__", None),
                                    "__spec__": getattr(m_obj, "__spec__", None),
                                    "__builtins__": o_dict.get("__builtins__", __builtins__),
                                }
                                if is_pkg and "__path__" in o_dict:
                                    base_ns["__path__"] = o_dict["__path__"]
                                m_obj.__dict__.clear()
                                m_obj.__dict__.update(base_ns)
                                exec(c_code, m_obj.__dict__)  # noqa: S102 -- confined CoW Zygote grandchild
                                for k, old_v in o_dict.items():
                                    nv = m_obj.__dict__.get(k)
                                    if (
                                        isinstance(old_v, types.FunctionType)
                                        and isinstance(nv, types.FunctionType)
                                        and not old_v.__closure__
                                        and not nv.__closure__
                                    ):
                                        old_v.__code__ = nv.__code__
                                        old_v.__defaults__ = nv.__defaults__
                                        old_v.__kwdefaults__ = nv.__kwdefaults__
                                        m_obj.__dict__[k] = old_v
                                    elif isinstance(old_v, type) and isinstance(nv, type):
                                        # Rewrite Python 3 `super()` `__class__` closure cells in `nv` methods -> `old_v`
                                        for mv in nv.__dict__.values():
                                            fns = (
                                                [mv]
                                                if isinstance(mv, types.FunctionType)
                                                else (
                                                    [mv.fget, mv.fset, mv.fdel]
                                                    if isinstance(mv, property)
                                                    else ([mv.__func__] if isinstance(mv, (classmethod, staticmethod)) else [])
                                                )
                                            )
                                            for fn in fns:
                                                if fn is not None and getattr(fn, "__closure__", None):
                                                    for cell in fn.__closure__:
                                                        try:
                                                            if cell.cell_contents is nv:
                                                                cell.cell_contents = old_v
                                                        except ValueError:
                                                            pass
                                        for mk in list(old_v.__dict__.keys()):
                                            if (
                                                mk not in ("__dict__", "__weakref__", "__module__", "__doc__", "__slots__")
                                                and not isinstance(old_v.__dict__[mk], skip_descr)
                                                and mk not in nv.__dict__
                                            ):
                                                try:
                                                    delattr(old_v, mk)
                                                except Exception:
                                                    pass
                                        for mk, mv in nv.__dict__.items():
                                            if mk in ("__dict__", "__weakref__", "__module__", "__slots__") or isinstance(mv, skip_descr):
                                                continue
                                            try:
                                                setattr(old_v, mk, mv)
                                            except Exception:
                                                pass
                                        m_obj.__dict__[k] = old_v
                                    if hasattr(old_v, "cache_clear"):
                                        try:
                                            old_v.cache_clear()
                                        except Exception:
                                            pass
                                for om_name, om in list(sys.modules.items()):
                                    if om is None or om is m_obj or not hasattr(om, "__dict__"):
                                        continue
                                    if not (om_name in pkg_prefixes or om_name.startswith(pkg_prefixes)):
                                        continue
                                    om_d = om.__dict__
                                    for ak, av in list(om_d.items()):
                                        if (
                                            not ak.startswith("__")
                                            and ak in o_dict
                                            and av is o_dict[ak]
                                            and not isinstance(av, types.ModuleType)
                                            and ak in m_obj.__dict__
                                        ):
                                            om_d[ak] = m_obj.__dict__[ak]

                        max_workers = max(2, min(8, os.cpu_count() or 4))
                        active_gpids: dict[int, tuple[int, float]] = {}
                        cursor = 0
                        while cursor < len(precompiled_items) or active_gpids:
                            while (
                                cursor < len(precompiled_items)
                                and len(active_gpids) < max_workers
                                and time.perf_counter() < child_deadline
                            ):
                                c_idx, ov_map = precompiled_items[cursor]
                                cursor += 1
                                gpid = os.fork()
                                if gpid == 0:
                                    ok_g = False
                                    try:
                                        signal.setitimer(signal.ITIMER_REAL, per_t)
                                        _apply_override_in_grandchild(ov_map)
                                        ok_g = True
                                        for it in live_items:
                                            reps = runtestprotocol(it, nextitem=None, log=False)
                                            if not reps or any(rp.failed for rp in reps):
                                                ok_g = False
                                                break
                                    except BaseException:
                                        ok_g = False
                                    finally:
                                        signal.setitimer(signal.ITIMER_REAL, 0.0)
                                    os._exit(0 if ok_g else 1)
                                active_gpids[gpid] = (c_idx, time.perf_counter())

                            if not active_gpids:
                                break
                            reaped_any = False
                            for gpid_chk, (c_idx_chk, t_start) in list(active_gpids.items()):
                                try:
                                    wpid, wst = os.waitpid(gpid_chk, os.WNOHANG)
                                except ChildProcessError:
                                    active_gpids.pop(gpid_chk, None)
                                    continue
                                if wpid == gpid_chk:
                                    active_gpids.pop(gpid_chk, None)
                                    reaped_any = True
                                    if os.WIFEXITED(wst) and os.WEXITSTATUS(wst) == 0:
                                        passed_indices.append(c_idx_chk)
                                elif (time.perf_counter() - t_start) > (per_t + 0.25):
                                    try:
                                        os.kill(gpid_chk, 9)
                                        os.waitpid(gpid_chk, 0)
                                    except OSError:
                                        pass
                                    active_gpids.pop(gpid_chk, None)
                                    reaped_any = True
                            if not reaped_any:
                                time.sleep(0.0002)

                        passed_indices.sort()
                        collected_ok["ok"] = True
                        return True

                pytest.main(
                    ["-q", "--tb=no", "--no-header", "-p", "no:cacheprovider", "-o", "addopts=", target_nodeid],
                    plugins=[_HotZygoteLoop()],
                )
                signal.signal(signal.SIGALRM, prev_sig)
                if collected_ok["ok"]:
                    payload = json.dumps(passed_indices).encode("utf-8")
            except BaseException:
                payload = b"null"
            finally:
                try:
                    _fork_pipe_write_all(w_fd, payload)
                    os.close(w_fd)
                except OSError:
                    pass
                os._exit(0)

        os.close(w_fd)
        raw_b, timed_out = _fork_wait_and_drain(pid, r_fd, max(1.0, budget_s + 1.0))
        if timed_out:
            return None
        try:
            parsed = json.loads(raw_b.decode("utf-8") or "null")
            return [int(x) for x in parsed] if isinstance(parsed, list) else None
        except Exception:
            return None

    def screen_batch(
        self,
        candidates: Sequence[CandidatePatch],
        *,
        max_parallel: int = 0,
        budget_s: float = 12.0,
        _targets_override: Sequence[str] | None = None,
        _skip_bytecode_zygote: bool = False,
    ) -> list[CandidatePatch]:
        """Return the subset of `candidates` that pass `self.fast_targets`."""
        active_targets = list(_targets_override) if _targets_override is not None else self.fast_targets
        if _targets_override is None:
            self.last_partial_survivors = []
        if not candidates or not active_targets:
            return []
        t0 = time.perf_counter()
        use_pytest = _has_pytest()
        if use_pytest:
            import pytest as _preloaded_pytest  # noqa: F401
            try:
                import _pytest.assertion  # noqa: F401
                import _pytest.config  # noqa: F401
                import _pytest.main  # noqa: F401
                import _pytest.python  # noqa: F401
                import _pytest.runner  # noqa: F401
            except Exception:
                pass

        if not hasattr(os, "fork") or threading.active_count() > 1:
            return self._screen_subprocess_fallback(candidates, budget_s=budget_s)

        # Ultra-Fast Path (Phase A `<1 ms` Bytecode Hot-Swap Zygote + Clean CoW Confirmation):
        # Evaluates all Python-module candidates in ONE collected `pytest_runtestloop` (~2.5 ms/cand vs ~110 ms/fork),
        # then confirms every survivor in a hermetic clean `_InMemoryModuleOverrideFinder` CoW fork!
        if not _skip_bytecode_zygote and _targets_override is None and use_pytest and len(candidates) >= 3:
            hot_items: list[tuple[int, CandidatePatch, dict[str, tuple[str, str, bool]]]] = []
            cold_cands: list[CandidatePatch] = []
            for idx_c, cand_c in enumerate(candidates):
                ov_c = self.to_module_overrides(cand_c.patched_files)
                if ov_c is not None and not cand_c.family.startswith(("M9b_", "M10b_")):
                    hot_items.append((idx_c, cand_c, ov_c))
                else:
                    cold_cands.append(cand_c)
            if hot_items:
                hot_surv_idxs = self._screen_bytecode_zygote_hot_swap(
                    hot_items,
                    active_targets[0],
                    budget_s=min(budget_s * 0.65, max(1.2, len(hot_items) * 0.04)),
                )
                if hot_surv_idxs is not None:
                    idx_set = set(hot_surv_idxs)
                    hot_stage1 = [cand_c for idx_c, cand_c, _ in hot_items if idx_c in idx_set]
                    self.last_partial_survivors = list(hot_stage1)
                    to_confirm = hot_stage1 + cold_cands
                    if not to_confirm:
                        return []
                    rem_c = max(1.0, budget_s - (time.perf_counter() - t0))
                    return self.screen_batch(
                        to_confirm,
                        max_parallel=max_parallel,
                        budget_s=rem_c,
                        _targets_override=active_targets,
                        _skip_bytecode_zygote=True,
                    )

        # Two-stage funnel: when multiple failing nodes exist, screen against the first failing node first!
        if _targets_override is None and use_pytest and len(active_targets) > 1 and len(candidates) > 4:
            first_pass = self.screen_batch(
                candidates,
                max_parallel=max_parallel,
                budget_s=budget_s * 0.72,
                _targets_override=[active_targets[0]],
                _skip_bytecode_zygote=True,
            )
            self.last_partial_survivors = list(first_pass)
            if not first_pass:
                return []
            rem_b = max(1.0, budget_s - (time.perf_counter() - t0))
            return self.screen_batch(
                first_pass,
                max_parallel=max_parallel,
                budget_s=rem_b,
                _targets_override=active_targets[1:],
                _skip_bytecode_zygote=True,
            )

        parallel = max_parallel if max_parallel > 0 else min(8, max(4, (os.cpu_count() or 2) * 2))
        survivors: list[CandidatePatch] = []
        tmp_ctx: tempfile.TemporaryDirectory[str] | None = None
        try:
            idx = 0
            n = len(candidates)
            while idx < n and (time.perf_counter() - t0) < budget_s:
                batch = candidates[idx : idx + parallel]
                idx += len(batch)
                active_pids: dict[int, tuple[CandidatePatch, float]] = {}
                for b_i, cand in enumerate(batch):
                    mod_ov = self.to_module_overrides(cand.patched_files) if use_pytest else None
                    overlay: pathlib.Path | None = None
                    if mod_ov is None:
                        if tmp_ctx is None:
                            tmp_ctx = tempfile.TemporaryDirectory(prefix="brain_cow_zygote_")
                        overlay = create_hardlinked_overlay(self.repo_dir, pathlib.Path(tmp_ctx.name), f"cand_{idx}_{b_i}")
                        write_unlinked_patch(overlay, cand.patched_files)
                    pid = os.fork()
                    if pid == 0:
                        exit_code = 1
                        try:
                            random.seed((os.getpid() ^ time.time_ns()) & 0xFFFFFFFF)
                            devnull = os.open(os.devnull, os.O_WRONLY)
                            os.dup2(devnull, 1)
                            os.dup2(devnull, 2)
                            os.close(devnull)
                            work_dir = self.repo_dir if mod_ov is not None else overlay  # type: ignore[assignment]
                            os.chdir(str(work_dir))
                            _evict_repo_and_test_modules(self._pkg_roots, list(mod_ov or ()))
                            if mod_ov is not None:
                                sys.meta_path.insert(0, _InMemoryModuleOverrideFinder(mod_ov))
                            else:
                                orig_s = str(self.repo_dir)
                                sys.path[:] = [p for p in sys.path if not p.startswith(orig_s)]
                            if (work_dir / "src").is_dir():
                                if str(work_dir) not in sys.path:
                                    sys.path.insert(0, str(work_dir))
                                if str(work_dir / "src") not in sys.path:
                                    sys.path.insert(0, str(work_dir / "src"))
                            elif str(work_dir) not in sys.path:
                                sys.path.insert(0, str(work_dir))
                            importlib.invalidate_caches()
                            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
                            if use_pytest:
                                import pytest

                                rc = pytest.main(
                                    ["-q", "--tb=no", "-x", "-p", "no:cacheprovider", "-o", "addopts=", *active_targets]
                                )
                                exit_code = 0 if int(getattr(rc, "value", rc)) == 0 else 1
                            else:
                                import unittest

                                ut_files = enclosing_test_files(work_dir, active_targets)
                                suite = unittest.TestSuite()
                                loader = unittest.TestLoader()
                                for uf in (ut_files or []):
                                    suite.addTests(loader.discover(str((work_dir / uf).parent), pattern=pathlib.Path(uf).name))
                                res = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
                                exit_code = 0 if res.wasSuccessful() and res.testsRun > 0 else 1
                        except BaseException:
                            exit_code = 2
                        finally:
                            os._exit(exit_code)
                    else:
                        active_pids[pid] = (cand, time.perf_counter())

                # Reap only owned child PIDs with 1 ms polling and bounded per-candidate deadline
                while active_pids:
                    reaped_any = False
                    now = time.perf_counter()
                    for r_pid, (cand_r, started) in list(active_pids.items()):
                        try:
                            done_pid, status = os.waitpid(r_pid, os.WNOHANG)
                        except ChildProcessError:
                            active_pids.pop(r_pid, None)
                            continue
                        if done_pid == r_pid:
                            active_pids.pop(r_pid, None)
                            reaped_any = True
                            if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0:
                                survivors.append(cand_r)
                        elif (now - started) > self.per_candidate_timeout_s:
                            try:
                                os.kill(r_pid, 9)
                                os.waitpid(r_pid, 0)
                            except OSError:
                                pass
                            active_pids.pop(r_pid, None)
                            reaped_any = True
                    if active_pids and not reaped_any:
                        time.sleep(0.001)
        finally:
            if tmp_ctx is not None:
                tmp_ctx.cleanup()
        return survivors

    def _screen_subprocess_fallback(self, candidates: Sequence[CandidatePatch], *, budget_s: float) -> list[CandidatePatch]:
        survivors: list[CandidatePatch] = []
        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="brain_cow_sub_") as tmp_s:
            tmp_root = pathlib.Path(tmp_s)
            for idx, cand in enumerate(candidates):
                if (time.perf_counter() - t0) >= budget_s:
                    break
                overlay = create_hardlinked_overlay(self.repo_dir, tmp_root, f"sub_{idx}")
                write_unlinked_patch(overlay, cand.patched_files)
                r = run_test_targets_subprocess(overlay, self.fast_targets, timeout_s=self.per_candidate_timeout_s, verbose=False)
                if r["returncode"] == 0:
                    survivors.append(cand)
        return survivors


# ---------------------------------------------------------------------------
# 4. MULTI-SIGNAL CAUSAL LOCALIZER & PROACTIVE `CodePlan` OBLIGATION ZIPPER
# ---------------------------------------------------------------------------


@dataclass
class CausalFaultSpectrum:
    failing_nodes: list[str]
    enclosing_files: list[str]
    ranked_files: list[str]
    ranked_functions: list[tuple[str, str, int, int]]  # (rel_file, func_or_class_name, start_line, end_line)
    suspect_lines: dict[str, list[int]]
    failure_kind: str  # "DID_NOT_RAISE" | "EXCEPTION" | "ASSERTION" | "OTHER"
    raw_output: str
    passing_nodes: list[str] = field(default_factory=list)
    producer_provenance: list[dict[str, Any]] = field(default_factory=list)
    rejected_assertions: list[dict[str, str]] = field(default_factory=list)


class MultiSignalCausalLocalizer:
    """Combines bottom-up traceback walking, AST `pytest.raises`/assertion callee
    import resolution, and `ZeroOverheadLineMonitor` dynamic line spectra.
    """

    @staticmethod
    def _is_test_rel(rel: str) -> bool:
        name = rel.rsplit("/", 1)[-1]
        return rel.startswith("tests/") or "/tests/" in rel or name.startswith("test_") or name.endswith("_test.py")

    @classmethod
    def localize(
        cls,
        repo_dir: pathlib.Path,
        targets: Sequence[str],
        init_run: Mapping[str, Any],
    ) -> CausalFaultSpectrum:
        repo_abs = repo_dir.resolve()
        out = str(init_run.get("output") or "")
        failing_nodes = list(init_run.get("failing_nodes") or [])
        enc_files = enclosing_test_files(repo_abs, failing_nodes or targets)

        failure_kind = "OTHER"
        if "DID NOT RAISE" in out:
            failure_kind = "DID_NOT_RAISE"
        elif "AssertionError" in out or "\nE       assert " in out:
            failure_kind = "ASSERTION"
        elif any(tok in out for tok in ("Error:", "Exception:", "Traceback")):
            failure_kind = "EXCEPTION"

        file_scores: dict[str, float] = {}
        suspect_lines: dict[str, list[int]] = {}
        test_fail_sites: list[tuple[str, int]] = []

        # 1. Extract all `path.py:lineno:` (pytest) and `File "path.py", line N` (Python/unittest) hits
        raw_hits: list[tuple[str, int]] = []
        for pat in (
            r"([A-Za-z0-9_./\\-]+\.py):(\d+):",
            r'File "([^"]+\.py)", line (\d+)',
        ):
            for m in re.finditer(pat, out):
                cand_str = m.group(1).replace("\\", "/")
                lineno = int(m.group(2))
                p_cand = pathlib.Path(cand_str).resolve() if pathlib.Path(cand_str).is_absolute() else (repo_abs / cand_str).resolve()
                if p_cand.is_file() and str(p_cand).startswith(str(repo_abs)):
                    rel = p_cand.relative_to(repo_abs).as_posix()
                    raw_hits.append((rel, lineno))

        for pos_idx, (rel, lineno) in enumerate(reversed(raw_hits)):
            if cls._is_test_rel(rel):
                if (rel, lineno) not in test_fail_sites:
                    test_fail_sites.append((rel, lineno))
                continue
            weight = 10.0 / (1.0 + 0.25 * pos_idx)
            file_scores[rel] = file_scores.get(rel, 0.0) + weight
            lines_list = suspect_lines.setdefault(rel, [])
            if lineno not in lines_list:
                lines_list.append(lineno)

        # 2. AST Callee & Import Resolution from failing test functions (`DID NOT RAISE` & `assert f(...)`)
        module_map = cls._build_repo_module_map(repo_abs)
        symbol_targets: list[tuple[str, str]] = []  # (rel_file, symbol_name)
        for test_rel, test_line in test_fail_sites[:6]:
            resolved = cls._resolve_test_callees(repo_abs / test_rel, test_line, module_map)
            for rel_src, sym_name in resolved:
                file_scores[rel_src] = file_scores.get(rel_src, 0.0) + 14.0
                if (rel_src, sym_name) not in symbol_targets:
                    symbol_targets.append((rel_src, sym_name))

        # 3. Naming affinity + `assertion_localisation_v1` symbol/literal index fusion
        for tf in enc_files:
            stem = pathlib.Path(tf).stem
            core_stem = stem[5:] if stem.startswith("test_") else (stem[:-5] if stem.endswith("_test") else stem)
            for mod_name, rel_src in module_map.items():
                leaf = mod_name.rsplit(".", 1)[-1]
                if leaf == core_stem or leaf == f"_{core_stem}":
                    file_scores[rel_src] = file_scores.get(rel_src, 0.0) + 6.0

        if test_fail_sites and failing_nodes:
            try:
                from canonical.tools import assertion_localisation_v1 as aloc

                t_rel0, t_ln0 = test_fail_sites[0]
                aloc_res = aloc.localise(repo_abs, failing_nodes[0], t_rel0, t_ln0, out)
                for rank_i, cand_p in enumerate((aloc_res.get("ranked") or aloc_res.get("symbol_hits") or ())[:5]):
                    if isinstance(cand_p, str) and (repo_abs / cand_p).is_file() and not cls._is_test_rel(cand_p):
                        file_scores[cand_p] = file_scores.get(cand_p, 0.0) + max(2.0, 9.0 - 1.5 * rank_i)
            except Exception:
                pass

        # 3b. Incremental Delta-Graph fusion (`incremental_semantic_graph_v1` SQLite WAL SHA-256 index)
        #     Used on medium/large repos (`> 20` modules) or when the persistent SQLite index is warm on disk.
        if len(module_map) > 20 or (repo_abs / ".brain_semantic_graph.sqlite").is_file():
            try:
                from canonical.swe_kernel import incremental_semantic_graph_v1 as isg

                isg_res = isg.localize_symptom_and_impacted_tests(repo_abs, out[-1800:])
                for rank_i, row_c in enumerate((isg_res.get("ranked_files") or isg_res.get("candidates") or ())[:5]):
                    cand_rel = str(row_c.get("path") if isinstance(row_c, Mapping) else row_c).strip()
                    if cand_rel and (repo_abs / cand_rel).is_file() and not cls._is_test_rel(cand_rel):
                        file_scores[cand_rel] = file_scores.get(cand_rel, 0.0) + max(1.5, 6.0 - 1.0 * rank_i)
            except Exception:
                pass

        # 4. Dynamic `ZeroOverheadLineMonitor` + Rejected-Value Producer Provenance (`the_value_that_was_rejected_had_a_producer_v1`)
        prod_prov = list(init_run.get("producer_provenance") or ())
        rej_asserts = list(init_run.get("rejected_assertions") or ())
        if not rej_asserts and out:
            try:
                from canonical.tools import the_value_that_was_rejected_had_a_producer_v1 as tvrp

                rej_txt = tvrp.rejected_value(out)
                if rej_txt:
                    rej_asserts.append({"op": "assert", "left_repr": rej_txt, "right_repr": "", "left_type": "", "right_type": ""})
            except Exception:
                pass
        for rank_p, pr_ev in enumerate(prod_prov[:5]):
            pr_rel = str(pr_ev.get("rel_file") or "")
            pr_fn = str(pr_ev.get("func") or "")
            pr_ln = int(pr_ev.get("line") or 0)
            if pr_rel and (repo_abs / pr_rel).is_file() and not cls._is_test_rel(pr_rel):
                file_scores[pr_rel] = file_scores.get(pr_rel, 0.0) + max(8.0, 22.0 - 3.0 * rank_p)
                if pr_ln > 0:
                    lst_pr = suspect_lines.setdefault(pr_rel, [])
                    if pr_ln not in lst_pr:
                        lst_pr.insert(0, pr_ln)
                if pr_fn and not pr_fn.startswith("<") and (pr_rel, pr_fn) not in symbol_targets:
                    symbol_targets.insert(0, (pr_rel, pr_fn))

        pre_hits = init_run.get("line_hits") or []
        if pre_hits and (init_run.get("line_hits_failing_only") or not (init_run.get("passing_nodes") or [])):
            dyn_hits = [(str(x[0]), int(x[1])) for x in pre_hits if isinstance(x, (list, tuple)) and len(x) == 2]
        elif (failing_nodes or enc_files) and _has_pytest() and hasattr(os, "fork") and threading.active_count() == 1:
            probe_target = failing_nodes[0] if failing_nodes else enc_files[0]
            dyn_hits = cls._collect_dynamic_line_hits_forked(repo_abs, probe_target)
        else:
            dyn_hits = [(str(x[0]), int(x[1])) for x in pre_hits if isinstance(x, (list, tuple)) and len(x) == 2]
        for rel_h, ln_h in dyn_hits:
            file_scores[rel_h] = file_scores.get(rel_h, 0.0) + 0.35
            lst = suspect_lines.setdefault(rel_h, [])
            if ln_h not in lst:
                lst.append(ln_h)

        ranked_files = [k for k, _ in sorted(file_scores.items(), key=lambda kv: (-kv[1], kv[0]))]
        # Ensure compact packages (`<= 12` source files) never miss un-named modules like `_parser.py` / `__init__.py`
        if len(ranked_files) < 6 and len(module_map) <= 16:
            for rel_extra in sorted(module_map.values()):
                if rel_extra not in ranked_files:
                    ranked_files.append(rel_extra)
                if len(ranked_files) >= 6:
                    break
        # When `line_hits_failing_only` captured post-import runtime lines in-session, module/class-level
        # `Assign` / `AnnAssign` constants (`DEFAULT_RULES`, compiled regexes, tables) executed at import time;
        # include their line spans in `suspect_lines` for `ranked_files[:6]` (~0.3 ms AST walk, zero extra fork!).
        if init_run.get("line_hits_failing_only"):
            for rf_imp in ranked_files[:6]:
                fp_imp = repo_abs / rf_imp
                if not fp_imp.is_file():
                    continue
                try:
                    raw_imp = fp_imp.read_text(encoding="utf-8", errors="replace")
                    if len(raw_imp) > 80_000:
                        continue
                    tree_imp = ast.parse(raw_imp)
                    lst_imp = suspect_lines.setdefault(rf_imp, [])
                    seen_imp = set(lst_imp)
                    for top_stmt in tree_imp.body:
                        if isinstance(top_stmt, (ast.Assign, ast.AnnAssign)):
                            for ln_x in range(top_stmt.lineno, getattr(top_stmt, "end_lineno", top_stmt.lineno) + 1):
                                if ln_x not in seen_imp:
                                    seen_imp.add(ln_x)
                                    lst_imp.append(ln_x)
                        elif isinstance(top_stmt, ast.ClassDef):
                            for c_stmt in top_stmt.body:
                                if isinstance(c_stmt, (ast.Assign, ast.AnnAssign)):
                                    for ln_x in range(c_stmt.lineno, getattr(c_stmt, "end_lineno", c_stmt.lineno) + 1):
                                        if ln_x not in seen_imp:
                                            seen_imp.add(ln_x)
                                            lst_imp.append(ln_x)
                except Exception:
                    pass
        ranked_functions = cls._extract_ranked_scopes(repo_abs, ranked_files[:6], suspect_lines, symbol_targets)

        return CausalFaultSpectrum(
            failing_nodes=failing_nodes,
            enclosing_files=enc_files,
            ranked_files=ranked_files,
            ranked_functions=ranked_functions,
            suspect_lines=suspect_lines,
            failure_kind=failure_kind,
            raw_output=out,
            passing_nodes=list(init_run.get("passing_nodes") or ())[:200],
            producer_provenance=prod_prov,
            rejected_assertions=rej_asserts,
        )

    @classmethod
    def _build_repo_module_map(cls, repo_dir: pathlib.Path) -> dict[str, str]:
        """Map dotted Python module names (`pkg.sub`) to relative file paths (`src/pkg/sub.py`)."""
        mapping: dict[str, str] = {}
        bases = [(repo_dir / "src", repo_dir / "src"), (repo_dir, repo_dir)] if (repo_dir / "src").is_dir() else [(repo_dir, repo_dir)]
        for base, rel_root in bases:
            if not base.is_dir():
                continue
            for py in sorted(base.rglob("*.py")):
                if ".git" in py.parts or "__pycache__" in py.parts:
                    continue
                rel_repo = py.relative_to(repo_dir).as_posix()
                if cls._is_test_rel(rel_repo):
                    continue
                rel_mod = py.relative_to(rel_root)
                parts = list(rel_mod.with_suffix("").parts)
                if parts and parts[-1] == "__init__":
                    parts = parts[:-1]
                if parts:
                    mapping[".".join(parts)] = rel_repo
        return mapping

    @classmethod
    def _resolve_test_callees(
        cls,
        test_file: pathlib.Path,
        fail_line: int,
        module_map: Mapping[str, str],
    ) -> list[tuple[str, str]]:
        """Find repo symbols called inside the failing test function around `fail_line`."""
        try:
            src = test_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except Exception:
            return []

        imported_symbols: dict[str, tuple[str, str]] = {}  # local_alias -> (rel_file, orig_symbol)
        imported_modules: dict[str, str] = {}  # local_alias -> mod_name
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                for alias in node.names:
                    as_name = alias.asname or alias.name
                    sub_mod = f"{mod}.{alias.name}"
                    if sub_mod in module_map:
                        imported_modules[as_name] = sub_mod
                    elif mod in module_map:
                        imported_symbols[as_name] = (module_map[mod], alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    as_name = alias.asname or alias.name.split(".")[0]
                    if alias.name in module_map:
                        imported_modules[as_name] = alias.name

        # Locate enclosing test FunctionDef / AsyncFunctionDef containing `fail_line`
        enclosing_fn: ast.AST = tree
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_ln = getattr(node, "end_lineno", node.lineno + 100)
                if node.lineno <= fail_line <= end_ln:
                    enclosing_fn = node
                    break

        hits: list[tuple[str, str]] = []
        for sub in ast.walk(enclosing_fn):
            if isinstance(sub, ast.Call):
                if isinstance(sub.func, ast.Name) and sub.func.id in imported_symbols:
                    pair = imported_symbols[sub.func.id]
                    if pair not in hits:
                        hits.append(pair)
                elif (
                    isinstance(sub.func, ast.Attribute)
                    and isinstance(sub.func.value, ast.Name)
                    and sub.func.value.id in imported_modules
                ):
                    mod_n = imported_modules[sub.func.value.id]
                    if mod_n in module_map:
                        pair = (module_map[mod_n], sub.func.attr)
                        if pair not in hits:
                            hits.append(pair)
            elif isinstance(sub, ast.Name) and sub.id in imported_symbols:
                pair = imported_symbols[sub.id]
                if pair not in hits:
                    hits.append(pair)
        return hits

    @classmethod
    def _collect_dynamic_line_hits_forked(cls, repo_dir: pathlib.Path, probe_target: str) -> list[tuple[str, int]]:
        """Fork once to collect exact `(rel_file, line_no)` hits via `ZeroOverheadLineMonitor`."""
        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            payload = b"[]"
            try:
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)
                os.close(devnull)
                os.chdir(str(repo_dir))
                if (repo_dir / "src").is_dir():
                    sys.path.insert(0, str(repo_dir))
                    sys.path.insert(0, str(repo_dir / "src"))
                else:
                    sys.path.insert(0, str(repo_dir))
                os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
                import pytest

                with ZeroOverheadLineMonitor(repo_dir, exclude_tests=True) as mon:
                    pytest.main(["-q", "--tb=no", "-p", "no:cacheprovider", "-o", "addopts=", probe_target])
                payload = json.dumps(sorted(mon.hits)[:600]).encode("utf-8")
            except BaseException:
                payload = b"[]"
            finally:
                try:
                    _fork_pipe_write_all(w_fd, payload)
                    os.close(w_fd)
                except OSError:
                    pass
                os._exit(0)
        os.close(w_fd)
        raw_bytes, _ = _fork_wait_and_drain(pid, r_fd, 4.0)
        try:
            arr = json.loads(raw_bytes.decode("utf-8") or "[]")
            return [(str(x[0]), int(x[1])) for x in arr if isinstance(x, list) and len(x) == 2]
        except Exception:
            return []

    @classmethod
    def _extract_ranked_scopes(
        cls,
        repo_dir: pathlib.Path,
        ranked_files: Sequence[str],
        suspect_lines: Mapping[str, Sequence[int]],
        symbol_targets: Sequence[tuple[str, str]],
    ) -> list[tuple[str, str, int, int]]:
        scopes: list[tuple[float, str, str, int, int]] = []
        sym_set = {(r, s) for r, s in symbol_targets}
        for f_rank, rel in enumerate(ranked_files):
            fp = repo_dir / rel
            try:
                tree = ast.parse(fp.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            lines = set(suspect_lines.get(rel) or ())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    end_ln = getattr(node, "end_lineno", node.lineno)
                    hit_count = sum(1 for ln in lines if node.lineno <= ln <= end_ln)
                    sym_bonus = 20.0 if (rel, node.name) in sym_set else 0.0
                    if hit_count > 0 or sym_bonus > 0.0:
                        score = sym_bonus + hit_count * 2.0 - f_rank * 1.5 - 0.01 * max(1, end_ln - node.lineno)
                        scopes.append((score, rel, node.name, node.lineno, end_ln))
        scopes.sort(key=lambda row: (-row[0], row[1], row[3]))
        return [(r, n, s, e) for _, r, n, s, e in scopes[:24]]


class CodePlanObligationZipper:
    """Proactive `CodePlan`-style multi-file AST symbol & arity obligation propagator.

    Indexes exported functions/classes and cross-module call sites so that signature
    or constructor arity edits propagate synchronized call-site updates across files.
    """

    def __init__(self, repo_dir: pathlib.Path) -> None:
        self.repo_dir = repo_dir.resolve()
        self.module_map = MultiSignalCausalLocalizer._build_repo_module_map(self.repo_dir)
        self.reverse_importers: dict[tuple[str, str], list[tuple[str, int]]] = {}
        self._orig_arity_cache: dict[str, dict[str, int]] = {}
        self._indexed = False

    def _ensure_indexed(self) -> None:
        if self._indexed:
            return
        self._indexed = True
        for mod_name, rel_path in self.module_map.items():
            try:
                fp_m = self.repo_dir / rel_path
                raw_txt = fp_m.read_text(encoding="utf-8", errors="replace")
                if len(raw_txt) > 80_000 and raw_txt.count("def ") <= 2:
                    continue
                tree = ast.parse(raw_txt)
            except Exception:
                continue
            imported_from: dict[str, tuple[str, str]] = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    target_rel = self.module_map.get(node.module)
                    if target_rel:
                        for alias in node.names:
                            imported_from[alias.asname or alias.name] = (target_rel, alias.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in imported_from:
                    key = imported_from[node.func.id]
                    sites = self.reverse_importers.setdefault(key, [])
                    if (rel_path, node.lineno) not in sites:
                        sites.append((rel_path, node.lineno))

    def dependent_callsites(self, rel_file: str, symbol_name: str) -> list[tuple[str, int]]:
        self._ensure_indexed()
        return list(self.reverse_importers.get((rel_file, symbol_name), ()))

    @staticmethod
    def _req_arity(tree: ast.Module) -> dict[str, int]:
        out: dict[str, int] = {}
        for n in tree.body:
            if isinstance(n, ast.FunctionDef):
                out[n.name] = len(n.args.args) - len(n.args.defaults)
            elif isinstance(n, ast.ClassDef):
                for item in n.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        out[n.name] = max(0, len(item.args.args) - 1 - len(item.args.defaults))
        return out

    def propagate_default_arg_obligations(
        self,
        primary_rel: str,
        orig_source: str,
        patched_source: str,
        *,
        patched_tree: ast.Module | None = None,
    ) -> dict[str, str]:
        """Return `{rel_path: source}` including any cross-file call-site obligations."""
        bundle = {primary_rel: patched_source}
        try:
            old_a = self._orig_arity_cache.get(primary_rel)
            if old_a is None:
                old_a = self._req_arity(ast.parse(orig_source))
                self._orig_arity_cache[primary_rel] = old_a
            new_tree = patched_tree if patched_tree is not None else ast.parse(patched_source)
        except SyntaxError:
            return bundle

        new_a = self._req_arity(new_tree)
        for sym, req_n in new_a.items():
            if sym in old_a and req_n > old_a[sym]:
                # Check external call sites; if any pass fewer positional args without keywords, pad `None`
                for dep_rel, _ in self.dependent_callsites(primary_rel, sym):
                    if dep_rel == primary_rel or dep_rel in bundle:
                        continue
                    dep_fp = self.repo_dir / dep_rel
                    try:
                        dep_src = dep_fp.read_text(encoding="utf-8", errors="replace")
                        dep_tree = ast.parse(dep_src)
                    except Exception:
                        continue
                    changed = False
                    for node in ast.walk(dep_tree):
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == sym:
                            if len(node.args) < req_n and not node.keywords:
                                while len(node.args) < req_n:
                                    node.args.append(ast.Constant(value=None))
                                changed = True
                    if changed:
                        ast.fix_missing_locations(dep_tree)
                        bundle[dep_rel] = ast.unparse(dep_tree) + "\n"
        return bundle


# ---------------------------------------------------------------------------
# 5. FIRST-PRINCIPLES STRUCTURAL & ALGEBRAIC MORPHISM SYNTHESIZER
# ---------------------------------------------------------------------------


def _mdl_bytes(source: str) -> int:
    try:
        from canonical.swe_kernel import compression_gain_v1 as cg

        return int(cg.description_bytes(ast.parse(source)))
    except Exception:
        return len(source.encode("utf-8"))


def _replace_node_segment(source: str, node: ast.AST, replacement: str) -> str | None:
    """Sub-0.1ms UTF-8 byte-span AST splicer (`angelic_cegis_repair_v1.splice_ast_node`) preserving formatting."""
    try:
        from canonical.swe_kernel import angelic_cegis_repair_v1 as acr

        spliced = acr.splice_ast_node(source, node, replacement)
        if spliced is not None:
            ast.parse(spliced)
            return spliced
    except Exception:
        pass
    lineno = getattr(node, "lineno", None)
    end_lineno = getattr(node, "end_lineno", None)
    col = getattr(node, "col_offset", None)
    end_col = getattr(node, "end_col_offset", None)
    if None in (lineno, end_lineno, col, end_col):
        return None
    lines = source.splitlines(keepends=True)
    if not (1 <= lineno <= len(lines) and 1 <= end_lineno <= len(lines)):
        return None
    start_b = sum(len(lines[i].encode("utf-8")) for i in range(lineno - 1)) + int(col)
    end_b = sum(len(lines[i].encode("utf-8")) for i in range(end_lineno - 1)) + int(end_col)
    raw = source.encode("utf-8")
    patched = (raw[:start_b] + replacement.encode("utf-8") + raw[end_b:]).decode("utf-8")
    try:
        ast.parse(patched)
    except SyntaxError:
        return None
    return patched


def pre_sieve_and_simulate_meaning_ir(
    baseline_source: str,
    candidate_sources: Sequence[str],
    *,
    entry_func: str | None = None,
    probe_args: Sequence[Any] | None = None,
    expected_return: Any = None,
    check_expected: bool = False,
) -> dict[str, Any]:
    """Microsecond Guarded Region-SSA Meaning-IR deduplicator & in-RAM simulator (`K3 = 0`).

    Unifies `guarded_meaning_ir_v1` (`SemiPersistentEGraph`, `lower_python`, `anti_unify`),
    `executable_simulator_mental_model_v1` (`simulate_python_fast`, `abstract_analyze_function`,
    `forward_backward_prunes_candidate`), and `concept_library_v1.eval_pure_ast_expr` to delete
    semantically redundant or provably non-fixing candidates in RAM BEFORE touching `os.fork()`.
    """
    t0 = time.perf_counter()
    from canonical.swe_kernel import executable_simulator_mental_model_v1 as esmm
    from canonical.swe_kernel import guarded_meaning_ir_v1 as gmir
    from canonical.swe_kernel import semantic_ir_v1 as sir

    egraph = gmir.SemiPersistentEGraph()
    base_sig: str | None = None
    try:
        base_mir = gmir.lower_python(baseline_source)
        base_sig = json.dumps(base_mir.as_dict(), sort_keys=True)
    except Exception:
        base_sig = None

    abstract_findings: list[dict[str, Any]] = []
    if entry_func:
        try:
            ir_prog = sir.lower_python_source(baseline_source, filename="<baseline>.py")
            for fn_ir in ir_prog.functions.values():
                if fn_ir.name == entry_func or fn_ir.qualname.endswith(entry_func):
                    for fnd in esmm.abstract_analyze_function(fn_ir):
                        abstract_findings.append(
                            {
                                "kind": fnd.kind,
                                "line": fnd.line,
                                "detail": fnd.detail,
                                "symbol": fnd.symbol,
                            }
                        )
        except Exception:
            pass

    kept_indices: list[int] = []
    pruned_semantic_dups = 0
    pruned_simulation_mismatch = 0
    seen_mir_sigs: set[str] = {base_sig} if base_sig is not None else set()

    for idx, cand_src in enumerate(candidate_sources):
        if not cand_src or cand_src == baseline_source:
            pruned_semantic_dups += 1
            continue
        # 1. Guarded Region-SSA Meaning-IR canonical equivalence check (`< 80 us`)
        egraph.push()
        try:
            cand_mir = gmir.lower_python(cand_src)
            cand_sig = json.dumps(cand_mir.as_dict(), sort_keys=True)
            if cand_sig in seen_mir_sigs:
                pruned_semantic_dups += 1
                continue
            seen_mir_sigs.add(cand_sig)
        except Exception:
            pass
        finally:
            egraph.pop()

        # 2. Optional microsecond in-RAM concrete delta simulation (`simulate_python_fast`)
        if entry_func and probe_args is not None:
            try:
                sim_out = esmm.simulate_python_fast(cand_src, entry_func, list(probe_args), step_quota=2500)
                if sim_out.get("status") in ("FAULT", "CYCLE", "QUOTA"):
                    pruned_simulation_mismatch += 1
                    continue
                if check_expected and sim_out.get("status") == "OK" and sim_out.get("value") != expected_return:
                    pruned_simulation_mismatch += 1
                    continue
            except Exception:
                pass

        kept_indices.append(idx)

    return {
        "schema": SCHEMA,
        "status": "PASS__MEANING_IR_PRE_SIEVED",
        "pass": True,
        "total_candidates": len(candidate_sources),
        "kept_indices": kept_indices,
        "kept_count": len(kept_indices),
        "pruned_semantic_duplicates": pruned_semantic_dups,
        "pruned_simulation_mismatches": pruned_simulation_mismatch,
        "abstract_findings": abstract_findings,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
        "parameters_stored": 0,
    }


class FirstPrinciplesMorphismSynthesizer:
    """Generates candidate repairs from general PL, type-homomorphism, and lexer laws."""

    @classmethod
    def synthesize(
        cls,
        repo_dir: pathlib.Path,
        spectrum: CausalFaultSpectrum,
        zipper: CodePlanObligationZipper,
        *,
        max_candidates: int = 96,
    ) -> list[CandidatePatch]:
        candidates: list[CandidatePatch] = []
        seen_hashes: set[str] = set()

        def _emit(family: str, rel_file: str, orig_src: str, new_src: str, desc: str) -> None:
            if len(candidates) >= max_candidates or new_src == orig_src:
                return
            digest = hashlib.sha256(f"{rel_file}\0{new_src}".encode("utf-8")).hexdigest()[:16]
            if digest in seen_hashes:
                return
            try:
                new_tree = ast.parse(new_src)
            except SyntaxError:
                return
            seen_hashes.add(digest)
            bundle = zipper.propagate_default_arg_obligations(rel_file, orig_src, new_src, patched_tree=new_tree)
            mdl_delta = len(new_src.encode("utf-8")) - len(orig_src.encode("utf-8"))
            candidates.append(
                CandidatePatch(
                    patch_id=f"{family}:{digest}",
                    family=family,
                    patched_files=bundle,
                    description=desc,
                    mdl_delta_bytes=mdl_delta,
                )
            )

        parsed_targets: list[tuple[str, str, ast.Module, set[int]]] = []
        for rel_file in spectrum.ranked_files[:5]:
            fp = repo_dir / rel_file
            if not fp.is_file():
                continue
            try:
                orig_src = fp.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(orig_src)
            except Exception:
                continue
            hot_lines = set(spectrum.suspect_lines.get(rel_file) or ())
            for r_f, _, s_ln, e_ln in spectrum.ranked_functions:
                if r_f == rel_file:
                    hot_lines.update(range(s_ln, e_ln + 1))
            parsed_targets.append((rel_file, orig_src, tree, hot_lines))

        # Pass 1: High-specificity algebraic & structural laws (`M1`-`M5`, `M8`-`M10`) across ALL top-5 files first!
        for rel_file, orig_src, tree, hot_lines in parsed_targets:
            if len(candidates) >= max_candidates:
                break
            cls._law_m1_init_self_projection_and_lazy_property(rel_file, orig_src, tree, hot_lines, _emit)
            cls._law_m2_regex_and_unicode_ascii_algebra(rel_file, orig_src, tree, hot_lines, _emit, spectrum.raw_output)
            cls._law_m3_collection_reduction_order_duals(rel_file, orig_src, tree, hot_lines, _emit)
            cls._law_m4_str_vs_iterable_homomorphism_guard(rel_file, orig_src, tree, hot_lines, _emit, spectrum.raw_output)
            cls._law_m5_error_collector_partial_continuation(rel_file, orig_src, tree, hot_lines, _emit)
            cls._law_m8_classmethod_and_copy_polymorphism(rel_file, orig_src, tree, hot_lines, _emit)
            cls._law_m9_pep681_copy_replace_and_pickle_state(rel_file, orig_src, tree, hot_lines, _emit, spectrum.raw_output)
            cls._law_m10_unknown_keys_callback_and_str_cache(rel_file, orig_src, tree, hot_lines, _emit, spectrum.raw_output)

        # Pass 2: Local argument & boundary duals (`M6`, `M7`) strictly capped (`<= 8` per law per file) on top-2 files
        for rel_file, orig_src, tree, hot_lines in parsed_targets[:2]:
            if len(candidates) >= max_candidates:
                break
            m6_count = [0]
            m7_count = [0]

            def _emit_m6(fam: str, rf: str, os_s: str, ns_s: str, dsc: str, _cnt: list[int] = m6_count) -> None:
                if _cnt[0] < 8:
                    _cnt[0] += 1
                    _emit(fam, rf, os_s, ns_s, dsc)

            def _emit_m7(fam: str, rf: str, os_s: str, ns_s: str, dsc: str, _cnt: list[int] = m7_count) -> None:
                if _cnt[0] < 8:
                    _cnt[0] += 1
                    _emit(fam, rf, os_s, ns_s, dsc)

            if len(orig_src) <= 45_000:
                cls._law_m6_scope_local_call_arg_substitution(rel_file, orig_src, tree, hot_lines, _emit_m6)
                cls._law_m7_predicate_and_boundary_duals(rel_file, orig_src, tree, hot_lines, _emit_m7)

        return candidates

    @classmethod
    def _law_m1_init_self_projection_and_lazy_property(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
    ) -> None:
        """Law M1: Eager `self.<attr> = f(self)` in `__init__` -> base projection / lazy `@property`."""
        lines = src.splitlines(keepends=True)
        for cls_node in ast.walk(tree):
            if not isinstance(cls_node, ast.ClassDef):
                continue
            existing_defs = {n.name for n in cls_node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for item in cls_node.body:
                if not (isinstance(item, ast.FunctionDef) and item.name == "__init__"):
                    continue
                for stmt in item.body:
                    target_node: ast.AST | None = None
                    val_node: ast.AST | None = None
                    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                        target_node, val_node = stmt.targets[0], stmt.value
                    elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                        target_node, val_node = stmt.target, stmt.value
                    if not (
                        isinstance(target_node, ast.Attribute)
                        and isinstance(target_node.value, ast.Name)
                        and target_node.value.id == "self"
                        and not target_node.attr.startswith("_")
                        and val_node is not None
                    ):
                        continue
                    val_src = ast.get_source_segment(src, val_node) or ""
                    if "self" not in val_src:
                        continue
                    attr_name = target_node.attr
                    # M1a: Replace `str(self)` with `super().__str__()` in `__init__` when class overrides `__str__`
                    if "str(self)" in val_src:
                        rep_super = _replace_node_segment(src, val_node, val_src.replace("str(self)", "super().__str__()"))
                        if rep_super:
                            emit("M1a_init_super_str", rel_file, src, rep_super, f"{cls_node.name}.__init__: str(self) -> super().__str__()")

                    # M1b: Lift `self.<attr> = <expr_with_self> if <param> is None else <param>` to lazy `@property` + setter
                    if attr_name not in existing_defs and isinstance(val_node, ast.IfExp):
                        param_src: str | None = None
                        default_src: str | None = None
                        if (
                            isinstance(val_node.test, ast.Compare)
                            and len(val_node.test.ops) == 1
                            and isinstance(val_node.test.ops[0], ast.Is)
                            and isinstance(val_node.test.comparators[0], ast.Constant)
                            and val_node.test.comparators[0].value is None
                        ):
                            param_src = ast.get_source_segment(src, val_node.test.left)
                            default_src = ast.get_source_segment(src, val_node.body)
                        if param_src and default_src:
                            stmt_indent = " " * stmt.col_offset
                            cls_body_indent = " " * item.col_offset
                            for default_variant in (default_src, default_src.replace("str(self)", "super().__str__()")):
                                replaced_init = _replace_node_segment(src, stmt, f"self._{attr_name} = {param_src}")
                                if not replaced_init:
                                    continue
                                r_lines = replaced_init.splitlines(keepends=True)
                                insert_at = getattr(item, "end_lineno", item.lineno + 1)
                                prop_block = (
                                    f"\n{cls_body_indent}@property\n"
                                    f"{cls_body_indent}def {attr_name}(self):\n"
                                    f"{stmt_indent}return {default_variant} if self._{attr_name} is None else self._{attr_name}\n"
                                    f"\n{cls_body_indent}@{attr_name}.setter\n"
                                    f"{cls_body_indent}def {attr_name}(self, value) -> None:\n"
                                    f"{stmt_indent}self._{attr_name} = value\n"
                                )
                                candidate_txt = "".join(r_lines[:insert_at]) + prop_block + "".join(r_lines[insert_at:])
                                emit(
                                    "M1b_lazy_property_lift",
                                    rel_file,
                                    src,
                                    candidate_txt,
                                    f"{cls_node.name}.{attr_name}: eager __init__ -> lazy @property + setter",
                                )

    @classmethod
    def _law_m2_regex_and_unicode_ascii_algebra(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
        raw_output: str = "",
    ) -> None:
        """Law M2: Regex lexer boundary laws (`[^ \\t]` -> `\\S`, `[^\\s;)]*` -> `[^\\s;,)]+`, `$` -> `\\Z`, `re.IGNORECASE | re.ASCII`, `.isascii()` contract guard)."""
        for node in ast.walk(tree):
            # Sub-law M2-flags: `re.compile(..., re.IGNORECASE)` without `re.ASCII` -> `| re.ASCII`
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "re"
                and node.func.attr in ("compile", "match", "search", "fullmatch")
            ):
                flag_nodes = list(node.args[1:]) + [kw.value for kw in node.keywords if kw.arg == "flags"]
                for fn_arg in flag_nodes:
                    f_src = ast.get_source_segment(src, fn_arg) or ""
                    if ("IGNORECASE" in f_src or re.search(r"\bre\.I\b", f_src)) and "ASCII" not in f_src and not re.search(r"\bre\.A\b", f_src):
                        patched = _replace_node_segment(src, fn_arg, f"({f_src} | re.ASCII)")
                        if patched:
                            emit("M2_regex_ascii_flag", rel_file, src, patched, f"restrict {f_src} case-folding to ASCII via re.ASCII")

            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value
                if len(s) < 2 or len(s) > 6000:
                    continue
                seg = ast.get_source_segment(src, node) or ""
                is_regex_like = any(tok in s for tok in ("[^", "\\s", "[A-Za-z", "[a-z", "^", "$", "(?P<"))
                if not is_regex_like:
                    continue
                rewrites: list[tuple[str, str]] = []
                if "[^ \\t]+" in s:
                    rewrites.append((s.replace("[^ \\t]+", "[^\\s]+"), "horizontal ws negation -> all-whitespace negation"))
                    rewrites.append((s.replace("[^ \\t]+", "[^ \\t\\r\\n]+"), "exclude CR/LF in token pattern"))
                if "[^\\s;)]*" in s:
                    rewrites.append((s.replace("[^\\s;)]*", "[^\\s;,)]+"), "require non-empty token & exclude comma delimiter"))
                    rewrites.append((s.replace("[^\\s;)]*", "[^\\s;)]+"), "require non-empty token quantifier"))
                if "[^\\s;]*" in s:
                    rewrites.append((s.replace("[^\\s;]*", "[^\\s;,]+"), "require non-empty token & exclude comma"))
                if s.endswith("$") and not s.endswith("\\$"):
                    rewrites.append((s[:-1] + "\\Z", "anchor end-of-string \\Z instead of pre-newline $"))
                if "DID NOT RAISE" in raw_output and "(?P<" in s and "*" in s:
                    # Kleene Algebra `A* -> A+` Non-Empty Capture Tightening Law:
                    # When a grammar fails `DID_NOT_RAISE`, any named group `(?P<name><atom>*)` accepts empty string `""`.
                    for m_kg in re.finditer(r"(\(\?P<[A-Za-z_][A-Za-z0-9_]*>(?:\(\?:[^()]+\)|\[[^\]\\]*(?:\\.[^\]\\]*)*\]|\\.|[^()\[\]*+?])+)\*(\))", s):
                        tightened = s[: m_kg.start()] + m_kg.group(1) + "+" + m_kg.group(2) + s[m_kg.end() :]
                        if tightened != s:
                            rewrites.append((tightened, "Kleene A* -> A+ non-empty named capture group tightening"))
                for new_pat, reason in rewrites:
                    if seg.startswith(('r"""', "r'''")) and '"""' not in new_pat:
                        lit = f'r"""{new_pat}"""'
                    elif seg.startswith(("r'", 'r"', "R'", 'R"')) and '"' not in new_pat and "\n" not in new_pat and not new_pat.endswith("\\"):
                        lit = f'r"{new_pat}"'
                    else:
                        lit = repr(new_pat)
                    patched = _replace_node_segment(src, node, lit)
                    if patched:
                        emit("M2_regex_boundary", rel_file, src, patched, reason)

            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("lower", "casefold")
                and not node.args
                and not node.keywords
            ):
                recv_src = ast.get_source_segment(src, node.func.value)
                full_call = ast.get_source_segment(src, node)
                if recv_src and full_call and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", recv_src):
                    guarded = f"({full_call} if {recv_src}.isascii() else {recv_src})"
                    patched = _replace_node_segment(src, node, guarded)
                    if patched:
                        emit(
                            "M2_ascii_casefold_guard",
                            rel_file,
                            src,
                            patched,
                            f"prevent non-ASCII Unicode case-fold collision on {full_call}",
                        )

        # Sub-law M2-contract: When `DID NOT RAISE <Exc>` + `match="...non-ASCII..."` appears in test failure,
        # synthesize an explicit `.isascii()` precondition guard raising `<Exc>` at string-validating entrypoints & casefold branches!
        m_dnr = re.search(r"DID NOT RAISE\s+(?:<class ['\"](?:[A-Za-z0-9_]+\.)*)?([A-Za-z_][A-Za-z0-9_]*)", raw_output)
        m_ascii = re.search(r"(?:match=['\"]([^'\"]*ascii[^'\"]*)['\"]|\b(non-ascii)\b)", raw_output, flags=re.IGNORECASE)
        if m_dnr and m_ascii:
            exc_cls = m_dnr.group(1)
            msg_hint = m_ascii.group(1) or m_ascii.group(2) or "non-ASCII"
            for fn in tree.body:
                if not isinstance(fn, ast.FunctionDef) or not fn.args.args or not fn.body:
                    continue
                first_param = fn.args.args[0].arg
                if first_param in ("self", "cls"):
                    if len(fn.args.args) < 2:
                        continue
                    first_param = fn.args.args[1].arg
                insert_stmt = fn.body[1] if (
                    len(fn.body) > 1
                    and isinstance(fn.body[0], ast.Expr)
                    and isinstance(fn.body[0].value, ast.Constant)
                    and isinstance(fn.body[0].value.value, str)
                ) else fn.body[0]
                stmt_src = ast.get_source_segment(src, insert_stmt)
                if stmt_src:
                    indent = " " * insert_stmt.col_offset
                    guard_code = (
                        f"if isinstance({first_param}, str) and not {first_param}.isascii():\n"
                        f"{indent}    raise {exc_cls}(f\"Invalid input ({{{first_param}!r}}): {msg_hint}\")\n"
                        f"{indent}{stmt_src}"
                    )
                    patched = _replace_node_segment(src, insert_stmt, guard_code)
                    if patched:
                        emit("M2_ascii_precondition_contract", rel_file, src, patched, f"{fn.name}: enforce .isascii() raising {exc_cls}")
                # Also guard local `.lower()` / `.casefold()` branches where Unicode casefolding erases non-ASCII (e.g. `ſ` -> `s`)
                for sub_if in ast.walk(fn):
                    if not isinstance(sub_if, ast.If) or not sub_if.body:
                        continue
                    t_seg = ast.get_source_segment(src, sub_if.test) or ""
                    m_lc = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\.(?:lower|casefold)\(\)", t_seg)
                    if not m_lc:
                        continue
                    lc_var = m_lc.group(1)
                    b0 = sub_if.body[0]
                    b0_src = ast.get_source_segment(src, b0)
                    if not b0_src:
                        continue
                    b_ind = " " * b0.col_offset
                    br_guard = (
                        f"if not {lc_var}.isascii():\n"
                        f"{b_ind}    raise {exc_cls}(f\"Invalid value ({msg_hint}): {{{lc_var}!r}}\")\n"
                        f"{b_ind}{b0_src}"
                    )
                    patched_br = _replace_node_segment(src, b0, br_guard)
                    if patched_br:
                        emit("M2_ascii_branch_casefold_contract", rel_file, src, patched_br, f"{fn.name}: reject {msg_hint} `{lc_var}` before casefold normalization")

    @classmethod
    def _law_m3_collection_reduction_order_duals(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
    ) -> None:
        """Law M3: `DictComp` `{k: v for x in seq}` last-wins -> `reversed(...)` first-wins dual."""
        for node in ast.walk(tree):
            if isinstance(node, ast.DictComp) and len(node.generators) == 1:
                gen = node.generators[0]
                if gen.is_async:
                    continue
                iter_src = ast.get_source_segment(src, gen.iter)
                if not iter_src or "reversed(" in iter_src:
                    continue
                for wrapped in (f"reversed({iter_src})", f"reversed(list({iter_src}))"):
                    patched = _replace_node_segment(src, gen.iter, wrapped)
                    if patched:
                        emit(
                            "M3_dictcomp_first_wins_dual",
                            rel_file,
                            src,
                            patched,
                            f"DictComp first-occurrence-wins dual via {wrapped}",
                        )
                        break

    @classmethod
    def _law_m4_str_vs_iterable_homomorphism_guard(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
        raw_output: str = "",
    ) -> None:
        """Law M4: `str` is an `Iterable[str]` — detect erroneous `if isinstance(x, str):` coercions,
        set-valued environment key lookups accepting `str`, or unguarded `isinstance(x, Iterable)` checks.
        """
        local_exceptions: list[str] = []
        m_dnr = re.search(r"DID NOT RAISE\s+([A-Za-z_][A-Za-z0-9_]*)", raw_output)
        if m_dnr:
            local_exceptions.append(m_dnr.group(1))
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                base_names = [ast.unparse(b) for b in n.bases]
                if any("Error" in b or "Exception" in b or b in ("ValueError", "TypeError", "KeyError") for b in base_names):
                    if n.name not in local_exceptions:
                        local_exceptions.append(n.name)

        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            fn_params = [a.arg for a in fn.args.args if a.arg not in ("self", "cls")]
            for node in ast.walk(fn):
                # Sub-pattern 4A: `if isinstance(v, str): return ... else: return ...` inside set/collection normalizer
                if (
                    isinstance(node, ast.If)
                    and isinstance(node.test, ast.Call)
                    and isinstance(node.test.func, ast.Name)
                    and node.test.func.id == "isinstance"
                    and len(node.test.args) == 2
                    and isinstance(node.test.args[1], ast.Name)
                    and node.test.args[1].id == "str"
                    and node.orelse
                ):
                    var_name = ast.get_source_segment(src, node.test.args[0]) or "value"
                    else_stmt_srcs = [ast.get_source_segment(src, s) for s in node.orelse]
                    indent = " " * node.col_offset
                    body_indent = indent + "    "
                    exc_choices = [*local_exceptions[:3], "TypeError", "ValueError"]
                    for exc_cls in dict.fromkeys(exc_choices):
                        else_joined = f"\n{indent}".join(s for s in else_stmt_srcs if s)
                        repl = (
                            f"if isinstance({var_name}, str):\n"
                            f"{body_indent}raise {exc_cls}(f\"Expected collection, got str: {{{var_name}!r}}\")\n"
                            f"{indent}{else_joined}"
                        )
                        patched = _replace_node_segment(src, node, repl)
                        if patched:
                            emit(
                                "M4a_reject_str_in_collection_normalizer",
                                rel_file,
                                src,
                                patched,
                                f"{fn.name}: reject str in collection normalizer with {exc_cls}",
                            )

                # Sub-pattern 4C: `if <key> in <SET_CONST>:` block that normalizes one operand without rejecting `str` on collection side
                if (
                    isinstance(node, ast.If)
                    and isinstance(node.test, ast.Compare)
                    and len(node.test.ops) == 1
                    and isinstance(node.test.ops[0], ast.In)
                    and isinstance(node.test.comparators[0], ast.Name)
                    and "SET" in node.test.comparators[0].id.upper()
                    and len(fn_params) >= 2
                ):
                    indent = " " * node.col_offset
                    body_indent = indent + "    "
                    orig_if_src = ast.get_source_segment(src, node)
                    if orig_if_src and local_exceptions:
                        exc_cls = local_exceptions[0]
                        # Check non-collection string values when set-valued key is compared
                        p_lhs, p_rhs = fn_params[0], fn_params[2] if len(fn_params) >= 3 else fn_params[1]
                        # In `val in set_var` (`op` in `("in", "not in")`), `p_rhs` must not be `str`; in `set_var == ...`, `p_lhs` or `p_rhs` is `set` vs `str`
                        op_param = fn_params[1] if len(fn_params) >= 3 else None
                        if op_param:
                            guard_hdr = (
                                f"if {ast.get_source_segment(src, node.test)}:\n"
                                f"{body_indent}if (isinstance({p_rhs}, str) and str({op_param}) in ('in', 'not in')) or (isinstance({p_lhs}, str) and isinstance({p_rhs}, str)):\n"
                                f"{body_indent}    raise {exc_cls}(f\"Cannot evaluate set-valued marker with string operand\")\n"
                                f"{indent}"
                            )
                            patched = _replace_node_segment(src, node, guard_hdr + orig_if_src)
                            if patched:
                                emit(
                                    "M4c_set_marker_str_operand_guard",
                                    rel_file,
                                    src,
                                    patched,
                                    f"{fn.name}: guard set-valued key against str operand raising {exc_cls}",
                                )

                # Sub-pattern 4B: `isinstance(x, (Iterable, Sequence, Collection))` without `not isinstance(x, str)`
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "isinstance"
                    and len(node.args) == 2
                ):
                    ty_src = ast.get_source_segment(src, node.args[1]) or ""
                    if any(tok in ty_src for tok in ("Iterable", "Collection", "Sequence", "Container")):
                        v_src = ast.get_source_segment(src, node.args[0])
                        c_src = ast.get_source_segment(src, node)
                        if v_src and c_src:
                            patched = _replace_node_segment(
                                src, node, f"({c_src} and not isinstance({v_src}, (str, bytes)))"
                            )
                            if patched:
                                emit(
                                    "M4b_exclude_str_from_iterable_check",
                                    rel_file,
                                    src,
                                    patched,
                                    f"{fn.name}: exclude (str, bytes) from {c_src}",
                                )

    @classmethod
    def _law_m5_error_collector_partial_continuation(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
    ) -> None:
        """Law M5: Error-accumulating parser returning `()` / `[]` instead of partial valid `tuple(acc)` / `acc`."""
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # Find list accumulators initialized in `fn` (`elements = []` or `elements: list[...] = []`)
            acc_names: list[str] = []
            for st in fn.body:
                if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                    if isinstance(st.value, ast.List) and len(st.value.elts) == 0:
                        acc_names.append(st.targets[0].id)
                elif isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name) and isinstance(st.value, ast.List) and len(st.value.elts) == 0:
                    acc_names.append(st.target.id)
            if not acc_names:
                continue
            # Look for `if <err_cond>: return ()` or `return []` AFTER the loop in `fn.body`
            saw_loop = False
            for st in fn.body:
                if isinstance(st, (ast.For, ast.While)):
                    saw_loop = True
                elif saw_loop and isinstance(st, ast.If) and len(st.body) == 1 and isinstance(st.body[0], ast.Return):
                    ret_stmt = st.body[0]
                    ret_val = ret_stmt.value
                    for acc in acc_names:
                        if isinstance(ret_val, ast.Tuple) and len(ret_val.elts) == 0:
                            patched = _replace_node_segment(src, ret_val, f"tuple({acc})")
                            if patched:
                                emit(
                                    "M5_partial_accumulator_return",
                                    rel_file,
                                    src,
                                    patched,
                                    f"{fn.name}: return partial tuple({acc}) on collected parse errors",
                                )
                        elif isinstance(ret_val, ast.List) and len(ret_val.elts) == 0:
                            patched = _replace_node_segment(src, ret_val, f"list({acc})")
                            if patched:
                                emit(
                                    "M5_partial_accumulator_return",
                                    rel_file,
                                    src,
                                    patched,
                                    f"{fn.name}: return partial list({acc}) on collected parse errors",
                                )

    @classmethod
    def _law_m6_scope_local_call_arg_substitution(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
    ) -> None:
        """Law M6: Replace duplicated or shadowed local variable arguments in `raise Exc(a, a, b)` / helper calls."""
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            scope_vars: list[str] = [
                a.arg for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs) if a.arg not in ("self", "cls")
            ]
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store) and sub.id not in scope_vars:
                    scope_vars.append(sub.id)
            if len(scope_vars) < 2:
                continue
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call) and len(sub.args) >= 2:
                    if hot_lines and getattr(sub, "lineno", 0) not in hot_lines:
                        continue
                    arg_names = [a.id if isinstance(a, ast.Name) else None for a in sub.args]
                    # Prioritize calls inside `raise ...` or calls with repeated arg names `(g, g, ...)`
                    has_dup = len([x for x in arg_names if x is not None]) != len({x for x in arg_names if x is not None})
                    func_src = ast.get_source_segment(src, sub.func) or ""
                    is_exc_like = bool(func_src and func_src[0].isupper())
                    if not (has_dup or is_exc_like):
                        continue
                    for idx_a, arg_node in enumerate(sub.args):
                        if not isinstance(arg_node, ast.Name):
                            continue
                        for cand_var in scope_vars[:8]:
                            if cand_var == arg_node.id:
                                continue
                            patched = _replace_node_segment(src, arg_node, cand_var)
                            if patched:
                                emit(
                                    "M6_scope_arg_substitution",
                                    rel_file,
                                    src,
                                    patched,
                                    f"{fn.name}: arg[{idx_a}] {arg_node.id} -> {cand_var} in {func_src}(...)",
                                )

    @classmethod
    def _law_m7_predicate_and_boundary_duals(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
    ) -> None:
        """Law M7: Tightly scoped comparison boundary & `not x` vs `x is None` truthiness duals on hot lines."""
        if not hot_lines:
            return
        op_duals = {
            ast.Lt: "<=",
            ast.LtE: "<",
            ast.Gt: ">=",
            ast.GtE: ">",
        }
        for node in ast.walk(tree):
            if getattr(node, "lineno", 0) not in hot_lines:
                continue
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in op_duals:
                left_s = ast.get_source_segment(src, node.left)
                right_s = ast.get_source_segment(src, node.comparators[0])
                if left_s and right_s:
                    new_cmp = f"{left_s} {op_duals[type(node.ops[0])]} {right_s}"
                    patched = _replace_node_segment(src, node, new_cmp)
                    if patched:
                        emit("M7_boundary_cmp_dual", rel_file, src, patched, f"boundary {new_cmp}")
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and isinstance(node.operand, ast.Name):
                patched = _replace_node_segment(src, node, f"{node.operand.id} is None")
                if patched:
                    emit("M7_none_vs_falsy_dual", rel_file, src, patched, f"not {node.operand.id} -> {node.operand.id} is None")

    @classmethod
    def _law_m8_classmethod_and_copy_polymorphism(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
    ) -> None:
        """Law M8: Liskov `@classmethod` `ClassName(...) -> cls(...)` & `type(self)` copy polymorphism."""
        for cls_node in ast.walk(tree):
            if not isinstance(cls_node, ast.ClassDef):
                continue
            cname = cls_node.name
            for item in cls_node.body:
                if not isinstance(item, ast.FunctionDef) or not item.args.args:
                    continue
                decs = [ast.unparse(d) for d in item.decorator_list]
                first_p = item.args.args[0].arg
                if "classmethod" in decs:
                    for sub in ast.walk(item):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == cname:
                            patched = _replace_node_segment(src, sub.func, first_p)
                            if patched:
                                emit(
                                    "M8a_classmethod_cls_polymorphism",
                                    rel_file,
                                    src,
                                    patched,
                                    f"{cname}.{item.name}: {cname}(...) -> {first_p}(...) for subclass round-trip",
                                )
                elif item.name in ("__copy__", "__deepcopy__", "copy"):
                    for sub in ast.walk(item):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == cname:
                            patched = _replace_node_segment(src, sub.func, f"type({first_p})")
                            if patched:
                                emit(
                                    "M8b_copy_type_self_polymorphism",
                                    rel_file,
                                    src,
                                    patched,
                                    f"{cname}.{item.name}: {cname}(...) -> type({first_p})(...)",
                                )

    @classmethod
    def _law_m9_pep681_copy_replace_and_pickle_state(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
        raw_output: str = "",
    ) -> None:
        """Law M9: PEP 681 `copy.replace` (`__replace__`) synthesis & legacy `__setstate__` dict upgrade."""
        lines = src.splitlines(keepends=True)
        out_low = raw_output.lower()
        wants_replace = "__replace__" in raw_output or "copy.replace" in out_low
        wants_pickle = "pickle" in out_low or "__setstate__" in raw_output or "__getstate__" in raw_output

        for cls_node in tree.body:
            if not isinstance(cls_node, ast.ClassDef):
                continue
            existing_methods = {n.name: n for n in cls_node.body if isinstance(n, ast.FunctionDef)}
            cls_end = getattr(cls_node, "end_lineno", cls_node.lineno)
            body_indent = " " * (cls_node.col_offset + 4)
            for item in cls_node.body:
                if hasattr(item, "col_offset"):
                    body_indent = " " * item.col_offset
                    break

            if wants_replace and "__replace__" not in existing_methods:
                # Extract known instance attributes from `__init__` / `__setstate__` / `AnnAssign`
                pub_attrs: list[str] = []
                priv_attrs: list[str] = []
                for m_scan in cls_node.body:
                    if isinstance(m_scan, ast.AnnAssign) and isinstance(m_scan.target, ast.Name):
                        nm = m_scan.target.id
                        if not nm.startswith("_") and nm not in pub_attrs:
                            pub_attrs.append(nm)
                    elif isinstance(m_scan, ast.FunctionDef) and m_scan.name in ("__init__", "__setstate__"):
                        for sub_a in ast.walk(m_scan):
                            attr_targets: list[ast.AST] = []
                            if isinstance(sub_a, ast.Assign):
                                attr_targets.extend(sub_a.targets)
                            elif isinstance(sub_a, ast.AnnAssign):
                                attr_targets.append(sub_a.target)
                            for t_a in attr_targets:
                                if isinstance(t_a, ast.Attribute) and isinstance(t_a.value, ast.Name) and t_a.value.id == "self":
                                    nm = t_a.attr
                                    if nm.startswith("_"):
                                        if nm not in priv_attrs:
                                            priv_attrs.append(nm)
                                    elif nm not in pub_attrs:
                                        pub_attrs.append(nm)
                if pub_attrs:
                    pub_tup = repr(tuple(pub_attrs))
                    priv_tup = repr(tuple(priv_attrs))
                    rep_obj_new = (
                        f"\n{body_indent}def __replace__(self, **changes):\n"
                        f"{body_indent}    import copy as _copy\n"
                        f"{body_indent}    _allowed = {pub_tup}\n"
                        f"{body_indent}    _priv = {priv_tup}\n"
                        f"{body_indent}    for _k in changes:\n"
                        f"{body_indent}        if _k not in _allowed:\n"
                        f"{body_indent}            raise TypeError(f\"{{type(self).__name__}}.__replace__() got an unexpected keyword argument {{_k!r}}\")\n"
                        f"{body_indent}    _new = object.__new__(type(self))\n"
                        f"{body_indent}    for _dk, _dv in getattr(self, '__dict__', {{}}).items():\n"
                        f"{body_indent}        if _dk not in _allowed and _dk not in _priv:\n"
                        f"{body_indent}            object.__setattr__(_new, _dk, _copy.deepcopy(_dv))\n"
                        f"{body_indent}    for _k in _allowed:\n"
                        f"{body_indent}        _val = changes[_k] if _k in changes else getattr(self, _k)\n"
                        f"{body_indent}        object.__setattr__(_new, _k, _copy.deepcopy(_val))\n"
                        f"{body_indent}    for _pk in _priv:\n"
                        f"{body_indent}        if hasattr(self, _pk):\n"
                        f"{body_indent}            object.__setattr__(_new, _pk, _copy.deepcopy(getattr(self, _pk)))\n"
                        f"{body_indent}    return _new\n"
                    )
                    patched_obj_new = "".join(lines[:cls_end]) + rep_obj_new + "".join(lines[cls_end:])
                    emit(
                        "M9a_pep681_field_copy_replace",
                        rel_file,
                        src,
                        patched_obj_new,
                        f"{cls_node.name}: implement field-cloning PEP 681 __replace__(self, **changes)",
                    )
                # Also emit constructor-revalidating `__replace__` when `__init__` accepts >= 2 named parameters
                init_fn = existing_methods.get("__init__")
                if init_fn is not None:
                    init_params = [
                        a.arg for a in (*init_fn.args.args, *init_fn.args.kwonlyargs) if a.arg not in ("self", "cls")
                    ]
                    if len(init_params) >= 2:
                        p_tuple = ", ".join(repr(p) for p in init_params)
                        rep_ctor = (
                            f"\n{body_indent}def __replace__(self, **changes):\n"
                            f"{body_indent}    _allowed = ({p_tuple},)\n"
                            f"{body_indent}    for _k in changes:\n"
                            f"{body_indent}        if _k not in _allowed:\n"
                            f"{body_indent}            raise TypeError(f\"{{type(self).__name__}}.__replace__() got an unexpected keyword argument {{_k!r}}\")\n"
                            f"{body_indent}    return type(self)(**{{_p: changes.get(_p, getattr(self, _p)) for _p in _allowed}})\n"
                        )
                        patched_ctor = "".join(lines[:cls_end]) + rep_ctor + "".join(lines[cls_end:])
                        emit(
                            "M9a_pep681_ctor_replace_protocol",
                            rel_file,
                            src,
                            patched_ctor,
                            f"{cls_node.name}: implement constructor-validating __replace__",
                        )
                    elif len(init_params) == 1 and "__str__" in existing_methods and pub_attrs:
                        # Codec Isomorphism + PutGet Lens Law (`parse ∘ __str__`):
                        # Single-arg parser class with canonical `__str__`
                        pub_tup = repr(tuple(pub_attrs))
                        priv_tup = repr(tuple(priv_attrs))
                        cls_nm = cls_node.name
                        exc_names = [
                            st_e.name for st_e in tree.body
                            if isinstance(st_e, ast.ClassDef) and ("Invalid" in st_e.name or st_e.name.endswith("Error"))
                        ]
                        dom_exc = exc_names[0] if exc_names else "ValueError"
                        rep_codec = (
                            f"\n{body_indent}def __replace__(self, **changes):\n"
                            f"{body_indent}    import copy as _copy\n"
                            f"{body_indent}    _allowed = {pub_tup}\n"
                            f"{body_indent}    _priv = {priv_tup}\n"
                            f"{body_indent}    for _k in changes:\n"
                            f"{body_indent}        if _k not in _allowed:\n"
                            f"{body_indent}            raise TypeError(f\"{{type(self).__name__}}.__replace__() got an unexpected keyword argument {{_k!r}}\")\n"
                            f"{body_indent}    _tmp = object.__new__({cls_nm})\n"
                            f"{body_indent}    for _k in _allowed:\n"
                            f"{body_indent}        object.__setattr__(_tmp, _k, changes[_k] if _k in changes else getattr(self, _k))\n"
                            f"{body_indent}    _parsed = {cls_nm}({cls_nm}.__str__(_tmp))\n"
                            f"{body_indent}    for _ok in _allowed:\n"
                            f"{body_indent}        if _ok not in changes and getattr(_parsed, _ok) != getattr(self, _ok):\n"
                            f"{body_indent}            raise {dom_exc}(f\"Field smuggling across {{_ok}} during __replace__\")\n"
                            f"{body_indent}    for _k, _cv in changes.items():\n"
                            f"{body_indent}        _pv_chk = getattr(_parsed, _k)\n"
                            f"{body_indent}        if _cv is not None and _pv_chk is None:\n"
                            f"{body_indent}            raise {dom_exc}(f\"Invalid {{_k}}: {{_cv!r}}\")\n"
                            f"{body_indent}        if isinstance(_cv, (set, frozenset, list, tuple)) and isinstance(_pv_chk, (set, frozenset)):\n"
                            f"{body_indent}            if len({{str(_x).lower().replace('_', '-') for _x in _cv}}) != len(_pv_chk):\n"
                            f"{body_indent}                raise {dom_exc}(f\"Invalid collection element in {{_k}}: {{_cv!r}}\")\n"
                            f"{body_indent}    _out = object.__new__(type(self))\n"
                            f"{body_indent}    for _dk, _dv in getattr(self, '__dict__', {{}}).items():\n"
                            f"{body_indent}        if _dk not in _allowed and _dk not in _priv:\n"
                            f"{body_indent}            object.__setattr__(_out, _dk, _copy.deepcopy(_dv))\n"
                            f"{body_indent}    for _k in _allowed:\n"
                            f"{body_indent}        _pv = getattr(_parsed, _k)\n"
                            f"{body_indent}        _src_v = changes[_k] if _k in changes else getattr(self, _k)\n"
                            f"{body_indent}        if _src_v is not None and not isinstance(_src_v, (str, bytes, int, float, bool, set, frozenset, tuple, list, dict)) and type(_src_v) is type(_pv) and str(_src_v) == str(_pv):\n"
                            f"{body_indent}            object.__setattr__(_out, _k, _copy.deepcopy(_src_v))\n"
                            f"{body_indent}        else:\n"
                            f"{body_indent}            object.__setattr__(_out, _k, _pv)\n"
                            f"{body_indent}    for _pk in _priv:\n"
                            f"{body_indent}        if hasattr(_parsed, _pk):\n"
                            f"{body_indent}            object.__setattr__(_out, _pk, getattr(_parsed, _pk))\n"
                            f"{body_indent}    return _out\n"
                        )
                        patched_codec = "".join(lines[:cls_end]) + rep_codec + "".join(lines[cls_end:])
                        emit(
                            "M9a_pep681_codec_roundtrip_replace",
                            rel_file,
                            src,
                            patched_codec,
                            f"{cls_nm}: implement parse-unparse codec-validating PEP 681 __replace__",
                        )

            if wants_pickle:
                # Sub-law M9b: Plain `__slots__` class lacking `__setstate__`
                has_slots = any(
                    isinstance(st, ast.Assign) and any(isinstance(t_n, ast.Name) and t_n.id == "__slots__" for t_n in st.targets)
                    for st in cls_node.body
                )
                is_dc = any("dataclass" in ast.unparse(d) for d in cls_node.decorator_list)
                if "__setstate__" not in existing_methods and has_slots and not is_dc:
                    setstate_m = (
                        f"\n{body_indent}def __setstate__(self, state):\n"
                        f"{body_indent}    _d = state[1] if (isinstance(state, tuple) and len(state) == 2 and isinstance(state[1], dict)) else state\n"
                        f"{body_indent}    if not isinstance(_d, dict):\n"
                        f"{body_indent}        raise TypeError(f\"Invalid pickle state for {{type(self).__name__}}\")\n"
                        f"{body_indent}    for _k, _v in _d.items():\n"
                        f"{body_indent}        object.__setattr__(self, _k, _v)\n"
                    )
                    patched_ss = "".join(lines[:cls_end]) + setstate_m + "".join(lines[cls_end:])
                    emit(
                        "M9b_legacy_dict_setstate",
                        rel_file,
                        src,
                        patched_ss,
                        f"{cls_node.name}: support legacy dict state in __setstate__",
                    )

        # Module-wide `@dataclass(..., slots=True)` post-decorator `__setstate__` installer
        # (CPython `dataclasses._add_slots` overwrites any in-body `def __setstate__`!)
        if wants_pickle:
            dc_slot_classes = [
                cn.name
                for cn in tree.body
                if isinstance(cn, ast.ClassDef)
                and any("dataclass" in ast.unparse(d) and "slots=True" in ast.unparse(d) for d in cn.decorator_list)
            ]
            if dc_slot_classes:
                cls_tuple_s = ", ".join(dc_slot_classes)
                trailer = (
                    "\n\ndef _install_legacy_dict_setstate(_cls):\n"
                    "    _orig_ss = getattr(_cls, '__setstate__', None)\n"
                    "    _fnames = tuple(_f.name for _f in dataclasses.fields(_cls))\n"
                    "    _fset = frozenset(_fnames)\n"
                    "    def __setstate__(self, state):\n"
                    "        if isinstance(state, dict):\n"
                    "            if set(state.keys()) != _fset:\n"
                    "                raise TypeError(f'Invalid pickle state keys for {type(self).__name__}')\n"
                    "            _tmp = type(self)(**state)\n"
                    "            for _fn in _fnames:\n"
                    "                object.__setattr__(self, _fn, getattr(_tmp, _fn))\n"
                    "            return\n"
                    "        if isinstance(state, tuple) and len(state) == 2 and state[0] is None and isinstance(state[1], dict):\n"
                    "            if set(state[1].keys()) != _fset:\n"
                    "                raise TypeError(f'Invalid pickle state keys for {type(self).__name__}')\n"
                    "            _tmp = type(self)(**state[1])\n"
                    "            for _fn in _fnames:\n"
                    "                object.__setattr__(self, _fn, getattr(_tmp, _fn))\n"
                    "            return\n"
                    "        if _orig_ss is not None:\n"
                    "            return _orig_ss(self, state)\n"
                    "        raise TypeError(f'Invalid state for {type(self).__name__}')\n"
                    "    _cls.__setstate__ = __setstate__\n\n"
                    f"for _dc_c in ({cls_tuple_s},):\n"
                    "    _install_legacy_dict_setstate(_dc_c)\n"
                )
                emit(
                    "M9b_dataclass_slots_legacy_dict_setstate",
                    rel_file,
                    src,
                    src.rstrip() + trailer,
                    f"post-dataclass slots legacy dict __setstate__ on ({cls_tuple_s})",
                )

    @classmethod
    def _law_m10_unknown_keys_callback_and_str_cache(
        cls,
        rel_file: str,
        src: str,
        tree: ast.Module,
        hot_lines: set[int],
        emit: Callable[[str, str, str, str, str], None],
        raw_output: str = "",
    ) -> None:
        """Law M10: Callback scalar-return contract, unknown set-key validation, & `__str__` identity cache."""
        # Sub-law M10a: Parser callback (`parse_float` / `parse_int`) returning illegal mutable container (`dict`/`list`)
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or not fn.body:
                continue
            fn_params = [
                a.arg for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)
                if a.arg not in ("self", "cls") and any(tok in a.arg.lower() for tok in ("parse_", "hook", "conv", "loader"))
            ]
            if not fn_params:
                continue
            # Entry-point wrapper: guards ALL call sites (`inf`, `nan`, `match_to_number`, etc.) in one place!
            first_stmt = fn.body[1] if (
                len(fn.body) >= 2
                and isinstance(fn.body[0], ast.Expr)
                and isinstance(fn.body[0].value, ast.Constant)
                and isinstance(fn.body[0].value.value, str)
            ) else fn.body[0]
            stmt_seg = ast.get_source_segment(src, first_stmt)
            if stmt_seg and len(fn.body) >= 2:
                ind_f = " " * first_stmt.col_offset
                p0 = fn_params[0]
                wrap_code = (
                    f"_orig_{p0} = {p0}\n"
                    f"{ind_f}def _checked_{p0}(_s):\n"
                    f"{ind_f}    _res = _orig_{p0}(_s)\n"
                    f"{ind_f}    if isinstance(_res, (dict, list)):\n"
                    f"{ind_f}        raise ValueError('{p0} must not return dicts or lists')\n"
                    f"{ind_f}    return _res\n"
                    f"{ind_f}{p0} = _checked_{p0}\n"
                    f"{ind_f}{stmt_seg}"
                )
                patched_wrap = _replace_node_segment(src, first_stmt, wrap_code)
                if patched_wrap:
                    emit(
                        "M10a_callback_entry_wrapper_guard",
                        rel_file,
                        src,
                        patched_wrap,
                        f"{fn.name}: wrap {p0} at entry to reject (dict, list) return values",
                    )
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Call) and isinstance(sub.value.func, ast.Name) and sub.value.func.id in fn_params:
                    cb_n = sub.value.func.id
                    call_s = ast.get_source_segment(src, sub.value)
                    if call_s:
                        ind = " " * sub.col_offset
                        guarded_ret = (
                            f"_cb_val = {call_s}\n"
                            f"{ind}if isinstance(_cb_val, (dict, list)):\n"
                            f"{ind}    raise ValueError('{cb_n} must not return dicts or lists')\n"
                            f"{ind}return _cb_val"
                        )
                        patched = _replace_node_segment(src, sub, guarded_ret)
                        if patched:
                            emit(
                                "M10a_callback_container_return_guard",
                                rel_file,
                                src,
                                patched,
                                f"{fn.name}: forbid mutable (dict, list) return from callback {cb_n}",
                            )

        # Sub-law M10b: `__str__` identity memoization when test asserts string object reuse (`is`)
        if " is " in raw_output or "reuses" in raw_output.lower():
            for cls_node in tree.body:
                if not isinstance(cls_node, ast.ClassDef):
                    continue
                slots_assign: ast.Assign | None = None
                slot_elts: list[str] = []
                for st in cls_node.body:
                    if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__slots__" for t in st.targets):
                        slots_assign = st
                        if isinstance(st.value, (ast.Tuple, ast.List)):
                            slot_elts = [e.value for e in st.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                        break
                for item in cls_node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__str__" and len(item.body) >= 1:
                        last_st = item.body[-1]
                        is_pure_ret = isinstance(last_st, ast.Return) and last_st.value is not None and (
                            len(item.body) == 1
                            or (
                                len(item.body) == 2
                                and isinstance(item.body[0], ast.Expr)
                                and isinstance(item.body[0].value, ast.Constant)
                            )
                        )
                        if is_pure_ret:
                            ret_expr = ast.get_source_segment(src, last_st.value)
                            if ret_expr and "_str_cache" not in ret_expr:
                                ind = " " * last_st.col_offset
                                cached_body = (
                                    f"_cached = getattr(self, '_str_cache', None)\n"
                                    f"{ind}if _cached is None:\n"
                                    f"{ind}    _cached = {ret_expr}\n"
                                    f"{ind}    object.__setattr__(self, '_str_cache', _cached)\n"
                                    f"{ind}return _cached"
                                )
                                base_src = src
                                if slots_assign is not None:
                                    if not slot_elts or "_str_cache" in slot_elts:
                                        continue
                                    new_slots = "__slots__ = (" + ", ".join(repr(s_e) for s_e in (*slot_elts, "_str_cache")) + ",)"
                                    upd_slots = _replace_node_segment(src, slots_assign, new_slots)
                                    if not upd_slots:
                                        continue
                                    t2 = ast.parse(upd_slots)
                                    c2 = next((n for n in t2.body if isinstance(n, ast.ClassDef) and n.name == cls_node.name), None)
                                    m2 = next((m for m in (c2.body if c2 else ()) if isinstance(m, ast.FunctionDef) and m.name == "__str__"), None)
                                    if m2 is None:
                                        continue
                                    patched = _replace_node_segment(upd_slots, m2.body[-1], cached_body)
                                else:
                                    patched = _replace_node_segment(base_src, last_st, cached_body)
                                # Cache-coherence invariant: invalidate `_str_cache` on `__init__` and `__setstate__`!
                                if patched:
                                    for _mut_m in ("__init__", "__setstate__"):
                                        t3 = ast.parse(patched)
                                        c3 = next((n for n in t3.body if isinstance(n, ast.ClassDef) and n.name == cls_node.name), None)
                                        ss3 = next((m for m in (c3.body if c3 else ()) if isinstance(m, ast.FunctionDef) and m.name == _mut_m and m.body), None)
                                        if ss3 is not None:
                                            ss_stmt0 = ss3.body[1] if (
                                                len(ss3.body) >= 2
                                                and isinstance(ss3.body[0], ast.Expr)
                                                and isinstance(ss3.body[0].value, ast.Constant)
                                            ) else ss3.body[0]
                                            ss_seg0 = ast.get_source_segment(patched, ss_stmt0)
                                            if ss_seg0:
                                                ss_ind = " " * ss_stmt0.col_offset
                                                patched_inv = _replace_node_segment(
                                                    patched,
                                                    ss_stmt0,
                                                    f"object.__setattr__(self, '_str_cache', None)\n{ss_ind}{ss_seg0}",
                                                )
                                                if patched_inv:
                                                    patched = patched_inv
                                if patched:
                                    emit(
                                        "M10b_str_identity_memoization",
                                        rel_file,
                                        src,
                                        patched,
                                        f"{cls_node.name}.__str__: memoize rendered string instance",
                                    )


# ---------------------------------------------------------------------------
# 6. WHOLE-SLICE MUTANT-KILLING & SEPARATING-WITNESS GATE (`STING` / `ACH` / MDL)
# ---------------------------------------------------------------------------


class WholeSliceMutantKillingGate:
    """Enforces zero-false-positive verification across the FULL enclosing test file
    using zero-copy in-RAM CoW forks (`run_test_targets_fast`), and breaks ties among
    multiple surviving patches via `repair_version_space_selection_v1` maximum-elimination
    probes, `metamorphic_laws_v1`, docstring guides, and MDL (`compression_gain_v1`).
    """

    @classmethod
    def select_verified_winner(
        cls,
        repo_dir: pathlib.Path,
        requested_targets: Sequence[str],
        baseline_enclosing_failures: frozenset[str] | None,
        candidates: Sequence[CandidatePatch],
        *,
        timeout_per_check_s: float = 16.0,
        budget_s: float = 20.0,
    ) -> tuple[CandidatePatch | None, dict[str, Any]]:
        t0 = time.perf_counter()
        repo_abs = repo_dir.resolve()
        enc_files = enclosing_test_files(repo_abs, requested_targets)
        verified: list[tuple[CandidatePatch, dict[str, Any]]] = []
        rejected_overfits = 0
        lazy_baseline_failures: frozenset[str] | None = baseline_enclosing_failures
        rel_to_mod = build_rel_to_module_map(repo_abs)

        def _cand_overrides(patched_files: Mapping[str, str]) -> dict[str, tuple[str, str, bool]] | None:
            out_ov: dict[str, tuple[str, str, bool]] = {}
            for rp, cs in patched_files.items():
                info = rel_to_mod.get(rp.replace("\\", "/").lstrip("/"))
                if info is None:
                    return None
                out_ov[info[0]] = (info[1], cs, info[2])
            return out_ov if out_ov else None

        tmp_ctx: tempfile.TemporaryDirectory[str] | None = None
        try:
            for idx, cand in enumerate(candidates):
                if (time.perf_counter() - t0) >= budget_s and verified:
                    break
                mod_ov = _cand_overrides(cand.patched_files)
                overlay: pathlib.Path | None = None
                if mod_ov is None:
                    if tmp_ctx is None:
                        tmp_ctx = tempfile.TemporaryDirectory(prefix="brain_whole_slice_")
                    overlay = create_hardlinked_overlay(repo_abs, pathlib.Path(tmp_ctx.name), f"verify_{idx}")
                    write_unlinked_patch(overlay, cand.patched_files)

                def _exec_targets(t_list: Sequence[str], t_out: float, verb: bool, mfail: int = 0) -> dict[str, Any]:
                    if mod_ov is not None:
                        return run_test_targets_fast(
                            repo_abs, t_list, timeout_s=t_out, verbose=verb, module_overrides=mod_ov, maxfail=mfail
                        )
                    return run_test_targets_fast(overlay, t_list, timeout_s=t_out, verbose=verb, maxfail=mfail)  # type: ignore[arg-type]

                # Step 1: Exact requested targets MUST pass 100% (skip duplicate run if `requested_targets == enc_files`)
                same_as_enc = bool(enc_files) and list(requested_targets) == list(enc_files)
                req_res: dict[str, Any] | None = None
                if not same_as_enc:
                    req_res = _exec_targets(requested_targets, min(10.0, timeout_per_check_s), False, mfail=1)
                    if req_res["returncode"] != 0:
                        rejected_overfits += 1
                        continue

                # Step 2: Entire enclosing test files MUST have 0 newly broken tests & resolve requested targets!
                if enc_files:
                    enc_res = _exec_targets(enc_files, max(12.0, timeout_per_check_s), True, mfail=(1 if same_as_enc else 0))
                    if enc_res["returncode"] == 0 and enc_res["passed"] > 0 and enc_res["failed"] == 0 and enc_res["errors"] == 0:
                        verified.append((cand, enc_res))
                        if len(verified) >= 3:
                            break
                        continue
                    if same_as_enc:
                        rejected_overfits += 1
                        continue
                    # Lazily compute baseline enclosing failures ONLY if a candidate actually had sibling failures
                    if lazy_baseline_failures is None:
                        base_enc = run_test_targets_fast(
                            repo_abs, enc_files, timeout_s=max(12.0, timeout_per_check_s), verbose=True
                        )
                        lazy_baseline_failures = frozenset(base_enc["failing_nodes"]) if base_enc["status"] != "TIMEOUT" else frozenset()
                    post_fail_set = frozenset(enc_res["failing_nodes"])
                    req_set = frozenset(requested_targets)
                    newly_broken = post_fail_set - lazy_baseline_failures
                    req_still_failing = post_fail_set & req_set
                    if (
                        enc_res["passed"] > 0
                        and enc_res["errors"] == 0
                        and len(newly_broken) == 0
                        and len(req_still_failing) == 0
                        and post_fail_set < lazy_baseline_failures
                    ):
                        verified.append((cand, enc_res))
                    else:
                        rejected_overfits += 1
                elif req_res is not None:
                    verified.append((cand, req_res))
        finally:
            if tmp_ctx is not None:
                tmp_ctx.cleanup()

        if not verified:
            return None, {
                "verified_candidates": 0,
                "rejected_single_node_overfits": rejected_overfits,
                "enclosing_files_checked": enc_files,
            }

        if len(verified) == 1:
            winner, run_meta = verified[0]
            return winner, {
                "verified_candidates": 1,
                "rejected_single_node_overfits": rejected_overfits,
                "enclosing_files_checked": enc_files,
                "enclosing_passed": run_meta.get("passed", 0),
                "tie_breaker": "unique_whole_slice_survivor",
            }

        # Step 3: Multiple candidates survived full enclosing suite!
        winner, tie_meta = cls._break_ties_mdl_and_probes(repo_abs, verified)
        return winner, {
            "verified_candidates": len(verified),
            "rejected_single_node_overfits": rejected_overfits,
            "enclosing_files_checked": enc_files,
            "enclosing_passed": tie_meta.get("enclosing_passed", 0),
            "tie_breaker": tie_meta.get("tie_breaker", "mdl_description_bytes"),
            "behaviour_clusters": tie_meta.get("behaviour_clusters", 1),
            "version_space_diagnosis": tie_meta.get("version_space_diagnosis"),
            "discriminating_probe": tie_meta.get("discriminating_probe"),
        }

    @classmethod
    def _break_ties_mdl_and_probes(
        cls,
        repo_dir: pathlib.Path,
        verified: Sequence[tuple[CandidatePatch, dict[str, Any]]],
    ) -> tuple[CandidatePatch, dict[str, Any]]:
        """Partition surviving patches via `repair_version_space_selection_v1`, check
        `metamorphic_laws_v1` canonicality & docstring guides, and prefer minimal MDL delta.
        """
        clusters = 1
        vs_diag: str | None = None
        best_probe: str | None = None
        law_violations_by_id: dict[str, int] = {}
        try:
            from canonical.swe_kernel import metamorphic_laws_v1 as mlaws
            from canonical.swe_kernel import repair_version_space_selection_v1 as rvss
            from canonical.tools import the_guide_is_a_test_suite_v1 as guide_ts

            c_ids = [cand.patch_id for cand, _ in verified]
            behaviours: dict[str, list[str]] = {}
            probe_ids = ["ast_canonical_sig", "docstring_guide_sig"]
            for cand, _ in verified:
                norm_sig = "|".join(
                    f"{rf}:{hashlib.sha256(EStitchSemanticSkillStore.canonicalize_snippet(rc).encode('utf-8')).hexdigest()[:12]}"
                    for rf, rc in sorted(cand.patched_files.items())
                )
                doc_count = 0
                law_v = 0
                for rf, rc in cand.patched_files.items():
                    law_v += len(mlaws.check_canonicality(rf, rc.splitlines()[0] if rc else ""))
                    orig_fp = repo_dir / rf
                    if orig_fp.is_file():
                        try:
                            doc_count += len(guide_ts.docstring_blocks(orig_fp))
                        except Exception:
                            pass
                law_violations_by_id[cand.patch_id] = law_v
                behaviours[cand.patch_id] = [f"value:{norm_sig}", f"value:docs={doc_count}:v={law_v}"]

            part = rvss.partition(c_ids, behaviours)
            clusters = int(part.get("distinct") or 1)
            diag_doc = rvss.diagnose(part)
            vs_diag = str(diag_doc.get("diagnosis") or diag_doc.get("status") or "")
            if clusters >= 2:
                probe_outcomes = {
                    pid: [behaviours[cid][p_idx] for cid in c_ids]
                    for p_idx, pid in enumerate(probe_ids)
                }
                best_probe = rvss.maximum_elimination(
                    part,
                    behaviours[c_ids[0]][0],
                    probe_ids=probe_ids,
                    probe_outcomes=probe_outcomes,
                )
        except Exception:
            clusters = len(verified)

        # Structural specification law bonus (`specification_from_structure_v1`)
        struct_law_count_by_id: dict[str, int] = {}
        try:
            from canonical.swe_kernel import specification_from_structure_v1 as sfs

            for cand, _ in verified:
                s_cnt = 0
                for rf, rc in cand.patched_files.items():
                    if rf.endswith(".py"):
                        d_spec = sfs.derive(rc, pathlib.Path(rf).stem)
                        s_cnt += len(d_spec.get("laws") or d_spec.get("proposals") or ())
                struct_law_count_by_id[cand.patch_id] = s_cnt
        except Exception:
            pass

        ranked = sorted(
            verified,
            key=lambda pair: (
                law_violations_by_id.get(pair[0].patch_id, 0),
                abs(pair[0].mdl_delta_bytes),
                pair[0].mdl_delta_bytes,
                len(pair[0].patched_files),
                -struct_law_count_by_id.get(pair[0].patch_id, 0),
                pair[0].patch_id,
            ),
        )
        best_cand, best_run = ranked[0]
        return best_cand, {
            "enclosing_passed": best_run.get("passed", 0),
            "tie_breaker": "repair_version_space_plus_metamorphic_laws_plus_mdl",
            "behaviour_clusters": clusters,
            "version_space_diagnosis": vs_diag,
            "discriminating_probe": best_probe,
        }


def verify_patch_uncheatable(
    workspace_dir: pathlib.Path | str,
    patched_files: Mapping[str, str],
    pytest_targets: Sequence[str],
    *,
    max_mutants: int = 8,
    min_kill_ratio: float = 1.0,
    timeout_s: float = 12.0,
) -> dict[str, Any]:
    """Uncheatable Behavioural Mutation & Structural Specification Gate (`K3 = 0`).

    Defends against weak-oracle / dead-code / stubbed patches (`STING` / `UTBoost` / `All Smoke, No Alarm`)
    by verifying:
      1. Full enclosing test suite passes on `patched_files` (`WholeSliceMutantKillingGate`),
      2. Changed executable lines in `patched_files` generate AST byte-span mutants via
         `python_review_diff_mutation_gate` and every sampled mutant is KILLED (fails tests)
         in `WarmCoWForkScreener` (`kill_ratio >= min_kill_ratio`),
      3. Zero-test structural specification laws (`specification_from_structure_v1.derive`)
         and behavioural equivalence classes (`evidence_demand_v1.group_by_behaviour`).
    """
    t0 = time.perf_counter()
    ws = pathlib.Path(workspace_dir).resolve()
    cand = CandidatePatch(
        patch_id="audit_patch",
        family="audit",
        patched_files=dict(patched_files),
        description="patch under uncheatable behavioural mutation audit",
    )
    winner, gate_meta = WholeSliceMutantKillingGate.select_verified_winner(
        ws,
        pytest_targets,
        None,
        [cand],
        timeout_per_check_s=min(12.0, timeout_s),
        budget_s=timeout_s,
    )
    if winner is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__BASE_SUITE_OR_WHOLE_SLICE_FAILED",
            "pass": False,
            "whole_slice_verified": False,
            "mutants_generated": 0,
            "mutants_killed": 0,
            "kill_ratio": 0.0,
            "surviving_mutants": [],
            "gate_telemetry": gate_meta,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # Generate AST mutants strictly on changed lines via `python_review_diff_mutation_gate`
    from canonical.runtime.bound_capabilities import python_review_diff_mutation_gate as mut_gate

    mutant_cands: list[CandidatePatch] = []
    mutant_meta: dict[str, dict[str, Any]] = {}
    structural_laws: list[dict[str, Any]] = []
    for rel_p, new_txt in patched_files.items():
        if not rel_p.endswith(".py"):
            continue
        orig_fp = ws / rel_p
        old_txt = orig_fp.read_text(encoding="utf-8", errors="replace") if orig_fp.is_file() else ""
        old_lines = set(old_txt.splitlines())
        changed_line_nos = {
            idx_l
            for idx_l, ln in enumerate(new_txt.splitlines(), start=1)
            if ln.strip() and not ln.lstrip().startswith("#") and ln not in old_lines
        }
        if not changed_line_nos and new_txt.strip():
            changed_line_nos = {
                idx_l
                for idx_l, ln in enumerate(new_txt.splitlines(), start=1)
                if ln.strip() and not ln.lstrip().startswith(("def ", "class ", "#", "@", "import ", "from "))
            }
        try:
            sites = mut_gate._mutants_for_text(rel_p, new_txt, changed_line_nos, max_mutants)
            for s_i, site in enumerate(sites[:max_mutants]):
                if len(mutant_cands) >= max_mutants:
                    break
                mut_txt = mut_gate._apply_splice(new_txt, rel_p, site)
                ast.parse(mut_txt)
                if mut_txt != new_txt:
                    mid = f"mut_{len(mutant_cands)}"
                    mut_files = dict(patched_files)
                    mut_files[rel_p] = mut_txt
                    mutant_cands.append(CandidatePatch(patch_id=mid, family=site.kind, patched_files=mut_files))
                    mutant_meta[mid] = site.row(rel_p)
        except BaseException:
            pass
        try:
            from canonical.swe_kernel import specification_from_structure_v1 as sfs

            derived_doc = sfs.derive(new_txt, pathlib.Path(rel_p).stem)
            structural_laws.append(
                {
                    "file": rel_p,
                    "functions": len(derived_doc.get("functions") or ()),
                    "proposed_laws": [
                        str(lw.get("kind") or lw.get("law") or "")
                        for lw in (derived_doc.get("laws") or derived_doc.get("proposals") or ())[:8]
                        if isinstance(lw, Mapping)
                    ],
                }
            )
        except Exception:
            pass

    if not mutant_cands:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__NO_MUTABLE_CHANGED_SITES",
            "pass": False,
            "whole_slice_verified": True,
            "mutants_generated": 0,
            "mutants_killed": 0,
            "kill_ratio": 0.0,
            "surviving_mutants": [],
            "structural_laws": structural_laws,
            "gate_telemetry": gate_meta,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    screener = WarmCoWForkScreener(ws, pytest_targets, per_candidate_timeout_s=min(3.0, timeout_s * 0.4))
    # Any mutant that PASSES `pytest_targets` SURVIVED (was NOT killed by the suite!)
    surviving = screener.screen_batch(mutant_cands, budget_s=max(2.0, timeout_s * 0.6))
    surviving_ids = {mc.patch_id for mc in surviving}
    total_m = len(mutant_cands)
    killed_m = total_m - len(surviving_ids)
    kill_ratio = round(float(killed_m) / float(max(1, total_m)), 4)
    passed_gate = kill_ratio >= min_kill_ratio
    return {
        "schema": SCHEMA,
        "status": "PASS__UNCHEATABLE_MUTATION_AND_SLICE_VERIFIED" if passed_gate else "FAIL_CLOSED__SURVIVING_DIFF_MUTANTS",
        "pass": passed_gate,
        "whole_slice_verified": True,
        "mutants_generated": total_m,
        "mutants_killed": killed_m,
        "kill_ratio": kill_ratio,
        "surviving_mutants": [mutant_meta[mid] for mid in sorted(surviving_ids) if mid in mutant_meta],
        "structural_laws": structural_laws,
        "gate_telemetry": gate_meta,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


# ---------------------------------------------------------------------------
# 7. SEMANTIC E-GRAPH SKILL STORE (`E-Stitch` ALPHA-NORMALIZED MOTIFS + BI-TEMPORAL)
# ---------------------------------------------------------------------------


class _AlphaNormalizer(ast.NodeTransformer):
    """Canonicalize local variable identifiers into positional `$v0, $v1, ...` slots."""

    _BUILTINS = frozenset(dir(__builtins__)) | {"self", "cls", "True", "False", "None"}

    def __init__(self) -> None:
        self._map: dict[str, str] = {}

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if node.arg in self._BUILTINS:
            return node
        slot = self._map.setdefault(node.arg, f"_v{len(self._map)}")
        return ast.copy_location(ast.arg(arg=slot, annotation=node.annotation, type_comment=node.type_comment), node)

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self._BUILTINS:
            return node
        slot = self._map.setdefault(node.id, f"_v{len(self._map)}")
        return ast.copy_location(ast.Name(id=slot, ctx=node.ctx), node)


@dataclass
class SemanticRepairMotif:
    motif_id: str
    family: str
    before_canonical: str
    after_canonical: str
    scope_digest: str
    t_valid_from: float
    t_invalidated_at: float | None = None
    mdl_gain_bytes: int = 0
    verified_hits: int = 1


class EStitchSemanticSkillStore:
    """Bi-temporal, alpha-normalized AST repair motif memory with MDL/surprise gating
    plus `O(1)` AST-node-kind open operator compilation (`edit_kind_learning_v1`) and
    non-interfering chain composition verification (`composition_verification_v1`).
    """

    def __init__(self, state_path: pathlib.Path | None = None) -> None:
        self.state_path = state_path
        self._motifs: dict[str, SemanticRepairMotif] = {}
        self._open_operators_by_kind: dict[str, list[Any]] = {}
        self._cst_rules: list[dict[str, Any]] = []
        self._induced_templates: list[Any] = []
        if self.state_path and self.state_path.is_file():
            self._load()

    @staticmethod
    def canonicalize_snippet(snippet: str) -> str:
        try:
            tree = ast.parse(snippet)
            norm = _AlphaNormalizer().visit(tree)
            ast.fix_missing_locations(norm)
            return ast.unparse(norm)
        except Exception:
            return snippet.strip()

    def _compile_open_operators(self, before_source: str, after_source: str, *, language: str = "python") -> int:
        """Induce `names_open` AST rewrite operators (`edit_kind_learning_v1`), contextual AST templates
        (`induced_edit_basis_v1`), AND 7-language Tree-Sitter CST skeletons (`tree_sitter_cst_skill_skeleton_v1`).
        """
        added = 0
        if language == "python":
            try:
                from canonical.runtime import edit_kind_learning_v1 as ekl

                ops = ekl.operators_of(before_source, after_source)
                for op in ops:
                    if getattr(op, "openness", "") != "names_open" or getattr(op, "before", None) is None:
                        continue
                    pos = getattr(op, "position", None)
                    bucket_key = f"{pos[0]}.{pos[1]}" if (isinstance(pos, tuple) and len(pos) == 2) else type(op.before).__name__
                    bucket = self._open_operators_by_kind.setdefault(bucket_key, [])
                    if len(bucket) < 32:
                        bucket.append(op)
                        added += 1
            except Exception:
                pass
            try:
                from canonical.swe_kernel import induced_edit_basis_v1 as ieb

                for tpl in ieb.induce_templates([(before_source, after_source)], context_depth=1, max_templates_per_pair=4):
                    if len(self._induced_templates) < 48:
                        self._induced_templates.append(tpl)
                        added += 1
            except Exception:
                pass
        try:
            from canonical.swe_kernel import tree_sitter_cst_skill_skeleton_v1 as tscss
            from canonical.swe_kernel import verified_skill_crystallizer_v1 as vsc

            b_lines = before_source.splitlines()
            a_lines = after_source.splitlines()
            diff_b = "\n".join(ln for ln in b_lines if ln not in a_lines).strip() or before_source.strip()
            diff_a = "\n".join(ln for ln in a_lines if ln not in b_lines).strip() or after_source.strip()
            rule = vsc.anti_unify_code_rule(diff_b, diff_a, language=language)
            if isinstance(rule, dict):
                skel = tscss.compile_rule_to_cst_skeleton(rule)
                if skel is not None and len(self._cst_rules) < 64:
                    merged_rule = dict(rule)
                    merged_rule["cst_skeleton"] = skel
                    self._cst_rules.append(merged_rule)
                    added += 1
        except Exception:
            pass
        return added

    def apply_cross_language_cst_skills(
        self,
        rel_file: str,
        source_text: str,
        target_language: str,
        *,
        suspect_lines: Sequence[int] | None = None,
        max_patches: int = 8,
    ) -> list[CandidatePatch]:
        """Transfer verified repairs across `python`, `rust`, `go`, `typescript`, `javascript`, `java`, `cpp` in `< 1 ms`."""
        if not self._cst_rules:
            return []
        out: list[CandidatePatch] = []
        seen: set[str] = set()
        try:
            from canonical.swe_kernel import tree_sitter_cst_skill_skeleton_v1 as tscss

            for rule in self._cst_rules:
                for cand_src in tscss.iter_cst_skeleton_candidates(
                    source_text,
                    rule,
                    target_language=target_language,
                    max_candidates=max_patches,
                    suspect_lines=suspect_lines,
                ):
                    if cand_src and cand_src != source_text and cand_src not in seen:
                        seen.add(cand_src)
                        dig = hashlib.sha256(f"{rel_file}\0{cand_src}".encode("utf-8")).hexdigest()[:14]
                        out.append(
                            CandidatePatch(
                                patch_id=f"cst_skill:{dig}",
                                family=f"cst_skill:{target_language}",
                                patched_files={rel_file: cand_src},
                                description=f"7-language CST skill {rule.get('skill_id', '')} -> {target_language}",
                                mdl_delta_bytes=len(cand_src.encode("utf-8")) - len(source_text.encode("utf-8")),
                            )
                        )
                        if len(out) >= max_patches:
                            return out
        except Exception:
            pass
        return out

    def apply_learned_operators(
        self,
        rel_file: str,
        source_text: str,
        hot_lines: set[int] | None = None,
        *,
        max_patches: int = 8,
    ) -> list[CandidatePatch]:
        """Apply compiled `O(1)` open AST operators to matching nodes in `<0.5 ms`."""
        if not self._open_operators_by_kind:
            return []
        try:
            from canonical.runtime import edit_kind_learning_v1 as ekl

            tree = ast.parse(source_text)
        except Exception:
            return []

        patches: list[CandidatePatch] = []
        seen_s: set[str] = set()
        for parent in ast.walk(tree):
            if len(patches) >= max_patches:
                break
            p_ln = getattr(parent, "lineno", 0)
            if hot_lines and p_ln and p_ln not in hot_lines:
                continue
            p_type = type(parent).__name__
            # Check slot-specific operators first (`If.test`, `Return.value`, etc.)
            for field_name, field_val in ast.iter_fields(parent):
                if not isinstance(field_val, ast.AST):
                    continue
                slot_ops = self._open_operators_by_kind.get(f"{p_type}.{field_name}") or ()
                for op in slot_ops:
                    bound: dict[str, Any] = {}
                    if ekl.fits(op.before, field_val, bound):
                        try:
                            rebuilt = ekl.built(op.after, bound)
                            ast.fix_missing_locations(rebuilt)
                            repl_txt = ast.unparse(rebuilt)
                            patched = _replace_node_segment(source_text, field_val, repl_txt)
                            if patched and patched != source_text and patched not in seen_s:
                                seen_s.add(patched)
                                dig = hashlib.sha256(f"{rel_file}\0{patched}".encode("utf-8")).hexdigest()[:14]
                                patches.append(
                                    CandidatePatch(
                                        patch_id=f"learned_op:{dig}",
                                        family="learned_open_ast_operator",
                                        patched_files={rel_file: patched},
                                        description=f"O(1) learned operator {p_type}.{field_name} -> {repl_txt[:60]}",
                                        mdl_delta_bytes=_mdl_bytes(patched) - _mdl_bytes(source_text),
                                    )
                                )
                        except Exception:
                            continue
        return patches[:max_patches]

    def record_verified_repair(
        self,
        *,
        family: str,
        before_source: str,
        after_source: str,
        scope_id: str = "global",
        surprise: float = 1.0,
    ) -> SemanticRepairMotif | None:
        """Consolidate a verified repair motif when surprise > 0.05; invalidate stale conflicting motifs."""
        if surprise < 0.05:
            return None
        self._compile_open_operators(before_source, after_source)
        b_lines = before_source.splitlines()
        a_lines = after_source.splitlines()
        diff_before = "\n".join(ln for ln in b_lines if ln not in a_lines)[:600]
        diff_after = "\n".join(ln for ln in a_lines if ln not in b_lines)[:600]
        b_can = self.canonicalize_snippet(diff_before or before_source[:400])
        a_can = self.canonicalize_snippet(diff_after or after_source[:400])
        scope_dig = hashlib.sha256(scope_id.encode("utf-8")).hexdigest()[:12]
        now = time.time()

        # Bi-temporal invalidation: if an active motif has identical `before_canonical` in same scope
        # but a different `after_canonical`, mark `t_invalidated_at = now` rather than overwriting history.
        for existing in self._motifs.values():
            if (
                existing.t_invalidated_at is None
                and existing.scope_digest == scope_dig
                and existing.before_canonical == b_can
                and existing.after_canonical != a_can
            ):
                existing.t_invalidated_at = now

        mid = hashlib.sha256(f"{family}\0{b_can}\0{a_can}\0{scope_dig}".encode("utf-8")).hexdigest()[:16]
        if mid in self._motifs and self._motifs[mid].t_invalidated_at is None:
            self._motifs[mid].verified_hits += 1
            motif = self._motifs[mid]
        else:
            gain = max(0, _mdl_bytes(before_source) - _mdl_bytes(after_source))
            motif = SemanticRepairMotif(
                motif_id=mid,
                family=family,
                before_canonical=b_can,
                after_canonical=a_can,
                scope_digest=scope_dig,
                t_valid_from=now,
                t_invalidated_at=None,
                mdl_gain_bytes=gain,
                verified_hits=1,
            )
            self._motifs[mid] = motif
        self._save()
        return motif

    def active_motifs(self, *, scope_id: str | None = None) -> list[SemanticRepairMotif]:
        s_dig = hashlib.sha256(scope_id.encode("utf-8")).hexdigest()[:12] if scope_id else None
        out = [
            m
            for m in self._motifs.values()
            if m.t_invalidated_at is None and (s_dig is None or m.scope_digest == s_dig)
        ]
        out.sort(key=lambda m: (-m.verified_hits, -m.t_valid_from, m.motif_id))
        return out

    def _save(self) -> None:
        if not self.state_path:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            rows = [m.__dict__ for m in self._motifs.values()]
            self.state_path.write_text(json.dumps({"schema": SCHEMA, "motifs": rows}, sort_keys=True), encoding="utf-8")
        except OSError:
            pass

    def _load(self) -> None:
        if not self.state_path:
            return
        try:
            doc = json.loads(self.state_path.read_text(encoding="utf-8"))
            for row in doc.get("motifs") or []:
                m = SemanticRepairMotif(**row)
                self._motifs[m.motif_id] = m
        except Exception:
            pass


_SHARED_SKILL_STORE = EStitchSemanticSkillStore()


def shared_semantic_skill_store() -> EStitchSemanticSkillStore:
    return _SHARED_SKILL_STORE


# ---------------------------------------------------------------------------
# 8. ACTIVE SYMBOLIC MEALY AUTOMATA LEARNER ($L^\#$ VIA `minimal_experiment_v1`)
# ---------------------------------------------------------------------------


class ActiveSymbolicMealyLearner:
    """Active black-box Mealy machine learner built on `minimal_experiment_v1`.

    Learns the minimal deterministic finite-state transducer consistent with an
    unknown stateful environment or CLI oracle by iteratively querying separating
    input sequences (`separating_word` + `rank_experiments`) until observational
    closure holds.
    """

    @staticmethod
    def learn_mealy_interface(
        oracle_fn: Callable[[Sequence[str]], Sequence[str]],
        alphabet: Sequence[str],
        *,
        accepting_outputs: Sequence[str] = ("1", "ACCEPT", "OK", "TRUE", "True"),
        max_states: int = 4,
        max_queries: int = 48,
        seed_traces: Sequence[tuple[Sequence[str], Sequence[str]]] = (),
    ) -> dict[str, Any]:
        from canonical.runtime import minimal_experiment_v1 as me

        alpha = tuple(dict.fromkeys(str(a) for a in alphabet))
        if not alpha:
            return {"status": "EMPTY_ALPHABET", "pass": False, "queries": 0}

        acc_tokens = frozenset(str(t) for t in accepting_outputs)
        trace_cache: dict[tuple[str, ...], tuple[str, ...]] = {
            tuple(inp): tuple(str(x) for x in out) for inp, out in seed_traces
        }
        queries = 0

        def _query(word: tuple[str, ...]) -> tuple[str, ...]:
            nonlocal queries
            if word in trace_cache:
                return trace_cache[word]
            queries += 1
            out = tuple(str(x) for x in oracle_fn(word))
            trace_cache[word] = out
            return out

        def _to_me_observations() -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            for word, out_seq in sorted(trace_cache.items()):
                if not word or not out_seq:
                    continue
                last_out = out_seq[-1]
                is_acc = last_out in acc_tokens
                rows.append(
                    {
                        "access": list(word[:-1]),
                        "action": word[-1],
                        "observation": "ACCEPT" if is_acc else "REJECT",
                        "accepting": is_acc,
                        "available": True,
                    }
                )
            return rows

        def _predict_accepting(machine: Mapping[str, Any], word: tuple[str, ...]) -> bool | None:
            state = int(machine.get("start", 0))
            trans = machine.get("transitions") or {}
            for sym in word:
                row = trans.get(str(state)) or {}
                if sym not in row:
                    return None
                state = int(row[sym])
            return state in {int(s) for s in (machine.get("accepting") or ())}

        # Phase 1: Seed 1-step & 2-step access/distinguishing prefixes (`L#` apartment seeds)
        for sym in alpha:
            if queries >= max_queries:
                break
            _query((sym,))
        for s1 in alpha:
            for s2 in alpha:
                if queries >= max_queries:
                    break
                _query((s1, s2))

        obs_rows = _to_me_observations()
        synth_env = me.minimal_consistent_machine(obs_rows)
        learned = synth_env.get("machine") if isinstance(synth_env, Mapping) else None
        if not isinstance(learned, Mapping) or not learned.get("states"):
            return {
                "status": str(synth_env.get("status") if isinstance(synth_env, Mapping) else "NO_CONSISTENT_MACHINE"),
                "pass": False,
                "n_states": 0,
                "queries": queries,
                "observations_count": len(obs_rows),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        # Phase 2: Active separating-word refinement via `rank_experiments` within `EXACT_NODE_LIMIT`
        exact_limit = int(getattr(me, "EXACT_NODE_LIMIT", 12))
        try:
            ranked_exp = me.rank_experiments(learned, max_depth=3)
            cand_words = [
                tuple(str(x) for x in (row.get("word") or ()))
                for row in (ranked_exp.get("experiments") or ())
                if row.get("word")
            ]
        except Exception:
            cand_words = []

        for w_probe in dict.fromkeys(cand_words):
            if queries >= max_queries or not w_probe or len(trace_cache) + 1 >= exact_limit:
                break
            pred_acc = _predict_accepting(learned, w_probe)
            actual_seq = _query(w_probe)
            actual_acc = bool(actual_seq and actual_seq[-1] in acc_tokens)
            if pred_acc is None or pred_acc != actual_acc:
                next_obs = _to_me_observations()
                next_env = me.minimal_consistent_machine(next_obs)
                if isinstance(next_env.get("machine"), Mapping):
                    synth_env = next_env
                    learned = next_env["machine"]

        obs_rows = _to_me_observations()
        consistent = bool(me.is_consistent(learned, obs_rows))
        return {
            "status": "PASS__MEALY_INTERFACE_LEARNED" if consistent else "FAIL_CLOSED__INCONSISTENT_ORACLE",
            "pass": consistent,
            "n_states": int(learned.get("state_count") or len(learned.get("states") or ())),
            "initial_state": int(learned.get("start", 0)),
            "optimality": str(synth_env.get("optimality") or "NONE"),
            "alphabet": list(alpha),
            "queries": queries,
            "observations_count": len(obs_rows),
            "machine": dict(learned),
            "model_calls": 0,
            "parameters_stored": 0,
        }


# ---------------------------------------------------------------------------
# 9. UNIFIED CONTRACT, REFUSAL & COMPOSER BRIDGE (`route_and_plan_contract`)
# ---------------------------------------------------------------------------


def verify_output_against_goal_contract(goal: str, output_text: str) -> dict[str, Any]:
    """Compile explicit natural-language formatting/structural constraints via `instruction_contract_v1`."""
    try:
        from canonical.runtime import instruction_contract_v1 as ic

        contract = ic.compile_contract(goal)
        verdict = ic.check_contract(output_text, contract)
        return {"compiled": True, "contract": contract, "verdict": verdict}
    except Exception as exc:
        return {"compiled": False, "error": f"{type(exc).__name__}:{exc}"}


def diagnose_and_plan_refusal_repair(stderr_text: str, workspace_dir: pathlib.Path) -> dict[str, Any]:
    """Read a world/CLI refusal diagnostic via `a_refusal_is_a_specification_v1`."""
    try:
        from canonical.runtime import a_refusal_is_a_specification_v1 as ref_spec

        parsed = ref_spec.read_refusal(stderr_text)
        return {"parsed": parsed is not None, "specification": parsed, "workspace": str(workspace_dir)}
    except Exception as exc:
        return {"parsed": False, "error": f"{type(exc).__name__}:{exc}"}


def learn_and_act_version_space_ui(
    demonstration_traces: Sequence[Sequence[tuple[Mapping[str, Any], str]]],
    query_observation: Mapping[str, Any] | None = None,
    *,
    step: int = 0,
) -> dict[str, Any]:
    """Synthesize a GUI/DOM Version-Space program from few-shot traces via `demonstration_version_space_v1`."""
    from canonical.runtime import demonstration_version_space_v1 as dvs

    skill = dvs.VersionSpaceSkill()
    accepted = 0
    for trace in demonstration_traces:
        if skill.add_success(trace):
            accepted += 1
    desc = skill.describe()
    action: str | None = None
    disagreement: dict[str, Any] | None = None
    if isinstance(query_observation, Mapping):
        action = skill.act(step, query_observation)
        disagreement = skill.disagreement(query_observation)
    passed = accepted > 0 and (query_observation is None or action is not None)
    return {
        "schema": SCHEMA,
        "status": "PASS__VERSION_SPACE_UI_SKILL" if passed else "FAIL_CLOSED__VERSION_SPACE_UNRESOLVED",
        "pass": passed,
        "accepted_demonstrations": accepted,
        "rejected_demonstrations": skill.rejected_examples,
        "program_description": desc,
        "predicted_action": action,
        "committee_disagreement": disagreement,
        "model_calls": 0,
        "parameters_stored": 0,
    }


def _extract_declarative_webmcp_tools_from_html(html_source: str) -> list[dict[str, Any]]:
    """Extract W3C Declarative WebMCP (`<form toolname=\"...\" tooldescription=\"...\">`) schemas in `< 0.3 ms`."""
    out: list[dict[str, Any]] = []
    for f_m in re.finditer(r"<form\b([^>]*)>(.*?)</form>", html_source, flags=re.IGNORECASE | re.DOTALL):
        attrs_s, body_s = f_m.group(1), f_m.group(2)
        tn_m = re.search(r"\btoolname\s*=\s*['\"]([^'\"]+)['\"]", attrs_s, flags=re.IGNORECASE)
        if not tn_m:
            continue
        td_m = re.search(r"\btooldescription\s*=\s*['\"]([^'\"]*)['\"]", attrs_s, flags=re.IGNORECASE)
        props: dict[str, dict[str, str]] = {}
        req: list[str] = []
        for inp_m in re.finditer(r"<(?:input|select|textarea)\b([^>]*)>", body_s, flags=re.IGNORECASE):
            ia = inp_m.group(1)
            nm = re.search(r"\bname\s*=\s*['\"]([^'\"]+)['\"]", ia, flags=re.IGNORECASE)
            if not nm:
                continue
            field_name = nm.group(1)
            tp = re.search(r"\btype\s*=\s*['\"]([^'\"]+)['\"]", ia, flags=re.IGNORECASE)
            raw_t = (tp.group(1).lower() if tp else "string")
            if raw_t == "submit":
                continue
            json_t = "integer" if raw_t == "number" else ("boolean" if raw_t == "checkbox" else "string")
            props[field_name] = {"type": json_t}
            if re.search(r"\brequired\b", ia, flags=re.IGNORECASE):
                req.append(field_name)
        out.append(
            {
                "name": tn_m.group(1),
                "description": td_m.group(1) if td_m else "",
                "input_schema": {"type": "object", "properties": props, "required": req},
            }
        )
    return out


def act_on_interface_unified(
    instruction: str,
    *,
    observation: Mapping[str, Any] | None = None,
    expected_generation: int | None = None,
    webmcp_tools: Sequence[Mapping[str, Any]] | None = None,
    html_source: str | None = None,
    a11y_env: Any | None = None,
    a11y_tree: str | None = None,
    screenshot_bytes: bytes | None = None,
    previous_screenshot_bytes: bytes | None = None,
    submit_effects: Mapping[str, Mapping[str, Any]] | None = None,
    goal_check: Callable[[Any], bool] | None = None,
    cli_need: Mapping[str, Any] | None = None,
    guide_pages: Mapping[str, Any] | None = None,
    help_key_table_text: str | None = None,
    state_graph_edges: Sequence[tuple[str, str]] | None = None,
    start_goal_states: tuple[str, str] | None = None,
    workspace_dir: pathlib.Path | str | None = None,
    demonstration_traces: Sequence[Sequence[tuple[Mapping[str, Any], str]]] | None = None,
    step: int = 0,
) -> dict[str, Any]:
    """Zero-VLM Generation-Stamped Computer-Use, WebMCP & CLI Action-Grammar dispatcher (`K3 = 0`).

    Unifies:
      -1. Strict Observation-Generation Counter Stale-Frame Refusal (`< 0.01 ms`, OSWorld 2.1 invariant),
       0. Imperative & Declarative HTML `<form toolname=...>` `WebMCP` tool-schema router (`0` pixels, `<0.5 ms`),
       1. `demonstration_version_space_v1.VersionSpaceSkill` (1-shot UI program algebra),
       2. `interface_action_grammar_v1.A11yEnvironment` + `solve_gui_goal` (HTML / AT-SPI Accessibility Tree),
       3. `osworld_v21_zero_model_policy_v1.ZeroModelOSWorldPolicy` + `universal_computer_agent_v1` + `computer_use_agent_v1`,
       4. `interface_action_grammar_v1.solve_cli_need` + `the_guide_is_a_key_table_v1` + `executable_mental_model_v1`.
    """
    t0 = time.perf_counter()

    # Pre-Gate: Strict Observation-Generation Counter Refusal (eliminates stale-UI clicks in `< 0.01 ms`!)
    if expected_generation is not None and isinstance(observation, Mapping) and "generation" in observation:
        obs_gen = int(observation["generation"])
        if obs_gen != int(expected_generation):
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__STALE_OBSERVATION_GENERATION",
                "pass": False,
                "modality": "GENERATION_STAMP_GUARD",
                "expected_generation": int(expected_generation),
                "observed_generation": obs_gen,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "model_calls": 0,
                "parameters_stored": 0,
            }

    # Auto-discover Declarative HTML `<form toolname="...">` WebMCP contracts BEFORE paying DOM/A11y cost!
    active_webmcp = list(webmcp_tools or ())
    if not active_webmcp and html_source and "toolname=" in html_source.lower():
        active_webmcp = _extract_declarative_webmcp_tools_from_html(html_source)

    # Optional Petri Articulation-Point Checkpointing (`computer_use_agent_v1.find_articulation_subgoals`)
    articulation_subgoals: list[str] = []
    if state_graph_edges and start_goal_states and len(start_goal_states) == 2:
        try:
            from canonical.swe_kernel import computer_use_agent_v1 as cua

            articulation_subgoals = list(
                cua.find_articulation_subgoals(list(state_graph_edges), start_goal_states[0], start_goal_states[1])
            )
        except Exception:
            articulation_subgoals = []

    # Tier 0: WebMCP structured tool schema (`name`, `description`, `input_schema`/`parameters`)
    if active_webmcp:
        inst_tokens = {w for w in re.findall(r"[a-z0-9_]+", instruction.lower()) if len(w) >= 2}
        kv_pairs = dict(re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*[=:]\s*['\"]?([^,'\"\s]+)['\"]?", instruction))
        quoted_vals = re.findall(r"['\"]([^'\"]+)['\"]", instruction)
        best_tool: Mapping[str, Any] | None = None
        best_score = -1
        for tool_spec in active_webmcp:
            if not isinstance(tool_spec, Mapping):
                continue
            t_name = str(tool_spec.get("name") or "")
            t_desc = str(tool_spec.get("description") or "")
            schema_obj = tool_spec.get("input_schema") or tool_spec.get("parameters") or {}
            props = schema_obj.get("properties") if isinstance(schema_obj, Mapping) else {}
            prop_keys = set(props.keys()) if isinstance(props, Mapping) else set()
            t_tokens = set(re.findall(r"[a-z0-9_]+", f"{t_name} {t_desc}".lower())) | {k.lower() for k in prop_keys}
            overlap = len(inst_tokens & t_tokens) * 3 + sum(2 for k in prop_keys if k in kv_pairs)
            if t_name.lower() in instruction.lower():
                overlap += 6
            if overlap > best_score:
                best_score = overlap
                best_tool = tool_spec
        if best_tool is not None and best_score > 0:
            schema_obj = best_tool.get("input_schema") or best_tool.get("parameters") or {}
            props = schema_obj.get("properties") if isinstance(schema_obj, Mapping) else {}
            req_keys = list(schema_obj.get("required") or ()) if isinstance(schema_obj, Mapping) else []
            bound_args: dict[str, Any] = {}
            q_idx = 0
            if isinstance(props, Mapping):
                for pk, pmeta in props.items():
                    if pk in kv_pairs:
                        raw_v = kv_pairs[pk]
                        ptype = str(pmeta.get("type") or "string") if isinstance(pmeta, Mapping) else "string"
                        if ptype == "integer" and raw_v.lstrip("-").isdigit():
                            bound_args[pk] = int(raw_v)
                        elif ptype == "boolean":
                            bound_args[pk] = raw_v.lower() in {"true", "1", "yes"}
                        else:
                            bound_args[pk] = raw_v
                    elif pk in req_keys and q_idx < len(quoted_vals):
                        bound_args[pk] = quoted_vals[q_idx]
                        q_idx += 1
            missing_req = [rk for rk in req_keys if rk not in bound_args]
            passed_mcp = len(missing_req) == 0
            return {
                "schema": SCHEMA,
                "status": "PASS__WEBMCP_TOOL_CALL_BOUND" if passed_mcp else "FAIL_CLOSED__WEBMCP_REQUIRED_SLOTS_MISSING",
                "pass": passed_mcp,
                "modality": "WEBMCP_STRUCTURED_TOOL",
                "tool_call": {"name": str(best_tool.get("name") or ""), "arguments": bound_args},
                "missing_required": missing_req,
                "articulation_subgoals": articulation_subgoals,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "model_calls": 0,
                "parameters_stored": 0,
            }

    if demonstration_traces:
        out = learn_and_act_version_space_ui(demonstration_traces, observation, step=step)
        out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        return out

    if html_source is not None or a11y_env is not None:
        from canonical.swe_kernel import interface_action_grammar_v1 as iag

        env_obj = a11y_env if a11y_env is not None else iag.A11yEnvironment.from_html(html_source or "", submit_effects=submit_effects)

        def _env_as_state_dict(e: Any) -> dict[str, Any]:
            banner = str(getattr(e, "status_banner", "") or "")
            merged_fx: dict[str, Any] = {}
            if banner and not banner.startswith("ERROR:"):
                for fx in (getattr(e, "submit_effects", {}) or {}).values():
                    if isinstance(fx, Mapping):
                        merged_fx.update(fx)
            return {
                "status_banner": banner,
                "navigated_url": str(getattr(e, "navigated_url", "") or ""),
                "values": {str(n.node_id): n.value for n in getattr(e, "nodes", ())},
                "checked": {str(n.node_id): bool(n.checked) for n in getattr(e, "nodes", ())},
                "effects": merged_fx,
            }

        def _wrapped_checker(e: Any) -> bool:
            if not callable(goal_check):
                banner = str(getattr(e, "status_banner", "") or "")
                return bool((banner and not banner.startswith("ERROR:")) or getattr(e, "navigated_url", ""))
            try:
                return bool(goal_check(e))
            except (AttributeError, TypeError, KeyError):
                return bool(goal_check(_env_as_state_dict(e)))

        gui_res = iag.solve_gui_goal(env_obj, instruction, _wrapped_checker)
        passed_g = bool(gui_res.get("pass") is True)
        return {
            "schema": SCHEMA,
            "status": str(gui_res.get("status") or ("PASS__A11Y_GUI_SOLVED" if passed_g else "FAIL_CLOSED__GUI_GOAL_NOT_REACHED")),
            "pass": passed_g,
            "modality": "A11Y_ACTION_GRAMMAR",
            "gui_result": gui_res,
            "osworld_pyautogui_script": list(gui_res.get("pyautogui") or getattr(env_obj, "pyautogui_log", ())),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # Tier 3: Pure-stdlib OSWorld AT-SPI XML + PNG Canvas Widget Tomography (`ZeroModelOSWorldPolicy` + `universal_computer_agent_v1`)
    if screenshot_bytes is not None or a11y_tree is not None:
        from canonical.runtime import osworld_v21_zero_model_policy_v1 as osw
        from canonical.swe_kernel import universal_computer_agent_v1 as uca

        policy = osw.ZeroModelOSWorldPolicy()
        obs_dict: dict[str, Any] = dict(observation) if isinstance(observation, Mapping) else {}
        if a11y_tree is not None:
            obs_dict["accessibility_tree"] = a11y_tree
        if screenshot_bytes is not None:
            obs_dict["screenshot"] = screenshot_bytes

        canvas_regions: list[dict[str, Any]] = []
        noop_detected = False
        if screenshot_bytes is not None:
            try:
                w, h, rgb = osw.decode_png_to_rgb(screenshot_bytes)
                grid_2d = [
                    [
                        (rgb[(ry * w + rx) * 3] << 16)
                        | (rgb[(ry * w + rx) * 3 + 1] << 8)
                        | rgb[(ry * w + rx) * 3 + 2]
                        for rx in range(w)
                    ]
                    for ry in range(h)
                ]
                canvas_regions = uca.extract_canvas_regions(grid_2d)
                if previous_screenshot_bytes is not None:
                    pw, ph, prgb = osw.decode_png_to_rgb(previous_screenshot_bytes)
                    if (pw, ph) == (w, h):
                        prev_grid = [
                            [
                                (prgb[(ry * pw + rx) * 3] << 16)
                                | (prgb[(ry * pw + rx) * 3 + 1] << 8)
                                | prgb[(ry * pw + rx) * 3 + 2]
                                for rx in range(pw)
                            ]
                            for ry in range(ph)
                        ]
                        fb_diff = uca.diff_framebuffers(prev_grid, grid_2d)
                        noop_detected = bool(fb_diff.get("changed_pixels", 0) == 0)
            except Exception:
                canvas_regions = []

        resp_text, actions = policy.predict(instruction, obs_dict)
        if (not actions or actions == ["WAIT"]) and canvas_regions:
            cx, cy = canvas_regions[0]["centroid"]
            actions = [f"pyautogui.click({int(cx)}, {int(cy)})"]
        passed_osw = bool(actions and actions != ["FAIL"])
        return {
            "schema": SCHEMA,
            "status": "PASS__OSWORLD_CANVAS_TOMOGRAPHY_ACTION" if passed_osw else "FAIL_CLOSED__OSWORLD_NO_GROUNDED_TARGET",
            "pass": passed_osw,
            "modality": "OSWORLD_A11Y_CANVAS_TOMOGRAPHY",
            "actions": list(actions),
            "policy_rationale": resp_text,
            "canvas_regions": canvas_regions[:12],
            "l3_noop_detected": noop_detected,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    if isinstance(cli_need, Mapping):
        from canonical.swe_kernel import interface_action_grammar_v1 as iag

        ws_p = pathlib.Path(workspace_dir or pathlib.Path.cwd()).resolve()
        cli_res = iag.solve_cli_need(cli_need, ws_p)
        passed_c = bool(cli_res.get("pass") is True or cli_res.get("status", "").startswith("PASS"))
        return {
            "schema": SCHEMA,
            "status": str(cli_res.get("status") or ("PASS__CLI_GRAMMAR_SOLVED" if passed_c else "FAIL_CLOSED__CLI_UNSOLVED")),
            "pass": passed_c,
            "modality": "CLI_ACTION_GRAMMAR",
            "cli_result": cli_res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    if help_key_table_text:
        from canonical.tools import the_guide_is_a_key_table_v1 as tgkt

        rows_kt = tgkt.table_rows(help_key_table_text)
        inst_toks = {w for w in re.findall(r"[a-z0-9_-]+", instruction.lower()) if len(w) >= 2}
        ranked_kt = sorted(
            rows_kt,
            key=lambda r: -len(inst_toks & set(re.findall(r"[a-z0-9_-]+", json.dumps(r).lower()))),
        )
        return {
            "schema": SCHEMA,
            "status": "PASS__KEY_TABLE_PARSED" if rows_kt else "FAIL_CLOSED__EMPTY_KEY_TABLE",
            "pass": bool(rows_kt),
            "modality": "CLI_HELP_KEY_TABLE",
            "selected_row": ranked_kt[0] if ranked_kt else None,
            "table_rows_count": len(rows_kt),
            "articulation_subgoals": articulation_subgoals,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    if isinstance(guide_pages, Mapping):
        from canonical.tools import the_guide_is_an_action_grammar_v1 as gag

        edges = gag.edges_of(dict(guide_pages))
        return {
            "schema": SCHEMA,
            "status": "PASS__GUIDE_ACTION_GRAMMAR_EXTRACTED" if edges else "FAIL_CLOSED__GUIDE_NO_ACTION_EDGES",
            "pass": bool(edges),
            "modality": "GUIDE_ACTION_GRAMMAR",
            "edges": list(edges),
            "articulation_subgoals": articulation_subgoals,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    if workspace_dir is not None and observation is None:
        from canonical.swe_kernel import executable_mental_model_v1 as emm

        snap = emm.perceive_environment_state(workspace_dir)
        return {
            "schema": SCHEMA,
            "status": "PASS__FIVE_LAYER_ENVIRONMENT_SNAPSHOT",
            "pass": True,
            "modality": "FIVE_LAYER_MENTAL_MODEL_SNAPSHOT",
            "files_count": len(getattr(snap, "files", ())),
            "sqlite_tables_count": len(getattr(snap, "sqlite_tables", ())),
            "dom_elements_count": len(getattr(snap, "dom_elements", ())),
            "canvas_regions_count": len(getattr(snap, "canvas_regions", ())),
            "articulation_subgoals": articulation_subgoals,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    if isinstance(observation, Mapping):
        from canonical.runtime import aimed_action_v1 as aimed
        from canonical.runtime import instruction_policy_v1 as ipol

        pol_res = ipol.first_action(instruction, observation)
        act_val = pol_res.get("action")
        aimed_cands: list[Any] = []
        try:
            aimed_cands = list(aimed.aimed_actions(observation))[:8]
        except Exception:
            aimed_cands = []
        passed_o = act_val is not None or len(aimed_cands) > 0
        return {
            "schema": SCHEMA,
            "status": "PASS__ZERO_EXPERIENCE_INSTRUCTION_POLICY" if act_val is not None else (
                "PASS__AIMED_STRUCTURAL_CANDIDATES" if aimed_cands else str(pol_res.get("refusal") or "FAIL_CLOSED__NO_ACTION")
            ),
            "pass": passed_o,
            "modality": "ZERO_EXPERIENCE_INSTRUCTION_POLICY",
            "action": act_val,
            "policy_result": pol_res,
            "aimed_candidates": aimed_cands,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__NO_INTERFACE_SURFACE_SUPPLIED",
        "pass": False,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
        "parameters_stored": 0,
    }


class _UniversalExplorationEnvAdapter:
    """Adapts OpenAI-Gym/POMDP `(observe/get_state, step, reset)` or native `(state, act, reset)`
    environments to the exact protocol expected by `systematic_exploration_v1`.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._last_obs: Any = None

    def reset(self) -> Any:
        if callable(getattr(self._inner, "reset", None)):
            self._last_obs = self._inner.reset()
        return self._last_obs

    def state(self) -> Any:
        if callable(getattr(self._inner, "state", None)):
            return self._inner.state()
        if callable(getattr(self._inner, "observe", None)):
            return self._inner.observe()
        if callable(getattr(self._inner, "get_state", None)):
            return self._inner.get_state()
        return self._last_obs

    def act(self, action: Any) -> Any:
        if callable(getattr(self._inner, "act", None)):
            self._last_obs = self._inner.act(action)
            return self._last_obs
        if callable(getattr(self._inner, "step", None)):
            out = self._inner.step(action)
            self._last_obs = out[0] if isinstance(out, tuple) and len(out) >= 2 else out
            return self._last_obs
        raise AttributeError("Environment defines neither `act` nor `step`")


def explore_unknown_environment_unified(
    env: Any,
    actions: Sequence[Any],
    *,
    is_goal: Callable[[Any], bool] | None = None,
    labeled_traces: Sequence[tuple[Sequence[Any], bool]] | None = None,
    provenance_transitions: Sequence[tuple[Sequence[Any], Sequence[Any]]] | None = None,
    state_graph_edges: Sequence[tuple[str, str]] | None = None,
    start_goal_nodes: tuple[str, str] | None = None,
    action_budget: int = 32,
    use_memory: bool = False,
    verify_replay: bool = False,
    interventional_call: tuple[str, Sequence[Any], Any] | None = None,
    refusal_line: str | None = None,
) -> dict[str, Any]:
    """Zero-instruction interactive state-graph & unknown-goal quotient explorer (`ARC-AGI-3` / POMDP spine).

    Combines:
      1. `the_goal_is_a_quotient_of_the_trace_v1` (`enumerate_lattice`, `coarsest` unknown-goal quotient induction),
      2. `an_actions_effect_is_a_provenance_map_v1` (`infer` causal slot provenance map),
      3. `universal_computer_agent_v1.compute_petri_dominator_cut_vertices` (mandatory bottleneck subgoals),
      4. `systematic_exploration_v1` (never paying twice for equivalent states),
      5. `interventional_goal_v1.intervene` + `the_refusal_is_the_curriculum_v1.read_demand` + `CalculatedState`.
    """
    import math
    from canonical.runtime import systematic_exploration_v1 as se
    from canonical.swe_kernel import interventional_goal_v1 as ig
    from canonical.swe_kernel import universal_computer_agent_v1 as uca
    from canonical.swe_kernel import weights_from_scratch_v1 as wfs
    from canonical.tools import an_actions_effect_is_a_provenance_map_v1 as prov_map
    from canonical.tools import the_goal_is_a_quotient_of_the_trace_v1 as tgq
    from canonical.tools import the_refusal_is_the_curriculum_v1 as ref_curr

    t0 = time.perf_counter()
    trace_quotient_doc: dict[str, Any] | None = None
    effective_goal = is_goal
    if labeled_traces:
        try:
            norm_labeled = [(list(tr), bool(lbl)) for tr, lbl in labeled_traces]
            gens = tgq.derived_generators([tr for tr, _ in norm_labeled])
            lattice = tgq.enumerate_lattice(norm_labeled, gens, max_size=3)
            coarsest_q = tgq.coarsest(lattice)
            if coarsest_q is not None:
                pos_cells = {
                    coarsest_q["project"](tr)
                    for tr, lbl in norm_labeled
                    if lbl
                }
                trace_quotient_doc = {
                    "generator_names": list(coarsest_q["names"]),
                    "quotient_cells": int(coarsest_q["cells"]),
                    "positive_cell_count": len(pos_cells),
                }
                if effective_goal is None:
                    proj_fn = coarsest_q["project"]
                    effective_goal = lambda st, _pf=proj_fn, _pc=pos_cells: (
                        _pf(list(st) if isinstance(st, (list, tuple)) else [st]) in _pc
                    )
        except Exception:
            trace_quotient_doc = None

    if effective_goal is None:
        effective_goal = lambda st: bool(
            isinstance(st, Mapping) and (st.get("goal") is True or st.get("done") is True or st.get("solved") is True)
        )

    provenance_doc: Any = None
    if provenance_transitions:
        try:
            provenance_doc = prov_map.infer([(list(b), list(a)) for b, a in provenance_transitions])
        except Exception:
            provenance_doc = None

    dominator_cut_vertices: list[str] = []
    if state_graph_edges and start_goal_nodes and len(start_goal_nodes) == 2:
        try:
            dominator_cut_vertices = uca.compute_petri_dominator_cut_vertices(
                start_goal_nodes[0],
                start_goal_nodes[1],
                list(state_graph_edges),
            )
        except Exception:
            dominator_cut_vertices = []

    adapted = env if (callable(getattr(env, "state", None)) and callable(getattr(env, "act", None))) else _UniversalExplorationEnvAdapter(env)
    # Cross-Environment Structural Fingerprint Transfer (`transfer_learning_v1`)
    env_fingerprint_doc: dict[str, Any] | None = None
    try:
        from canonical.runtime import transfer_learning_v1 as tlearn

        if callable(getattr(adapted, "reset", None)):
            fp_raw = tlearn.fingerprint(adapted, list(actions)[:6], probes=2, probe_depth=2)
            env_fingerprint_doc = {
                "action_count": len(actions),
                "fingerprint_keys": sorted(fp_raw.keys())[:8] if isinstance(fp_raw, Mapping) else [],
            }
            adapted.reset()
    except Exception:
        env_fingerprint_doc = None

    if use_memory or verify_replay:
        exp_out = se.drive(
            adapted,
            actions,
            is_goal=effective_goal,
            action_budget=action_budget,
            use_memory=use_memory,
            verify=verify_replay,
        )
    else:
        exp_out = se.explore_to_goal(
            adapted,
            actions,
            is_goal=effective_goal,
            action_budget=action_budget,
        )

    do_probe: dict[str, Any] | None = None
    if interventional_call is not None and len(interventional_call) == 3:
        fn_n, args_s, exp_v = interventional_call
        iv = ig.intervene(str(fn_n), list(args_s), exp_v)
        if iv is not None:
            do_probe = {"do_args": iv[0], "expected_under_do": iv[1]}

    refusal_demand: Any = None
    if refusal_line:
        try:
            refusal_demand = ref_curr.read_demand(refusal_line)
        except Exception:
            refusal_demand = None

    passed = bool(exp_out.get("pass") is True or exp_out.get("reached") is True)
    explored_sub = exp_out.get("explored") if isinstance(exp_out.get("explored"), Mapping) else {}
    shortest_plan = list(exp_out.get("plan_shortest") or explored_sub.get("plan_shortest") or exp_out.get("plan") or ())
    budget_spent = int(
        exp_out.get("budget_spent")
        or explored_sub.get("budget_spent")
        or exp_out.get("acts")
        or explored_sub.get("acts")
        or 0
    )
    state_count = int(exp_out.get("state_count") or explored_sub.get("state_count") or 0)
    calc_state = wfs.CalculatedState()
    shortest_len = len(shortest_plan)
    rhae_ratio = round(float(shortest_len) / float(max(1, budget_spent)), 4) if shortest_len > 0 else 0.0
    c_ids_bits = round(math.log2(max(1, state_count)) / float(max(1, budget_spent)), 4) if state_count > 0 else 0.0
    calc_state.add(
        "action_efficiency_ratio",
        rhae_ratio,
        "len(plan_shortest) / max(1, budget_spent) from systematic_exploration_v1",
    )
    calc_state.add(
        "causal_info_bits_per_step",
        c_ids_bits,
        "log2(max(1, state_count)) / max(1, budget_spent) causal information gain rate",
    )

    return {
        "schema": SCHEMA,
        "status": str(exp_out.get("status") or ("PASS__GOAL_REACHED" if passed else "FAIL_CLOSED__BUDGET_EXHAUSTED")),
        "pass": passed,
        "reached": bool(exp_out.get("reached", passed)),
        "plan_shortest": shortest_plan,
        "budget_spent": budget_spent,
        "state_count": state_count,
        "action_efficiency_ratio": rhae_ratio,
        "causal_info_bits_per_step": c_ids_bits,
        "trace_quotient": trace_quotient_doc,
        "action_provenance_map": provenance_doc,
        "dominator_cut_vertices": dominator_cut_vertices,
        "environment_fingerprint": env_fingerprint_doc,
        "do_intervention": do_probe,
        "refusal_curriculum_demand": refusal_demand,
        "calculated_fast_state": calc_state.as_dict(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
        "parameters_stored": 0,
    }


class VSAWoodburyFastMemory:
    """Zero-Neural-Weight Hyperdimensional VSA + Sherman-Morrison/Woodbury + Bi-Temporal PPR Memory (`K3 = 0`).

    Combines:
      1. 64-bit SimHash Hyperdimensional Vector-Symbolic Architecture (`O(1)` XOR + `.bit_count()`
         Hamming similarity, zero neural weights, zero gradient descent),
      2. Exact Closed-Form Sherman-Morrison / Woodbury Rank-1 Ridge Estimator:
         `P_t = P_{t-1} - (P_{t-1} x x^T P_{t-1}) / (1 + x^T P_{t-1} x)`
         recomputed online from verified episodic tuples (`parameters_stored == 0`),
      3. *Memoir* Credit-Boundary Read/Write Separation (`credit_verified=False` stages episodes in
         ephemeral scratch without polluting Woodbury precision state during inner-loop pondering), and
      4. Bi-Temporal Validity (`valid_from`, `invalidated_at`) + 2-hop Personalized PageRank (PPR)
         concept-token graph propagation (`HippoRAG 2` / `Graphiti` zero-embedding associative recall).
    """

    def __init__(self, dim: int = 16, ridge_lambda: float = 1.0) -> None:
        self.dim = max(4, min(64, int(dim)))
        self.ridge_lambda = max(1e-4, float(ridge_lambda))
        inv_l = 1.0 / self.ridge_lambda
        self._p_inv: list[list[float]] = [
            [inv_l if i == j else 0.0 for j in range(self.dim)]
            for i in range(self.dim)
        ]
        self._b_vec: list[float] = [0.0] * self.dim
        # (sig64, key_text, payload, utility, valid_from, invalidated_at, tokens_tuple)
        self._episodes: list[tuple[int, str, Any, float, float, float | None, tuple[str, ...]]] = []
        self._staged_ponder: list[tuple[str, Any, float]] = []

    @staticmethod
    def simhash64(tokens: Sequence[str]) -> int:
        acc = [0] * 64
        for tok in tokens:
            digest = hashlib.blake2b(tok.encode("utf-8", errors="ignore"), digest_size=8).digest()
            hv = int.from_bytes(digest, "big")
            for bit in range(64):
                acc[bit] += 1 if ((hv >> bit) & 1) else -1
        out = 0
        for bit in range(64):
            if acc[bit] >= 0:
                out |= 1 << bit
        return out

    def _feature_vec(self, tokens: Sequence[str]) -> list[float]:
        vec = [0.0] * self.dim
        for tok in tokens:
            h = int.from_bytes(hashlib.blake2b(tok.encode("utf-8", errors="ignore"), digest_size=4).digest(), "big")
            idx = h % self.dim
            sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
            vec[idx] += sign
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm for v in vec] if norm > 0.0 else vec

    def observe(
        self,
        key_text: str,
        payload: Any,
        utility: float = 1.0,
        *,
        credit_verified: bool = True,
    ) -> dict[str, Any]:
        # Memoir Law: never mutate persistent associative memory during unverified inner-loop pondering!
        if not credit_verified:
            self._staged_ponder.append((key_text, payload, float(utility)))
            return {"staged_only": True, "staged_count": len(self._staged_ponder), "episodes": len(self._episodes)}

        toks = tuple(dict.fromkeys(re.findall(r"[a-zA-Z0-9_]+", key_text.lower()) or [key_text]))
        sig64 = self.simhash64(toks)
        now = time.time()
        for idx_e, (e_sig, e_key, e_pay, e_util, e_vf, e_inv, e_toks) in enumerate(self._episodes):
            if e_inv is None and e_key == key_text and e_pay != payload:
                self._episodes[idx_e] = (e_sig, e_key, e_pay, e_util, e_vf, now, e_toks)

        x = self._feature_vec(toks)
        px = [sum(self._p_inv[i][j] * x[j] for j in range(self.dim)) for i in range(self.dim)]
        denom = 1.0 + sum(x[i] * px[i] for i in range(self.dim))
        if denom > 1e-12:
            inv_d = 1.0 / denom
            for i in range(self.dim):
                px_i = px[i] * inv_d
                row_i = self._p_inv[i]
                for j in range(self.dim):
                    row_i[j] -= px_i * px[j]
        for i in range(self.dim):
            self._b_vec[i] += x[i] * float(utility)
        self._episodes.append((sig64, key_text, payload, float(utility), now, None, toks))
        return {"simhash64": hex(sig64), "episodes": len(self._episodes), "staged_only": False}

    def query(self, query_text: str, *, top_k: int = 3, include_invalidated: bool = False) -> dict[str, Any]:
        toks = re.findall(r"[a-zA-Z0-9_]+", query_text.lower()) or [query_text]
        q_set = set(toks)
        q_sig = self.simhash64(toks)
        q_x = self._feature_vec(toks)
        theta = [sum(self._p_inv[i][j] * self._b_vec[j] for j in range(self.dim)) for i in range(self.dim)]
        woodbury_utility = sum(q_x[i] * theta[i] for i in range(self.dim))
        uncertainty = max(0.0, sum(q_x[i] * sum(self._p_inv[i][j] * q_x[j] for j in range(self.dim)) for i in range(self.dim))) ** 0.5

        active_eps = [ep for ep in self._episodes if (include_invalidated or ep[5] is None)]
        tok_to_ep_idxs: dict[str, list[int]] = {}
        for idx_a, ep in enumerate(active_eps):
            for tk in ep[6]:
                tok_to_ep_idxs.setdefault(tk, []).append(idx_a)
        ppr_mass = [0.0] * len(active_eps)
        seed_idxs = {idx_s for tk in q_set for idx_s in tok_to_ep_idxs.get(tk, ())}
        if seed_idxs:
            init_w = 1.0 / len(seed_idxs)
            for si in seed_idxs:
                ppr_mass[si] = init_w
            for _ in range(2):
                nxt_mass = [0.15 * (init_w if i in seed_idxs else 0.0) for i in range(len(active_eps))]
                for i_m, m_val in enumerate(ppr_mass):
                    if m_val <= 1e-9:
                        continue
                    ep_toks = active_eps[i_m][6]
                    neighbors = {nb for tk in ep_toks for nb in tok_to_ep_idxs.get(tk, ())}
                    if neighbors:
                        share = (0.85 * m_val) / len(neighbors)
                        for nb in neighbors:
                            nxt_mass[nb] += share
                ppr_mass = nxt_mass

        scored: list[tuple[float, dict[str, Any]]] = []
        for idx_a, (sig64, k_txt, payload, util, v_from, inv_at, _etoks) in enumerate(active_eps):
            hamming_sim = 1.0 - ((q_sig ^ sig64).bit_count() / 64.0)
            ppr_bonus = ppr_mass[idx_a]
            combined = 0.60 * hamming_sim + 0.25 * max(-1.0, min(1.0, util)) + 0.15 * ppr_bonus
            scored.append(
                (
                    combined,
                    {
                        "key": k_txt,
                        "payload": payload,
                        "vsa_similarity": round(hamming_sim, 4),
                        "ppr_score": round(ppr_bonus, 4),
                        "observed_utility": util,
                        "valid_from": v_from,
                        "invalidated_at": inv_at,
                        "combined_score": round(combined, 4),
                    },
                )
            )
        scored.sort(key=lambda pair: -pair[0])
        return {
            "schema": SCHEMA,
            "status": "PASS__VSA_WOODBURY_ASSOCIATED" if scored else "PASS__EMPTY_FAST_MEMORY",
            "pass": True,
            "query_simhash64": hex(q_sig),
            "woodbury_predicted_utility": round(woodbury_utility, 4),
            "epistemic_uncertainty": round(uncertainty, 4),
            "matches": [m for _, m in scored[: max(1, top_k)]],
            "episodes_indexed": len(active_eps),
            "staged_unverified_count": len(self._staged_ponder),
            "model_calls": 0,
            "parameters_stored": 0,
        }


def decide_one_shot_sufficiency_and_experiment(
    *,
    before_state: Mapping[str, bytes] | None = None,
    after_state: Mapping[str, bytes] | None = None,
    probe_states: Sequence[Mapping[str, bytes]] | None = None,
    precondition_table: Sequence[tuple[Iterable[str], bool]] | None = None,
    precondition_vocabulary: Sequence[str] | None = None,
    claim_text: str | None = None,
    version_space_examples: Sequence[tuple[tuple[Any, ...], Any]] | None = None,
) -> dict[str, Any]:
    """Decidable 1-Shot Sufficiency, Hidden-Precondition Abduction & Active Experiment Compiler (`K3 = 0`).

    Unifies:
      1. `demonstration_sufficiency_v1` (`space`, `experiment_table`, `sufficiency`, `decide`),
      2. `the_precondition_is_not_in_the_trace_v1.exact_precondition`,
      3. `the_right_question_is_an_experiment_v1.extract_claims`, and
      4. `settlement_v1` (`VersionSpace`, `settle`, `derive_probe_space`).
    """
    t0 = time.perf_counter()
    suff_doc: dict[str, Any] | None = None
    decision = "UNSPECIFIED"
    if isinstance(before_state, Mapping) and isinstance(after_state, Mapping):
        from canonical.swe_kernel import demonstration_sufficiency_v1 as dsuff

        hyps = dsuff.space(before_state)
        candidate_states = [dict(before_state)] + [dict(ps) for ps in (probe_states or ())]
        # Build explicit finite experiment table over `candidate_states`
        from canonical.runtime import finite_identifiability as fin_id

        exps: list[Any] = []
        state_ids: list[str] = []
        for idx_s, st_map in enumerate(candidate_states):
            sid = f"state_{idx_s}"
            state_ids.append(sid)
            outcomes_by_h = {
                h.id: dsuff.signature(
                    dsuff.apply(h.meta["kind"], st_map, src=h.meta.get("src"), dst=h.meta.get("dst"), n=int(h.meta.get("n", 0)))
                )
                for h in hyps
                if isinstance(getattr(h, "meta", None), Mapping)
            }
            if outcomes_by_h:
                exps.append(fin_id.Experiment(id=sid, outcomes=outcomes_by_h))
        obs_sig = dsuff.signature(after_state)
        observed = {"state_0": obs_sig}
        suff_verdict = dsuff.sufficiency(hyps, exps, observed, state_ids)
        decision = dsuff.decide(suff_verdict)
        suff_doc = {
            "decision": decision,
            "hypothesis_space_size": len(hyps),
            "verdict": suff_verdict,
        }

    precond_doc: tuple[str, ...] | None = None
    if precondition_table and precondition_vocabulary:
        from canonical.tools import the_precondition_is_not_in_the_trace_v1 as tpnt

        norm_tbl = [(frozenset(str(x) for x in fs), bool(ok)) for fs, ok in precondition_table]
        precond_doc = tpnt.exact_precondition(norm_tbl, list(precondition_vocabulary))

    claims_doc: list[dict[str, Any]] = []
    if claim_text:
        from canonical.tools import the_right_question_is_an_experiment_v1 as trqe

        claims_doc = trqe.extract_claims(claim_text)[:12]

    settlement_doc: dict[str, Any] | None = None
    if version_space_examples:
        from canonical.runtime import settlement_v1 as stlm

        probes = stlm.derive_probe_space(list(version_space_examples))
        settlement_doc = {
            "derived_probe_count": len(probes),
            "sample_probes": [list(p) for p in probes[:6]],
            "structure_diagnosis": stlm.diagnose_structure(list(version_space_examples)),
        }

    passed = bool(
        (suff_doc is not None and decision in ("act", "experiment"))
        or precond_doc is not None
        or len(claims_doc) > 0
        or settlement_doc is not None
    )
    return {
        "schema": SCHEMA,
        "status": f"PASS__SUFFICIENCY_DECISION_{decision.upper()}" if suff_doc else (
            "PASS__EXPERIMENT_AND_PRECONDITION_COMPILED" if passed else "FAIL_CLOSED__NO_SUFFICIENCY_WITNESS"
        ),
        "pass": passed,
        "decision": decision,
        "demonstration_sufficiency": suff_doc,
        "abduced_precondition": list(precond_doc) if precond_doc is not None else None,
        "compiled_experiment_claims": claims_doc,
        "settlement": settlement_doc,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def compose_and_calibrate_verified_skills(
    source_text: str,
    before_after_lessons: Sequence[tuple[str, str]],
    *,
    target_language: str = "python",
    pure_organ_source: str | None = None,
) -> dict[str, Any]:
    """Proved Skill Composition, Diagnostic Scope Calibration & 7-Language CST Transfer (`K3 = 0`).

    Unifies:
      1. `verified_skill_crystallizer_v1.anti_unify_code_rule`,
      2. `proved_composition_v1` (`compose`, `rule_op` — refuses dead premises, no-ops, reverts, and killed proofs!),
      3. `rule_scope_learning_v1` (`calibrate_rule_scope`, `synthesize_diagnostic_probes`),
      4. `tree_sitter_cst_skill_skeleton_v1` (`compile_rule_to_cst_skeleton`, `iter_cst_skeleton_candidates`), and
      5. `meta_circular_organ_graph_v1.verify_pure_organ_ast`.
    """
    from canonical.swe_kernel import meta_circular_organ_graph_v1 as mcog
    from canonical.swe_kernel import proved_composition_v1 as pcomp
    from canonical.swe_kernel import rule_scope_learning_v1 as rsl
    from canonical.swe_kernel import tree_sitter_cst_skill_skeleton_v1 as tscss
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as vsc

    t0 = time.perf_counter()
    rules: list[dict[str, Any]] = []
    scope_reports: list[dict[str, Any]] = []
    ops: list[Any] = []
    for idx_l, (b_snip, a_snip) in enumerate(before_after_lessons):
        rule = vsc.anti_unify_code_rule(b_snip, a_snip, language="python")
        if not isinstance(rule, dict):
            continue
        rules.append(rule)
        ops.append(pcomp.rule_op(f"lesson_{idx_l}", rule))
        try:
            cal = rsl.calibrate_rule_scope(rule)
            scope_reports.append(
                {
                    "skill_id": rule.get("skill_id"),
                    "learned_scope": cal.get("learned_scope") or cal.get("surviving_scope") or cal.get("status"),
                    "probes_synthesized": len(rsl.synthesize_diagnostic_probes(rule)),
                }
            )
        except Exception:
            pass

    comp_verdict: dict[str, Any] | None = None
    composed_output: str | None = None
    cst_transferred: list[str] = []

    if target_language == "python" and ops:
        comp_verdict = pcomp.compose(source_text, ops)
        if comp_verdict.get("verdict") == pcomp.PASS:
            composed_output = str(comp_verdict.get("output") or comp_verdict.get("final_state") or "")
    elif target_language != "python" and rules:
        cur_src = source_text
        for rule in rules:
            skel = tscss.compile_rule_to_cst_skeleton(rule)
            if skel is None:
                continue
            cands = list(tscss.iter_cst_skeleton_candidates(cur_src, rule, target_language=target_language, max_candidates=4))
            if cands:
                cur_src = cands[0]
                cst_transferred.append(cur_src)
        if cst_transferred and cur_src != source_text:
            composed_output = cur_src

    pure_organ_valid: bool | None = None
    if pure_organ_source is not None:
        try:
            mcog.verify_pure_organ_ast(pure_organ_source)
            pure_organ_valid = True
        except Exception:
            pure_organ_valid = False

    passed = bool(
        (comp_verdict is not None and comp_verdict.get("verdict") == pcomp.PASS)
        or (target_language != "python" and composed_output is not None)
    )
    refusal_code = str((comp_verdict or {}).get("verdict") or "NO_APPLICABLE_COMPOSITION")
    return {
        "schema": SCHEMA,
        "status": "PASS__PROVED_SKILL_COMPOSITION" if passed else f"FAIL_CLOSED__{refusal_code}",
        "pass": passed,
        "target_language": target_language,
        "rules_crystallized": len(rules),
        "scope_calibrations": scope_reports,
        "composition_receipt": comp_verdict,
        "output_source": composed_output,
        "cst_candidates": cst_transferred[:4],
        "pure_organ_ast_verified": pure_organ_valid,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def induce_hypothesis_and_vocabulary_unified(
    points: Sequence[tuple[Any, Any]] | None = None,
    *,
    param_names: Sequence[str] = ("x",),
    candidate_domain: Sequence[Any] | None = None,
    corpus_bodies: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Unifies `hypothesis_classes_v1` (symbolic/piecewise law fitting + active query design)
    and `vocabulary_induction_v1` (sleep/wake library compression & non-forgetting concept growth).
    """
    from canonical.runtime import hypothesis_classes_v1 as hc
    from canonical.runtime import vocabulary_induction_v1 as vi

    t0 = time.perf_counter()
    hyp_doc: dict[str, Any] | None = None
    if points:
        raw_pts = [(pt[0][0] if isinstance(pt[0], tuple) and len(pt[0]) == 1 else pt[0], pt[1]) for pt in points]
        fitted = hc.fit_all(raw_pts)
        det = hc.determine(raw_pts)
        next_query = hc.question_for(raw_pts) if len(fitted) != 1 else None
        top_row = fitted[0] if fitted else None
        top_expr = top_row.get("formula") or top_row.get("expression") or str(top_row) if isinstance(top_row, Mapping) else (str(top_row) if top_row is not None else None)
        hyp_doc = {
            "surviving_count": len(fitted),
            "determined": bool(det.get("determined") or len(fitted) == 1),
            "top_expression": top_expr,
            "active_disambiguating_query": next_query,
            "determination": det,
        }

    vocab_doc: dict[str, Any] | None = None
    if corpus_bodies:
        onto = vi.Ontology()
        encounters = [vi.encounter(onto, list(corpus_bodies))]
        vocab_doc = {
            "concepts_induced": len(getattr(onto, "concepts", ())),
            "concept_names": [getattr(c, "name", str(c)) for c in list(getattr(onto, "concepts", ()))[:12]],
            "encounter_summary": encounters[0] if encounters else {},
        }

    passed = bool((hyp_doc and hyp_doc["surviving_count"] > 0) or (vocab_doc and vocab_doc["concepts_induced"] >= 0))
    return {
        "schema": SCHEMA,
        "status": "PASS__HYPOTHESIS_AND_VOCABULARY_INDUCED" if passed else "FAIL_CLOSED__INSUFFICIENT_OBSERVATIONS",
        "pass": passed,
        "hypothesis": hyp_doc,
        "vocabulary": vocab_doc,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def teach_edit_by_example_unified(
    target_source: str,
    before_example: str,
    after_example: str,
) -> dict[str, Any]:
    """1-Shot Program-Transformation Transfer (`canonical.swe_kernel.taught_actions.edit_by_example_v1`).

    Infers the structural AST edit law mapping `before_example -> after_example` and applies
    it deterministically to `target_source` (`0` model calls, `0` stored weights).
    """
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe

    t0 = time.perf_counter()
    out_src: str | None = None
    raw_res: Any = None
    try:
        raw_res = ebe.edit_by_example(target_source, before_example, after_example)
        if isinstance(raw_res, str):
            out_src = raw_res
        elif isinstance(raw_res, Mapping):
            out_src = raw_res.get("edited") or raw_res.get("result") or raw_res.get("source")
    except Exception as exc_ebe:
        raw_res = {"refused": str(exc_ebe)}
        try:
            from canonical.runtime import edit_kind_learning_v1 as ekl

            ops = ekl.operators_of([(before_example, after_example)])
            if ops:
                t_tree = ast.parse(target_source)
                for node in ast.walk(t_tree):
                    for op in ops:
                        env = ekl.fits(op.lhs, node)
                        if env is not None:
                            repl = ekl.built(op.rhs, env)
                            cand_s = _replace_node_segment(target_source, node, ast.unparse(repl))
                            if cand_s and cand_s != target_source:
                                out_src = cand_s
                                break
                    if out_src is not None:
                        break
        except Exception:
            pass
    passed = bool(isinstance(out_src, str) and out_src != target_source)
    return {
        "schema": SCHEMA,
        "status": "PASS__TAUGHT_EDIT_TRANSFERRED" if passed else "FAIL_CLOSED__NO_UNIQUE_EDIT_MATCH",
        "pass": passed,
        "edited_source": out_src,
        "raw_result": raw_res,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
        "parameters_stored": 0,
    }


# ---------------------------------------------------------------------------
# 9B. IN-MEMORY SINGLE-RUN RELATION & TYPE-HABITATION ABDUCER (ZERO DISK I/O)
# ---------------------------------------------------------------------------


class InMemoryRelationAndHabitationAbducer:
    """Unifies `the_relation_is_read_from_the_failing_run_v1` (live runtime value
    relation abduction), `metamorphic_habitation_zipper_v1` (`generate_type_habitation_candidates`),
    and `cow_angelic_zygote_v1` (`synthesize_algebraic_differential_repairs`) purely in RAM.

    Probes the top localized file in a single Copy-on-Write child via `_InMemoryModuleOverrideFinder`
    (injecting `__brain_rel__` into `module.__dict__` with zero disk writes and zero `builtins` mutation!).
    """

    @classmethod
    def probe_live_relations_in_ram(
        cls,
        repo_dir: pathlib.Path,
        source_rel: str,
        probe_target: str,
        only_lines: set[int] | None = None,
        *,
        timeout_s: float = 3.5,
    ) -> dict[str, Any]:
        if not hasattr(os, "fork") or threading.active_count() > 1 or not _has_pytest():
            return {}
        rel_to_mod = build_rel_to_module_map(repo_dir)
        mod_info = rel_to_mod.get(source_rel)
        src_fp = repo_dir / source_rel
        if mod_info is None or not src_fp.is_file():
            return {}
        try:
            from canonical.tools import the_relation_is_read_from_the_failing_run_v1 as trr

            orig_source = src_fp.read_text(encoding="utf-8", errors="replace")
            if len(orig_source) > 55_000:
                return {}
            all_sites = trr.sites_in(orig_source)
            sites = [s for s in all_sites if (not only_lines or s.line in only_lines)][:48]
            if not sites:
                sites = all_sites[:48]
            carried = trr.instrument(orig_source, sites)
            if carried == orig_source:
                return {}
            ast.parse(carried)
        except Exception:
            return {}

        mod_name, abs_orig, is_pkg = mod_info
        pkg_roots = WarmCoWForkScreener._discover_top_packages(repo_dir)
        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            payload = b"{}"
            try:
                import itertools
                import pytest

                signal.setitimer(signal.ITIMER_REAL, max(0.6, min(1.3, timeout_s)))
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)
                os.close(devnull)
                os.chdir(str(repo_dir))

                samples: dict[int, list[dict[str, Any]]] = {}
                facts: dict[str, Any] = {"message": None, "assertions": [], "exception_type": None, "reports": []}
                budget = {"left": 500}

                def _shape(val: Any) -> dict[str, Any]:
                    snap: dict[str, Any] = {
                        "type": type(val).__name__,
                        "module": getattr(type(val), "__module__", None),
                        "repr": None,
                        "is_none": val is None,
                    }
                    try:
                        snap["truth"] = bool(val)
                    except Exception:
                        snap["truth"] = None
                    try:
                        sz = len(val)
                        snap["len"] = sz
                    except Exception:
                        sz = None
                    try:
                        snap["repr"] = repr(val)[:120]
                    except Exception:
                        snap["repr"] = "<unrepr>"
                    try:
                        hash(val)
                        snap["hashable"] = True
                    except Exception:
                        snap["hashable"] = False
                    if sz is not None and sz > 5000:
                        return snap
                    try:
                        snap["items"] = sorted(repr(it)[:80] for it in itertools.islice(iter(val), 8))
                    except Exception:
                        pass
                    try:
                        snap["keys"] = sorted(repr(k)[:80] for k in itertools.islice(iter(val.keys()), 8))
                    except Exception:
                        pass
                    return snap

                def _probe_rel(index: int, thunk: Callable[[], Any], label: Any = None) -> Any:
                    val = thunk()
                    idx_i = int(index)
                    bkt = samples.get(idx_i)
                    if bkt is None:
                        samples[idx_i] = [_shape(val)]
                    elif len(bkt) < 4 and budget["left"] > 0:
                        bkt.append(_shape(val))
                        budget["left"] -= 1
                    return val

                class _RelPlugin:
                    def pytest_runtest_logreport(self, report: Any) -> None:
                        if getattr(report, "when", "") == "call":
                            if len(facts["reports"]) < 500:
                                facts["reports"].append([report.nodeid, report.outcome])
                            if report.failed:
                                longrepr = getattr(report, "longrepr", None)
                                crash = getattr(longrepr, "reprcrash", None)
                                facts["message"] = str(crash.message)[:1800] if crash is not None else str(longrepr)[-1800:]
                                try:
                                    facts["exception_type"] = (
                                        type(longrepr.excinfo[1]).__name__ if getattr(longrepr, "excinfo", None) else None
                                    )
                                except Exception:
                                    facts["exception_type"] = None

                    def pytest_assertrepr_compare(self, config: Any, op: str, left: Any, right: Any) -> None:
                        if len(facts["assertions"]) < 8:
                            try:
                                facts["assertions"].append({"op": op, "left": _shape(left), "right": _shape(right)})
                            except Exception:
                                pass
                        return None

                _evict_repo_and_test_modules(pkg_roots, [mod_name])
                finder = _InMemoryModuleOverrideFinder(
                    {mod_name: (abs_orig, carried, is_pkg)},
                    injected_globals={"__brain_rel__": _probe_rel},
                )
                sys.meta_path.insert(0, finder)
                if (repo_dir / "src").is_dir():
                    if str(repo_dir) not in sys.path:
                        sys.path.insert(0, str(repo_dir))
                    if str(repo_dir / "src") not in sys.path:
                        sys.path.insert(0, str(repo_dir / "src"))
                elif str(repo_dir) not in sys.path:
                    sys.path.insert(0, str(repo_dir))
                importlib.invalidate_caches()
                os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

                with ZeroOverheadLineMonitor(repo_dir, exclude_tests=True) as mon:
                    pytest.main(
                        ["-q", "--no-header", "-x", "-p", "no:cacheprovider", "-o", "addopts=", "--tb=short", probe_target],
                        plugins=[_RelPlugin()],
                    )
                payload = json.dumps(
                    {
                        "samples": {str(k): v for k, v in samples.items()},
                        "facts": facts,
                        "sites": [s.as_dict() for s in sites],
                        "executed_lines": sorted(ln for rel_x, ln in mon.hits if rel_x == source_rel),
                    }
                ).encode("utf-8")
            except BaseException:
                payload = b"{}"
            finally:
                try:
                    _fork_pipe_write_all(w_fd, payload)
                    os.close(w_fd)
                except OSError:
                    pass
                os._exit(0)

        os.close(w_fd)
        raw_bytes, _ = _fork_wait_and_drain(pid, r_fd, timeout_s)
        try:
            return json.loads(raw_bytes.decode("utf-8") or "{}")
        except Exception:
            return {}

    @classmethod
    def synthesize(
        cls,
        repo_dir: pathlib.Path,
        spectrum: CausalFaultSpectrum,
        zipper: CodePlanObligationZipper,
        *,
        max_candidates: int = 64,
    ) -> list[CandidatePatch]:
        """Generate trace-licensed relation edits + type-habitation + algebraic differential candidates in memory."""
        out: list[CandidatePatch] = []
        seen: set[str] = set()

        def _add_patch(family: str, rel_file: str, orig_s: str, patched_s: str, desc: str) -> None:
            if len(out) >= max_candidates or not patched_s or patched_s == orig_s:
                return
            dig = hashlib.sha256(f"{rel_file}\0{patched_s}".encode("utf-8")).hexdigest()[:16]
            if dig in seen:
                return
            try:
                new_tree = ast.parse(patched_s)
            except SyntaxError:
                return
            seen.add(dig)
            bundle = zipper.propagate_default_arg_obligations(rel_file, orig_s, patched_s, patched_tree=new_tree)
            out.append(
                CandidatePatch(
                    patch_id=f"{family}:{dig}",
                    family=family,
                    patched_files=bundle,
                    description=desc,
                    mdl_delta_bytes=len(patched_s.encode("utf-8")) - len(orig_s.encode("utf-8")),
                )
            )

        # 1. Single-run live relation abduction (`the_relation_is_read_from_the_failing_run_v1`) on top localized file
        probe_target = spectrum.failing_nodes[0] if spectrum.failing_nodes else (spectrum.enclosing_files[0] if spectrum.enclosing_files else "")
        live_rt_vars_by_file: dict[str, dict[str, Any]] = {}
        if probe_target:
            try:
                from canonical.tools import the_relation_is_read_from_the_failing_run_v1 as trr

                for rel_f in spectrum.ranked_files[:1]:
                    fp = repo_dir / rel_f
                    if not fp.is_file():
                        continue
                    orig_s = fp.read_text(encoding="utf-8", errors="replace")
                    hot_set = set(spectrum.suspect_lines.get(rel_f) or ())
                    traced = cls.probe_live_relations_in_ram(repo_dir, rel_f, probe_target, hot_set or None, timeout_s=1.5)
                    if not traced or not traced.get("facts"):
                        continue
                    facts = traced["facts"]
                    wanted = trr.demanded_values(facts)
                    msg = str(facts.get("message") or "")
                    forb_tok = trr.forbidden_token(facts)
                    demanded_raise = trr.raises_demand(msg)
                    samples = {int(k): v for k, v in (traced.get("samples") or {}).items()}
                    exec_here = set(traced.get("executed_lines") or hot_set)
                    if exec_here:
                        lst_s = spectrum.suspect_lines.setdefault(rel_f, [])
                        for lx in exec_here:
                            if lx not in lst_s:
                                lst_s.append(lx)

                    sites = [
                        trr.Site(
                            r["index"], r["line"], r["end_line"], r["col"], r["end_col"],
                            r["text"], r["kind"], r["context"], r.get("ifexp"), r.get("branches"),
                        )
                        for r in (traced.get("sites") or ())
                    ]
                    by_index = {s.index: s for s in sites}
                    all_sites = trr.sites_in(orig_s)
                    by_all = {s.index: s for s in all_sites}
                    linked = trr.linked_patterns(orig_s)

                    # Harvest live runtime variable types from sampled simple identifiers for Type-Habitation!
                    rt_map: dict[str, Any] = {}
                    for idx_s, vals_s in samples.items():
                        st_obj = by_index.get(idx_s) or by_all.get(idx_s)
                        if st_obj is not None and st_obj.text.isidentifier() and vals_s:
                            v0 = vals_s[0]
                            rt_map[st_obj.text] = {
                                "type": v0.get("type", ""),
                                "is_none": bool(v0.get("is_none")),
                                "is_falsey": (v0.get("truth") is False and not v0.get("is_none")),
                                "has_nl": "\\n" in str(v0.get("repr") or ""),
                            }
                            if v0.get("type") == "generator":
                                rt_map.setdefault("__gen_lines__", []).append(st_obj.line)
                    if rt_map:
                        live_rt_vars_by_file[rel_f] = rt_map

                    for line_p, names_p in (linked or {}).items():
                        if not names_p:
                            continue
                        users = [
                            val_u for idx2, val_u in samples.items()
                            if by_index.get(idx2) is not None
                            and by_index[idx2].kind == "regex_argument"
                            and by_index[idx2].context.split("Call:", 1)[-1] in names_p
                        ]
                        if users:
                            for s2 in all_sites:
                                if s2.kind == "regex" and line_p in (s2.line, s2.end_line) and s2.index not in samples:
                                    samples[s2.index] = [{"type": "Pattern", "truth": True, "is_none": False, "repr": "<pattern>"}]
                                    exec_here.add(s2.line)

                    hyps: list[dict[str, Any]] = []
                    sites_inside_all = [
                        (by_index[i] if i in by_index else by_all[i], v)
                        for i, v in sorted(samples.items())[:48]
                        if (i in by_index or i in by_all)
                    ]
                    for idx_h, vals_h in sorted(samples.items())[:48]:
                        st_h = by_index.get(idx_h) or by_all.get(idx_h)
                        if st_h is None or (exec_here and st_h.line not in exec_here):
                            continue
                        hyps.extend(
                            trr.relations_for(
                                st_h,
                                vals_h,
                                wanted,
                                facts.get("exception_type"),
                                msg,
                                forbidden=forb_tok,
                                wanted_raise=demanded_raise,
                                patterns_linked=linked,
                                sites_inside=[( sx, vx ) for sx, vx in sites_inside_all if sx.index != idx_h][:24],
                            )
                        )
                    for hyp in hyps[:16]:
                        st_target = by_index.get(hyp["site"]) or by_all.get(hyp["site"])
                        if st_target is None:
                            continue
                        edited = trr.apply_edit(orig_s, st_target, str(hyp["edit"]), str(hyp["relation"]))
                        if edited:
                            _add_patch(
                                f"relation:{hyp['relation']}",
                                rel_f,
                                orig_s,
                                edited,
                                f"live-relation {hyp['relation']} at L{hyp['line']}",
                            )

                    # 1b. Zero-Extra-Fork Formatted-Message Blame & Guard Derivation (`the_failing_run_names_the_expression_v1`)
                    try:
                        from canonical.tools import the_failing_run_names_the_expression_v1 as tfrne

                        blame_records: list[dict[str, Any]] = []
                        for idx_b, vals_b in sorted(samples.items())[:64]:
                            st_b = by_index.get(idx_b) or by_all.get(idx_b)
                            if st_b is None or not vals_b:
                                continue
                            for vb in vals_b[:2]:
                                blame_records.append(
                                    {
                                        "line": int(st_b.line),
                                        "expr": str(st_b.text),
                                        "value": str(vb.get("repr") or ""),
                                        "type": str(vb.get("type") or ""),
                                    }
                                )
                        fail_txt = f"{msg}\n{spectrum.raw_output[-1200:]}"
                        blamed_items = tfrne.blame_from_messages(blame_records, fail_txt) or tfrne.blame(blame_records, fail_txt)[:4]
                        for b_it in blamed_items[:4]:
                            g_span = tfrne.guard_span(orig_s, int(b_it["line"]))
                            if g_span is None:
                                continue
                            g_ln, g_txt, s_off, e_off = g_span
                            for cand_guard in tfrne.derived_candidates(g_txt, str(b_it["expr"]), str(b_it["value"]))[:4]:
                                spliced_g = orig_s[:s_off] + cand_guard + orig_s[e_off:]
                                _add_patch(
                                    "failing_run_blame:guard_exclusion",
                                    rel_f,
                                    orig_s,
                                    spliced_g,
                                    f"blamed `{b_it['expr']}={b_it['value']}` guard exclusion at L{g_ln}",
                                )
                    except Exception:
                        pass
            except Exception:
                pass

        # 2. Pure in-memory Type-Habitation (`metamorphic_habitation_zipper_v1`)
        #    + Algebraic Differential Lenses (`cow_angelic_zygote_v1`)
        #    + Angelic OE Structural Patches (`angelic_oe_synthesizer_v1`)
        #    + Grammar-Closed Operator Swaps (`grammar_closed_repair_v1`)
        try:
            from canonical.swe_kernel import angelic_oe_synthesizer_v1 as aoe
            from canonical.swe_kernel import cow_angelic_zygote_v1 as caz
            from canonical.swe_kernel import metamorphic_habitation_zipper_v1 as mhz
            from canonical.tools import grammar_closed_repair_v1 as gcr

            profile = mhz.mine_repo_idiom_profile(repo_dir)
            assert_lits = mhz._parse_assertion_literals(spectrum.raw_output)
            uncaught_excs = [(m.group(1), m.group(2).strip()) for m in mhz._UNCAUGHT_EXC_RE.finditer(spectrum.raw_output)]
            loc_bundle = mhz.FaultLocalizationBundle(
                failing_nodeids=list(spectrum.failing_nodes),
                ranked_files=list(spectrum.ranked_files[:5]),
                executed_lines={rf: set(lns) for rf, lns in spectrum.suspect_lines.items()},
                traceback_lines={rf: list(lns[:8]) for rf, lns in spectrum.suspect_lines.items()},
                runtime_types=live_rt_vars_by_file,
                uncaught_exceptions=uncaught_excs,
                assertion_literals=assert_lits,
                raw_output=spectrum.raw_output,
            )
            for rel_f in spectrum.ranked_files[:4]:
                fp = repo_dir / rel_f
                if not fp.is_file():
                    continue
                orig_s = fp.read_text(encoding="utf-8", errors="replace")
                act_lines = set(spectrum.suspect_lines.get(rel_f) or ())
                for hc in mhz.generate_type_habitation_candidates(repo_dir, rel_f, loc_bundle, profile, max_candidates=16):
                    _add_patch(f"mhz:{hc.mechanism}", rel_f, orig_s, hc.patched_source, hc.description)
                for ac in caz.synthesize_algebraic_differential_repairs(repo_dir, rel_f, act_lines, spectrum.raw_output, max_candidates=12):
                    _add_patch(f"caz:{ac.mechanism}", rel_f, orig_s, ac.patched_source, ac.description)
                if act_lines and len(orig_s) <= 45_000:
                    try:
                        for oe_row in aoe.synthesize_causal_structural_patches(orig_s, sorted(act_lines)[:8])[:6]:
                            oe_src = oe_row[0] if isinstance(oe_row, tuple) else (oe_row.get("patched_source") if isinstance(oe_row, Mapping) else None)
                            oe_dsc = oe_row[1] if (isinstance(oe_row, tuple) and len(oe_row) > 1) else "angelic_oe_structural"
                            if isinstance(oe_src, str):
                                _add_patch("angelic_oe:structural", rel_f, orig_s, oe_src, str(oe_dsc))
                    except Exception:
                        pass
                    try:
                        tree_gc = ast.parse(orig_s)
                        gc_added = 0
                        for nd_gc in ast.walk(tree_gc):
                            if gc_added >= 6:
                                break
                            if getattr(nd_gc, "lineno", 0) not in act_lines or not isinstance(nd_gc, (ast.Compare, ast.BinOp, ast.BoolOp)):
                                continue
                            for swapped_txt in gcr.operator_swaps(nd_gc)[:3]:
                                sp_gc = _replace_node_segment(orig_s, nd_gc, swapped_txt)
                                if sp_gc:
                                    _add_patch("grammar_closed:op_swap", rel_f, orig_s, sp_gc, f"grammar-closed swap at L{nd_gc.lineno}")
                                    gc_added += 1
                    except Exception:
                        pass
        except Exception:
            pass

        return out


# ---------------------------------------------------------------------------
# 10. TOP-LEVEL PORTFOLIO WORKSPACE REPAIR (`run_unified_epistemic_portfolio`)
# ---------------------------------------------------------------------------


def run_unified_epistemic_portfolio(
    *,
    workspace_dir: pathlib.Path,
    goal_text: str = "",
    pytest_targets: Sequence[str] | None = None,
    suspect_files: Sequence[str] | None = None,
    skill_store: EStitchSemanticSkillStore | None = None,
    timeout_s: float = 45.0,
) -> dict[str, Any]:
    """Execute the full zero-model (`K3 = 0`) multi-organ SWE portfolio with
    Warm CoW Fork Screening and Whole-Slice Mutant-Killing Verification.
    """
    t0 = time.perf_counter()
    ws = workspace_dir.resolve()
    active_skills = skill_store if skill_store is not None else shared_semantic_skill_store()
    organ_trace: list[str] = []

    if not ws.is_dir():
        return {
            "schema": SCHEMA,
            "status": "INVALID_WORKSPACE",
            "pass": False,
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # Stage P0: Environment layout & polyglot dispatch (`the_environment_broker_v1` + C/JS CEGIS)
    layout_info: dict[str, Any] = {}
    try:
        from canonical.swe_kernel import the_environment_broker_v1 as env_broker

        layout_info = env_broker.detect_layout(ws)
        organ_trace.append(f"env_broker:{layout_info.get('language', 'unknown')}")
    except Exception:
        organ_trace.append("env_broker:fallback")

    c_files = [p for p in ws.rglob("*.c") if ".git" not in p.parts][:8]
    js_files = [p for p in ws.rglob("*.js") if ".git" not in p.parts and "node_modules" not in p.parts][:8]
    rs_files = [p for p in ws.rglob("*.rs") if ".git" not in p.parts and "target" not in p.parts][:8]
    go_files = [p for p in ws.rglob("*.go") if ".git" not in p.parts][:8]
    ts_files = [p for p in ws.rglob("*.ts") if ".git" not in p.parts and "node_modules" not in p.parts][:8]
    cpp_files = [p for p in (*ws.rglob("*.cpp"), *ws.rglob("*.cc")) if ".git" not in p.parts][:8]
    java_files = [p for p in ws.rglob("*.java") if ".git" not in p.parts][:8]
    py_files = sorted(
        p.relative_to(ws).as_posix()
        for p in ws.rglob("*.py")
        if ".git" not in p.parts and "__pycache__" not in p.parts
    )

    if not py_files and (rs_files or go_files or ts_files or cpp_files or java_files):
        try:
            from canonical.swe_kernel import polyglot_build_ci_engine_v1 as poly_ci

            poly_res: dict[str, Any] | None = None
            poly_regime = ""
            if rs_files:
                poly_res = poly_ci.rust_repair_and_verify(ws)
                poly_regime = "POLYGLOT_RUST_CARGO_REPAIR"
            elif go_files:
                poly_res = poly_ci.go_repair_and_verify(ws)
                poly_regime = "POLYGLOT_GO_REPAIR"
            elif ts_files:
                poly_res = poly_ci.ts_repair_and_verify(ws)
                poly_regime = "POLYGLOT_TS_REPAIR"
            if poly_res and (poly_res.get("pass") or poly_res.get("verified") or poly_res.get("status") == "VERIFIED"):
                organ_trace.append(f"polyglot_ci:{poly_regime}")
                return {
                    "schema": SCHEMA,
                    "status": "VERIFIED",
                    "pass": True,
                    "regime": poly_regime,
                    "mechanism": "polyglot_build_ci_engine_v1",
                    "organ_trace": organ_trace,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
        except Exception:
            pass

    if not py_files and c_files:
        try:
            from canonical.swe_kernel import c_asan_cegis_repair_v1 as c_cegis

            c_res = c_cegis.repair_c_repo_asan_cegis(ws, timeout_s=min(20.0, timeout_s))
            organ_trace.append(f"c_asan_cegis:{c_res.get('status')}")
            if c_res.get("repaired") or c_res.get("pass") or c_res.get("status") == "VERIFIED":
                return {
                    "schema": SCHEMA,
                    "status": "VERIFIED",
                    "pass": True,
                    "regime": "POLYGLOT_C_ASAN_CEGIS",
                    "mechanism": "c_asan_cegis_repair_v1",
                    "organ_trace": organ_trace,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
        except Exception:
            pass

    if not py_files and js_files:
        try:
            from canonical.swe_kernel import js_causal_cegis_repair_v1 as js_cegis

            js_res = js_cegis.repair_js_repo_causal_cegis(ws, timeout_s=min(20.0, timeout_s))
            organ_trace.append(f"js_causal_cegis:{js_res.get('status')}")
            if js_res.get("repaired") or js_res.get("pass") or js_res.get("status") == "VERIFIED":
                return {
                    "schema": SCHEMA,
                    "status": "VERIFIED",
                    "pass": True,
                    "regime": "POLYGLOT_JS_CAUSAL_CEGIS",
                    "mechanism": "js_causal_cegis_repair_v1",
                    "organ_trace": organ_trace,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
        except Exception:
            pass

    # Discover Python test targets
    targets = list(pytest_targets) if pytest_targets else [
        f for f in py_files if pathlib.Path(f).name.startswith(("test_", "check_")) or f.endswith("_test.py")
    ][:6]
    if not targets:
        return {
            "schema": SCHEMA,
            "status": "NO_TEST_TARGETS",
            "pass": False,
            "organ_trace": organ_trace,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # Stage P1: Fast Zero-Cold-Start Baseline Run (`run_test_targets_fast` via CoW fork + diversity scheduler + in-session failing line hits!)
    init_timeout = min(12.0, max(4.5, timeout_s * 0.28))
    init_run = run_test_targets_fast(ws, targets, timeout_s=init_timeout, verbose=True, collect_line_hits=True, maxfail=20)
    organ_trace.append(f"init_run:{init_run['status']}:rc={init_run['returncode']}:{init_run.get('elapsed_ms', 0)}ms")
    if init_run["status"] == "TIMEOUT":
        return {
            "schema": SCHEMA,
            "status": "INIT_TEST_TIMEOUT",
            "pass": False,
            "organ_trace": organ_trace,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }
    if init_run["returncode"] == 0:
        return {
            "schema": SCHEMA,
            "status": "ALREADY_PASSING",
            "pass": False,
            "organ_trace": organ_trace,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    enc_files = enclosing_test_files(ws, targets)

    # Stage P2: Multi-Signal Causal Localization + Proactive `CodePlan` Dependency Zipper
    spectrum = MultiSignalCausalLocalizer.localize(ws, targets, init_run)
    if suspect_files:
        merged_ranked = list(dict.fromkeys([*suspect_files, *spectrum.ranked_files]))
        spectrum.ranked_files = merged_ranked
    # Demote pure-constant generated lookup tables (>80 KB with zero `def ` / `class ` bodies) behind executable modules
    exec_first: list[str] = []
    data_only: list[str] = []
    for rf_cand in spectrum.ranked_files:
        fp_c = ws / rf_cand
        try:
            if fp_c.is_file() and fp_c.stat().st_size > 80_000:
                txt_c = fp_c.read_text(encoding="utf-8", errors="replace")
                if "def " not in txt_c:
                    data_only.append(rf_cand)
                    continue
        except OSError:
            pass
        exec_first.append(rf_cand)
    spectrum.ranked_files = exec_first + data_only
    zipper = CodePlanObligationZipper(ws)
    organ_trace.append(f"localized:{spectrum.failure_kind}:top={spectrum.ranked_files[:3]}")

    # Pre-read localized repo sources & enclosing test sources once in memory (shared across 3D, 3E, 3F)
    localized_repo_sources: dict[str, str] = {}
    for rf_loc in spectrum.ranked_files[:6]:
        fp_loc = ws / rf_loc
        if fp_loc.is_file():
            try:
                localized_repo_sources[rf_loc] = fp_loc.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    localized_test_sources: dict[str, str] = {}
    for tf_loc in enc_files[:4]:
        fp_tf = ws / tf_loc
        if fp_tf.is_file():
            try:
                localized_test_sources[tf_loc] = fp_tf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

    # Stage P3: Single-Pass Unified In-Memory Synthesis -> Sub-Millisecond Bytecode Hot-Swap Zygote Screening!
    fast_targets = spectrum.failing_nodes[:16] if (_has_pytest() and spectrum.failing_nodes) else targets[:4]
    unified_candidates: list[CandidatePatch] = []
    seen_patch_sigs: set[str] = set()

    def _enqueue_unique(cands_iter: Sequence[CandidatePatch]) -> None:
        for cp in cands_iter:
            sig = hashlib.sha256(
                "\0".join(f"{k}:{v}" for k, v in sorted(cp.patched_files.items())).encode("utf-8")
            ).hexdigest()[:16]
            if sig not in seen_patch_sigs:
                seen_patch_sigs.add(sig)
                unified_candidates.append(cp)

    # 3A. O(1) Learned Open AST Operators (`edit_kind_learning_v1`) + 7-Language CST Skeletons (`tree_sitter_cst_skill_skeleton_v1`)
    for rel_f, orig_l in list(localized_repo_sources.items())[:3]:
        hot_l = set(spectrum.suspect_lines.get(rel_f) or ())
        _enqueue_unique(active_skills.apply_learned_operators(rel_f, orig_l, hot_l))
        _enqueue_unique(active_skills.apply_cross_language_cst_skills(rel_f, orig_l, "python", suspect_lines=sorted(hot_l) or None))

    # 3B. First-Principles Morphisms (`M1`-`M10`)
    _enqueue_unique(FirstPrinciplesMorphismSynthesizer.synthesize(ws, spectrum, zipper, max_candidates=64))

    # 3C. Single-Run In-RAM Relation Abduction (`the_relation_is_read_from_the_failing_run_v1`)
    #     + Codebase Type-Habitation (`metamorphic_habitation_zipper_v1`)
    #     + Algebraic Differential Lenses (`cow_angelic_zygote_v1`)
    _enqueue_unique(InMemoryRelationAndHabitationAbducer.synthesize(ws, spectrum, zipper, max_candidates=36))

    # 3D. Pure In-Memory `reverse_tomography_algebra_v1` & FULL `residual_wall_closers_v1` (`repo_sources` + `test_sources`!)
    try:
        from canonical.swe_kernel import residual_wall_closers_v1 as rwc
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta

        closer = rwc.ResidualWallCloser()
        extra_cands: list[CandidatePatch] = []
        m_exc_t = re.search(r"\b([A-Z][A-Za-z0-9_]*(?:Error|Exception))\b", spectrum.raw_output)
        exc_type_s = m_exc_t.group(1) if m_exc_t else ""
        for rel_f in spectrum.ranked_files[:3]:
            orig_s = localized_repo_sources.get(rel_f)
            if not orig_s:
                continue
            traced_s = set(spectrum.suspect_lines.get(rel_f) or ())
            for gen_name, gen_fn in (
                ("rta_shadow", lambda s=orig_s, t=traced_s: rta.synthesize_dataflow_shadow_subst_patches(s, t)),
                ("rta_habitation", lambda s=orig_s, t=traced_s: rta.mine_repo_type_habitation_patches(ws, s, t, exc_type=exc_type_s, max_patches=12)),
                ("rta_callee_hook", lambda s=orig_s, t=traced_s: rta.synthesize_callee_hook_fallback_patches(s, t)),
                ("rta_bracket", lambda s=orig_s, t=traced_s: rta.synthesize_bracket_safe_partition_patches(s, t, exc_msg=spectrum.raw_output[-400:])),
                ("rta_regex", lambda s=orig_s, t=traced_s: rta.synthesize_regex_refinement_patches(s, t)),
                ("rta_boundary", lambda s=orig_s, t=traced_s: rta.synthesize_boundary_norm_prelude_patches(s, t)),
                ("rta_vararg", lambda s=orig_s, t=traced_s: rta.synthesize_vararg_signature_patches(s, spectrum.raw_output[-600:], t)),
            ):
                try:
                    for lbl, _ln, patched_s in gen_fn()[:8]:
                        if patched_s and patched_s != orig_s:
                            dig = hashlib.sha256(f"{rel_f}\0{patched_s}".encode("utf-8")).hexdigest()[:14]
                            extra_cands.append(
                                CandidatePatch(
                                    patch_id=f"{gen_name}:{dig}",
                                    family=f"{gen_name}:{lbl}",
                                    patched_files={rel_f: patched_s},
                                    description=str(lbl),
                                    mdl_delta_bytes=len(patched_s.encode("utf-8")) - len(orig_s.encode("utf-8")),
                                )
                            )
                except Exception:
                    pass
            fn_names = [fn_n for r_x, fn_n, _, _ in spectrum.ranked_functions if r_x == rel_f][:4]
            target_fn_0 = fn_names[0] if fn_names else ""
            try:
                for wc in closer.mine_all(
                    orig_s,
                    target_fn_0,
                    functions=fn_names,
                    repo_sources=localized_repo_sources,
                    test_sources=localized_test_sources,
                )[:10]:
                    if wc.patched_module_source and wc.patched_module_source != orig_s:
                        dig = hashlib.sha256(f"{rel_f}\0{wc.patched_module_source}".encode("utf-8")).hexdigest()[:14]
                        extra_cands.append(
                            CandidatePatch(
                                patch_id=f"rwc_{wc.mechanism}:{dig}",
                                family=f"rwc:{wc.mechanism}",
                                patched_files={rel_f: wc.patched_module_source},
                                description=wc.explanation,
                                mdl_delta_bytes=len(wc.patched_module_source.encode("utf-8")) - len(orig_s.encode("utf-8")),
                            )
                        )
            except Exception:
                pass
        _enqueue_unique(extra_cands)
    except Exception:
        pass

    # 3E. Localized ~15ms ProjectCPG + `spec_contract_synthesis_v1` (DID_NOT_RAISE exception contracts, frame containments, postconditions)
    try:
        from canonical.swe_kernel import semantic_causal_engine_v1 as scm
        from canonical.swe_kernel import spec_contract_synthesis_v1 as scs

        loc_fns: list[Any] = []
        loc_by_file: dict[str, list[int]] = {}
        loc_by_name: dict[str, list[int]] = {}
        for rf_cpg, txt_cpg in list(localized_repo_sources.items())[:5]:
            raw_cpg = txt_cpg.encode("utf-8", errors="replace")
            extracted = scm._extract_python_functions_cpg(rf_cpg, txt_cpg, raw_cpg, include_sites=True)
            for fn_node in extracted:
                idx_n = len(loc_fns)
                loc_fns.append(fn_node)
                loc_by_file.setdefault(rf_cpg, []).append(idx_n)
                loc_by_name.setdefault(fn_node.name, []).append(idx_n)
        loc_cpg = scm.ProjectCPG(
            functions=tuple(loc_fns),
            by_file={k: tuple(v) for k, v in loc_by_file.items()},
            by_name={k: tuple(v) for k, v in loc_by_name.items()},
            call_edges=(),
            reverse_callers={},
            file_imports={},
        )
        prio_pairs = [(r_x, fn_x) for r_x, fn_x, _, _ in spectrum.ranked_functions[:6]]
        scs_cands: list[CandidatePatch] = []
        for sc_patch in (
            *scs.synthesize_spec_guards(ws, loc_cpg, localized_test_sources, max_candidates=14, prioritize=prio_pairs),
            *scs.synthesize_frame_containments(ws, loc_cpg, max_candidates=8, prioritize=prio_pairs),
        ):
            orig_sc = localized_repo_sources.get(sc_patch.file_path, "")
            if sc_patch.patched_source and sc_patch.patched_source != orig_sc:
                dig = hashlib.sha256(f"{sc_patch.file_path}\0{sc_patch.patched_source}".encode("utf-8")).hexdigest()[:14]
                scs_cands.append(
                    CandidatePatch(
                        patch_id=f"scs_{sc_patch.family}:{dig}",
                        family=f"scs:{sc_patch.family}",
                        patched_files={sc_patch.file_path: sc_patch.patched_source},
                        description=sc_patch.rationale,
                        mdl_delta_bytes=len(sc_patch.patched_source.encode("utf-8")) - len(orig_sc.encode("utf-8")),
                    )
                )
        post_contracts = scs.mine_postcondition_contracts(localized_test_sources)
        if post_contracts:
            for st_patch in scs.state_consistency_candidates(ws, loc_cpg, post_contracts, max_candidates=8):
                orig_st = localized_repo_sources.get(st_patch.file_path, "")
                if st_patch.patched_source and st_patch.patched_source != orig_st:
                    dig = hashlib.sha256(f"{st_patch.file_path}\0{st_patch.patched_source}".encode("utf-8")).hexdigest()[:14]
                    scs_cands.append(
                        CandidatePatch(
                            patch_id=f"scs_post:{dig}",
                            family=f"scs:{st_patch.family}",
                            patched_files={st_patch.file_path: st_patch.patched_source},
                            description=st_patch.rationale,
                            mdl_delta_bytes=len(st_patch.patched_source.encode("utf-8")) - len(orig_st.encode("utf-8")),
                        )
                    )
        _enqueue_unique(scs_cands)
    except Exception:
        pass

    # 3F. Aimed Statement Commutation (`aimed_edits_from_the_program_and_the_failure_v1.commuted`)
    try:
        from canonical.tools import aimed_edits_from_the_program_and_the_failure_v1 as aimed_ed

        comm_cands: list[CandidatePatch] = []
        for rel_f in spectrum.ranked_files[:2]:
            orig_cm = localized_repo_sources.get(rel_f, "")
            if not orig_cm or len(orig_cm) > 35_000:
                continue
            hot_cm = set(spectrum.suspect_lines.get(rel_f) or ())
            tree_cm = ast.parse(orig_cm)
            checked_cm = 0
            for cm_row in aimed_ed.commuted(tree_cm):
                checked_cm += 1
                if checked_cm > 64:
                    break
                if hot_cm and int(cm_row.get("lineno") or 0) not in hot_cm:
                    continue
                cm_src = str(cm_row.get("source") or "")
                if not cm_src or cm_src == orig_cm:
                    continue
                dig = hashlib.sha256(f"{rel_f}\0{cm_src}".encode("utf-8")).hexdigest()[:14]
                comm_cands.append(
                    CandidatePatch(
                        patch_id=f"aimed_commute:{dig}",
                        family="aimed_commute:commute_site",
                        patched_files={rel_f: cm_src + "\n"},
                        description=f"commute {cm_row.get('site')} at L{cm_row.get('lineno')}",
                        mdl_delta_bytes=0,
                    )
                )
                if len(comm_cands) >= 6:
                    break
        _enqueue_unique(comm_cands)
    except Exception:
        pass

    # 3F-bis. Zero-Disk CoW In-RAM Live-Frame Differential Witness Inversion (`differential_witness_inversion_v1`, ~140ms)
    rem = lambda: max(0.0, timeout_s - (time.perf_counter() - t0))
    if spectrum.failing_nodes and rem() > 3.0 and _has_pytest() and hasattr(os, "fork") and threading.active_count() == 1:
        try:
            from canonical.swe_kernel import differential_witness_inversion_v1 as dwi

            dwi_rows, _ = dwi.synthesize_live_differential_witness_repairs_in_ram(
                ws,
                spectrum.failing_nodes[:2],
                spectrum.passing_nodes[:8],
                timeout_sec=min(1.6, max(0.7, rem() * 0.16)),
            )
            dwi_cands: list[CandidatePatch] = []
            for p_map, _mech, d_desc in dwi_rows[:18]:
                if not p_map:
                    continue
                rf_d, new_d = next(iter(p_map.items()))
                orig_d = localized_repo_sources.get(rf_d)
                if orig_d is None and (ws / rf_d).is_file():
                    orig_d = (ws / rf_d).read_text(encoding="utf-8", errors="replace")
                if orig_d and new_d and new_d != orig_d:
                    dig_d = hashlib.sha256(f"{rf_d}\0{new_d}".encode("utf-8")).hexdigest()[:14]
                    dwi_cands.append(
                        CandidatePatch(
                            patch_id=f"diff_witness:{dig_d}",
                            family="diff_witness:live_frame_inversion",
                            patched_files=zipper.propagate_default_arg_obligations(rf_d, orig_d, new_d),
                            description=d_desc,
                            mdl_delta_bytes=len(new_d.encode("utf-8")) - len(orig_d.encode("utf-8")),
                        )
                    )
            if dwi_cands:
                _enqueue_unique(dwi_cands)
                organ_trace.append(f"diff_witness_ram:{len(dwi_cands)}")
        except Exception:
            pass

    def _cand_priority_key(cp: CandidatePatch) -> tuple[int, int]:
        fam = cp.family
        if fam.startswith(("learned_op:", "cst_skill:", "diff_witness:", "failing_run_blame:")):
            tier = 0
        elif fam.startswith(("M1", "M2", "M3", "M4", "M5", "M8", "M9", "M10", "scs:", "relation:", "angelic_oe:", "rta_shadow:", "rta_habitation:", "rta_callee_hook:", "rta_bracket:", "rta_regex:", "rta_vararg:")):
            tier = 1
        elif fam.startswith(("M6", "M7", "rwc:", "mhz:", "caz:", "aimed_commute:", "grammar_closed:", "rta_boundary:")):
            tier = 2
        else:
            tier = 3
        return (tier, abs(cp.mdl_delta_bytes))

    unified_candidates.sort(key=_cand_priority_key)
    # Sound AST + Guarded Region-SSA Meaning-IR Deduplication Pre-Sieve (`< 1.5 ms` in RAM — deletes formatting/parenthesization/SSA-equivalent duplicates before `fork()`, NEVER drops unmodeled module constants, `raise`s, or class methods!)
    if len(unified_candidates) > 12:
        try:
            from canonical.swe_kernel import guarded_meaning_ir_v1 as gmir

            base_mir_cache: dict[str, str] = {}
            for rf_b, orig_b in localized_repo_sources.items():
                if len(orig_b) <= 22_000:
                    try:
                        base_mir_cache[rf_b] = json.dumps(gmir.lower_python(orig_b).as_dict(), sort_keys=True)
                    except Exception:
                        pass

            seen_sem_keys: set[str] = set()
            deduped_cands: list[CandidatePatch] = []
            for cp_m in unified_candidates:
                if len(cp_m.patched_files) == 1:
                    rf_m, src_m = next(iter(cp_m.patched_files.items()))
                    if len(src_m) <= 28_000:
                        try:
                            tree_m = ast.parse(src_m)
                            ast_canon = ast.dump(tree_m, include_attributes=False)
                            sem_k = f"ast:{rf_m}:{hashlib.sha256(ast_canon.encode('utf-8')).hexdigest()[:18]}"
                            # Only collapse distinct ASTs via `gmir` when `gmir` faithfully captures the delta AND no `Raise`/`Try`/module-assign changed
                            if len(src_m) <= 22_000 and rf_m in base_mir_cache:
                                mir_json = json.dumps(gmir.lower_python(src_m).as_dict(), sort_keys=True)
                                if mir_json != base_mir_cache[rf_m]:
                                    non_fn_sig = "|".join(
                                        ast.dump(st_n, include_attributes=False)
                                        for st_n in tree_m.body
                                        if not isinstance(st_n, ast.FunctionDef)
                                    )
                                    has_unmodeled = any(
                                        isinstance(sub_n, (ast.Raise, ast.Try, ast.Yield, ast.YieldFrom, ast.For, ast.While, ast.With))
                                        for st_n in tree_m.body
                                        if isinstance(st_n, ast.FunctionDef)
                                        for sub_n in ast.walk(st_n)
                                    )
                                    if not has_unmodeled:
                                        sem_k = f"mir:{rf_m}:{hashlib.sha256((mir_json + '||' + non_fn_sig).encode('utf-8')).hexdigest()[:18]}"
                            if sem_k in seen_sem_keys:
                                continue
                            seen_sem_keys.add(sem_k)
                        except Exception:
                            pass
                deduped_cands.append(cp_m)
            pruned_n = len(unified_candidates) - len(deduped_cands)
            if pruned_n > 0:
                organ_trace.append(f"mir_presieve_pruned:{pruned_n}")
            unified_candidates = deduped_cands
        except Exception:
            pass

    unified_candidates = unified_candidates[:96]
    organ_trace.append(f"synthesized_total:{len(unified_candidates)}")

    screener = WarmCoWForkScreener(ws, fast_targets, per_candidate_timeout_s=min(2.2, max(1.0, rem() * 0.14)))
    screened_survivors = screener.screen_batch(unified_candidates, budget_s=min(5.5, rem() * 0.48))
    organ_trace.append(f"cow_fork_survivors:{len(screened_survivors)}")

    # 3G. Orthogonal Multi-Hunk / Multi-File Composition (`causal_cegis_inventor_v1.merge_orthogonal_file_patches`)
    #     When multiple failing tests exist and single candidates each resolve a non-empty subset (`last_partial_survivors`),
    #     compose complementary pairs and screen them!
    if not screened_survivors and len(screener.last_partial_survivors) >= 2 and rem() > 3.5:
        try:
            from canonical.swe_kernel import causal_cegis_inventor_v1 as cci

            partials = screener.last_partial_survivors[:8]
            composed_cands: list[CandidatePatch] = []
            for i_p in range(len(partials)):
                c1, p1 = partials[i_p]
                for j_p in range(i_p + 1, len(partials)):
                    c2, p2 = partials[j_p]
                    if len(p1 | p2) <= max(len(p1), len(p2)):
                        continue
                    # Disjoint files -> direct union; same file -> merge via `merge_orthogonal_file_patches`
                    if set(c1.patched_files).isdisjoint(c2.patched_files):
                        merged_map = {**c1.patched_files, **c2.patched_files}
                    elif len(c1.patched_files) == 1 and set(c1.patched_files) == set(c2.patched_files):
                        only_rf = next(iter(c1.patched_files))
                        orig_m = localized_repo_sources.get(only_rf, "")
                        merged_txt = cci.merge_orthogonal_file_patches(
                            orig_m,
                            c1.patched_files[only_rf],
                            c2.patched_files[only_rf],
                        )
                        merged_map = {only_rf: merged_txt} if merged_txt else {}
                    else:
                        merged_map = {}
                    if merged_map:
                        dig_m = hashlib.sha256(
                            "\0".join(f"{k}:{v}" for k, v in sorted(merged_map.items())).encode("utf-8")
                        ).hexdigest()[:14]
                        composed_cands.append(
                            CandidatePatch(
                                patch_id=f"composed:{dig_m}",
                                family=f"composed:{c1.family}+{c2.family}",
                                patched_files=merged_map,
                                description=f"orthogonal composition of {c1.patch_id} and {c2.patch_id}",
                                mdl_delta_bytes=c1.mdl_delta_bytes + c2.mdl_delta_bytes,
                            )
                        )
            if composed_cands:
                comp_surv = screener.screen_batch(composed_cands[:12], budget_s=min(2.5, rem() * 0.35))
                if comp_surv:
                    screened_survivors.extend(comp_surv)
                    organ_trace.append(f"composed_survivors:{len(comp_surv)}")
        except Exception:
            pass

    winner, gate_meta = WholeSliceMutantKillingGate.select_verified_winner(
        ws,
        targets,
        None,
        screened_survivors,
        timeout_per_check_s=14.0,
        budget_s=max(8.0, rem() * 0.6),
    )

    # Stage P4 (Elon's Law: 35s 4-organ subprocess cascade DELETED!):
    # Only run a tight <= 0.9s CoW Angelic Separating-Guard pass (`PytestCoWZygoteServer`) when Pass 1 abstained.
    if (
        winner is None
        and rem() > 2.5
        and enc_files
        and 1 <= len(spectrum.failing_nodes) <= 2
        and _has_pytest()
        and hasattr(os, "fork")
        and threading.active_count() == 1
    ):
        try:
            from canonical.swe_kernel import cow_angelic_zygote_v1 as caz

            ang_candidates: list[CandidatePatch] = []
            ang_deadline = time.monotonic() + min(0.9, rem() * 0.35)
            with caz.PytestCoWZygoteServer(ws) as zygote:
                for rel_f in spectrum.ranked_files[:1]:
                    if time.monotonic() >= ang_deadline:
                        break
                    fp_a = ws / rel_f
                    if not fp_a.is_file():
                        continue
                    orig_a = fp_a.read_text(encoding="utf-8", errors="replace")
                    act_l = set(spectrum.suspect_lines.get(rel_f) or ())
                    for ac in caz.synthesize_angelic_separating_guards(
                        ws,
                        rel_f,
                        act_l,
                        spectrum.failing_nodes[:4],
                        enc_files[0],
                        spectrum.raw_output,
                        zygote,
                        deadline=ang_deadline,
                        max_candidates=12,
                        tb_lines=act_l,
                    ):
                        if ac.patched_source and ac.patched_source != orig_a:
                            dig = hashlib.sha256(f"{rel_f}\0{ac.patched_source}".encode("utf-8")).hexdigest()[:14]
                            ang_candidates.append(
                                CandidatePatch(
                                    patch_id=f"angelic_guard:{dig}",
                                    family=f"angelic_guard:{ac.mechanism}",
                                    patched_files={rel_f: ac.patched_source},
                                    description=ac.description,
                                    mdl_delta_bytes=_mdl_bytes(ac.patched_source) - _mdl_bytes(orig_a),
                                )
                            )
            organ_trace.append(f"angelic_guards:{len(ang_candidates)}")
            if ang_candidates:
                ang_survivors = screener.screen_batch(ang_candidates, budget_s=min(3.5, rem() * 0.5))
                if ang_survivors:
                    winner, gate_meta = WholeSliceMutantKillingGate.select_verified_winner(
                        ws,
                        targets,
                        None,
                        ang_survivors,
                        timeout_per_check_s=14.0,
                        budget_s=max(6.0, rem()),
                    )
        except Exception:
            pass

    if winner is None:
        return {
            "schema": SCHEMA,
            "status": "ABSTAINED__WHOLE_SLICE_GATE_UNSATISFIED",
            "pass": False,
            "localized_files": spectrum.ranked_files[:5],
            "failure_kind": spectrum.failure_kind,
            "gate_telemetry": gate_meta,
            "organ_trace": organ_trace,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # Stage P5: Commit Whole-Slice-Verified Winner to `ws` & Consolidate E-Stitch Motif!
    learned_motif_id: str | None = None
    for rel_f, new_content in winner.patched_files.items():
        dest_f = ws / rel_f
        old_content = dest_f.read_text(encoding="utf-8", errors="replace") if dest_f.is_file() else ""
        dest_f.parent.mkdir(parents=True, exist_ok=True)
        dest_f.write_text(new_content, encoding="utf-8")
        motif = active_skills.record_verified_repair(
            family=winner.family,
            before_source=old_content,
            after_source=new_content,
            scope_id=ws.name,
            surprise=1.0,
        )
        if motif is not None:
            learned_motif_id = motif.motif_id

    return {
        "schema": SCHEMA,
        "status": "VERIFIED",
        "pass": True,
        "regime": "UNIFIED_EPISTEMIC_PORTFOLIO_WHOLE_SLICE_VERIFIED",
        "mechanism": winner.family,
        "patch_id": winner.patch_id,
        "description": winner.description,
        "patched_files": dict(winner.patched_files),
        "learned_motif_id": learned_motif_id,
        "gate_telemetry": gate_meta,
        "organ_trace": organ_trace,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def self_check() -> dict[str, Any]:
    """Falsifiable behavioral contract for the unified epistemic portfolio pre-sieve.

    Proves three non-tautological properties:
    1. Semantic-IR pre-sieving eliminates both semantic duplicates of the buggy baseline
       and candidates whose simulated output contradicts the observed expected return,
       retaining only the genuinely distinct passing candidate.
    2. Negative control: when NO candidate satisfies the expected output, kept_count is 0
       (a rubber-stamp sieve that keeps everything fails this control).
    3. Determinism: identical inputs produce identical kept indices and prune counts.
    """
    failures: list[str] = []

    def check(label: str, ok: bool) -> None:
        if not ok:
            failures.append(label)

    baseline = "def add(a, b):\n    return a - b\n"
    candidates = [
        "def add(a, b):\n    return a - b\n",
        "def add(a, b):\n    return a + b\n",
        "def add(a, b):\n    return a * b\n",
    ]
    res1 = pre_sieve_and_simulate_meaning_ir(
        baseline,
        candidates,
        entry_func="add",
        probe_args=(2, 3),
        expected_return=5,
        check_expected=True,
    )
    check("sieve succeeds with zero model calls", bool(res1.get("pass")) and res1.get("model_calls") == 0)
    check("keeps only the true passing candidate index [1]", res1.get("kept_indices") == [1])
    check("prunes semantic duplicate of baseline", int(res1.get("pruned_semantic_duplicates", 0)) >= 1)
    check("prunes simulation mismatch candidate", int(res1.get("pruned_simulation_mismatches", 0)) >= 1)

    neg = pre_sieve_and_simulate_meaning_ir(
        baseline,
        candidates,
        entry_func="add",
        probe_args=(2, 3),
        expected_return=999,
        check_expected=True,
    )
    check("negative control: unsatisfiable expectation yields 0 survivors", neg.get("kept_count") == 0)

    res2 = pre_sieve_and_simulate_meaning_ir(
        baseline,
        candidates,
        entry_func="add",
        probe_args=(2, 3),
        expected_return=5,
        check_expected=True,
    )
    check(
        "deterministic sieve output",
        res1.get("kept_indices") == res2.get("kept_indices")
        and res1.get("pruned_semantic_duplicates") == res2.get("pruned_semantic_duplicates"),
    )

    total = 6
    return {
        "schema": "BRAIN_UNIFIED_EPISTEMIC_PORTFOLIO_V1_SELF_CHECK",
        "checks": total,
        "passed": total - len(failures),
        "failures": failures,
        "verdict": "SELF_CHECK_PASS" if not failures else "SELF_CHECK_FAIL",
    }
