"""Exact-byte theorem composition deleting O/Q classification from the universal proof path.

This bridge proves only a reduction of prerequisites:

* initialize the load-bearing acceptance relation uncertainty at TOP, which
  soundly contains the actual relation by construction;
* treat objective/qualitative acceptance as special cases of one relation
  uncertainty object, not as an exhaustive taxonomy that must be proved first;
* refine only by one-sided proof-carrying constraints, preserving the actual
  relation;
* retain ESCAPE_PROGRESS_TOTALITY as the sole live universal premise.

It grants no D_B, U-empty, ABC, finality, or terminal credit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_ACCEPTANCE_RELATION_TOP_REDUCTION_V1"

SOURCES = {
    "acceptance": (
        "canonical/governance/ACCEPTANCE_RELATION_UNCERTAINTY_NORMAL_FORM_20261007_V1.json",
        "42498bbe40327cd47be5e4251e7f524a8c0c8d5b",
    ),
    "top": (
        "canonical/governance/TOP_SEMANTIC_OVERAPPROXIMATION_SOUNDNESS_TRUTH_REPAIR_20261007_V1.json",
        "2e37860a0fb9d8212aa854c0d8c8749919c76204",
    ),
    "monotone": (
        "canonical/governance/MONOTONE_PROOF_CARRYING_SEMANTIC_REFINEMENT_THEOREM_20261007_V1.json",
        "8a3690d95997b2fdf3776ec59ba067005cb44fce",
    ),
    "adaptive": (
        "canonical/governance/ADAPTIVE_ABSTRACT_POSITIVE_COVER_FIXED_POINT_THEOREM_20261007_V2.json",
        "2ac97a6677cf577a52c3fd6d01739ee29be1e9d8",
    ),
    "root": (
        "canonical/governance/TERMINAL_EXECUTION_ROOT_20261007_V1.json",
        "e70f662d27e0b917eaf6ef8ba9da3bebc5ab7ee0",
    ),
    "frontier": (
        "canonical/governance/CURRENT_PRIMITIVE_U_FRONTIER_20261007_V1.json",
        "8340829830dc81095abd4d643a8be6894a39f2f3",
    ),
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "acceptance_relation_top_sound": False,
        "oq_scope_complete_classification_required": True,
        "monotone_truth_preservation_bound": False,
        "common_policy_over_top_proved": False,
        "escape_progress_totality_proved": False,
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

    a = docs["acceptance"]
    top = docs["top"]
    mono = docs["monotone"]
    adaptive = docs["adaptive"]
    root = docs["root"]
    frontier = docs["frontier"]

    errors: list[str] = []

    if a.get("schema") != "PROJECT_BRAIN_ACCEPTANCE_RELATION_UNCERTAINTY_NORMAL_FORM_V1":
        errors.append("ACCEPTANCE_SCHEMA")
    if not str(a.get("status", "")).startswith("PROVED_LOGICAL_REDUCTION"):
        errors.append("ACCEPTANCE_STATUS")
    defs = a.get("definitions") or {}
    if "R_STAR" not in defs or "R_OVER" not in defs or "Adeq_c_p_R" not in defs:
        errors.append("ACCEPTANCE_DEFINITIONS")
    if "O_AND_Q_ARE_NOT_DISTINCT_TERMINAL_PROOF_PRIMITIVES" not in str(a.get("consequence", "")):
        errors.append("OQ_COLLAPSE")
    if "BIND_A_SOUND_R_OVER" not in str(a.get("single_U_primitive", "")):
        errors.append("RELATION_UNCERTAINTY_PRIMITIVE")

    if top.get("schema") != "PROJECT_BRAIN_TOP_SEMANTIC_OVERAPPROXIMATION_SOUNDNESS_TRUTH_REPAIR_V1":
        errors.append("TOP_SCHEMA")
    t = top.get("theorem") or {}
    if t.get("conclusion") != "W_TRUE_E_IS_A_SUBSET_OF_MODELS(PSI_TOP)":
        errors.append("TOP_SOUNDNESS")
    if "UNKNOWN__NOT_POLICY_FAILURE" not in str(t.get("fail_closed", "")):
        errors.append("TOP_FAIL_CLOSED")

    if mono.get("schema") != "PROJECT_BRAIN_MONOTONE_PROOF_CARRYING_SEMANTIC_REFINEMENT_THEOREM_V1":
        errors.append("MONOTONE_SCHEMA")
    mt = mono.get("theorem_candidate") or {}
    if not str(mt.get("sound_overapproximation_invariant", "")).startswith("FOR_ALL_i__Omega_E_IS_A_SUBSET"):
        errors.append("MONOTONE_INVARIANT")
    if "UNSOUNDLY_ADMITTED_CONSTRAINT" not in str(mt.get("false_assertion_consequence", "")):
        errors.append("UNSOUND_REFINEMENT_HAZARD")

    if adaptive.get("schema") != "PROJECT_BRAIN_ADAPTIVE_ABSTRACT_POSITIVE_COVER_FIXED_POINT_THEOREM_V2":
        errors.append("ADAPTIVE_SCHEMA")
    if not str(adaptive.get("only_live_universal_premise", "")).startswith("ESCAPE_PROGRESS_TOTALITY"):
        errors.append("ADAPTIVE_LIVE_PREMISE")

    if root.get("schema") != "PROJECT_BRAIN_TERMINAL_EXECUTION_ROOT_V1":
        errors.append("ROOT_SCHEMA")
    if root.get("current_truth", {}).get("single_live_pre_abc_research_primitive") != "ESCAPE_POLICY_ADEQUACY":
        errors.append("ROOT_LIVE_PRIMITIVE")

    if frontier.get("schema") != "PROJECT_BRAIN_CURRENT_PRIMITIVE_U_FRONTIER_V3":
        errors.append("FRONTIER_SCHEMA")
    if frontier.get("single_live_primitive") != (
        "SCOPE_COMPLETE_OBSERVATIONAL_QUOTIENT_WITH_NO_TARGET_SUPPORTED_"
        "UNSPLITTABLE_POLICY_CONFLICT_CLASS"
    ):
        errors.append("FRONTIER_SINGLE_PRIMITIVE")

    if errors:
        return _fail("SOURCE_THEOREM_SEMANTICS_MISMATCH", errors=sorted(errors))

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__OQ_CLASSIFICATION_DEMOTED__ACCEPTANCE_RELATION_TOP_INITIALIZATION_SOUND",
        "source_bindings": {
            key: {"path": path, "git_blob_sha": blob}
            for key, (path, blob) in SOURCES.items()
        },
        "initial_relation_overapproximation": "TOP_ALL_ADMISSIBLE_LOAD_BEARING_ACCEPTANCE_RELATIONS",
        "acceptance_relation_top_sound": True,
        "actual_relation_preserved": True,
        "oq_scope_complete_classification_required": False,
        "oq_role": "OPTIONAL_PLANNING_SPECIAL_CASES_ONLY",
        "monotone_truth_preservation_bound": True,
        "refinement_rule": (
            "ADD_ONLY_SOUND_PROOF_CARRYING_POLICY_CHANGING_CONSTRAINTS_AND_PRESERVE_R_STAR"
        ),
        "common_policy_over_top_proved": False,
        "escape_progress_totality_proved": False,
        "only_live_universal_premise": "ESCAPE_PROGRESS_TOTALITY",
        "next_decision": (
            "TRY_ONE_AUTHENTICATED_BRAIN_OWNED_POLICY_ADEQUATE_OVER_TOP_OR_CURRENT_"
            "SOUND_R_OVER__ELSE_BIND_ONLY_ONE_TRUTHFUL_POLICY_CHANGING_REFINEMENT"
        ),
        "global_scope_effect": (
            "ACCEPTANCE_REGIME_TAXONOMY_COMPLETENESS_IS_NOT_A_LOAD_BEARING_PRECONDITION;"
            "EVERY_CONTEXT_STARTS_SOUNDLY_AT_RELATION_TOP"
        ),
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "PREREQUISITE_REDUCTION_ONLY__NO_COMMON_POLICY_OR_PROGRESS_TOTALITY_PROOF"
        ),
    }
