from canonical.runtime.ccrt_good_lower_kernel_v1 import (
    GOOD_SCHEMA,
    GOOD_VERIFY_SCHEMA,
    _sha256,
    admit,
    initialize,
)
from canonical.runtime.coverage_claim_scope_guard_v2 import compute_claim_id

MISSION = "4d3d7866ad8ee54606a11791f53519eef15a80700bd5dcc221ec0da676ceb942"
AUTHORITY = "PROJECT_BRAIN_REAL_MISSION_OBJECTIVE_V1"
AUTH_BLOB = "a" * 40
VERIFIER_BLOB = "b" * 40


def claim():
    c = {
        "claim_kind": "PROPERTY_CERTIFICATE",
        "mission_semantics_sha256": MISSION,
        "scope_sha256": "1" * 64,
        "target_predicate_sha256": "2" * 64,
        "semantics_sha256": "3" * 64,
        "epoch": "2026-10-09",
        "authority_id": AUTHORITY,
        "terminal_credit_delta": 0,
    }
    c["claim_id"] = compute_claim_id(c)
    return c


def policy():
    return {
        "mission_semantic_authority": {"mission_semantics_sha256": MISSION},
        "authorized_issuer": {"authority_id": AUTHORITY},
    }


def authorization(c):
    return {
        "schema": "PROJECT_BRAIN_CCRT_CLAIM_AUTHORIZATION_RECEIPT_V1",
        **{k: c[k] for k in (
            "claim_id", "claim_kind", "mission_semantics_sha256", "scope_sha256",
            "target_predicate_sha256", "semantics_sha256", "epoch", "authority_id",
        )},
        "authorized": True,
    }


def auth_verify(c):
    return {
        "schema": "PROJECT_BRAIN_CCRT_CLAIM_AUTHORIZATION_INDEPENDENT_VERIFICATION_V1",
        "subject_git_blob_sha": AUTH_BLOB,
        "claim_id": c["claim_id"],
        "pass": True,
        "independent_verified": True,
        "mission_authorization_semantics_verified": True,
        "independent_verifier_id": "AUTH-INDEPENDENT",
    }


def registry():
    return {
        "verifiers": [{
            "verifier_id": "TEST_GOAL_VERIFIER",
            "path": "canonical/runtime/test_goal.py",
            "git_blob_sha": VERIFIER_BLOB,
            "success_status": "PASS__GOAL_ACCEPTED",
        }]
    }


def cert(c, cell_id="cell-1"):
    return {
        "schema": GOOD_SCHEMA,
        "claim_id": c["claim_id"],
        "mission_semantics_sha256": MISSION,
        "scope_sha256": c["scope_sha256"],
        "claim_semantics_sha256": c["semantics_sha256"],
        "cell_id": cell_id,
        "behavior_or_result_sha256": "4" * 64,
        "accepted": True,
        "actual_claim_satisfaction_verified": True,
        "verifier_id": "TEST_GOAL_VERIFIER",
        "verifier_path": "canonical/runtime/test_goal.py",
        "verifier_git_blob_sha": VERIFIER_BLOB,
        "verifier_status": "PASS__GOAL_ACCEPTED",
        "verifier_output_sha256": "5" * 64,
    }


def good_verify(c, certificate):
    return {
        "schema": GOOD_VERIFY_SCHEMA,
        "subject_certificate_sha256": _sha256(certificate),
        "claim_id": c["claim_id"],
        "cell_id": certificate["cell_id"],
        "behavior_or_result_sha256": certificate["behavior_or_result_sha256"],
        "pass": True,
        "independent_verified": True,
        "claim_semantics_binding_verified": True,
        "goal_satisfaction_semantics_verified": True,
        "independent_verifier_id": "GOOD-INDEPENDENT",
    }


def state(c):
    return initialize(
        c,
        current_mission_semantics_sha256=MISSION,
        authorization_policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        authorization_verification=auth_verify(c),
    )


def test_empty_base_preserves_r2_by_construction():
    c = claim()
    out = state(c)
    assert out["pass"] is True
    assert out["g_minus_cell_count"] == 0
    assert out["r2_invariant_preserved"] is True
    assert out["r2_globally_closed"] is False


def test_independently_verified_good_cell_is_admitted():
    c = claim()
    certificate = cert(c)
    out = admit(
        state(c), c,
        current_mission_semantics_sha256=MISSION,
        authorization_policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        authorization_verification=auth_verify(c),
        verifier_registry=registry(),
        certificate=certificate,
        independent_verification=good_verify(c, certificate),
    )
    assert out["pass"] is True
    assert out["g_minus_cell_count"] == 1
    assert out["r2_invariant_preserved"] is True


def test_unregistered_goal_verifier_cannot_enter_g_minus():
    c = claim()
    certificate = cert(c)
    certificate["verifier_id"] = "UNKNOWN"
    out = admit(
        state(c), c,
        current_mission_semantics_sha256=MISSION,
        authorization_policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        authorization_verification=auth_verify(c),
        verifier_registry=registry(),
        certificate=certificate,
        independent_verification=good_verify(c, certificate),
    )
    assert out["pass"] is False
    assert out["reason"] == "GOAL_SATISFACTION_VERIFIER_NOT_REGISTERED"


def test_self_asserted_satisfaction_cannot_enter_g_minus():
    c = claim()
    certificate = cert(c)
    certificate["actual_claim_satisfaction_verified"] = False
    out = admit(
        state(c), c,
        current_mission_semantics_sha256=MISSION,
        authorization_policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        authorization_verification=auth_verify(c),
        verifier_registry=registry(),
        certificate=certificate,
        independent_verification=good_verify(c, certificate),
    )
    assert out["pass"] is False
    assert out["reason"] == "ACTUAL_CLAIM_SATISFACTION_NOT_VERIFIED"


def test_independent_semantics_verification_is_required():
    c = claim()
    certificate = cert(c)
    verify = good_verify(c, certificate)
    verify["goal_satisfaction_semantics_verified"] = False
    out = admit(
        state(c), c,
        current_mission_semantics_sha256=MISSION,
        authorization_policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        authorization_verification=auth_verify(c),
        verifier_registry=registry(),
        certificate=certificate,
        independent_verification=verify,
    )
    assert out["pass"] is False
    assert out["reason"] == "GOOD_CELL_GOAL_SATISFACTION_SEMANTICS_NOT_VERIFIED"


def test_same_cell_same_certificate_is_idempotent():
    c = claim()
    certificate = cert(c)
    first = admit(
        state(c), c,
        current_mission_semantics_sha256=MISSION,
        authorization_policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        authorization_verification=auth_verify(c),
        verifier_registry=registry(),
        certificate=certificate,
        independent_verification=good_verify(c, certificate),
    )
    second = admit(
        first, c,
        current_mission_semantics_sha256=MISSION,
        authorization_policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        authorization_verification=auth_verify(c),
        verifier_registry=registry(),
        certificate=certificate,
        independent_verification=good_verify(c, certificate),
    )
    assert second["pass"] is True
    assert second["g_minus_cell_count"] == 1
    assert second["status"] == "PASS__IDEMPOTENT_GOOD_CELL_ALREADY_ADMITTED"
