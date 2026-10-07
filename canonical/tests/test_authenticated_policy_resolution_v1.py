import json
import tempfile
from pathlib import Path

from canonical.runtime.authenticated_policy_resolution_v1 import resolve_authenticated_policy
import canonical.runtime.proof_carrying_semantic_refinement_v3 as auth


def test_logically_true_policy_condition_is_not_adequacy():
    out = resolve_authenticated_policy(
        [],
        {"forged": {"op": "TRUE"}},
        proved_constraints=[],
    )
    assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    assert out["entailed_policy_conditions"] == ["forged"]
    assert out["certified_common_policies"] == []


def test_no_entailed_policy_remains_unresolved_not_fail_open():
    out = resolve_authenticated_policy(
        ["A"],
        {"p": {"op": "ATOM", "id": "A"}},
        proved_constraints=[],
    )
    assert out["status"] == "UNRESOLVED"
    assert out["certified_common_policies"] == []


def test_authenticated_exact_condition_can_certify():
    condition = {"op": "TRUE"}
    old_root = auth.ROOT
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth.ROOT = root
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)

            adequacy_path = gov / "p.json"
            adequacy = {
                "schema": auth.ADEQUACY_SCHEMA,
                "policy_id": "p",
                "policy_condition_sha256": auth._condition_sha256(condition),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }
            adequacy_path.write_text(json.dumps(adequacy, sort_keys=True), encoding="utf-8")
            adequacy_blob = auth._git_blob_sha(adequacy_path)

            verify_path = ver / "p_verify.json"
            verification = {
                "schema": auth.VERIFY_SCHEMA,
                "policy_id": "p",
                "subject_git_blob_sha": adequacy_blob,
                "pass": True,
            }
            verify_path.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
            verify_blob = auth._git_blob_sha(verify_path)

            out = resolve_authenticated_policy(
                [],
                {"p": condition},
                proved_constraints=[],
                policy_adequacy_bindings={
                    "p": {
                        "adequacy_certificate_path": "canonical/governance/p.json",
                        "adequacy_certificate_blob_sha": adequacy_blob,
                        "independent_verification_path": "canonical/verification/p_verify.json",
                        "independent_verification_blob_sha": verify_blob,
                    }
                },
            )
            assert out["status"] == "COMMON_POLICY_CERTIFIED"
            assert out["certified_common_policies"] == ["p"]
            assert len(out["authenticated_policy_adequacy"]) == 1
    finally:
        auth.ROOT = old_root


def test_certificate_for_different_condition_is_rejected():
    old_root = auth.ROOT
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth.ROOT = root
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)

            adequacy_path = gov / "p.json"
            adequacy = {
                "schema": auth.ADEQUACY_SCHEMA,
                "policy_id": "p",
                "policy_condition_sha256": auth._condition_sha256({"op": "FALSE"}),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }
            adequacy_path.write_text(json.dumps(adequacy, sort_keys=True), encoding="utf-8")
            adequacy_blob = auth._git_blob_sha(adequacy_path)
            verify_path = ver / "p_verify.json"
            verification = {
                "schema": auth.VERIFY_SCHEMA,
                "policy_id": "p",
                "subject_git_blob_sha": adequacy_blob,
                "pass": True,
            }
            verify_path.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
            verify_blob = auth._git_blob_sha(verify_path)

            out = resolve_authenticated_policy(
                [],
                {"p": {"op": "TRUE"}},
                proved_constraints=[],
                policy_adequacy_bindings={
                    "p": {
                        "adequacy_certificate_path": "canonical/governance/p.json",
                        "adequacy_certificate_blob_sha": adequacy_blob,
                        "independent_verification_path": "canonical/verification/p_verify.json",
                        "independent_verification_blob_sha": verify_blob,
                    }
                },
            )
            assert out["status"] == "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
            assert out["certified_common_policies"] == []
            assert "ADEQUACY_CONDITION_MISMATCH" in out["rejected_policy_adequacy_bindings"][0]["reason"]
    finally:
        auth.ROOT = old_root
