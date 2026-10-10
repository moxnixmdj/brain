from __future__ import annotations

from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TASK_ACCEPTANCE_QUOTIENT_INVENTORY_V1"

TOP_SUPPORT_ZERO_IDS={
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
}
MATCHED_SCOPE_TARGET_BOUND_IDS={
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
}
MATCHED_SCOPE_STRUCTURAL_IDS={
    "VISION_DENSE_NONCHART_SCOPE",
}

class InventoryError(ValueError):
    pass

def classify(predicate: Mapping[str,Any]) -> dict[str,Any]:
    pid=str(predicate.get("id") or "")
    kind=str(predicate.get("kind") or "")
    acceptance=str(predicate.get("acceptance") or "")
    family=str(predicate.get("family") or "")
    if not pid or not kind or not acceptance or not family:
        raise InventoryError("PREDICATE_FIELDS_INCOMPLETE")

    if kind=="PUBLIC_FIXED_BAR":
        return {
            "predicate_id":pid,
            "family":family,
            "kind":kind,
            "quotient_class":"OTHER",
            "route":"EXPLICIT_THRESHOLD_RESULT_OR_STRONGER_PROOF",
            "opus_case_level_result_required":False,
            "brain_result_or_stronger_proof_required":True,
            "target_specific_information":"FROZEN_THRESHOLD_HARNESS_AND_UNIT",
            "reason":"THE_ACCEPTANCE_ORDER_IS_EXPLICIT_BUT_THE_BRAIN_SCORE_IS_NOT_YET_PROVED_AT_OR_ABOVE_THE_BAR",
        }

    if kind=="MATCHED_NONINFERIORITY":
        return {
            "predicate_id":pid,
            "family":family,
            "kind":kind,
            "quotient_class":"H_SEPARATING",
            "route":"MATCHED_TARGET_RESULT_OR_DISTRIBUTION_EQUIVALENCE_OR_STRONGER_CLASS_COMPLETE_PROOF",
            "opus_case_level_result_required":True,
            "brain_result_or_stronger_proof_required":True,
            "target_specific_information":"MATCHED_TARGET_BEHAVIOR_OR_STRONGER_DOMINANCE_CERTIFICATE",
            "reason":"DISTINCT_TARGET_AND_BRAIN_TRAJECTORY_DISTRIBUTIONS_CAN_REVERSE_A_HIDDEN_OR_MATCHED_ACCEPTANCE_ORDER",
        }

    if kind=="MATCHED_SCOPE_AUDIT" and pid in TOP_SUPPORT_ZERO_IDS:
        return {
            "predicate_id":pid,
            "family":family,
            "kind":kind,
            "quotient_class":"M_RESTRICTED",
            "route":"UNIVERSAL_ZERO_VIOLATION_TOP_SUPPORT_VIA_COMPLETE_MEDIATION",
            "opus_case_level_result_required":False,
            "brain_result_or_stronger_proof_required":True,
            "target_specific_information":"NONE_IF_SCOPE_COMPLETE_ZERO_TOP_SUPPORT_RECEIPT_PASSES",
            "reason":"ZERO_CRITICAL_VIOLATIONS_IS_A_TARGET_FREE_TOP_CLASS_IF_COMPLETE_MEDIATION_AND_GUARD_SOUNDNESS_ARE_SCOPE_COMPLETELY_PROVED",
        }

    if kind=="MATCHED_SCOPE_AUDIT" and pid in MATCHED_SCOPE_TARGET_BOUND_IDS:
        return {
            "predicate_id":pid,
            "family":family,
            "kind":kind,
            "quotient_class":"H_SEPARATING",
            "route":"MATCHED_SCOPE_RESULT_OR_STRONGER_MULTI_DIMENSION_TOP_SUPPORT_PROOF",
            "opus_case_level_result_required":True,
            "brain_result_or_stronger_proof_required":True,
            "target_specific_information":"MATCHED_SCOPE_SAFETY_BASELINE_UNLESS_STRONGER_TOP_SUPPORT_PROOF_EXISTS",
            "reason":"NO_MATERIAL_REGRESSION_IS_RELATIVE_AND_INCLUDES_FAILURE_DIMENSIONS_NOT_CURRENTLY_PROVED_AT_A_UNIVERSAL_TOP_CLASS",
        }

    if kind=="MATCHED_SCOPE_AUDIT" and pid in MATCHED_SCOPE_STRUCTURAL_IDS:
        return {
            "predicate_id":pid,
            "family":family,
            "kind":kind,
            "quotient_class":"OTHER",
            "route":"SCOPE_COMPLETE_DIRECT_PROOF_OR_MATCHED_AUDIT",
            "opus_case_level_result_required":False,
            "brain_result_or_stronger_proof_required":True,
            "target_specific_information":"SCOPE_BOUNDARY_OR_MATCHED_DIRECT_EVIDENCE",
            "reason":"THE_OPEN_OBLIGATION_IS_SCOPE_COVERAGE_NOT_A_SINGLE_TOTAL_ORDERED_UTILITY",
        }

    if kind=="DIRECT_SCOPE_AUDIT":
        return {
            "predicate_id":pid,
            "family":family,
            "kind":kind,
            "quotient_class":"OTHER",
            "route":"EXHAUSTIVE_OR_UNIVERSAL_SCOPE_PROOF",
            "opus_case_level_result_required":False,
            "brain_result_or_stronger_proof_required":True,
            "target_specific_information":"NONE_IF_EXHAUSTIVE_SCOPE_PROOF_PASSES",
            "reason":"DIRECT_SCOPE_COMPLETENESS_CAN_BE_PROVED_WITHOUT_TARGET_OUTCOMES",
        }

    if kind=="DEPENDENCY_PROOF":
        return {
            "predicate_id":pid,
            "family":family,
            "kind":kind,
            "quotient_class":"OTHER",
            "route":"DETERMINISTIC_DEPENDENCY_CLOSURE",
            "opus_case_level_result_required":False,
            "brain_result_or_stronger_proof_required":True,
            "target_specific_information":"NONE_BEYOND_FROZEN_DEPENDENCY_MANIFEST",
            "reason":"THE_OBLIGATION_CLOSES_WHEN_ALL_FROZEN_COMPONENT_DEPENDENCIES_HAVE_SCOPED_PROOFS",
        }

    raise InventoryError("UNCLASSIFIED_OPEN_PREDICATE:"+pid+":"+kind)

def compile_inventory(predicates:list[Mapping[str,Any]], proved_ids:set[str]) -> dict[str,Any]:
    open_rows=[classify(p) for p in predicates if str(p.get("id") or "") not in proved_ids]
    if len(open_rows)!=24:
        raise InventoryError("OPEN_PREDICATE_COUNT_DRIFT:"+str(len(open_rows)))
    ids=[x["predicate_id"] for x in open_rows]
    if len(set(ids))!=len(ids):
        raise InventoryError("DUPLICATE_OPEN_PREDICATE")
    counts={}
    for row in open_rows:
        counts[row["quotient_class"]]=counts.get(row["quotient_class"],0)+1
    matched=[x["predicate_id"] for x in open_rows if x["opus_case_level_result_required"]]
    target_free=[x["predicate_id"] for x in open_rows if not x["opus_case_level_result_required"]]
    return {
        "schema":SCHEMA,
        "status":"PASS__24_OPEN_ATOMS_PARTITIONED_BY_WEAKEST_SOUND_ACCEPTANCE_INFORMATION_ROUTE__ZERO_CREDIT",
        "open_predicate_count":24,
        "quotient_class_counts":dict(sorted(counts.items())),
        "opus_case_level_result_required_count":len(matched),
        "opus_case_level_result_required":matched,
        "opus_case_level_result_not_required_count":len(target_free),
        "opus_case_level_result_not_required":target_free,
        "rows":open_rows,
        "hard_rule":"CLASSIFICATION_CHANGES_SCHEDULING_ONLY__NO_ACCEPTANCE_CREDIT_WITHOUT_THE_ROUTE_SPECIFIC_RECEIPT",
        "acceptance_credit_delta":0,
    }
