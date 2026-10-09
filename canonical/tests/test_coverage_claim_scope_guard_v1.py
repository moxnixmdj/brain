from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id, validate_claim

MISSION = "52b98f8019938fa7d8164e6a47e359ffb0faeb6a"


def valid_claim():
    c = {
        "claim_kind": "CHECKPOINT_ACCEPTANCE",
        "mission_blob_sha": MISSION,
        "scope_sha256": "1" * 64,
        "target_predicate_sha256": "2" * 64,
        "semantics_sha256": "3" * 64,
        "epoch": "2026-10-09",
        "authority_id": "PROJECT_BRAIN_CURRENT_MISSION_OBJECTIVE",
        "terminal_credit_delta": 0,
    }
    c["claim_id"] = compute_claim_id(c)
    return c


def test_valid_frozen_claim_is_soundness_only():
    out = validate_claim(valid_claim(), current_mission_blob_sha=MISSION)
    assert out["pass"] is True
    assert out["claim_soundness_only"] is True
    assert out["global_mission_completion_derivable"] is False
    assert out["terminal_credit_delta"] == 0


def test_open_ended_global_completion_kind_is_not_allowed():
    c = valid_claim()
    c["claim_kind"] = "GLOBAL_OPEN_ENDED_MISSION_COMPLETE"
    c["claim_id"] = compute_claim_id(c)
    out = validate_claim(c, current_mission_blob_sha=MISSION)
    assert "CLAIM_KIND_NOT_ALLOWED" in out["errors"]


def test_stale_mission_binding_fails():
    c = valid_claim()
    c["mission_blob_sha"] = "stale"
    c["claim_id"] = compute_claim_id(c)
    out = validate_claim(c, current_mission_blob_sha=MISSION)
    assert "MISSION_BINDING_STALE" in out["errors"]


def test_claim_id_prevents_semantic_scope_drift():
    c = valid_claim()
    c["scope_sha256"] = "4" * 64
    out = validate_claim(c, current_mission_blob_sha=MISSION)
    assert "CLAIM_ID_MISMATCH" in out["errors"]


def test_invalid_scope_digest_fails():
    c = valid_claim()
    c["scope_sha256"] = "not-a-sha"
    c["claim_id"] = compute_claim_id(c)
    out = validate_claim(c, current_mission_blob_sha=MISSION)
    assert "INVALID_SHA256:scope_sha256" in out["errors"]


def test_claim_scope_cannot_grant_credit():
    c = valid_claim()
    c["terminal_credit_delta"] = 1
    out = validate_claim(c, current_mission_blob_sha=MISSION)
    assert "NONZERO_CREDIT_FORBIDDEN" in out["errors"]
