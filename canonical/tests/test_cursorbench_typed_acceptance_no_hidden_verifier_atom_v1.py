from __future__ import annotations

from canonical.runtime import cursorbench_typed_acceptance_no_hidden_verifier_atom_v1 as proof

GOOD = {
    "path": proof.BINDING_PATH,
    "git_blob_sha": proof.BINDING_BLOB_SHA,
}


def test_exact_content_addressed_prewave_boundary_proves_only_no_hidden_verifier_atom():
    out = proof.verify(GOOD)
    assert out["pass"] is True, out
    assert out["atom_truth_authorized"] is True
    assert out["atom_id"] == "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
    assert out["proved_constraint"] == {
        "op": "ATOM",
        "id": "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
    }
    assert out["other_condition_atoms_proved"] == []
    assert out["prewave_replay"]["status"] == "PASS"
    assert out["membership_self_certified"] is False
    assert out["whole_policy_condition_proved"] is False
    assert out["whole_cursorbench_adequate"] is False
    assert out["terminal_authority"] is False


def test_wrong_binding_sha_cannot_mint_atom():
    bad = dict(GOOD)
    bad["git_blob_sha"] = "0" * 40
    out = proof.verify(bad)
    assert out["pass"] is False
    assert out["atom_truth_authorized"] is False
    assert out["reason"] == "BINDING_REFERENCE_SHA_MISMATCH"


def test_wrong_binding_path_cannot_mint_atom():
    bad = dict(GOOD)
    bad["path"] = "canonical/governance/not-the-prewave.json"
    out = proof.verify(bad)
    assert out["pass"] is False
    assert out["atom_truth_authorized"] is False
    assert out["reason"] == "BINDING_PATH_NOT_EXACT_PREWAVE"
