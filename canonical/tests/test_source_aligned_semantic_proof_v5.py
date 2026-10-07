from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime.source_aligned_semantic_proof_v5 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v5 import resolve_from_source_proof


def context():
    c = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"exposure_amount": {"type": "DECIMAL_STRING", "value": "130.00"}},
    }
    return c, typed_context_sha256(c)


def test_explicit_defined_term_condition_can_select_policy():
    text = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Total exposure is at least 125.50."
    )
    c, digest = context()
    claim = {
        "claim_id": "defined",
        "kind": "CERTIFIED_DEFINED_TERM_TYPED_CONDITION",
        "condition_holds": True,
        "defined_term": "Total exposure",
        "field_name": "exposure_amount",
    }
    checked = verify_proof(
        text,
        source_id="s",
        claims=[claim],
        typed_context=c,
        expected_typed_context_sha256=digest,
    )
    assert checked["status"] == "PROOF_CHECKED", checked
    accepted = checked["accepted_claims"][0]
    atom_id = accepted["condition_atom_id"]
    out = resolve_from_source_proof(
        text,
        source_id="s",
        claims=[claim],
        typed_context=c,
        expected_typed_context_sha256=digest,
        decision_basis=[atom_id],
        policy_conditions={
            "exception_policy": {"op": "ATOM", "id": atom_id},
            "ordinary_policy": {"op": "NOT", "arg": {"op": "ATOM", "id": atom_id}},
        },
    )
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["exception_policy"]
    assert out["certified_common_policies"] == []


def test_caller_cannot_relabel_defined_term_or_field():
    text = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Total exposure is at least 125.50."
    )
    c, digest = context()
    out = verify_proof(
        text,
        source_id="s",
        claims=[{
            "claim_id": "defined",
            "kind": "CERTIFIED_DEFINED_TERM_TYPED_CONDITION",
            "condition_holds": True,
            "defined_term": "Aggregate exposure",
            "field_name": "other_amount",
        }],
        typed_context=c,
        expected_typed_context_sha256=digest,
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []


def test_paraphrase_without_explicit_definition_stays_unproved():
    text = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Aggregate exposure is at least 125.50."
    )
    c, digest = context()
    out = verify_proof(
        text,
        source_id="s",
        claims=[{
            "claim_id": "defined",
            "kind": "CERTIFIED_DEFINED_TERM_TYPED_CONDITION",
            "condition_holds": True,
        }],
        typed_context=c,
        expected_typed_context_sha256=digest,
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []
