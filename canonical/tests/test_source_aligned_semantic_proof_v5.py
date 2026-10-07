import json
import tempfile
from pathlib import Path

from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime.source_aligned_semantic_proof_v5 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v5 import resolve_from_source_proof
import canonical.runtime.proof_carrying_semantic_refinement_v3 as auth


def context():
    c = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"exposure_amount": {"type": "DECIMAL_STRING", "value": "130.00"}},
    }
    return c, typed_context_sha256(c)


def checked_defined_term():
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
        text, source_id="s", claims=[claim], typed_context=c,
        expected_typed_context_sha256=digest,
    )
    assert checked["status"] == "PROOF_CHECKED", checked
    atom_id = checked["accepted_claims"][0]["condition_atom_id"]
    return text, c, digest, claim, atom_id


def test_explicit_defined_term_condition_entails_but_does_not_self_authenticate_policy():
    text, c, digest, claim, atom_id = checked_defined_term()
    out = resolve_from_source_proof(
        text, source_id="s", claims=[claim], typed_context=c,
        expected_typed_context_sha256=digest, decision_basis=[atom_id],
        policy_conditions={
            "exception_policy": {"op": "ATOM", "id": atom_id},
            "ordinary_policy": {"op": "NOT", "arg": {"op": "ATOM", "id": atom_id}},
        },
    )
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["exception_policy"]
    assert out["certified_common_policies"] == []


def test_true_formula_exploit_is_not_policy_adequacy():
    text, c, digest, claim, atom_id = checked_defined_term()
    out = resolve_from_source_proof(
        text, source_id="s", claims=[claim], typed_context=c,
        expected_typed_context_sha256=digest, decision_basis=[atom_id],
        policy_conditions={"forged": {"op": "TRUE"}},
    )
    assert out["entailed_policy_conditions"] == ["forged"]
    assert out["certified_common_policies"] == []
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"


def test_authenticated_defined_term_policy_condition_can_be_certified():
    text, c, digest, claim, atom_id = checked_defined_term()
    condition = {"op": "ATOM", "id": atom_id}
    old_root = auth.ROOT
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth.ROOT = root
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)
            adequacy_path = gov / "exception_policy.json"
            adequacy = {
                "schema": auth.ADEQUACY_SCHEMA,
                "policy_id": "exception_policy",
                "policy_condition_sha256": auth._condition_sha256(condition),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }
            adequacy_path.write_text(json.dumps(adequacy, sort_keys=True), encoding="utf-8")
            adequacy_blob = auth._git_blob_sha(adequacy_path)
            verification_path = ver / "exception_policy_verify.json"
            verification = {
                "schema": auth.VERIFY_SCHEMA,
                "policy_id": "exception_policy",
                "subject_git_blob_sha": adequacy_blob,
                "pass": True,
            }
            verification_path.write_text(
                json.dumps(verification, sort_keys=True), encoding="utf-8"
            )
            verification_blob = auth._git_blob_sha(verification_path)
            out = resolve_from_source_proof(
                text, source_id="s", claims=[claim], typed_context=c,
                expected_typed_context_sha256=digest, decision_basis=[atom_id],
                policy_conditions={"exception_policy": condition},
                policy_adequacy_bindings={
                    "exception_policy": {
                        "adequacy_certificate_path":
                            "canonical/governance/exception_policy.json",
                        "adequacy_certificate_blob_sha": adequacy_blob,
                        "independent_verification_path":
                            "canonical/verification/exception_policy_verify.json",
                        "independent_verification_blob_sha": verification_blob,
                    }
                },
            )
            assert out["status"] == "COMMON_POLICY_CERTIFIED"
            assert out["certified_common_policies"] == ["exception_policy"]
    finally:
        auth.ROOT = old_root


def test_caller_cannot_relabel_defined_term_or_field():
    text = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Total exposure is at least 125.50."
    )
    c, digest = context()
    out = verify_proof(
        text, source_id="s",
        claims=[{
            "claim_id": "defined",
            "kind": "CERTIFIED_DEFINED_TERM_TYPED_CONDITION",
            "condition_holds": True,
            "defined_term": "Aggregate exposure",
            "field_name": "other_amount",
        }],
        typed_context=c, expected_typed_context_sha256=digest,
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
        text, source_id="s",
        claims=[{
            "claim_id": "defined",
            "kind": "CERTIFIED_DEFINED_TERM_TYPED_CONDITION",
            "condition_holds": True,
        }],
        typed_context=c, expected_typed_context_sha256=digest,
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []
