from __future__ import annotations

from canonical.runtime import cursorbench_typed_acceptance_no_hidden_verifier_atom_v1 as proof

GOOD = {
    "path": proof.EVIDENCE_PATH,
    "git_blob_sha": proof.EVIDENCE_BLOB_SHA,
}


def test_exact_independent_execution_receipt_proves_only_no_hidden_verifier_atom():
    out = proof.verify(GOOD)
    assert out["pass"] is True, out
    assert out["atom_truth_authorized"] is True
    assert out["atom_id"] == "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
    assert out["proved_constraint"] == {
        "op": "ATOM",
        "id": "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
    }
    assert out["other_condition_atoms_proved"] == []
    assert out["evidence_git_blob_sha"] == proof.EVIDENCE_BLOB_SHA
    assert out["candidate_git_blob_sha"] == proof.CANDIDATE_BLOB_SHA
    assert out["suite_git_blob_sha"] == proof.SUITE_BLOB_SHA
    assert out["test_git_blob_sha"] == proof.TEST_BLOB_SHA
    assert out["membership_self_certified"] is False
    assert out["whole_policy_condition_proved"] is False
    assert out["whole_cursorbench_adequate"] is False
    assert out["terminal_authority"] is False


def test_wrong_evidence_sha_cannot_mint_atom():
    bad = dict(GOOD)
    bad["git_blob_sha"] = "0" * 40
    out = proof.verify(bad)
    assert out["pass"] is False
    assert out["atom_truth_authorized"] is False
    assert out["reason"] == "EVIDENCE_REFERENCE_SHA_MISMATCH"


def test_wrong_evidence_path_cannot_mint_atom():
    bad = dict(GOOD)
    bad["path"] = "canonical/verification/not-the-independent-receipt.json"
    out = proof.verify(bad)
    assert out["pass"] is False
    assert out["atom_truth_authorized"] is False
    assert out["reason"] == "EVIDENCE_PATH_NOT_EXACT_INDEPENDENT_RECEIPT"
