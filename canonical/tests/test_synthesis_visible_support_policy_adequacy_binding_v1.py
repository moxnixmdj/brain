from canonical.runtime.proof_carrying_semantic_refinement_v3 import _authenticate_policy_adequacy

CONDITION = {"op": "ATOM", "id": "SYNTHESIS_TYPED_VISIBLE_SUPPORT_COMMON_POLICY_TOP_LAW_V1"}
BINDING = {
    "adequacy_certificate_path": "canonical/governance/SYNTHESIS_VISIBLE_SUPPORT_POLICY_ADEQUACY_CERTIFICATE_20261007_V1.json",
    "adequacy_certificate_blob_sha": "0e7fb524a83d97d85523c6c818af803608b72e81",
    "independent_verification_path": "canonical/verification/SYNTHESIS_VISIBLE_SUPPORT_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_20261007_V1.json",
    "independent_verification_blob_sha": "c8615927bd08bcc7daf79c419d3c5eb204a19bdd",
}

def test_real_synthesis_policy_adequacy_binding_authenticates():
    ok, row = _authenticate_policy_adequacy(
        "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1",
        CONDITION,
        BINDING,
    )
    assert ok is True, row
    assert row["policy_id"] == "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1"

def test_real_synthesis_policy_adequacy_binding_rejects_wrong_condition():
    ok, row = _authenticate_policy_adequacy(
        "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1",
        {"op": "TRUE"},
        BINDING,
    )
    assert ok is False
    assert "ADEQUACY_CONDITION_MISMATCH" in row["reason"]
