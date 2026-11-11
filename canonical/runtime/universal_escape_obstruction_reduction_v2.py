"""Exact-byte reconciliation of the live universal proof frontier.

This is not a solver. It composes already-proved Brain theorems and current
authority into the smallest still-live universal obstruction:

    target-supported reachable unsplittable policy-conflict class.

It also records that serial enumeration of the non-exhaustive D_B cache is not
required for the positive universal route. Any source-byte drift or semantic
mismatch fails closed. No U-empty, ABC, D-finality, or terminal authority is
granted here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_ESCAPE_OBSTRUCTION_REDUCTION_V2"

SOURCES = {
    "authority": (
        "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        "3d73433cd177afa603b6e96f93bdbc8cf708f132",
    ),
    "single_primitive": (
        "canonical/governance/ABOVE_EXPONENTIAL_U_SINGLE_PRIMITIVE_RECONCILIATION_20261007_V2.json",
        "f0776f0f900962228e8924aaf602d98973f5eddb",
    ),
    "catchall": (
        "canonical/governance/DB_ESCAPE_CATCHALL_TOTAL_ABSTRACTION_REDUCTION_20261007_V1.json",
        "3bd081e9253a5d7dff32c213c1c11b6e03834308",
    ),
    "obstruction": (
        "canonical/governance/OBSERVATIONAL_QUOTIENT_ESCAPE_PROGRESS_REDUCTION_20261007_V1.json",
        "57eeba3e14fc042f690d7a75d575993ac68a4246",
    ),
    "frontier": (
        "canonical/governance/CURRENT_PRIMITIVE_U_FRONTIER_20261007_V1.json",
        "8340829830dc81095abd4d643a8be6894a39f2f3",
    ),
    "p3_cegar": (
        "canonical/governance/P3_ROBUST_POLICY_ADEQUACY_CEGAR_ACTIVATION_20261008_V1.json",
        "d31c083392134b51d3bb094689e1c7bdfa6f7d68",
    ),
    "gdpval_cut": (
        "canonical/governance/GDPVAL_EVALUATION_LAW_MINIMUM_INFORMATION_CUT_20261008_V1.json",
        "7bf8b2ffc8186e14380da080e5a9832a2fd9a2a8",
    ),
    "gdpval_quotient": (
        "canonical/governance/GDPVAL_EVALUATOR_FACING_QUOTIENT_U_ROUTE_20261008_V1.json",
        "0ca5160b40d9d378688b480b2972a7ee334a1655",
    ),
    "acceptance_top": (
        "canonical/governance/UNIVERSAL_ACCEPTANCE_RELATION_TOP_REDUCTION_20261008_V1.json",
        "478f38e9a746e9db99767dd03376481834decd51",
    ),
    "p3_seed": (
        "canonical/verification/UNIVERSAL_REAL_DB_RESIDUAL_P3_SEED_VERIFICATION_20261008_V1.json",
        "25d4129ac679360e0a9f5c69e12b625dcad66b6b",
    ),
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "only_live_universal_obstruction": None,
        "serial_db_region_enumeration_required": True,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def verify_reduction(*, repo_root: str | Path) -> dict[str, Any]:
    docs: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, str]] = {}
    try:
        for key, (path, blob) in SOURCES.items():
            resolved = resolve_receipt_bytes(
                {"path": path, "git_blob_sha": blob},
                repo_root=repo_root,
            )
            docs[key] = resolved["document"]
            bindings[key] = {"path": path, "git_blob_sha": blob}
    except Exception as exc:
        return _fail(
            "SOURCE_BINDING_INVALID",
            exception_type=type(exc).__name__,
            detail_text=str(exc)[:240],
        )

    errors: list[str] = []

    authority = docs["authority"]
    if authority.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V34":
        errors.append("AUTHORITY_SCHEMA")
    override = authority.get("terminal_architecture_override") or {}
    if override.get("primary_pre_abc_research_root") != "U_EMPTY":
        errors.append("AUTHORITY_PRIMARY_ROOT")
    live = (
        "SCOPE_COMPLETE_OBSERVATIONAL_QUOTIENT_WITH_NO_TARGET_SUPPORTED_"
        "UNSPLITTABLE_POLICY_CONFLICT_CLASS"
    )
    if override.get("live_primitive") != live:
        errors.append("AUTHORITY_LIVE_PRIMITIVE")
    if override.get("u_empty_proved") is not False:
        errors.append("AUTHORITY_U_TRUTH")

    single = docs["single_primitive"]
    if single.get("schema") != "PROJECT_BRAIN_ABOVE_EXPONENTIAL_U_SINGLE_PRIMITIVE_RECONCILIATION_V2":
        errors.append("SINGLE_SCHEMA")
    if (single.get("normal_form") or {}).get("only_live_primitive") != "ESCAPE_POLICY_ADEQUACY":
        errors.append("SINGLE_LIVE_PRIMITIVE")

    catchall = docs["catchall"]
    if catchall.get("schema") != "PROJECT_BRAIN_DB_ESCAPE_CATCHALL_TOTAL_ABSTRACTION_REDUCTION_V1":
        errors.append("CATCHALL_SCHEMA")
    if not str((catchall.get("critical_path_reduction") or {}).get("only_live_primitive", "")).startswith(
        "ESCAPE_POLICY_ADEQUACY"
    ):
        errors.append("CATCHALL_LIVE_PRIMITIVE")
    scheduler = " ".join(catchall.get("scheduler") or [])
    if "TEST_EXISTING_BRAIN_POLICIES" not in scheduler or "NO_NEW_GENERIC_SOLVER" not in scheduler:
        errors.append("CATCHALL_SCHEDULER")

    obstruction = docs["obstruction"]
    if obstruction.get("schema") != "PROJECT_BRAIN_OBSERVATIONAL_QUOTIENT_ESCAPE_PROGRESS_REDUCTION_V1":
        errors.append("OBSTRUCTION_SCHEMA")
    if "UNSPLITTABLE_POLICY_CONFLICT" not in str(
        (obstruction.get("scheduler_reduction") or {}).get("new_exact_obstruction_root", "")
    ):
        errors.append("OBSTRUCTION_ROOT")
    falsifier = str(obstruction.get("falsifier", ""))
    if (
        "TARGET_SUPPORTED_FULL_DISCRIMINATOR_EQUIVALENCE_CLASS" not in falsifier
        or "NO_COMMON_AUTHENTICATED_SAFE_ADEQUATE_BRAIN_POLICY" not in falsifier
    ):
        errors.append("OBSTRUCTION_FALSIFIER")

    frontier = docs["frontier"]
    if frontier.get("schema") != "PROJECT_BRAIN_CURRENT_PRIMITIVE_U_FRONTIER_V3":
        errors.append("FRONTIER_SCHEMA")
    if frontier.get("single_live_primitive") != live:
        errors.append("FRONTIER_LIVE_PRIMITIVE")
    ftruth = frontier.get("current_truth") or {}
    if ftruth.get("complete_declared_discriminator_quotient_scope_required_for_positive_cover") is not False:
        errors.append("FRONTIER_Q_COMPLETENESS")
    if ftruth.get("exact_true_world_set_completeness_required_for_positive_cover") is not False:
        errors.append("FRONTIER_WORLD_COMPLETENESS")
    if ftruth.get("positive_cover_over_current_sound_overapproximation_proved") is not False:
        errors.append("FRONTIER_CURRENT_CLOSURE")

    p3 = docs["p3_cegar"]
    if p3.get("schema") != "PROJECT_BRAIN_P3_ROBUST_POLICY_ADEQUACY_CEGAR_ACTIVATION_V1":
        errors.append("P3_CEGAR_SCHEMA")
    if not str(p3.get("status", "")).startswith("VERIFIED_BRAIN_OWNED_FINITE_ROBUST_POLICY_SELECTION"):
        errors.append("P3_CEGAR_STATUS")
    still = " ".join((p3.get("causal_effect") or {}).get("still_required_for_live_capacity_binding_no_weight_context", []))
    if "SCOPE_COMPLETE_AUTHENTICATED_POLICY_ADEQUACY_COVER" not in still:
        errors.append("P3_CEGAR_BOUNDARY")

    top = docs["acceptance_top"]
    if top.get("schema") != "PROJECT_BRAIN_UNIVERSAL_ACCEPTANCE_RELATION_TOP_REDUCTION_20261008_V1":
        errors.append("ACCEPTANCE_TOP_SCHEMA")
    ttruth = top.get("current_truth") or {}
    if ttruth.get("only_live_universal_premise") != "ESCAPE_PROGRESS_TOTALITY":
        errors.append("ACCEPTANCE_TOP_LIVE_PREMISE")
    if ttruth.get("escape_progress_totality_proved") is not False:
        errors.append("ACCEPTANCE_TOP_CURRENT_TRUTH")

    gcut = docs["gdpval_cut"]
    if gcut.get("schema") != "PROJECT_BRAIN_GDPVAL_EVALUATION_LAW_MINIMUM_INFORMATION_CUT_20261008_V1":
        errors.append("GDPVAL_CUT_SCHEMA")
    cut_text = str(gcut)
    if "PUBLIC" not in cut_text or "NONIDENTIFIABILITY" not in str(gcut.get("status", "")):
        errors.append("GDPVAL_CUT_SEMANTICS")

    gquot = docs["gdpval_quotient"]
    if gquot.get("schema") != "PROJECT_BRAIN_GDPVAL_EVALUATOR_FACING_QUOTIENT_U_ROUTE_20261008_V1":
        errors.append("GDPVAL_QUOTIENT_SCHEMA")
    reality = gquot.get("current_reality") or {}
    for key in (
        "complete_evaluator_facing_quotient_semantically_proved",
        "complete_opus55_220_quotient_laws_bound",
        "quotient_law_equality_proved",
        "gdpval_closed",
    ):
        if reality.get(key) is not False:
            errors.append("GDPVAL_QUOTIENT_OPEN:" + key)

    seed = docs["p3_seed"]
    if seed.get("schema") != "PROJECT_BRAIN_UNIVERSAL_REAL_DB_RESIDUAL_P3_SEED_VERIFICATION_V1":
        errors.append("P3_SEED_SCHEMA")
    if (seed.get("compiled_seed_result") or {}).get("semantic_status") != "SAT_ON_DECLARED_BOUNDED_MODEL":
        errors.append("P3_SEED_EXPECTED_COMPLEMENT")
    if (seed.get("compiled_seed_result") or {}).get("residual_model") != {"P3_STRICT_TOPLAW_REGION": False}:
        errors.append("P3_SEED_WITNESS")

    if errors:
        return _fail("SOURCE_THEOREM_SEMANTICS_MISMATCH", errors=sorted(errors))

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__UNIVERSAL_FRONTIER_REDUCED_TO_ONE_TARGET_SUPPORTED_UNSPLITTABLE_POLICY_CONFLICT_OBSTRUCTION",
        "source_bindings": bindings,
        "only_live_universal_obstruction": "TARGET_SUPPORTED_REACHABLE_UNSPLITTABLE_POLICY_CONFLICT_CLASS",
        "escape_policy_adequacy_is_live_primitive": True,
        "total_sound_abstraction_structurally_available": True,
        "acceptance_relation_top_initialization_sound": True,
        "serial_db_region_enumeration_required": False,
        "db_region_residual_role": "OPTIONAL_MONOTONE_ESCAPE_SHRINKING_EVIDENCE_ONLY",
        "p3_seed_role": "ONE_VERIFIED_SUBREGION_REMOVAL__NOT_A_SERIAL_GLOBAL_COVER_PLAN",
        "common_policy_first": True,
        "minimum_truthful_policy_changing_discriminator_second": True,
        "complete_discriminator_library_required_for_positive_cover": False,
        "exact_true_world_enumeration_required_for_positive_cover": False,
        "residual_unsat_compiler_role": (
            "PROOF_UTILITY_AFTER_A_SCOPE_COMPLETE_SYMBOLIC_COVER_OR_FOR_LOCALIZED_BOUNDED_RESIDUALS__"
            "NOT_THE_PRIMARY_SCHEDULER"
        ),
        "current_constructive_witness_family": "GDPVAL_HIDDEN_EVALUATOR_RELATION",
        "gdpval_public_information_identifies_target_relation": False,
        "gdpval_complete_evaluator_facing_quotient_proved": False,
        "gdpval_exact_opus55_quotient_law_bound": False,
        "load_bearing_moves_if_conflict_class_survives": [
            "PROVE_ONE_COMMON_AUTHENTICATED_SAFE_ADEQUATE_BRAIN_POLICY_OVER_THE_CLASS",
            "PROVE_ACTUAL_TARGET_SUPPORT_EXCLUDES_THE_CLASS",
            "IF_THE_CLASS_IS_NOT_ACTUALLY_UNSPLITTABLE__BIND_ONLY_ONE_TRUTHFUL_POLICY_CHANGING_DISCRIMINATOR_AND_RECURSE",
        ],
        "forbidden_primary_work": [
            "SERIALIZE_ALL_KNOWN_DB_REGIONS",
            "GENERAL_WORLD_MODEL_RECONSTRUCTION",
            "GENERAL_ACCEPTANCE_REGIME_TAXONOMY_COMPLETENESS",
            "MORE_POINT_BENCHMARKS_WITHOUT_SCOPE_LIFT",
            "NEW_GENERIC_SOLVER_AS_PROGRESS_PROXY",
        ],
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "REDUCTION_ONLY__THE_REACHABLE_TARGET_SUPPORTED_OBSTRUCTION_UNION_IS_NOT_PROVED_EMPTY"
        ),
    }
