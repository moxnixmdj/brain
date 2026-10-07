from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime.source_aligned_semantic_proof_v4 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v4 import resolve_from_source_proof


def ctx(value):
    c = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"exception_holds": {"type": "BOOL", "value": value}},
    }
    return c, typed_context_sha256(c)


def test_true_condition_enters_trusted_state_and_selects_exception_policy():
    text = "Apply Rule A unless exception_holds is true."
    c, digest = ctx(True)
    claim = {
        "claim_id": "cond",
        "kind": "CERTIFIED_TYPED_UNLESS_CONDITION",
        "condition_holds": True,
    }
    checked = verify_proof(
        text,
        source_id="s",
        claims=[claim],
        typed_context=c,
        expected_typed_context_sha256=digest,
    )
    assert checked["status"] == "PROOF_CHECKED", checked
    atom_id = checked["accepted_claims"][0]["condition_atom_id"]
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
    assert out["status"] == "COMMON_POLICY_CERTIFIED"
    assert out["certified_common_policies"] == ["exception_policy"]


def test_false_condition_enters_as_negation_and_selects_ordinary_policy():
    text = "Apply Rule A unless exception_holds is true."
    c, digest = ctx(False)
    claim = {
        "claim_id": "cond",
        "kind": "CERTIFIED_TYPED_UNLESS_CONDITION",
        "condition_holds": False,
    }
    checked = verify_proof(
        text,
        source_id="s",
        claims=[claim],
        typed_context=c,
        expected_typed_context_sha256=digest,
    )
    atom_id = checked["accepted_claims"][0]["condition_atom_id"]
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
    assert out["certified_common_policies"] == ["ordinary_policy"]


def test_wrong_claimed_condition_result_is_rejected():
    text = "Apply Rule A unless exception_holds is true."
    c, digest = ctx(True)
    out = verify_proof(
        text,
        source_id="s",
        claims=[{
            "claim_id": "cond",
            "kind": "CERTIFIED_TYPED_UNLESS_CONDITION",
            "condition_holds": False,
        }],
        typed_context=c,
        expected_typed_context_sha256=digest,
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []
    assert out["rejected_claims"][0]["reason"] == "CONDITION_RESULT_MISMATCH"


def test_uncontrolled_exception_prose_cannot_mint_condition_fact():
    text = "Apply Rule A unless the customer qualifies under the exception."
    c, digest = ctx(True)
    out = verify_proof(
        text,
        source_id="s",
        claims=[{
            "claim_id": "cond",
            "kind": "CERTIFIED_TYPED_UNLESS_CONDITION",
            "condition_holds": True,
        }],
        typed_context=c,
        expected_typed_context_sha256=digest,
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []
