from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime.source_aligned_semantic_proof_v4 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v4 import resolve_from_source_proof
import canonical.runtime.proof_carrying_semantic_refinement_v3 as adequacy_auth


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
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["exception_policy"]
    assert out["certified_common_policies"] == []


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
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["ordinary_policy"]
    assert out["certified_common_policies"] == []


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


def test_v4_uses_v3_adequacy_authenticator_before_common_policy_credit():
    text = "Apply Rule A unless exception_holds is true."
    c, digest = ctx(True)
    claim = {
        "claim_id": "cond",
        "kind": "CERTIFIED_TYPED_UNLESS_CONDITION",
        "condition_holds": True,
    }
    checked = verify_proof(
        text, source_id="s", claims=[claim], typed_context=c,
        expected_typed_context_sha256=digest,
    )
    atom_id = checked["accepted_claims"][0]["condition_atom_id"]
    condition = {"op": "ATOM", "id": atom_id}
    old = adequacy_auth._authenticate_policy_adequacy
    calls = []
    try:
        def accept(pid, supplied_condition, binding):
            calls.append((pid, supplied_condition, binding))
            return True, {"policy_id": pid, "verified": True}
        adequacy_auth._authenticate_policy_adequacy = accept
        out = resolve_from_source_proof(
            text, source_id="s", claims=[claim], typed_context=c,
            expected_typed_context_sha256=digest, decision_basis=[atom_id],
            policy_conditions={"exception_policy": condition},
            policy_adequacy_bindings={"exception_policy": {"bound": True}},
        )
        assert out["status"] == "COMMON_POLICY_CERTIFIED"
        assert out["certified_common_policies"] == ["exception_policy"]
        assert calls == [("exception_policy", condition, {"bound": True})]
    finally:
        adequacy_auth._authenticate_policy_adequacy = old
