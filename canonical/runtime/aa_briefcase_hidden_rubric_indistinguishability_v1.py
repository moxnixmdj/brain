from __future__ import annotations

from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_HIDDEN_RUBRIC_INDISTINGUISHABILITY_V1"
PUBLIC_SUPERDOMAIN_BLOB = "cf612adf37da0cf5d7d1940b4656fd72e483481e"
PUBLIC_CONTRACT_BLOB = "32b44233529221ac6aa21132782690a1fbf0f748"


class HiddenRubricCutError(ValueError):
    pass


def prove_two_rubric_cut(
    *,
    public_contract: Mapping[str, Any],
    policy_support: Iterable[str],
    output_a: str,
    output_b: str,
) -> dict[str, Any]:
    if public_contract.get("public_contract_blob") != PUBLIC_CONTRACT_BLOB:
        raise HiddenRubricCutError("PUBLIC_CONTRACT_BLOB_MISMATCH")
    if public_contract.get("public_superdomain_blob") != PUBLIC_SUPERDOMAIN_BLOB:
        raise HiddenRubricCutError("PUBLIC_SUPERDOMAIN_BLOB_MISMATCH")
    if public_contract.get("private_rubric_semantics_known") is not False:
        raise HiddenRubricCutError("PRIVATE_RUBRIC_SEMANTICS_BOUNDARY_MISMATCH")
    if public_contract.get("arbitrary_finite_hidden_binary_predicates_included") is not True:
        raise HiddenRubricCutError("OPAQUE_RUBRIC_SUPERDOMAIN_NOT_BOUND")
    if public_contract.get("all_finite_submission_bytes_included") is not True:
        raise HiddenRubricCutError("SUBMISSION_SUPERDOMAIN_NOT_BOUND")
    if output_a == output_b:
        raise HiddenRubricCutError("DISTINCT_OUTPUTS_REQUIRED")

    support = frozenset(str(x) for x in policy_support)
    if not support:
        raise HiddenRubricCutError("POLICY_SUPPORT_MUST_BE_NONEMPTY")

    # Construct two rubric worlds allowed by the public opaque-predicate superdomain.
    # R_A passes exactly output_a. R_B passes exactly output_b.
    top_a = frozenset({output_a})
    top_b = frozenset({output_b})

    top_in_a = support <= top_a
    top_in_b = support <= top_b
    common_top_support = top_in_a and top_in_b

    # Because output_a != output_b, top_a ∩ top_b = ∅. A nonempty policy
    # support cannot be confined to both top sets when the hidden rubric is
    # unavailable to the policy and the visible task input is identical.
    if common_top_support:
        raise HiddenRubricCutError("INTERNAL_LOGIC_ERROR_COMMON_TOP_SUPPORT")

    return {
        "schema": SCHEMA,
        "status": "PASS__TWO_RUBRIC_INDISTINGUISHABILITY_COUNTERMODEL",
        "same_visible_task_input": True,
        "hidden_rubric_not_observed_by_policy": True,
        "rubric_world_a_top_support": sorted(top_a),
        "rubric_world_b_top_support": sorted(top_b),
        "policy_support": sorted(support),
        "policy_top_in_world_a": top_in_a,
        "policy_top_in_world_b": top_in_b,
        "policy_top_in_both_worlds": False,
        "raw_public_superdomain_global_top_support_possible": False,
        "consequence": (
            "NO_TARGET_INDEPENDENT_POLICY_CAN_BE_PROVED_GLOBAL_TOP_OVER_THE_RAW_"
            "AA_PUBLIC_SUPERDOMAIN_WHILE_ACTUAL_HIDDEN_RUBRIC_SEMANTICS_REMAIN_"
            "UNRESTRICTED_OPAQUE_PREDICATES"
        ),
        "does_not_disprove_actual_aa_noninferiority": True,
        "does_not_claim_actual_private_rubrics_are_adversarial": True,
        "terminal_authority": False,
    }
