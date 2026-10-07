import json
import tempfile
from pathlib import Path

from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime.source_aligned_semantic_proof_v4 import verify_proof
import canonical.runtime.proof_carrying_semantic_refinement_v4 as bridge
import canonical.runtime.proof_carrying_semantic_refinement_v3 as adequacy_auth


def ctx(value):
    c = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"exception_holds": {"type": "BOOL", "value": value}},
    }
    return c, typed_context_sha256(c)


def _condition_atom(text, value):
    c, digest = ctx(value)
    claim = {
        "claim_id": "cond",
        "kind": "CERTIFIED_TYPED_UNLESS_CONDITION",
        "condition_holds": value,
    }
    checked = verify_proof(
        text,
        source_id="s",
        claims=[claim],
        typed_context=c,
        expected_typed_context_sha256=digest,
    )
    assert checked["status"] == "PROOF_CHECKED", checked
    return c, digest, claim, checked["accepted_claims"][0]["condition_atom_id"]


def test_true_condition_entails_exception_policy_but_does_not_self_authenticate_adequacy():
    text = "Apply Rule A unless exception_holds is true."
    c, digest, claim, atom_id = _condition_atom(text, True)
    out = bridge.resolve_from_source_proof(
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
    assert out["rejected_policy_adequacy_bindings"][0]["reason"] == "ADEQUACY_BINDING_MISSING"


def test_false_condition_entails_ordinary_policy_but_does_not_self_authenticate_adequacy():
    text = "Apply Rule A unless exception_holds is true."
    c, digest, claim, atom_id = _condition_atom(text, False)
    out = bridge.resolve_from_source_proof(
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


def test_true_policy_condition_exploit_is_blocked_without_adequacy_authentication():
    text = "Apply Rule A unless exception_holds is true."
    c, digest, claim, atom_id = _condition_atom(text, True)
    out = bridge.resolve_from_source_proof(
        text,
        source_id="s",
        claims=[claim],
        typed_context=c,
        expected_typed_context_sha256=digest,
        decision_basis=[atom_id],
        policy_conditions={"forged": {"op": "TRUE"}},
    )
    assert out["entailed_policy_conditions"] == ["forged"]
    assert out["certified_common_policies"] == []
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"


def test_exact_authenticated_policy_adequacy_can_certify_v4_entailed_policy():
    text = "Apply Rule A unless exception_holds is true."
    c, digest, claim, atom_id = _condition_atom(text, True)
    condition = {"op": "ATOM", "id": atom_id}

    old_root = adequacy_auth.ROOT
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            adequacy_auth.ROOT = root
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)

            adequacy_path = gov / "exception_policy.json"
            adequacy = {
                "schema": adequacy_auth.ADEQUACY_SCHEMA,
                "policy_id": "exception_policy",
                "policy_condition_sha256": adequacy_auth._condition_sha256(condition),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }
            adequacy_path.write_text(json.dumps(adequacy, sort_keys=True), encoding="utf-8")
            adequacy_blob = adequacy_auth._git_blob_sha(adequacy_path)

            verify_path = ver / "exception_policy_verify.json"
            verification = {
                "schema": adequacy_auth.VERIFY_SCHEMA,
                "policy_id": "exception_policy",
                "subject_git_blob_sha": adequacy_blob,
                "pass": True,
            }
            verify_path.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
            verify_blob = adequacy_auth._git_blob_sha(verify_path)

            out = bridge.resolve_from_source_proof(
                text,
                source_id="s",
                claims=[claim],
                typed_context=c,
                expected_typed_context_sha256=digest,
                decision_basis=[atom_id],
                policy_conditions={"exception_policy": condition},
                policy_adequacy_bindings={
                    "exception_policy": {
                        "adequacy_certificate_path": "canonical/governance/exception_policy.json",
                        "adequacy_certificate_blob_sha": adequacy_blob,
                        "independent_verification_path": "canonical/verification/exception_policy_verify.json",
                        "independent_verification_blob_sha": verify_blob,
                    }
                },
            )
            assert out["status"] == "COMMON_POLICY_CERTIFIED"
            assert out["certified_common_policies"] == ["exception_policy"]
            assert len(out["authenticated_policy_adequacy"]) == 1
    finally:
        adequacy_auth.ROOT = old_root


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
