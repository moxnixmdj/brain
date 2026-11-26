#!/usr/bin/env bash
# Run in a disposable checkout. Supply the interpreter, browser and shared libs
# described in SINGLE_EPISODE_REPRODUCTION. No acquisition/update inside tests.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"; x=canonical/tests
[[ -x ${BRAIN_TEST_CHROME:?set to a real Chromium executable} ]]
a=($x/test_{boundary_evidence,subtree_witness_replay,petri_cow_unified_architecture,petri_cow_splicing_engine,v4_subtree_fuzzer_harbor,causal_swe_repair,harbor_epistemic_agent,harbor_experimental_vm,harbor_cold_smoke,harbor_pro_git_capture,harbor_pro_patch_handoff,harbor_process_cleanup_worker,unified_epistemic_portfolio,zero_knowledge_cua_kernel,witnessed_native_route,witnessed_revision_history,contrast_and_browser_boundary,frontier_leapfrog_waves21_25,frontier_leapfrog_wave39,unified_frontier_spines,repair_input_dependency_gate,finite_minimax_decision_region,induced_edit_basis,arm_learned_from_its_own_verified_repairs,domain_atlas}_v1.py)
b=($x/test_{tied_evidence_and_policy_cache,compiled_repair_witness,frame_program,typed_invention,minimal_experiment,perfect_algorithm_lifted_generalization,the_refusal_is_the_curriculum,contrastive_oracle_bootstrap,cow_angelic_zygote,meta_circular_global_sentient_creature,evidence_census_and_calibration}_v1.py $x/test_same_identity_supervisor.py)
w36=$x/test_frontier_leapfrog_wave36_v1.py::TestFrontierLeapfrogWave36V1
c=("$w36"::test_02_byte_effect_oracle_catches_lying_extensions_and_collateral_mutations "$w36"::test_03_dra_ddmin_hunk_minimizer_and_mutation_kill_audit "$w36"::test_07_dbsp_zset_kumiho_agm_and_pre_commit_failure_gate "$w36"::test_08_score_conformal_evalue_ville_inequality_and_decisions "$w36"::test_09_wake_sleep_growlibm_creature_and_newly_federated_kernels)
u=$x/test_unification_wave2_frontier_v1.py
d=("$u"::test_03_semi_persistent_egraph_anti_unification_and_sleep_compression "$u"::test_04_verifier_falsification_catches_sting_vacuous_oracles "$u"::test_05_instruction_contract_and_failing_run_demand_extraction "$u"::test_18_mutation_admission_gate_rejects_weak_verifier_and_admits_strong_verifier $x/test_reverse_tomography_algebra_v1.py::test_pillar1_reverse_execution_backprop_fstring_repr_regex_and_cow_fork)
exec "${PYTHON:-python3}" -m pytest -p no:cacheprovider -q --tb=short "$@" "${a[@]}" "${b[@]}" "${c[@]}" "${d[@]}"
