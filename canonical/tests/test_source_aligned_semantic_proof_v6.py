import json

from canonical.runtime.source_aligned_semantic_proof_v6 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v6 import resolve_from_source_proof


POLICY = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)


def facts(value="130.00"):
    return json.dumps({
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {
            "exposure_amount": {"type": "DECIMAL_STRING", "value": value},
        },
    }, separators=(",", ":"))


def test_raw_fact_source_entails_exception_policy_without_certifying_adequacy():
    claim = {
        "claim_id": "raw",
        "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
        "condition_holds": True,
    }
    checked = verify_proof(
        POLICY, source_id="policy", claims=[claim],
        fact_source=facts("130.00"), fact_source_id="case-facts",
    )
    assert checked["status"] == "PROOF_CHECKED", checked
    atom_id = checked["accepted_claims"][0]["condition_atom_id"]
    out = resolve_from_source_proof(
        POLICY, source_id="policy", claims=[claim],
        fact_source=facts("130.00"), fact_source_id="case-facts",
        decision_basis=[atom_id],
        policy_conditions={
            "exception_policy": {"op": "ATOM", "id": atom_id},
            "ordinary_policy": {"op": "NOT", "arg": {"op": "ATOM", "id": atom_id}},
        },
    )
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["exception_policy"]
    assert out["certified_common_policies"] == []


def test_raw_fact_source_below_threshold_entails_ordinary_policy_without_certifying_adequacy():
    claim = {
        "claim_id": "raw",
        "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
        "condition_holds": False,
    }
    checked = verify_proof(
        POLICY, source_id="policy", claims=[claim],
        fact_source=facts("100.00"), fact_source_id="case-facts",
    )
    atom_id = checked["accepted_claims"][0]["condition_atom_id"]
    out = resolve_from_source_proof(
        POLICY, source_id="policy", claims=[claim],
        fact_source=facts("100.00"), fact_source_id="case-facts",
        decision_basis=[atom_id],
        policy_conditions={
            "exception_policy": {"op": "ATOM", "id": atom_id},
            "ordinary_policy": {"op": "NOT", "arg": {"op": "ATOM", "id": atom_id}},
        },
    )
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["ordinary_policy"]
    assert out["certified_common_policies"] == []


def test_duplicate_key_fact_source_cannot_mint_semantic_constraint():
    bad = '{"schema_id":"X","fields":{"exposure_amount":{"type":"DECIMAL_STRING","value":"130"},"exposure_amount":{"type":"DECIMAL_STRING","value":"0"}}}'
    out = verify_proof(
        POLICY, source_id="policy",
        claims=[{
            "claim_id": "raw",
            "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
            "condition_holds": True,
        }],
        fact_source=bad, fact_source_id="case-facts",
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []


def test_wrong_claimed_result_is_rejected():
    out = verify_proof(
        POLICY, source_id="policy",
        claims=[{
            "claim_id": "raw",
            "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
            "condition_holds": False,
        }],
        fact_source=facts("130.00"), fact_source_id="case-facts",
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []
