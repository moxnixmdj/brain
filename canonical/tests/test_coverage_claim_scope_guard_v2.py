from canonical.runtime.coverage_claim_scope_guard_v2 import (
    compute_claim_id,
    validate_claim,
)

MISSION = "4d3d7866ad8ee54606a11791f53519eef15a80700bd5dcc221ec0da676ceb942"


def claim(authority_id="PROJECT_BRAIN_REAL_MISSION_OBJECTIVE_V1"):
    c = {
        "claim_kind": "PROPERTY_CERTIFICATE",
        "mission_semantics_sha256": MISSION,
        "scope_sha256": "1" * 64,
        "target_predicate_sha256": "2" * 64,
        "semantics_sha256": "3" * 64,
        "epoch": "2026-10-09",
        "authority_id": authority_id,
        "terminal_credit_delta": 0,
    }
    c["claim_id"] = compute_claim_id(c)
    return c


def test_structural_claim_is_not_authorization():
    out = validate_claim(claim(), current_mission_semantics_sha256=MISSION)
    assert out["pass"] is True
    assert out["structural_scope_valid"] is True
    assert out["mission_authorized"] is False
    assert out["claim_soundness_proved"] is False


def test_arbitrary_authority_string_does_not_gain_authority():
    out = validate_claim(
        claim("ARBITRARY_UNAUTHORIZED_AUTHORITY"),
        current_mission_semantics_sha256=MISSION,
    )
    assert out["pass"] is True
    assert out["mission_authorized"] is False


def test_semantic_mission_drift_fails():
    out = validate_claim(claim(), current_mission_semantics_sha256="f" * 64)
    assert "MISSION_SEMANTICS_BINDING_STALE" in out["errors"]


def test_scope_drift_breaks_claim_id():
    c = claim()
    c["scope_sha256"] = "4" * 64
    out = validate_claim(c, current_mission_semantics_sha256=MISSION)
    assert "CLAIM_ID_MISMATCH" in out["errors"]


def test_global_open_ended_completion_forbidden():
    c = claim()
    c["claim_kind"] = "GLOBAL_OPEN_ENDED_MISSION_COMPLETE"
    c["claim_id"] = compute_claim_id(c)
    out = validate_claim(c, current_mission_semantics_sha256=MISSION)
    assert "CLAIM_KIND_NOT_ALLOWED" in out["errors"]


def test_pointer_blob_not_in_claim_identity():
    a = claim()
    b = dict(a)
    b["incidental_mission_pointer_blob_sha"] = "f" * 40
    assert compute_claim_id(a) == compute_claim_id(b)
