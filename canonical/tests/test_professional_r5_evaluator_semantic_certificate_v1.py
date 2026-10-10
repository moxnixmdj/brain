from copy import deepcopy
from canonical.runtime.professional_r5_evaluator_semantic_certificate_v1 import (
    CLAIM_KIND, ROOT_ID, SEMANTIC_ROLES, certify, digest,
)

GOV = {
    "schema": "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_V1",
    "status": "CANDIDATE_CONDITIONAL_THEOREM__ARITHMETIC_ONLY__ZERO_GDPVAL_AND_TERMINAL_CREDIT",
    "current_reality": {
        "sound_complete_gdpval_owner_decomposition_bound": False,
        "current_owner_pairwise_relation_bound": False,
        "complete_opus55_220_evaluator_facing_laws_bound": False,
        "gdpval_closed": False,
    },
    "soundness_firewall": {
        "admissible_decomposition_proof_classes": [
            "AUTHENTIC_CURRENT_OWNER_SEMANTICS",
            "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
            "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
            "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_BOUND",
        ],
        "forbidden_as_semantic_containment_proof": [
            "PUBLIC_METHODOLOGY_ONLY",
            "PUBLIC_RUBRIC_ONLY",
            "HISTORICAL_V1_PROMPT_CARRYFORWARD",
            "UNVERIFIED_RECONSTRUCTED_GRADER",
        ],
    },
}
VERIFY = {
    "schema": "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_V1",
    "status": "INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS__11_OF_11__SEMANTIC_DECOMPOSITION_UNVERIFIED__ZERO_CREDIT",
    "verified_mechanics": [
        "POSITIVE_ROBUST_MARGIN_CERTIFICATE_PASSES",
        "UNPROVED_DECOMPOSITION_FAILS_CLOSED",
        "PUBLIC_RUBRIC_ONLY_SEMANTIC_CLASS_IS_FIREWALLED",
        "NONINDEPENDENT_DECOMPOSITION_RECEIPT_FAILS_CLOSED",
        "NONZERO_MASS_DIFFERENCE_VECTOR_FAILS_CLOSED",
        "NEGATIVE_K_CONE_DIRECTION_FAILS_DUAL_MEMBERSHIP",
        "NONORTHOGONAL_LINEALITY_FAILS_EVEN_WITH_LARGE_NOMINAL_MARGIN",
        "BOUNDED_UNCERTAINTY_CAN_BE_ABSORBED_BY_SUFFICIENT_CERTIFIED_MARGIN",
        "EXCESS_BOUNDED_UNCERTAINTY_FAILS",
        "EMPTY_BOUNDED_SET_REDUCES_TO_ZERO_ADJUSTMENT",
        "DIMENSION_MISMATCH_FAILS_CLOSED",
    ],
    "verification_boundary": [
        "THIS_REPLAY_PROVES_RUNTIME_AND_TEST_MECHANICS_ONLY.",
        "IT_DOES_NOT_PROVE_THE_TRUE_CURRENT_GDPVAL_OWNER_EVALUATOR_IS_CONTAINED_IN_ANY_PROPOSED_u0_PLUS_CONE_K_PLUS_CONV_B_PLUS_SPAN_L_DECOMPOSITION.",
        "NO_GDPVAL_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT.",
    ],
}


def binding(g=GOV, v=VERIFY):
    return {
        "root_id": ROOT_ID,
        "claim_kind": CLAIM_KIND,
        "governance_digest": digest(g),
        "verification_digest": digest(v),
        "semantic_roles": dict(SEMANTIC_ROLES),
    }


def test_positive_bounded_semantics_pass():
    out = certify(GOV, VERIFY, binding())
    assert out["pass"] is True, out
    assert out["semantic_leaf_credit"] is False
    assert out["quality_authority"] is False
    assert "NO_PROOF_THE_TRUE_CURRENT_OWNER_EVALUATOR_IS_IN_ANY_PROPOSED_DECOMPOSITION" in out["claim_scope"]["limitations"]


def test_binding_drift_fails_closed():
    b = binding()
    b["governance_digest"] = "sha256:bad"
    out = certify(GOV, VERIFY, b)
    assert out["pass"] is False
    assert out["reason"] == "GOVERNANCE_BINDING_DRIFT"


def test_public_rubric_must_remain_forbidden_semantic_authority():
    g = deepcopy(GOV)
    g["soundness_firewall"]["forbidden_as_semantic_containment_proof"].remove("PUBLIC_RUBRIC_ONLY")
    out = certify(g, VERIFY, binding(g, VERIFY))
    assert out["pass"] is False
    assert out["reason"] == "FORBIDDEN_SEMANTIC_PROOF_CLASSES_INCOMPLETE"


def test_real_owner_nonclaim_is_load_bearing():
    v = deepcopy(VERIFY)
    v["verification_boundary"] = [
        x for x in v["verification_boundary"]
        if "DOES_NOT_PROVE_THE_TRUE_CURRENT_GDPVAL_OWNER_EVALUATOR" not in x
    ]
    out = certify(GOV, v, binding(GOV, v))
    assert out["pass"] is False
    assert out["reason"] == "REAL_OWNER_NONCLAIM_MISSING"


def test_global_boundary_state_cannot_be_silently_upgraded():
    g = deepcopy(GOV)
    g["current_reality"]["current_owner_pairwise_relation_bound"] = True
    out = certify(g, VERIFY, binding(g, VERIFY))
    assert out["pass"] is False
    assert out["reason"] == "BOUNDARY_STATE_NOT_EXACTLY_PRESERVED"


def test_missing_exact_rational_mechanic_fails_closed():
    v = deepcopy(VERIFY)
    v["verified_mechanics"].remove("DIMENSION_MISMATCH_FAILS_CLOSED")
    out = certify(GOV, v, binding(GOV, v))
    assert out["pass"] is False
    assert out["reason"] == "VERIFIED_MECHANICS_INCOMPLETE"
