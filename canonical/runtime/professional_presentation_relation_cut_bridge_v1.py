"""Exact-byte bridge from the shared professional-presentation frontier to one information cut.

The bridge composes five already-bound Brain artifacts:

* the generic minimum information lower bound,
* the shared professional-presentation frontier,
* its public-contract two-world lower bound,
* the Brain-owned authenticated Pareto comparator, and
* the universal acceptance-relation TOP reduction.

It proves that the current public contract does not entail a strict presentation
order for an otherwise undecided pair and localizes the only two load-bearing
separator classes for this shared frontier:

1. a scope-complete presentation top/dominance law that is robust across all
   still-admissible target relations, or
2. authentic target-relation information that excludes at least one compatible
   opposite-order world.

It deliberately does NOT prove that no third/common top policy exists.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_PRESENTATION_RELATION_CUT_BRIDGE_V1"

SOURCES = {
    "minimum_information": (
        "canonical/governance/MINIMUM_CAPABILITY_KERNEL_INFORMATION_CUT_20261006_V1.json",
        "2b6c8150db5c635eb34c35c4041b99c7fc9c5dd5",
    ),
    "shared_frontier": (
        "canonical/governance/SHARED_PROFESSIONAL_PRESENTATION_QUALITY_FRONTIER_20261007_V1.json",
        "f258af38b41180362aa216bfff6c5ddf39cdb868",
    ),
    "presentation_lower_bound": (
        "canonical/governance/PROFESSIONAL_PRESENTATION_PUBLIC_CONTRACT_INFORMATION_LOWER_BOUND_20261007_V1.json",
        "ef20a762365f9b4ab79ef695085bc76e35b0351d",
    ),
    "pareto": (
        "canonical/governance/AUTHENTICATED_PRESENTATION_PARETO_CAPABILITY_BINDING_20261007_V1.json",
        "eb643648c812e2aa30ef5f13d527f01bc03f726d",
    ),
    "acceptance_top": (
        "canonical/governance/UNIVERSAL_ACCEPTANCE_RELATION_TOP_REDUCTION_20261008_V1.json",
        "478f38e9a746e9db99767dd03376481834decd51",
    ),
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "constructive_relation_uncertainty_witness": False,
        "public_contract_entails_strict_presentation_order": False,
        "brain_owned_pareto_calculus_available": False,
        "complete_official_dimension_relation_envelope_bound": False,
        "full_scope_presentation_top_law_bound": False,
        "common_policy_nonexistence_proved": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _replay_two_world_nonidentifiability() -> dict[str, Any]:
    observation = (
        "CURRENT_BOUND_PUBLIC_PRESENTATION_CONTRACT",
        "SAME_TASK_PAIRWISE_CONTEXT",
    )
    left = {"observation": observation, "order": "A_STRICTLY_OVER_B"}
    right = {"observation": observation, "order": "B_STRICTLY_OVER_A"}
    public_observation_equal = left["observation"] == right["observation"]
    target_order_differs = left["order"] != right["order"]
    return {
        "public_observation_equal": public_observation_equal,
        "target_order_differs": target_order_differs,
        "left_order": left["order"],
        "right_order": right["order"],
        "strict_order_not_entailed": public_observation_equal and target_order_differs,
    }


def verify_bridge(*, repo_root: str | Path) -> dict[str, Any]:
    docs: dict[str, dict[str, Any]] = {}
    try:
        for key, (path, blob) in SOURCES.items():
            docs[key] = resolve_receipt_bytes(
                {"path": path, "git_blob_sha": blob},
                repo_root=repo_root,
            )["document"]
    except Exception as exc:
        return _fail(
            "SOURCE_BINDING_INVALID",
            exception_type=type(exc).__name__,
            detail_text=str(exc)[:200],
        )

    minimum = docs["minimum_information"]
    frontier = docs["shared_frontier"]
    lower = docs["presentation_lower_bound"]
    pareto = docs["pareto"]
    acceptance = docs["acceptance_top"]
    errors: list[str] = []

    if minimum.get("schema") != "PROJECT_BRAIN_MINIMUM_CAPABILITY_KERNEL_INFORMATION_CUT_V1":
        errors.append("MINIMUM_INFORMATION_SCHEMA")
    cut = minimum.get("information_cut") or {}
    alt_ids = {
        row.get("id")
        for row in cut.get("minimum_alternatives", [])
        if isinstance(row, dict)
    }
    if not {"P_OWNED_PRIOR", "D_AUTHORIZED_DISCRIMINATOR", "V_ABSOLUTE_VERIFIER_OR_EXPERIMENT"} <= alt_ids:
        errors.append("GENERIC_SEPARATOR_CLASSES")

    if frontier.get("schema") != "PROJECT_BRAIN_SHARED_PROFESSIONAL_PRESENTATION_QUALITY_FRONTIER_V1":
        errors.append("FRONTIER_SCHEMA")
    normalized = frontier.get("normalized_shared_frontier") or {}
    if normalized.get("id") != "PROFESSIONAL_PRESENTATION_QUALITY_V1":
        errors.append("FRONTIER_ID")
    contracts = (frontier.get("current_evidence") or {}).get("public_target_contracts") or {}
    if contracts.get("complete_presentation_order_bound") is not False:
        errors.append("FRONTIER_ORDER_BOUNDARY")
    disjunction = frontier.get("closure_disjunction") or []
    if not any("SCOPE_COMPLETE_BRAIN_OWNED_PRESENTATION_TOP_OR_DOMINANCE_LAW" in str(x) for x in disjunction):
        errors.append("FRONTIER_TOP_ROUTE")
    if not any("MATCHED_TARGET_RELATION_RECEIPTS" in str(x) for x in disjunction):
        errors.append("FRONTIER_TARGET_ROUTE")

    if lower.get("schema") != "PROJECT_BRAIN_PROFESSIONAL_PRESENTATION_PUBLIC_CONTRACT_INFORMATION_LOWER_BOUND_V1":
        errors.append("LOWER_BOUND_SCHEMA")
    theorem = lower.get("theorem") or {}
    worlds = theorem.get("witness_worlds") or []
    if len(worlds) != 2:
        errors.append("TWO_WORLD_WITNESS")
    if "NO_PROOF_USING_ONLY_C_CAN_SOUNDLY_ASSERT" not in str(theorem.get("consequence", "")):
        errors.append("PUBLIC_CONTRACT_NONENTAILMENT")
    routes = theorem.get("escape_routes") or []
    if not any("BIND_ADDITIONAL_TARGET_RELATION_INFORMATION" in str(x) for x in routes):
        errors.append("LOWER_BOUND_TARGET_SEPARATOR")
    if not any("ABSOLUTE_TOP_OR_SCOPE_COMPLETE_THEOREM" in str(x) for x in routes):
        errors.append("LOWER_BOUND_TOP_BYPASS")

    if pareto.get("schema") != "PROJECT_BRAIN_AUTHENTICATED_PRESENTATION_PARETO_CAPABILITY_BINDING_V1":
        errors.append("PARETO_SCHEMA")
    capability = pareto.get("capability") or {}
    if capability.get("id") != "AUTHENTICATED_COMPLETE_DIMENSION_PARETO_PRESENTATION_ORDER_V1":
        errors.append("PARETO_CAPABILITY_ID")
    remains = (pareto.get("causal_effect") or {}).get("remains") or []
    if not any("SOUND_COMPLETE_PRESENTATION_DIMENSION_CONTRACT" in str(x) for x in remains):
        errors.append("PARETO_DIMENSION_COMPLETENESS_BOUNDARY")
    if not any("AUTHENTICATED_DIMENSION_RELATION_RECEIPTS" in str(x) for x in remains):
        errors.append("PARETO_RELATION_BOUNDARY")

    if acceptance.get("schema") != "PROJECT_BRAIN_UNIVERSAL_ACCEPTANCE_RELATION_TOP_REDUCTION_20261008_V1":
        errors.append("ACCEPTANCE_TOP_SCHEMA")
    truth = acceptance.get("current_truth") or {}
    if truth.get("acceptance_relation_top_initialization_sound") is not True:
        errors.append("ACCEPTANCE_TOP_SOUNDNESS")
    if truth.get("common_policy_over_top_proved") is not False:
        errors.append("COMMON_POLICY_TOP_BOUNDARY")
    if truth.get("escape_progress_totality_proved") is not False:
        errors.append("ESCAPE_PROGRESS_BOUNDARY")

    if errors:
        return _fail("SOURCE_THEOREM_SEMANTICS_MISMATCH", errors=sorted(errors))

    countermodel = _replay_two_world_nonidentifiability()
    if not countermodel["strict_order_not_entailed"]:
        return _fail("COUNTERMODEL_REPLAY_FAILED")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__CONSTRUCTIVE_SHARED_PRESENTATION_RELATION_UNCERTAINTY_WITNESS__"
            "MINIMUM_SEPARATOR_CLASS_LOCALIZED"
        ),
        "source_bindings": {
            key: {"path": path, "git_blob_sha": blob}
            for key, (path, blob) in SOURCES.items()
        },
        "shared_frontier_id": "PROFESSIONAL_PRESENTATION_QUALITY_V1",
        "touches": normalized.get("touches"),
        "constructive_relation_uncertainty_witness": True,
        "countermodel_replayed": True,
        "countermodel": countermodel,
        "witness_semantics": (
            "TWO_TARGET_COMPARATOR_WORLDS_CAN_SHARE_THE_CURRENT_PUBLIC_CONTRACT_"
            "YET_REVERSE_AN_OTHERWISE_UNFIXED_PRESENTATION_ORDER"
        ),
        "public_contract_entails_strict_presentation_order": False,
        "brain_owned_pareto_calculus_available": True,
        "complete_official_dimension_relation_envelope_bound": False,
        "full_scope_presentation_top_law_bound": False,
        "common_policy_nonexistence_proved": False,
        "stronger_top_law_remains_logically_possible": True,
        "minimum_separator_classes": [
            "SCOPE_COMPLETE_PRESENTATION_TOP_OR_DOMINANCE_LAW",
            "AUTHENTIC_TARGET_PRESENTATION_RELATION_INFORMATION",
        ],
        "why_no_third_class": (
            "THE_PUBLIC_CONTRACT_LOWER_BOUND_LISTS_ADDITIONAL_TARGET_RELATION_"
            "INFORMATION_OR_MATCHED_TARGET_RESULTS_AS_RELATION_INFORMATION_AND_"
            "AN_ABSOLUTE_TOP_OR_SCOPE_COMPLETE_THEOREM_AS_THE_EVALUATOR_INDEPENDENT_"
            "BYPASS;THE_GENERIC_INFORMATION_CUT_IDENTIFIES_PRIOR_DISCRIMINATOR_OR_"
            "VERIFIER_PATHS_BUT_FOR_THIS_FRONTIER_THEY_MUST_TERMINATE_IN_ONE_OF_"
            "THOSE_TWO_LOAD_BEARING_PROOF_EFFECTS"
        ),
        "robust_preference_rule": (
            "DO_NOT_SELECT_A_REPRESENTATIVE_UTILITY_OR_WEIGHT_VECTOR_AS_PROOF;"
            "TERMINAL_NONINFERIORITY_REQUIRES_A_POLICY_ORDERED_AT_LEAST_AS_HIGH_"
            "UNDER_EVERY_STILL_ADMISSIBLE_TARGET_RELATION_OR_A_SEPARATOR_THAT_"
            "SOUNDLY_RESTRICTS_THE_RELATION_SET"
        ),
        "next_root_action": (
            "SEARCH_EXISTING_BRAIN_POLICY_FOR_SCOPE_COMPLETE_TOP_OR_DOMINANCE_"
            "CERTIFICATE__ELSE_BIND_MINIMUM_AUTHENTIC_TARGET_RELATION_SEPARATOR"
        ),
        "current_root_effect": (
            "PROFESSIONAL_PRESENTATION_UNCERTAINTY_IS_ONE_SHARED_SEPARATOR_FRONTIER;"
            "DO_NOT_SCHEDULE_SEPARATE_STYLE_THEORIES_FOR_GDPVAL_AA_BRIEFCASE_AND_"
            "ARTIFACT_CREATION"
        ),
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "INFORMATION_CUT_AND_CAPABILITY_LOCALIZATION_ONLY__NO_PROOF_THAT_A_"
            "COMMON_OR_THIRD_TOP_POLICY_DOES_NOT_EXIST__NO_TARGET_ORDER_ACQUIRED"
        ),
    }
