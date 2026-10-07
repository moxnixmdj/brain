import json
import tempfile
from pathlib import Path

from canonical.runtime.source_aligned_semantic_proof_v6 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v6 import resolve_from_source_proof
import canonical.runtime.proof_carrying_semantic_refinement_v3 as auth_bridge


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


def claim(holds):
    return {
        "claim_id": "raw",
        "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
        "condition_holds": holds,
    }


def checked_atom(value, holds):
    checked = verify_proof(
        POLICY,
        source_id="policy",
        claims=[claim(holds)],
        fact_source=facts(value),
        fact_source_id="case-facts",
    )
    assert checked["status"] == "PROOF_CHECKED", checked
    return checked["accepted_claims"][0]["condition_atom_id"]


def test_raw_fact_source_entails_exception_policy_but_does_not_self_certify_adequacy():
    atom_id = checked_atom("130.00", True)
    out = resolve_from_source_proof(
        POLICY,
        source_id="policy",
        claims=[claim(True)],
        fact_source=facts("130.00"),
        fact_source_id="case-facts",
        decision_basis=[atom_id],
        policy_conditions={
            "exception_policy": {"op": "ATOM", "id": atom_id},
            "ordinary_policy": {"op": "NOT", "arg": {"op": "ATOM", "id": atom_id}},
        },
    )
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["exception_policy"]
    assert out["certified_common_policies"] == []


def test_raw_fact_source_below_threshold_entails_ordinary_policy_but_does_not_self_certify_adequacy():
    atom_id = checked_atom("100.00", False)
    out = resolve_from_source_proof(
        POLICY,
        source_id="policy",
        claims=[claim(False)],
        fact_source=facts("100.00"),
        fact_source_id="case-facts",
        decision_basis=[atom_id],
        policy_conditions={
            "exception_policy": {"op": "ATOM", "id": atom_id},
            "ordinary_policy": {"op": "NOT", "arg": {"op": "ATOM", "id": atom_id}},
        },
    )
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["ordinary_policy"]
    assert out["certified_common_policies"] == []


def test_true_condition_exploit_cannot_self_certify_policy():
    atom_id = checked_atom("130.00", True)
    out = resolve_from_source_proof(
        POLICY,
        source_id="policy",
        claims=[claim(True)],
        fact_source=facts("130.00"),
        fact_source_id="case-facts",
        decision_basis=[atom_id],
        policy_conditions={"forged": {"op": "TRUE"}},
    )
    assert out["entailed_policy_conditions"] == ["forged"]
    assert out["certified_common_policies"] == []
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"


def test_authenticated_exact_policy_condition_can_be_certified():
    atom_id = checked_atom("130.00", True)
    condition = {"op": "ATOM", "id": atom_id}
    old_root = auth_bridge.ROOT
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth_bridge.ROOT = root
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)

            adequacy_path = gov / "exception_policy.json"
            adequacy = {
                "schema": auth_bridge.ADEQUACY_SCHEMA,
                "policy_id": "exception_policy",
                "policy_condition_sha256": auth_bridge._condition_sha256(condition),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }
            adequacy_path.write_text(json.dumps(adequacy, sort_keys=True), encoding="utf-8")
            adequacy_blob = auth_bridge._git_blob_sha(adequacy_path)

            verification_path = ver / "exception_policy_verify.json"
            verification = {
                "schema": auth_bridge.VERIFY_SCHEMA,
                "policy_id": "exception_policy",
                "subject_git_blob_sha": adequacy_blob,
                "pass": True,
            }
            verification_path.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
            verification_blob = auth_bridge._git_blob_sha(verification_path)

            out = resolve_from_source_proof(
                POLICY,
                source_id="policy",
                claims=[claim(True)],
                fact_source=facts("130.00"),
                fact_source_id="case-facts",
                decision_basis=[atom_id],
                policy_conditions={"exception_policy": condition},
                policy_adequacy_bindings={
                    "exception_policy": {
                        "adequacy_certificate_path": "canonical/governance/exception_policy.json",
                        "adequacy_certificate_blob_sha": adequacy_blob,
                        "independent_verification_path": "canonical/verification/exception_policy_verify.json",
                        "independent_verification_blob_sha": verification_blob,
                    }
                },
            )
            assert out["status"] == "COMMON_POLICY_CERTIFIED"
            assert out["certified_common_policies"] == ["exception_policy"]
            assert len(out["authenticated_policy_adequacy"]) == 1
    finally:
        auth_bridge.ROOT = old_root


def test_forged_verification_subject_cannot_certify_policy():
    atom_id = checked_atom("130.00", True)
    condition = {"op": "ATOM", "id": atom_id}
    old_root = auth_bridge.ROOT
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth_bridge.ROOT = root
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)

            adequacy_path = gov / "exception_policy.json"
            adequacy_path.write_text(json.dumps({
                "schema": auth_bridge.ADEQUACY_SCHEMA,
                "policy_id": "exception_policy",
                "policy_condition_sha256": auth_bridge._condition_sha256(condition),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }, sort_keys=True), encoding="utf-8")
            adequacy_blob = auth_bridge._git_blob_sha(adequacy_path)

            verification_path = ver / "exception_policy_verify.json"
            verification_path.write_text(json.dumps({
                "schema": auth_bridge.VERIFY_SCHEMA,
                "policy_id": "exception_policy",
                "subject_git_blob_sha": "0" * 40,
                "pass": True,
            }, sort_keys=True), encoding="utf-8")
            verification_blob = auth_bridge._git_blob_sha(verification_path)

            out = resolve_from_source_proof(
                POLICY,
                source_id="policy",
                claims=[claim(True)],
                fact_source=facts("130.00"),
                fact_source_id="case-facts",
                decision_basis=[atom_id],
                policy_conditions={"exception_policy": condition},
                policy_adequacy_bindings={
                    "exception_policy": {
                        "adequacy_certificate_path": "canonical/governance/exception_policy.json",
                        "adequacy_certificate_blob_sha": adequacy_blob,
                        "independent_verification_path": "canonical/verification/exception_policy_verify.json",
                        "independent_verification_blob_sha": verification_blob,
                    }
                },
            )
            assert out["certified_common_policies"] == []
            assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    finally:
        auth_bridge.ROOT = old_root


def test_duplicate_key_fact_source_cannot_mint_semantic_constraint():
    bad = '{"schema_id":"X","fields":{"exposure_amount":{"type":"DECIMAL_STRING","value":"130"},"exposure_amount":{"type":"DECIMAL_STRING","value":"0"}}}'
    out = verify_proof(
        POLICY,
        source_id="policy",
        claims=[claim(True)],
        fact_source=bad,
        fact_source_id="case-facts",
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []


def test_wrong_claimed_result_is_rejected():
    out = verify_proof(
        POLICY,
        source_id="policy",
        claims=[claim(False)],
        fact_source=facts("130.00"),
        fact_source_id="case-facts",
    )
    assert out["status"] == "PROOF_CHECKED_WITH_REJECTIONS"
    assert out["proved_constraints"] == []
