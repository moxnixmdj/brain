#!/usr/bin/env python3
"""Audit the real hard-open population before any further learning claim.

This tool does NOT propose an action, repair a program, train a weight, register a
capability, or claim verification. It answers one integrity question first:

    Across every measured repair receipt in this tree, which REAL published
    QuixBugs tasks have already been repaired, and which tasks are still open?

The answer is the admission population for any future mechanism. Re-running a task
that some earlier receipt already repaired is not progress. A test on an invented
toy is not a hardest-open test. The tool therefore reads measured receipts and the
real corpus test-file names, asserts their set algebra, and writes a receipt.

The name records the answer's unit without declaring a capability: in a live
environment the binding quantity is SEPARATION -- a hypothesis space that contains
the truth and an observation that splits it. Maintaining separation in an open
world requires an operation, the premise under which it preserves meaning, and a
falsifiable counterfactual verdict derived from live execution. Those parts
already exist in the tree under non-obvious names; this tool only prevents future
sessions from rebuilding or congratulating them.

Authority NONE. Producer-run, one sandbox. No model call, no network call, $0.
`truth.achieved` is not touched. No protected path is touched.

Usage:
    python3 canonical/tools/proof_carrying_counterfactual_union_v1.py \
        --quixbugs /path/to/QuixBugs \
        --out canonical/verification/PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any, Iterable

SCHEMA = "BRAIN_PROOF_CARRYING_COUNTERFACTUAL_UNION_AUDIT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ANSWER_KEY = "correct_python_programs"
MODEL_DEPENDENCY_COUNT = 0
NETWORK_DEPENDENCY_COUNT = 0
INCREMENTAL_SPEND_USD = 0

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "canonical" / "verification"

#: Every receipt in the measured repair line that reports a task list. These are
#: read from the current tree; no task name below is hard-coded as a known win.
REPAIR_RECEIPTS = (
    "COMPARISONS_CLOSE_THE_LAST_MILE_20261116_V1.json",
    "THE_EDIT_SPACE_IS_THE_PROGRAM_NOT_A_LIST_20261116_V1.json",
    "REGION_REWRITES_AND_THE_REFUSAL_AUDIT_20261116_V1.json",
    "CONTRACT_GROUNDED_REPAIR_20261116_V1.json",
    "INTERVENTIONAL_GOAL_20261116_V1.json",
    "RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json",
    "SYNTHESIS_FROM_THE_FAILURE_20261116_V1.json",
    "WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json",
    # New main evidence: the projected union is now a composed run under one
    # judge, and a second run learns its own alpha-canonical vocabulary inside
    # the pass. They report the same 24 tasks; neither adds a new repair.
    "COMPOSED_REPAIR_ONE_RUN_20261116_V1.json",
    "ARM_LEARNED_IN_ONE_RUN_20261116_V1.json",
    # Insert composition (force/aug + insert) closed 6 further hard-open tasks
    # under the corpus pytest; the suite-as-observable verifier-root fix closed
    # 2 more that had been misreported as collection failures (rc 2).
    "COUNTERFACTUAL_REPAIR_QUIXBUGS_INSERTION_20261116_V1.json",
    "SUITE_AS_OBSERVABLE_VERIFIER_ROOTS_20261116_V1.json",
)

#: The cross-corpus transfer receipt has a second arm shown 39 other QuixBugs
#: fixes. Its clean arm was also a claim until PR #6887 re-ran the recorded line
#: changes under the corpus pytest: 16 confirmed, 4 not reconstructible. Only the
#: rerun receipt's confirmed list is admitted to the union.
RECEIPT_ARMS_IGNORED = (
    {
        "receipt": "QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json",
        "arm": "summary.all_other_fixes",
        "reason": "Shown 39 QuixBugs fixes; not a clean held-out vocabulary transfer.",
    },
    {
        "receipt": "QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json",
        "arm": "summary.another_benchmark",
        "reason": "Claimed 20 repairs; PR #6887 re-judged them under pytest and confirmed 16, with 4 not reconstructible. Superseded by RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json.",
    },
)

#: Mechanisms indexed by EFFECT, not filename. A future session that searches for
#: obvious names and declares a part missing should find this census first.
MECHANISM_GROUPS: dict[str, tuple[str, ...]] = {
    "capture_and_premise": (
        "canonical/swe_kernel/verified_skill_crystallizer_v1.py",
        "canonical/swe_kernel/one_demonstration_reach_v1.py",
        "canonical/runtime/applicability_v1.py",
        "canonical/swe_kernel/lesson_admission_gate_v1.py",
    ),
    "constructive_actions_and_operands": (
        "canonical/tools/grammar_closed_repair_v1.py",
        "canonical/tools/quixbugs_required_edit_taxonomy_v1.py",
        "canonical/runtime/derived_value_v1.py",
        "canonical/runtime/inert_action_prior_v1.py",
        "canonical/runtime/anchored_frame_v1.py",
        "canonical/tools/synthesized_expression_from_the_failure_v1.py",
        "canonical/tools/miniwob_contract_arm_arm_v1.py",
    ),
    "goal_and_counterfactual_verdict": (
        "canonical/swe_kernel/contract_grounded_repair_v1.py",
        "canonical/swe_kernel/interventional_goal_v1.py",
        "canonical/runtime/semantic_operator_counterfactuals.py",
        "canonical/runtime/contrast_selection_v1.py",
    ),
    "identification_and_separation": (
        "canonical/runtime/finite_identifiability.py",
        "canonical/tools/identification_cost_in_a_real_space_v1.py",
        "canonical/swe_kernel/one_demonstration_identifies_v1.py",
        "canonical/swe_kernel/repair_version_space_selection_v1.py",
        "canonical/swe_kernel/closed_loop_trace_abduction_repair_v1.py",
        "canonical/tools/version_space_selection_measure_v1.py",
        "canonical/tools/closed_loop_trace_abduction_measure_v1.py",
        "canonical/swe_kernel/specification_from_structure_v1.py",
        "canonical/tools/grammar_closed_repair_v1.py",
    ),
    "independent_witness_and_admission": (
        "canonical/runtime/instruction_contract_v1.py",
        "canonical/runtime/instruction_policy_v1.py",
        "canonical/runtime/observable_descriptor_v1.py",
        "canonical/tools/repair_where_the_suite_is_the_observable_v1.py",
        "canonical/tools/rerun_the_learned_arms_repairs_v1.py",
        "canonical/swe_kernel/test_suite_admission_v1.py",
        "canonical/swe_kernel/weight_update_admission_v1.py",
        "canonical/swe_kernel/learned_skill_verdict_v1.py",
    ),
    "hidden_synthesis_and_orchestration": (
        "canonical/runtime/counterexample_guided_causal_architecture_synthesizer_v1.py",
        "canonical/runtime/finite_grid_program_inducer_v1.py",
        "canonical/runtime/swe_observational_program_synthesizer_v1.py",
        "canonical/runtime/unified_cognitive_fabric_v1.py",
        "canonical/swe_kernel/closed_loop_autonomous_controller_v1.py",
        "canonical/runtime/bound_capabilities/software_patch_cegis_z3_v1.py",
        "canonical/runtime/bound_capabilities/hardcore_software_engineering_orchestrator_v1.py",
    ),
    # 2026-11-16 main additions, indexed by EFFECT. The decision/composition
    # layer is not missing: these are the non-obvious names it already has.
    "exact_decision_past_enumeration": (
        "canonical/runtime/applicability_v1.py",
        "canonical/runtime/contrast_selection_v1.py",
        "canonical/tests/test_the_learner_decides_past_the_enumeration_wall_v1.py",
    ),
    "invariance_and_in_run_learning": (
        "canonical/runtime/implied_ending_v1.py",
        "canonical/runtime/picker_answer_v1.py",
        "canonical/tools/composed_repair_one_run_v1.py",
        "canonical/tools/arm_learned_from_its_own_verified_repairs_v1.py",
        "canonical/tools/what_one_verified_repair_travels_v1.py",
        "canonical/swe_kernel/induced_edit_basis_v1.py",
    ),
    "environment_cost_and_composition": (
        "canonical/tools/instant_learning_in_a_new_environment_v1.py",
        "canonical/runtime/environment_learning_v1.py",
        "canonical/runtime/capability_planner.py",
        "canonical/runtime/generic_goal_tool_effect_planner_v1.py",
        "canonical/runtime/capability_composer_v1.py",
        "canonical/runtime/verified_skill_macro_planner_v1.py",
        "canonical/runtime/explicit_recovery_planner.py",
        "canonical/swe_kernel/predicate_world_abstraction_v1.py",
        "canonical/swe_kernel/operator_semantics_v1.py",
        "canonical/swe_kernel/hierarchical_skill_library_v1.py",
    ),
    "read_first_operand_and_replay_drift": (
        "canonical/runtime/learn_or_read_v1.py",
        "canonical/runtime/derived_value_v1.py",
        "canonical/swe_kernel/action_replay_under_change_v1.py",
        "canonical/tools/derived_value_full_suite_receipt_v1.py",
        "canonical/tools/learn_or_read_board_v1.py",
    ),
    "long_tail_trigger_and_basin": (
        "canonical/runtime/declared_trigger_census_v1.py",
        "canonical/runtime/derived_value_v1.py",
        "canonical/runtime/applicability_v1.py",
        "canonical/runtime/contrast_selection_v1.py",
        "canonical/swe_kernel/one_demonstration_basin_v1.py",
    ),
    "gui_invariance_and_operand_boundary": (
        "canonical/tools/gui_invariance_census_v1.py",
        "canonical/tools/gui_phrase_blind_basis_arm_v1.py",
        "canonical/runtime/derived_value_v1.py",
    ),
    "proved_composition": (
        "canonical/swe_kernel/proved_composition_v1.py",
        "canonical/runtime/verified_skill_macro_planner_v1.py",
        "canonical/runtime/capability_composer_v1.py",
    ),
    "four_levers_and_edit_supply": (
        "canonical/tools/the_four_levers_of_learning_from_experience_v1.py",
        "canonical/swe_kernel/systematic_edit_supply_v1.py",
        "canonical/runtime/demonstration_version_space_v1.py",
        "canonical/runtime/contrast_selection_v1.py",
    ),
    "index_specification_and_value_layer": (
        "canonical/tools/the_index_is_the_bottleneck_v1.py",
        "canonical/tools/compose_measured_effects_v1.py",
        "canonical/swe_kernel/systematic_edit_supply_v1.py",
        "canonical/runtime/contrast_selection_v1.py",
        "canonical/runtime/applicability_v1.py",
    ),
    "unbound_name_binding_and_retraction": (
        "canonical/runtime/what_one_experience_buys_v1.py",
        "canonical/runtime/demonstration_version_space_v1.py",
        "canonical/tools/miniwob_one_success_generalisation_measure_v1.py",
        "canonical/tests/test_what_one_experience_buys_v1.py",
    ),
}

SUPERSEDES = (
    "THE_GOAL_IS_A_COUNTERFACTUAL_WORLD_MODEL_20261116_V1.md",
    "THE_GOAL_IS_THE_BOTTLENECK_20261116_V1.md",
    "WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md",
)

#: Newly merged evidence read by effect before this answer was written. These are
#: measured results, not prose permission slips.
EVIDENCE_READ = (
    "THE_EDIT_SPACE_IS_THE_PROGRAM_NOT_A_LIST_20261116_V1.md",
    "THE_HAND_WAS_NEVER_THE_BOTTLENECK_20261116_V1.md",
    "THE_JUDGE_WAS_THE_MISSING_PART_20261116_V1.md",
    "WHAT_ONE_DEMONSTRATION_REACHES_20261116_V1.md",
    "ONE_DEMONSTRATION_LEAVES_TEN_BITS_20261116_V1.md",
    "THE_SPACE_IS_ASSEMBLED_NOT_LISTED_20261116_V1.md",
    "WHAT_ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.md",
    "WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.md",
    "ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_20261116_V1.md",
    "RERUN_THE_REPAIRS_NOT_THE_CLAIM_20261116_V1.md",
    "canonical/action_intents/THE_ROW_WAS_ALWAYS_THERE_20261116_V1.json",
    "canonical/verification/RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json",
    "canonical/verification/THE_ROW_WAS_ALWAYS_THERE_20261116_V1.json",
    "canonical/verification/IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1.json",
    "canonical/verification/ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1.json",
    "canonical/verification/ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.json",
    "canonical/verification/ONE_DEMONSTRATION_REACH_20261116_V1.json",
    "canonical/verification/PROJECT_BRAIN_INSTRUCTION_POLICY_VERIFICATION_20261116_V1.json",
    "canonical/verification/INSTRUCTION_CONTRACT_20261116_V1.json",
    "canonical/verification/OBSERVABLE_DESCRIPTOR_20261116_V1.json",
    "canonical/verification/SYNTHESIS_FROM_THE_FAILURE_20261116_V1.json",
    "canonical/verification/WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json",
    "canonical/verification/QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json",
    # Verifier-root fix: the suite-as-observable path's corpus pytest was dying
    # at collection (rc 2) because PYTHONPATH lacked python_programs/ and
    # python_testcases/. Fixed; re-run closed depth_first_search and detect_cycle.
    "canonical/verification/SUITE_AS_OBSERVABLE_VERIFIER_ROOTS_20261116_V1.json",
    "canonical/tools/grammar_closed_repair_v1.py",
    "canonical/verification/COMPARISONS_CLOSE_THE_LAST_MILE_20261116_V1.json",
    # One-run, invariance, exact-decision, browser and new-environment evidence
    # merged to main after the previous answer was written.
    "ONE_RUN_THREE_VOCABULARIES_ONE_JUDGE_20261116_V1.md",
    "THE_INVARIANCE_IS_THE_REACH_20261116_V1.md",
    "THE_LEARNER_DECIDES_PAST_THE_ENUMERATION_WALL_20261116_V1.md",
    "THE_PRICE_OF_A_NEW_ENVIRONMENT_20261116_V1.md",
    "canonical/action_intents/ONE_RUN_THREE_VOCABULARIES_ONE_JUDGE_20261116_V1.json",
    "canonical/action_intents/THE_INVARIANCE_IS_THE_REACH_20261116_V1.json",
    "canonical/action_intents/DECIDE_PAST_THE_ENUMERATION_WALL_20261116_V1.json",
    "canonical/action_intents/THE_SENTENCE_DID_NOT_HAVE_TO_SAY_SUBMIT_20261116_V1.json",
    "canonical/action_intents/THE_PRICE_OF_A_NEW_ENVIRONMENT_20261116_V1.json",
    "canonical/verification/COMPOSED_REPAIR_ONE_RUN_20261116_V1.json",
    "canonical/verification/ARM_LEARNED_IN_ONE_RUN_20261116_V1.json",
    "canonical/verification/WHAT_ONE_VERIFIED_REPAIR_TRAVELS_20261116_V1.json",
    "canonical/verification/THE_SENTENCE_DID_NOT_HAVE_TO_SAY_SUBMIT_20261116_V1.json",
    "canonical/verification/INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json",
    "canonical/verification/INSTANT_LEARNING_SHUFFLED_CONTROL_20261116_V1.json",
    # Final main move before the single merge: read-first named gaps, operand
    # addition, and replay-under-change drift. Read once; no further chase.
    "THE_MISSING_PART_IS_THE_OPERAND_NOT_THE_EXPERIENCE_20261116_V1.md",
    "WHY_LEARN_ONCE_REPLAY_FOREVER_FAILS_20261116_V1.md",
    "canonical/action_intents/READ_FIRST_AND_LEARN_ONLY_FOR_A_NAMED_GAP_20261116_V1.json",
    "canonical/action_intents/THE_MISSING_PART_IS_THE_OPERAND_20261116_V1.json",
    "canonical/action_intents/WHY_LEARN_ONCE_REPLAY_FOREVER_FAILS_20261116_V1.json",
    "canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json",
    "canonical/verification/DERIVED_VALUE_FULL_SUITE_20261116_V1.json",
    "canonical/verification/LEARN_OR_READ_BOARD_20261116_V1.json",
    "canonical/verification/READ_FIRST_AND_LEARN_ONLY_FOR_A_NAMED_GAP_20261116_V1.json",
    # Final main move: the trigger was a phrase, the unsolved remainder is a
    # long tail, and one demonstration learns a domain, not an environment.
    "THERE_IS_NO_SINGLE_BOTTLENECK_AND_THE_TRIGGER_WAS_THE_REASON_20261116_V1.md",
    "ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.md",
    "canonical/action_intents/THE_REMAINDER_IS_A_LONG_TAIL_20261116_V1.json",
    "canonical/action_intents/ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.json",
    "canonical/verification/DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json",
    "canonical/verification/ONE_DEMONSTRATION_BASIN_20261116_V1.json",
    # Final GUI measurement: no non-trivial judge quotient, so the code-side
    # invariance lever has no job here; the operand boundary remains.
    "THE_GUI_HAS_NO_INVARIANCE_TO_FIND_20261116_V1.md",
    "canonical/action_intents/THE_GUI_HAS_NO_INVARIANCE_TO_FIND_20261116_V1.json",
    "canonical/verification/GUI_INVARIANCE_IS_VACUOUS_OR_ABSENT_20261116_V1.json",
    # Final main measurement: compose only what is proved; the affirmative
    # organ is measured, not a new single lever.
    "COMPOSE_ONLY_WHAT_IS_PROVED_20261116_V1.md",
    "COMPOSE_ONLY_WHAT_IS_PROVED_20261116_V1.json",
    # Final main move: "once" is arithmetic, and real-work supply for a
    # demonstration is about one sixth of commits.
    "YOU_ARE_WRONG_ABOUT_ONCE_AND_IT_IS_ARITHMETIC_20261116_V1.md",
    "ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.md",
    "canonical/action_intents/YOU_ARE_WRONG_ABOUT_ONCE_AND_IT_IS_ARITHMETIC_20261116_V1.json",
    "canonical/action_intents/ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.json",
    "canonical/verification/THE_FOUR_LEVERS_OF_LEARNING_FROM_EXPERIENCE_20261116_V1.json",
    "canonical/verification/SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json",
    "canonical/tools/the_four_levers_of_learning_from_experience_v1.py",
    "canonical/swe_kernel/systematic_edit_supply_v1.py",
    "canonical/tests/test_the_four_levers_of_learning_from_experience_v1.py",
    "canonical/tests/test_systematic_edit_supply_v1.py",
    "canonical/tests/fixtures/systematic_edit_corpus_v1.jsonl",
    # Closing main move: the shared defect is the index/specification, not
    # more learning; composition needs a frame, and inferred values are guesses.
    "COMPOSITION_CLOSES_ONE_AND_PROVES_TWO_20261116_V1.md",
    "THE_BOTTLENECK_IS_THE_INDEX_NOT_THE_LEARNING_20261116_V1.md",
    "canonical/action_intents/COMPOSITION_CLOSES_ONE_AND_PROVES_TWO_20261116_V1.json",
    "canonical/action_intents/SYSTEMATIC_EDIT_VALUE_LAYER_DERIVATION_20261116_V1.json",
    "canonical/action_intents/THE_BOTTLENECK_IS_THE_INDEX_NOT_THE_LEARNING_20261116_V1.json",
    "canonical/verification/COMPOSE_MEASURED_EFFECTS_20261116_V1.json",
    "canonical/verification/SYSTEMATIC_EDIT_DERIVATION_20261116_V1.json",
    "canonical/verification/THE_INDEX_IS_THE_BOTTLENECK_20261116_V1.json",
    "canonical/tools/compose_measured_effects_v1.py",
    "canonical/tools/the_index_is_the_bottleneck_v1.py",
    "canonical/tests/test_compose_measured_effects_v1.py",
    "canonical/tests/test_the_index_is_the_bottleneck_v1.py",
    # Final base move: retract the "second language" diagnosis; the missing
    # link was one unbound name, measured by a paired same-seed A/B.
    "canonical/action_intents/AN_UNBOUND_NAME_WAS_THE_MISSING_LINK_20261116_V1.json",
    "canonical/runtime/what_one_experience_buys_v1.py",
    "canonical/runtime/demonstration_version_space_v1.py",
    "canonical/tests/test_what_one_experience_buys_v1.py",
    "canonical/tests/test_miniwob_one_success_generalisation_v1.py",
    "canonical/verification/THE_TREE_ALREADY_SPOKE_ONE_LANGUAGE_20261116_V1.json",
    # Verifier-root fix on the suite-as-observable path (collection rc 2 was
    # a PYTHONPATH defect, not an information barrier) and its re-run receipt.
    "canonical/verification/SUITE_AS_OBSERVABLE_VERIFIER_ROOTS_20261116_V1.json",
    "canonical/verification/COUNTERFACTUAL_REPAIR_QUIXBUGS_INSERTION_20261116_V1.json",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repaired_from_receipt(data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for value in (
        data.get("repaired_tasks"),
        data.get("measured", {}).get("repaired_tasks"),
        data.get("confirmed"),
    ):
        if isinstance(value, list):
            names.update(str(x) for x in value if isinstance(x, str) and x)
    # QUIXBUGS_EDIT_KIND_TRANSFER has two arms. Only `another_benchmark` is
    # clean: 164 HumanEvalFix fixes and ZERO QuixBugs fixes. `all_other_fixes`
    # was shown 39 QuixBugs fixes and is deliberately never read here.
    clean_arm = data.get("summary", {}).get("another_benchmark", {})
    if isinstance(clean_arm, dict):
        which = clean_arm.get("which")
        if isinstance(which, list):
            names.update(str(x) for x in which if isinstance(x, str) and x)
    # Insert-composition receipt nests its list under summary.repaired_tasks.
    summary_list = data.get("summary", {}).get("repaired_tasks")
    if isinstance(summary_list, list):
        names.update(str(x) for x in summary_list if isinstance(x, str) and x)
    for task, row in (data.get("per_bug") or {}).items():
        if isinstance(row, dict) and row.get("another_benchmark", {}).get("repaired") is True:
            if isinstance(task, str) and task:
                names.add(task)
    for row in data.get("rows", []):
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", ""))
        stage = str(row.get("stage", ""))
        task = row.get("task") or row.get("name")
        if (status.startswith("REPAIRED") or stage.startswith("REPAIRED")) and isinstance(task, str) and task:
            names.add(task)
        if row.get("repaired") is True and isinstance(task, str) and task:
            names.add(task)
    return names


def receipt_census(root: pathlib.Path = ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    union: set[str] = set()
    for name in REPAIR_RECEIPTS:
        path = root / "canonical" / "verification" / name
        if not path.is_file():
            rows.append({"receipt": name, "status": "MISSING", "repaired_tasks": []})
            continue
        data = read_json(path)
        names = repaired_from_receipt(data)
        union |= names
        rows.append({
            "receipt": name,
            "status": "READ",
            "sha256": sha256_bytes(path.read_bytes()),
            "repaired_count": data.get("repaired", data.get("measured", {}).get("repaired")),
            "repaired_tasks": sorted(names),
            "answer_keys_present": data.get("measured", {}).get("answer_keys_present"),
        })
    return {"rows": rows, "repaired_union": sorted(union)}


def real_task_names(quixbugs_root: pathlib.Path) -> list[str]:
    test_dir = quixbugs_root / "python_testcases"
    paths = sorted(test_dir.glob("test_*.py"))
    if not paths:
        raise RuntimeError("NO_REAL_PUBLISHED_TEST_FILES")
    return [p.stem[len("test_"):] for p in paths]


def mechanism_census(root: pathlib.Path = ROOT) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    all_present = True
    for group, paths in MECHANISM_GROUPS.items():
        present = [p for p in paths if (root / p).is_file()]
        missing = [p for p in paths if p not in present]
        all_present = all_present and not missing
        groups[group] = {"count": len(present), "present": present, "missing": missing}
    return {"groups": groups, "all_declared_mechanism_files_present": all_present}


def upstream_head(quixbugs_root: pathlib.Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(quixbugs_root), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def audit(quixbugs_root: pathlib.Path, root: pathlib.Path = ROOT) -> dict[str, Any]:
    tasks = real_task_names(quixbugs_root)
    census = receipt_census(root)
    repaired = set(census["repaired_union"])
    never = sorted(set(tasks) - repaired)
    unknown_repaired = sorted(repaired - set(tasks))
    unmeasurable = sorted(
        task for task in never
        if not (quixbugs_root / "json_testcases" / f"{task}.json").is_file()
    )
    searchable = [task for task in never if task not in set(unmeasurable)]
    mechanisms = mechanism_census(root)
    evidence_present = [p for p in EVIDENCE_READ if (root / p).is_file()]
    evidence_missing = [p for p in EVIDENCE_READ if p not in evidence_present]
    observable_gap_path = root / "canonical" / "verification" / "WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json"
    observable_gap = read_json(observable_gap_path) if observable_gap_path.is_file() else None
    selection_path = root / "canonical" / "verification" / "ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1.json"
    selection = read_json(selection_path) if selection_path.is_file() else None
    rerun_path = root / "canonical" / "verification" / "RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json"
    rerun = read_json(rerun_path) if rerun_path.is_file() else None
    V = root / "canonical" / "verification"
    A = root / "canonical" / "action_intents"
    composed = read_json(V / "COMPOSED_REPAIR_ONE_RUN_20261116_V1.json") if (V / "COMPOSED_REPAIR_ONE_RUN_20261116_V1.json").is_file() else None
    arm = read_json(V / "ARM_LEARNED_IN_ONE_RUN_20261116_V1.json") if (V / "ARM_LEARNED_IN_ONE_RUN_20261116_V1.json").is_file() else None
    travel = read_json(V / "WHAT_ONE_VERIFIED_REPAIR_TRAVELS_20261116_V1.json") if (V / "WHAT_ONE_VERIFIED_REPAIR_TRAVELS_20261116_V1.json").is_file() else None
    browser_new = read_json(V / "THE_SENTENCE_DID_NOT_HAVE_TO_SAY_SUBMIT_20261116_V1.json") if (V / "THE_SENTENCE_DID_NOT_HAVE_TO_SAY_SUBMIT_20261116_V1.json").is_file() else None
    environment = read_json(V / "INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json") if (V / "INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json").is_file() else None
    shuffled = read_json(V / "INSTANT_LEARNING_SHUFFLED_CONTROL_20261116_V1.json") if (V / "INSTANT_LEARNING_SHUFFLED_CONTROL_20261116_V1.json").is_file() else None
    invariance_intent = read_json(A / "THE_INVARIANCE_IS_THE_REACH_20261116_V1.json") if (A / "THE_INVARIANCE_IS_THE_REACH_20261116_V1.json").is_file() else None
    decide_intent = read_json(A / "DECIDE_PAST_THE_ENUMERATION_WALL_20261116_V1.json") if (A / "DECIDE_PAST_THE_ENUMERATION_WALL_20261116_V1.json").is_file() else None
    environment_intent = read_json(A / "THE_PRICE_OF_A_NEW_ENVIRONMENT_20261116_V1.json") if (A / "THE_PRICE_OF_A_NEW_ENVIRONMENT_20261116_V1.json").is_file() else None
    read_first = read_json(V / "READ_FIRST_AND_LEARN_ONLY_FOR_A_NAMED_GAP_20261116_V1.json") if (V / "READ_FIRST_AND_LEARN_ONLY_FOR_A_NAMED_GAP_20261116_V1.json").is_file() else None
    operand = read_json(A / "THE_MISSING_PART_IS_THE_OPERAND_20261116_V1.json") if (A / "THE_MISSING_PART_IS_THE_OPERAND_20261116_V1.json").is_file() else None
    replay = read_json(A / "WHY_LEARN_ONCE_REPLAY_FOREVER_FAILS_20261116_V1.json") if (A / "WHY_LEARN_ONCE_REPLAY_FOREVER_FAILS_20261116_V1.json").is_file() else None
    replay_receipt = read_json(V / "ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json") if (V / "ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json").is_file() else None
    taxonomy = read_json(V / "DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json") if (V / "DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json").is_file() else None
    basin = read_json(V / "ONE_DEMONSTRATION_BASIN_20261116_V1.json") if (V / "ONE_DEMONSTRATION_BASIN_20261116_V1.json").is_file() else None
    long_tail_intent = read_json(A / "THE_REMAINDER_IS_A_LONG_TAIL_20261116_V1.json") if (A / "THE_REMAINDER_IS_A_LONG_TAIL_20261116_V1.json").is_file() else None
    basin_intent = read_json(A / "ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.json") if (A / "ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.json").is_file() else None
    gui_census = read_json(V / "GUI_INVARIANCE_IS_VACUOUS_OR_ABSENT_20261116_V1.json") if (V / "GUI_INVARIANCE_IS_VACUOUS_OR_ABSENT_20261116_V1.json").is_file() else None
    gui_intent = read_json(A / "THE_GUI_HAS_NO_INVARIANCE_TO_FIND_20261116_V1.json") if (A / "THE_GUI_HAS_NO_INVARIANCE_TO_FIND_20261116_V1.json").is_file() else None
    proved = read_json(ROOT / "COMPOSE_ONLY_WHAT_IS_PROVED_20261116_V1.json") if (ROOT / "COMPOSE_ONLY_WHAT_IS_PROVED_20261116_V1.json").is_file() else None
    levers_receipt = read_json(V / "THE_FOUR_LEVERS_OF_LEARNING_FROM_EXPERIENCE_20261116_V1.json") if (V / "THE_FOUR_LEVERS_OF_LEARNING_FROM_EXPERIENCE_20261116_V1.json").is_file() else None
    supply_receipt = read_json(V / "SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json") if (V / "SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json").is_file() else None
    arithmetic_intent = read_json(A / "YOU_ARE_WRONG_ABOUT_ONCE_AND_IT_IS_ARITHMETIC_20261116_V1.json") if (A / "YOU_ARE_WRONG_ABOUT_ONCE_AND_IT_IS_ARITHMETIC_20261116_V1.json").is_file() else None
    supply_intent = read_json(A / "ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.json") if (A / "ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.json").is_file() else None
    compose_effects = read_json(V / "COMPOSE_MEASURED_EFFECTS_20261116_V1.json") if (V / "COMPOSE_MEASURED_EFFECTS_20261116_V1.json").is_file() else None
    index_receipt = read_json(V / "THE_INDEX_IS_THE_BOTTLENECK_20261116_V1.json") if (V / "THE_INDEX_IS_THE_BOTTLENECK_20261116_V1.json").is_file() else None
    derivation_receipt = read_json(V / "SYSTEMATIC_EDIT_DERIVATION_20261116_V1.json") if (V / "SYSTEMATIC_EDIT_DERIVATION_20261116_V1.json").is_file() else None
    compose_intent = read_json(A / "COMPOSITION_CLOSES_ONE_AND_PROVES_TWO_20261116_V1.json") if (A / "COMPOSITION_CLOSES_ONE_AND_PROVES_TWO_20261116_V1.json").is_file() else None
    index_intent = read_json(A / "THE_BOTTLENECK_IS_THE_INDEX_NOT_THE_LEARNING_20261116_V1.json") if (A / "THE_BOTTLENECK_IS_THE_INDEX_NOT_THE_LEARNING_20261116_V1.json").is_file() else None
    value_intent = read_json(A / "SYSTEMATIC_EDIT_VALUE_LAYER_DERIVATION_20261116_V1.json") if (A / "SYSTEMATIC_EDIT_VALUE_LAYER_DERIVATION_20261116_V1.json").is_file() else None
    binding_receipt = read_json(V / "THE_TREE_ALREADY_SPOKE_ONE_LANGUAGE_20261116_V1.json") if (V / "THE_TREE_ALREADY_SPOKE_ONE_LANGUAGE_20261116_V1.json").is_file() else None
    binding_intent = read_json(A / "AN_UNBOUND_NAME_WAS_THE_MISSING_LINK_20261116_V1.json") if (A / "AN_UNBOUND_NAME_WAS_THE_MISSING_LINK_20261116_V1.json").is_file() else None
    answer_key_counts = [
        row["answer_keys_present"] for row in census["rows"]
        if isinstance(row.get("answer_keys_present"), int)
    ]
    task_files_exist = all(
        (quixbugs_root / "python_testcases" / f"test_{task}.py").is_file()
        for task in tasks
    )
    invariants = {
        "all_task_names_from_real_published_test_files": task_files_exist and len(tasks) == len(set(tasks)),
        "repaired_and_open_partition_corpus": set(repaired) | set(never) == set(tasks),
        "no_known_win_in_open_population": not (set(repaired) & set(never)),
        "no_receipt_task_outside_real_corpus": not unknown_repaired,
        "no_answer_key_count_above_zero_in_measured_receipts": all(x == 0 for x in answer_key_counts),
        "all_declared_mechanism_files_present": mechanisms["all_declared_mechanism_files_present"],
        "all_newly_merged_evidence_files_read": not evidence_missing,
        "observable_gap_receipt_read": observable_gap is not None,
        "no_screen_only_verdict_counted_as_repair": bool(
            observable_gap
            and observable_gap.get("repaired") == 0
            and not observable_gap.get("repaired_tasks")
            and observable_gap.get("stages", {}).get("SCREEN_ACCEPTED__CORPUS_TEST_FAILS") == 3
        ),
        "selection_measurement_read": selection is not None,
        "no_majority_vote_counted_as_selector": bool(
            selection
            and selection.get("why_majority_vote_is_not_a_selector", {}).get("conclusion")
            == "self-consistency is not evidence; a labelled answer to a chosen input is"
            and selection.get("summary", {}).get("settled_and_equal_to_the_reference_behaviour") == 8
        ),
        "claimed_learned_arm_superseded_by_pytest_rerun": bool(
            rerun
            and len(rerun.get("confirmed", [])) == 16
            and len(rerun.get("inapplicable", [])) == 4
            and rerun.get("screen_said_pass_runner_said_no_in_the_record") == 0
        ),
        # After insert composition + the suite-as-observable PYTHONPATH fix the
        # measured union is 32 of 40. The composed-run receipt still reports
        # its own 24 independently below.
        "verified_union_is_32_after_insert_and_verifier_roots": len(repaired) == 32,
        "composed_run_is_one_run_one_judge_24_of_40": bool(
            composed
            and composed.get("tasks") == 41
            and composed.get("repaired") == 24
            and composed.get("stages", {}).get("REPAIRED") == 24
            and sum(len(v) for v in composed.get("by_arm", {}).values()) == 24
            and composed.get("model_dependency_count") == 0
        ),
        "invariance_changes_reach_not_capability": bool(
            arm
            and travel
            and invariance_intent
            and arm.get("learned_arms", {}).get("LEARNED_THIS_RUN", {}).get("survived_the_programs_own_examples") == 0
            and arm.get("learned_arms", {}).get("ALPHA_LEARNED_THIS_RUN", {}).get("survived_the_programs_own_examples") == 4
            and arm.get("learned_arms", {}).get("ALPHA_LEARNED_THIS_RUN", {}).get("won")
            == ["find_in_sorted", "mergesort", "next_palindrome", "quicksort"]
            and arm.get("learned_arms", {}).get("ALPHA_LEARNED_THIS_RUN", {}).get("wins_over_bugs_the_three_arms_could_not_repair") == []
            and travel.get("rung_3_a_different_bug", {}).get("transfers") == 11
            and len(travel.get("rung_3_a_different_bug", {}).get("tasks_repaired", [])) == 5
            and invariance_intent.get("measured_effect", {}).get("capability_gain_over_the_three_arm_composition") == 0
        ),
        "exact_decision_past_enumeration_wall_is_not_capability_credit": bool(
            decide_intent
            and decide_intent.get("measured_effect", {}).get("raw_survivors_pinned_corpus") == 8388600
            and decide_intent.get("measured_effect", {}).get("inclusion_extraction_seconds") == 0.0
            and decide_intent.get("measured_effect", {}).get("exhaustive_ie_families") == 5058
            and decide_intent.get("measured_effect", {}).get("capability_credit_claimed") is False
            and decide_intent.get("measured_effect", {}).get("benchmark_credit_claimed") is False
        ),
        "browser_zero_experience_census_is_66_with_no_regressions": bool(
            browser_new
            and browser_new.get("measured_effect", {}).get("seed_1060", {}).get("after") == 66
            and browser_new.get("measured_effect", {}).get("seed_1060", {}).get("before") == 52
            and browser_new.get("measured_effect", {}).get("regressions") == []
            and browser_new.get("measured_effect", {}).get("parameters") == 0
            and browser_new.get("measured_effect", {}).get("experience") == "none"
        ),
        "new_environment_cost_law_is_bounded_and_shuffle_invariant": bool(
            environment
            and shuffled
            and environment_intent
            and environment.get("summary", {}).get("machines") == 4
            and environment.get("summary", {}).get("requests") == 16
            and environment.get("summary", {}).get("requests_solved") == 13
            and environment.get("summary", {}).get("learn_each_requests_solved") == 11
            and environment.get("summary", {}).get("learn_each_trials_per_request") == 2.125
            and environment_intent.get("measured_effect", {}).get("trials_per_request_after_adaptation") == 1.0
            and environment_intent.get("measured_effect", {}).get("trials_per_request_by_demonstration") == 2.125
            and shuffled.get("summary", {}).get("requests_solved") == 13
            and environment_intent.get("measured_effect", {}).get("break_even_requests_per_machine") == 6.44
            and environment_intent.get("measured_effect", {}).get("refusals", {}).get("effect_needs_composition") == ["TARBALL REPLACE"]
        ),
        "read_first_policy_is_measured_and_does_not_forbid_learning": bool(
            read_first
            and read_first.get("measured_effect", {}).get("composition_rule", {}).get("LEARN_pages") == 41
            and read_first.get("measured_effect", {}).get("composition_rule", {}).get("READ_pages") == 89
            and read_first.get("measured_effect", {}).get("composition_rule", {}).get("READ_pages_reading_won") == 66
            and str(read_first.get("measured_effect", {}).get("composition_rule", {}).get("false_negatives", "")).startswith("0")
            and read_first.get("measured_effect", {}).get("cells", {}).get("reading_wins_where_nothing_was_demonstrable") == 9
        ),
        "operand_addition_is_bounded_to_its_design_set": bool(
            operand
            and operand.get("measured_effect", {}).get("addition_vs_shipped", {}).get("chromium_seed_1060", {}).get("gains") == 5
            and operand.get("measured_effect", {}).get("addition_vs_shipped", {}).get("chromium_seed_1060", {}).get("losses") == 0
            and operand.get("measured_effect", {}).get("addition_vs_shipped", {}).get("chromium_seed_1060", {}).get("actions_saved") == 1917
            and operand.get("measured_effect", {}).get("transfer_boundary", {}).get("held_out_pages") == 121
            and operand.get("measured_effect", {}).get("transfer_boundary", {}).get("shipped_solves") == 77
            and operand.get("measured_effect", {}).get("transfer_boundary", {}).get("union_solves") == 77
            and operand.get("measured_effect", {}).get("transfer_boundary", {}).get("gains_outside_design_set") == []
            and str(operand.get("measured_effect", {}).get("compute_control", {}).get("shipped_hand_at_4x_budget", "")).startswith("0 of 5")
        ),
        "replay_forever_is_falsified_by_state_drift": bool(
            replay
            and replay_receipt
            and replay.get("measured_effect", {}).get("arms", {}).get("live_re_decision", {}).get("pairs") == 228
            and replay.get("measured_effect", {}).get("arms", {}).get("live_re_decision", {}).get("premise_held_after_the_change") == 228
            and replay.get("measured_effect", {}).get("arms", {}).get("replay_of_the_record", {}).get("matches_live") == 106
            and replay.get("measured_effect", {}).get("arms", {}).get("replay_of_the_record", {}).get("silent_corruption") == 71
            and replay.get("measured_effect", {}).get("arms", {}).get("replay_of_the_record", {}).get("stale") == 122
            and replay_receipt.get("counts", {}).get("SILENT_CORRUPTION") == 71
        ),
        "declared_format_prior_is_too_small_to_be_a_single_lever": bool(
            taxonomy
            and taxonomy.get("declared_surface", {}).get("pages_usable") == 123
            and taxonomy.get("declared_surface", {}).get("pages_declaring_a_format") == 6
            and taxonomy.get("declared_surface", {}).get("pages_with_a_typeable_field") == 39
            and taxonomy.get("declared_surface", {}).get("pages_with_no_typeable_field") == 84
            and taxonomy.get("declared_surface", {}).get("input_type_counts", {}).get("text") == 37
        ),
        "the_unsolved_remainder_is_a_long_tail_not_one_bottleneck": bool(
            taxonomy
            and long_tail_intent
            and taxonomy.get("taxonomy", {}).get("pages_unsolved") == 46
            and taxonomy.get("taxonomy", {}).get("classes") == 16
            and taxonomy.get("taxonomy", {}).get("largest_class") == 6
            and long_tail_intent.get("measured_effect", {}).get("taxonomy", {}).get("classes") == 16
            and long_tail_intent.get("measured_effect", {}).get("taxonomy", {}).get("largest_class") == 6
            and "English phrase" in taxonomy.get("why_the_algebra_did_not_transfer", {}).get("cause", "")
        ),
        "one_demonstration_learns_a_domain_not_the_environment": bool(
            basin
            and basin_intent
            and basin.get("environment", {}).get("states") == 168
            and basin.get("environment", {}).get("executed_transitions") == 1680
            and basin.get("environment", {}).get("truncated") is False
            and basin_intent.get("measured_effect", {}).get("arms", {}).get("status_level_goal", {}).get("true_domain") == 112
            and basin_intent.get("measured_effect", {}).get("arms", {}).get("premise_task_under_status", {}).get("undecidable") == 24
            and basin_intent.get("measured_effect", {}).get("arms", {}).get("premise_task_under_one_file", {}).get("undecidable") == 16
            and basin_intent.get("measured_effect", {}).get("arms", {}).get("premise_task_under_all_content", {}).get("undecidable") == 0
            and basin_intent.get("measured_effect", {}).get("arms", {}).get("command_output_control", {}).get("undecidable") == 168
        ),
        "gui_identity_invariance_is_vacuous_by_construction": bool(
            gui_census
            and gui_census.get("part_a_invariance_census", {}).get("identity_arms") == 15
            and gui_census.get("part_a_invariance_census", {}).get("identity_verdicts", {}).get("INVARIANT") == 13
            and gui_census.get("part_a_identity_use_by_the_rules", "").startswith("derived_value_v1:397")
        ),
        "gui_judge_has_no_task_equivalence_to_quotient": bool(
            gui_census
            and gui_intent
            and gui_census.get("part_a_invariance_census", {}).get("judge_pages") == 5
            and gui_intent.get("measured_effect", {}).get("judge_pages_with_quotient_zero") == 4
            and gui_census.get("part_a_invariance_census", {}).get("pages_with_a_nontrivial_quotient") == ["scroll-text"]
            and gui_census.get("part_a_invariance_census", {}).get("quotient_is_real", {}).get("scroll-text", "").startswith("SEMANTIC")
        ),
        "phrase_blind_basis_adds_no_full_surface_capability": bool(
            gui_census
            and gui_intent
            and gui_census.get("part_b_phrase_blind_arm", {}).get("pages") == 123
            and gui_census.get("part_b_phrase_blind_arm", {}).get("gated_solved") == 9
            and gui_census.get("part_b_phrase_blind_arm", {}).get("blind_solved") == 5
            and gui_census.get("part_b_phrase_blind_arm", {}).get("blind_only") == []
            and gui_intent.get("measured_effect", {}).get("phrase_blind_arm_design_set", {}).get("blind_solved") == 4
            and gui_intent.get("measured_effect", {}).get("phrase_blind_arm_design_set", {}).get("gated_solved") == 5
        ),
        "proved_composition_is_bounded_not_a_single_lever": bool(
            proved
            and proved.get("second_step_attempts") == 80
            and proved.get("premises_held_attempts") == 58
            and proved.get("composed_verified") == 31
            and proved.get("damaged") == 0
            and proved.get("reach_compose") == 0.3875
            and proved.get("reach_where_premises_held") == 0.5345
            and proved.get("boxes", {}).get("PREMISE_DIED") == 22
            and proved.get("boxes", {}).get("B_REFUSED") == 27
            and proved.get("boxes", {}).get("NO_SECOND_CANDIDATE") == 34
        ),
        "one_demonstration_is_arithmetic_not_identification": bool(
            levers_receipt
            and arithmetic_intent
            and round(float(levers_receipt.get("levers", {}).get("bits_before", 0)), 4) == 5.5546
            and round(float(levers_receipt.get("levers", {}).get("bits_after_one", 0)), 4) == 3.8176
            and arithmetic_intent.get("measured_effect", {}).get("bits_before") == 5.5546
            and arithmetic_intent.get("measured_effect", {}).get("bits_after_one") == 3.8176
            and arithmetic_intent.get("measured_effect", {}).get("bits_per_chosen_question") == 1.9088
            and arithmetic_intent.get("measured_effect", {}).get("bits_per_further_demonstration") == 1.0927
            and arithmetic_intent.get("measured_effect", {}).get("question_over_demonstration_ratio") == 1.747
            and arithmetic_intent.get("measured_effect", {}).get("state_name_arm", {}).get("as_is", {}).get("carried_model_survived") == 7
            and arithmetic_intent.get("measured_effect", {}).get("state_name_arm", {}).get("renamed", {}).get("carried_model_survived") == 0
        ),
        "one_demonstration_amortises_only_a_sixth_of_real_work": bool(
            supply_receipt
            and supply_intent
            and supply_receipt.get("commits_in_corpus") == 393
            and supply_receipt.get("scanned") == 268
            and supply_intent.get("measured_effect", {}).get("arms", {}).get("supply", {}).get("siblings_shape_only") == 43
            and supply_intent.get("measured_effect", {}).get("arms", {}).get("supply", {}).get("siblings_context_both") == 31
            and supply_intent.get("measured_effect", {}).get("arms", {}).get("determinacy", {}).get("pairs") == 245
            and supply_intent.get("measured_effect", {}).get("arms", {}).get("determinacy", {}).get("verbatim_repeats") == 103
            and supply_intent.get("measured_effect", {}).get("arms", {}).get("determinacy", {}).get("forced_by_the_demonstration") == 31
            and supply_intent.get("measured_effect", {}).get("arms", {}).get("determinacy", {}).get("wrong") == 64
        ),
        "index_key_lacks_the_observable_not_just_granularity": bool(
            index_receipt
            and index_intent
            and len(index_receipt.get("sweep", [])) == 5
            and index_receipt.get("usable_key_families") == []
            and index_receipt.get("verdict") == "NO_GRANULARITY_OF_THESE_FEATURES_SEPARATES_WHAT_THE_POLICY_DEPENDS_ON"
            and index_intent.get("measured_effect", {}).get("instance_sensitivity", {}).get("kinds_whose_policy_set_changes_with_instance") == 5
            and index_intent.get("measured_effect", {}).get("cross_language", {}).get("store_offered_any_non_python") is False
            and len(index_intent.get("measured_effect", {}).get("cross_language", {}).get("transferred_and_narrow", [])) == 4
            and index_intent.get("measured_effect", {}).get("retrieval_ceiling_on_real_prs", {}).get("kinds_with_zero_matches") == 7
        ),
        "composition_needs_a_frame_and_proves_its_refusals": bool(
            compose_effects
            and compose_intent
            and compose_effects.get("summary", {}).get("solved") == 14
            and compose_effects.get("summary", {}).get("solved_with_two_steps") == 1
            and compose_effects.get("summary", {}).get("proven_unreachable") == 2
            and compose_effects.get("summary", {}).get("prediction_mismatches") == 0
            and compose_effects.get("summary", {}).get("unrequested_side_effects") == 0
            and compose_effects.get("summary", {}).get("relaxed_plans_that_break_the_frame") == 15
            and compose_intent.get("measured_effect", {}).get("solved_before_composition") == 13
        ),
        "inferred_edit_values_are_guesses_until_execution": bool(
            value_intent
            and derivation_receipt
            and value_intent.get("measured_effect", {}).get("arms", {}).get("value_layer", {}).get("derive", {}).get("precision_when_fired") == 0.2143
            and value_intent.get("measured_effect", {}).get("arms", {}).get("value_layer", {}).get("derive_contrast", {}).get("precision_when_fired") == 0.4
            and value_intent.get("measured_effect", {}).get("arms", {}).get("value_layer", {}).get("derive", {}).get("derivation_fired") == 42
            and derivation_receipt.get("commits_in_corpus") == 393
        ),
        "unbound_name_binding_is_local_and_retracts_second_language_claim": bool(
            binding_receipt
            and binding_intent
            and binding_receipt.get("decision") == "THE_DESCRIPTION_WAS_NEVER_THE_PROBLEM__THE_BINDING_WAS"
            and len(binding_receipt.get("retraction", {}).get("how_it_was_refuted", [])) == 4
            and binding_receipt.get("measured_effect_kept", {}).get("bits_per_step_still_reported") == 5.428
            and binding_receipt.get("measured_effect_kept", {}).get("the_price_of_the_preferred_description") == 0.102
            and binding_receipt.get("measured_effect_kept", {}).get("elements_where_the_preferred_description_is_ambiguous", {}).get("count") == 67
            and binding_receipt.get("what_was_actually_missing", {}).get("the_effect", {}).get("controlled_ab", {}).get("after_mean") == 0.29
            and binding_receipt.get("what_was_actually_missing", {}).get("the_effect", {}).get("controlled_ab", {}).get("before_mean") == 0.2233
            and binding_intent.get("measured_effect", {}).get("id_binding_ab", {}).get("delta") == 0.0667
            and binding_intent.get("measured_effect", {}).get("structure_field_ab", {}).get("delta") == 0.0022
            and "run variance" in " ".join(binding_receipt.get("honest_limits", [])).lower()
        ),
    }
    audit_pass = all(invariants.values())
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "upstream": "https://github.com/jkoppel/QuixBugs",
        "upstream_head": upstream_head(quixbugs_root),
        "corpus": {
            "real_published_test_files": len(tasks),
            "task_names": tasks,
            "source_of_task_names": "python_testcases/test_*.py in a fresh clone; no invented task",
        },
        "measured_receipts": census["rows"],
        "receipt_arms_ignored": list(RECEIPT_ARMS_IGNORED),
        "union_projection_status": {
            "status": "ONE_COMPOSED_RUN_UNDER_THE_CORPUS_PYTEST_MEASURED_24_OF_40",
            "reason": "PR #6887 re-ran the claimed learned-arm repairs from their own record: 16 confirmed, 4 not reconstructible, 0 screen disagreements in that record. The projected 26/40 is superseded by the verified 24/40; main #6892 then ran the three vocabularies together in one command under the corpus's own pytest and measured the same 24/40 in 387.8 s. The earlier union is no longer an arithmetic projection, but capability is unchanged: 16 tasks remain hard-open.",
        },
        "composed_run": {
            "receipt": "canonical/verification/COMPOSED_REPAIR_ONE_RUN_20261116_V1.json",
            "tasks": (composed or {}).get("tasks"),
            "repaired": (composed or {}).get("repaired"),
            "seconds": (composed or {}).get("seconds"),
            "by_arm": (composed or {}).get("by_arm", {}),
            "stages": (composed or {}).get("stages", {}),
            "judge": "the corpus's own pytest on a fresh copy with the answer key absent",
            "status": "MEASURED_ONE_RUN_NOT_CAPABILITY_GAIN_OVER_THE_PYTEST_REJUDGED_UNION",
        },
        "invariance_and_reach": {
            "receipts": [
                "canonical/verification/ARM_LEARNED_IN_ONE_RUN_20261116_V1.json",
                "canonical/verification/WHAT_ONE_VERIFIED_REPAIR_TRAVELS_20261116_V1.json",
            ],
            "literal_preconditions": (arm or {}).get("learned_arms", {}).get("LEARNED_THIS_RUN", {}),
            "alpha_canonical_preconditions": (arm or {}).get("learned_arms", {}).get("ALPHA_LEARNED_THIS_RUN", {}),
            "travel_ladder": {
                "rung_1_same_bug": (travel or {}).get("rung_1_same_bug", {}),
                "rung_2_same_bug_renamed": (travel or {}).get("rung_2_same_bug_renamed", {}),
                "rung_3_a_different_bug": (travel or {}).get("rung_3_a_different_bug", {}),
            },
            "capability_gain_over_the_three_arm_composition": (invariance_intent or {}).get("measured_effect", {}).get("capability_gain_over_the_three_arm_composition"),
            "status": "DEMONSTRATION_IS_CONTENT_INVARIANCE_IS_REACH",
        },
        "exact_decision_past_enumeration_wall": {
            "receipt": "canonical/action_intents/DECIDE_PAST_THE_ENUMERATION_WALL_20261116_V1.json",
            "measured_effect": (decide_intent or {}).get("measured_effect", {}),
            "status": "EXACT_INCLUSION_EXTRACTION_NOT_A_NEW_CAPABILITY",
        },
        "browser_zero_experience_census": {
            "receipt": "canonical/verification/THE_SENTENCE_DID_NOT_HAVE_TO_SAY_SUBMIT_20261116_V1.json",
            "measured_effect": (browser_new or {}).get("measured_effect", {}),
            "status": "IMPLIED_ENDING_AND_PICKER_ARE_CONTRACT_NOT_NEW_WEIGHTS",
        },
        "new_environment_cost_law": {
            "receipts": [
                "canonical/verification/INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json",
                "canonical/verification/INSTANT_LEARNING_SHUFFLED_CONTROL_20261116_V1.json",
            ],
            "summary": (environment or {}).get("summary", {}),
            "shuffled_summary": (shuffled or {}).get("summary", {}),
            "measured_effect": (environment_intent or {}).get("measured_effect", {}),
            "status": "COST_MOVES_FROM_REQUESTS_TO_ENVIRONMENTS_NOT_ZERO_AND_NOT_ALL_COMPUTER_USE",
        },
        "read_first_operand_and_replay_drift": {
            "receipts": [
                "canonical/verification/READ_FIRST_AND_LEARN_ONLY_FOR_A_NAMED_GAP_20261116_V1.json",
                "canonical/verification/DERIVED_VALUE_FULL_SUITE_20261116_V1.json",
                "canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json",
            ],
            "read_first": (read_first or {}).get("measured_effect", {}),
            "operand": (operand or {}).get("measured_effect", {}),
            "replay": (replay or {}).get("measured_effect", {}),
            "status": "READ_FIRST_FOR_A_NAMED_GAP_ADD_THE_MISSING_OPERAND_NEVER_REPLAY_A_PLAN_AS_A_MACRO",
        },
        "long_tail_trigger_and_basin": {
            "receipts": [
                "canonical/verification/DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json",
                "canonical/verification/ONE_DEMONSTRATION_BASIN_20261116_V1.json",
            ],
            "declared_surface": (taxonomy or {}).get("declared_surface", {}),
            "taxonomy": (taxonomy or {}).get("taxonomy", {}),
            "why_the_algebra_did_not_transfer": (taxonomy or {}).get("why_the_algebra_did_not_transfer", {}),
            "basin": (basin_intent or {}).get("measured_effect", {}),
            "status": "NO_SINGLE_LEVER_THE_REMAINDER_IS_A_LONG_TAIL_AND_THE_PREMISE_MUST_BE_OBSERVABLE",
        },
        "gui_invariance_and_operand_boundary": {
            "receipt": "canonical/verification/GUI_INVARIANCE_IS_VACUOUS_OR_ABSENT_20261116_V1.json",
            "identity_invariance": (gui_census or {}).get("part_a_invariance_census", {}),
            "judges": (gui_census or {}).get("part_a_judges", []),
            "phrase_blind_arm": (gui_census or {}).get("part_b_phrase_blind_arm", {}),
            "measured_effect": (gui_intent or {}).get("measured_effect", {}),
            "status": "NO_GUI_INVARIANCE_LEVER_THE_REMAINING_BOUNDARY_IS_AN_OPERAND_NOT_ON_THE_PAGE",
        },
        "proved_composition": {
            "receipt": "COMPOSE_ONLY_WHAT_IS_PROVED_20261116_V1.json",
            "scan": (proved or {}).get("scan", {}),
            "step_one": (proved or {}).get("step_one", {}),
            "boxes": (proved or {}).get("boxes", {}),
            "reach": {
                "compose": (proved or {}).get("reach_compose"),
                "where_premises_held": (proved or {}).get("reach_where_premises_held"),
            },
            "status": "COMPOSE_ONLY_WHAT_IS_PROVED_AFFIRMATIVE_ORGAN_IS_BOUNDED_NOT_A_SINGLE_LEVER",
        },
        "four_levers_and_edit_supply": {
            "receipts": [
                "canonical/verification/THE_FOUR_LEVERS_OF_LEARNING_FROM_EXPERIENCE_20261116_V1.json",
                "canonical/verification/SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json",
            ],
            "law": (levers_receipt or {}).get("law", ""),
            "levers": (levers_receipt or {}).get("levers", {}),
            "state_name_arm": (levers_receipt or {}).get("state_name_arm", {}),
            "arithmetic": (arithmetic_intent or {}).get("measured_effect", {}),
            "supply": (supply_intent or {}).get("measured_effect", {}),
            "status": "ONCE_IS_ARITHMETIC_AND_REAL_WORK_SUPPLY_IS_ABOUT_ONE_SIXTH",
        },
        "index_specification_and_value_layer": {
            "receipts": [
                "canonical/verification/THE_INDEX_IS_THE_BOTTLENECK_20261116_V1.json",
                "canonical/verification/COMPOSE_MEASURED_EFFECTS_20261116_V1.json",
                "canonical/verification/SYSTEMATIC_EDIT_DERIVATION_20261116_V1.json",
            ],
            "index": {
                "verdict": (index_receipt or {}).get("verdict", ""),
                "reading": (index_receipt or {}).get("reading", ""),
                "sweep": (index_receipt or {}).get("sweep", []),
                "usable_key_families": (index_receipt or {}).get("usable_key_families", []),
                "measured_effect": (index_intent or {}).get("measured_effect", {}),
            },
            "composition": {
                "summary": (compose_effects or {}).get("summary", {}),
                "measured_effect": (compose_intent or {}).get("measured_effect", {}),
                "status": "COMPOSITION_CLOSES_ONE_REFUSAL_PROVES_TWO_AND_NEEDS_A_FRAME",
            },
            "value_inference": {
                "measured_effect": (value_intent or {}).get("measured_effect", {}),
                "status": "A_STORED_VALUE_IS_A_STORED_GUESS_ONLY_EXECUTION_CLOSES_IT",
            },
            "status": "INDEX_AND_FRAME_ARE_NECESSARY_SHARED_DEFECTS_NOT_A_SINGLE_SUFFICIENT_LEVER",
        },
        "unbound_name_binding_and_retraction": {
            "receipt": "canonical/verification/THE_TREE_ALREADY_SPOKE_ONE_LANGUAGE_20261116_V1.json",
            "decision": (binding_receipt or {}).get("decision", ""),
            "retraction": (binding_receipt or {}).get("retraction", {}),
            "measured_effect_kept": (binding_receipt or {}).get("measured_effect_kept", {}),
            "what_was_actually_missing": (binding_receipt or {}).get("what_was_actually_missing", {}),
            "second_fix": (binding_receipt or {}).get("second_fix", {}),
            "honest_limits": (binding_receipt or {}).get("honest_limits", []),
            "measured_effect": (binding_intent or {}).get("measured_effect", {}),
            "status": "ONE_UNBOUND_NAME_IS_A_LOCAL_BINDING_FIX_NOT_A_SECOND_LANGUAGE_OR_SINGLE_LEVER",
        },
        "verified_repair_rerun": {
            "receipt": "canonical/verification/RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json",
            "claimed_repaired": (rerun or {}).get("claimed_repaired"),
            "confirmed": (rerun or {}).get("confirmed", []),
            "not_confirmed": (rerun or {}).get("not_confirmed", []),
            "inapplicable": (rerun or {}).get("inapplicable", []),
            "screen_said_pass_runner_said_no_in_the_record": (rerun or {}).get("screen_said_pass_runner_said_no_in_the_record"),
        },
        "observable_gap_receipt": {
            "receipt": "canonical/verification/WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json",
            "tasks_without_json": (observable_gap or {}).get("tasks_with_no_json", []),
            "tasks_measured": (observable_gap or {}).get("tasks_measured"),
            "repaired": (observable_gap or {}).get("repaired"),
            "stages": (observable_gap or {}).get("stages", {}),
        },
        "selection_measurement": {
            "receipt": "canonical/verification/ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1.json",
            "corpus": "100 held-out HumanEvalFix bugs; scored bug's own fix was never a lesson",
            "summary": (selection or {}).get("summary", {}),
            "majority_vote": (selection or {}).get("why_majority_vote_is_not_a_selector", {}),
            "status": "SELECTION_AMONG_TEST_PASSING_CANDIDATES_NOT_A_QUIXBUGS_REPAIR_RECEIPT",
        },
        "repaired_union_count": len(repaired),
        "repaired_union_tasks": sorted(repaired),
        "known_wins_not_counted_as_progress": sorted(repaired),
        "hard_open_population_count": len(never),
        "hard_open_population_tasks": never,
        "example_searchable_open_tasks": searchable,
        "example_searchable_open_count": len(searchable),
        "unmeasurable_without_published_input_output_examples": unmeasurable,
        "unmeasurable_without_published_input_output_examples_count": len(unmeasurable),
        "unknown_receipt_tasks_outside_real_corpus": unknown_repaired,
        "mechanism_census_by_effect": mechanisms["groups"],
        "evidence_read_by_effect": evidence_present,
        "evidence_missing": evidence_missing,
        "invariants": invariants,
        "audit_pass": audit_pass,
        "killed_instruments": [
            {
                "instrument": "canonical/runtime/bound_capabilities/software_patch_cegis_z3_v1.py",
                "calibration_on_already_solved_tasks": "0 / 5",
                "calibration_tasks_not_counted_as_progress": [
                    "bitcount", "pascal", "quicksort", "is_valid_parenthesization", "rpn_eval"
                ],
                "open_task_probe_not_counted_as_progress": ["sqrt", "flatten", "to_base"],
                "reason_killed": (
                    "A zero result on open tasks would be vacuous because the instrument also "
                    "returned zero on five already-solved calibration tasks; sqrt hit its own "
                    "baseline timeout. Do not ship an all-zero open-task run as evidence."
                ),
            },
        ],
        "what_this_is": (
            "A set-algebra audit of measured receipts against the real published corpus, using only "
            "clean held-out arms, plus an effect-based census of mechanisms already in the tree. "
            "The 24/40 union is now also one composed run under the corpus pytest, and the audit "
            "reads the later invariance, exact-decision, browser, new-environment, read-first, "
            "operand, replay-drift, trigger, long-tail, one-demonstration-basin and GUI-invariance "
            "measurements without crediting any of them as new capability. It also indexes the separate selection "
            "measurement among test-passing HumanEvalFix candidates; that measurement is not a "
            "QuixBugs repair receipt. It is not a solver."
        ),
        "what_this_is_not": (
            "Not a repair contest, not a capability, not a benchmark score, not independent "
            "verification, not a proof of correctness, not a sentience claim, and not permission "
            "to merge over a red or missing referee."
        ),
        "hard_nonclaims": [
            "NOT_A_FRONTIER_SCORE",
            "NOT_SWE_BENCH",
            "NO_SYNTHETIC_TASKS",
            "NO_KNOWN_WIN_COUNTED_AS_PROGRESS",
            "NO_SCREEN_ONLY_VERDICT_COUNTED_AS_REPAIR",
            "NO_MAJORITY_VOTE_AS_SELECTOR",
            "NO_UNRERUN_CLAIMED_ARM_COUNTED_AS_CONFIRMED",
            "NO_NEW_LEARNER_OR_VERIFIER",
            "NO_CAPABILITY_REGISTERED",
            "NO_PROTECTED_PATH_TOUCHED",
            "NO_MODEL_CALLS",
            "NO_NETWORK_CALLS",
            "NO_WEIGHT_UPDATE",
            "NO_REPLAY_FOREVER_ANYWHERE_CLAIM",
            "NO_SINGLE_LEVER_CLAIM",
            "NO_ONE_DEMONSTRATION_PER_ENVIRONMENT_CLAIM",
            "NO_GUI_INVARIANCE_LEVER",
            "NO_PROOF_COMPOSITION_AS_SINGLE_LEVER",
            "NO_ONCE_IDENTIFIES_A_RULE",
            "NO_ONE_DEMONSTRATION_COVERS_MOST_REAL_WORK",
            "NO_GRANULARITY_OF_THESE_FEATURES_AS_A_REPAIR",
            "NO_COMPOSITION_CLOSES_COMPUTER_USE",
            "NO_INFERRED_VALUE_AS_AN_ESTABLISHED_FACT",
            "NO_INDEX_OR_SPECIFICATION_FIX_AS_TERMINAL_UNLOCK",
            "NO_SECOND_LANGUAGE_5_43_BITS_CLAIM",
            "NO_ID_BINDING_AS_SINGLE_LEVER",
            "NO_UNPAIRED_RUN_VARIANCE_CLAIM",
            "PRODUCER_RUN_NOT_INDEPENDENT_VERIFICATION",
            "TERMINAL_TRUTH_UNTOUCHED",
        ],
        "supersedes": list(SUPERSEDES),
        "model_dependency_count": MODEL_DEPENDENCY_COUNT,
        "network_dependency_count": NETWORK_DEPENDENCY_COUNT,
        "incremental_spend_usd": INCREMENTAL_SPEND_USD,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", required=True, help="path to a real QuixBugs clone")
    parser.add_argument("--out", required=True, help="where to write the audit receipt")
    parser.add_argument("--repo-root", default=str(ROOT), help="repository root holding receipts")
    args = parser.parse_args(list(argv) if argv is not None else None)
    quixbugs_root = pathlib.Path(args.quixbugs).resolve()
    repo_root = pathlib.Path(args.repo_root).resolve()
    result = audit(quixbugs_root, repo_root)
    out = pathlib.Path(args.out)
    if not out.is_absolute():
        out = repo_root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"real_tasks={result['corpus']['real_published_test_files']} "
        f"repaired_union={result['repaired_union_count']} "
        f"hard_open={result['hard_open_population_count']} "
        f"example_searchable_open={result['example_searchable_open_count']} "
        f"unmeasurable={result['unmeasurable_without_published_input_output_examples_count']} "
        f"audit_pass={result['audit_pass']}"
    )
    return 0 if result["audit_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
