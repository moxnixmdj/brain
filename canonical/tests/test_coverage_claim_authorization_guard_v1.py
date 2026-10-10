from canonical.runtime.coverage_claim_scope_guard_v2 import compute_claim_id
from canonical.runtime.coverage_claim_authorization_guard_v1 import authorize_claim

MISSION = "4d3d7866ad8ee54606a11791f53519eef15a80700bd5dcc221ec0da676ceb942"
AUTHORITY = "PROJECT_BRAIN_REAL_MISSION_OBJECTIVE_V1"
AUTH_BLOB = "a" * 40


def claim(authority_id=AUTHORITY):
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


def policy():
    return {
        "mission_semantic_authority": {"mission_semantics_sha256": MISSION},
        "authorized_issuer": {"authority_id": AUTHORITY},
    }


def authorization(c):
    return {
        "schema": "PROJECT_BRAIN_CCRT_CLAIM_AUTHORIZATION_RECEIPT_V1",
        **{k: c[k] for k in (
            "claim_id",
            "claim_kind",
            "mission_semantics_sha256",
            "scope_sha256",
            "target_predicate_sha256",
            "semantics_sha256",
            "epoch",
            "authority_id",
        )},
        "authorized": True,
    }


def verification(c, *, independent_id="INDEPENDENT_MISSION_AUTH_VERIFIER"):
    return {
        "schema": "PROJECT_BRAIN_CCRT_CLAIM_AUTHORIZATION_INDEPENDENT_VERIFICATION_V1",
        "subject_git_blob_sha": AUTH_BLOB,
        "claim_id": c["claim_id"],
        "pass": True,
        "independent_verified": True,
        "mission_authorization_semantics_verified": True,
        "independent_verifier_id": independent_id,
    }


def test_exact_authorized_claim_passes_but_does_not_claim_satisfaction():
    c = claim()
    out = authorize_claim(
        c,
        current_mission_semantics_sha256=MISSION,
        policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        verification=verification(c),
    )
    assert out["pass"] is True
    assert out["mission_authorized"] is True
    assert out["g_minus_claim_eligible"] is True
    assert out["actual_claim_satisfaction_verified"] is False


def test_arbitrary_authority_counterexample_is_blocked():
    c = claim("ARBITRARY_UNAUTHORIZED_AUTHORITY")
    out = authorize_claim(
        c,
        current_mission_semantics_sha256=MISSION,
        policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        verification=verification(c),
    )
    assert out["pass"] is False
    assert "AUTHORIZATION_ISSUER_NOT_MISSION_AUTHORITY" in out["errors"]


def test_self_consistent_hash_does_not_replace_authorization():
    c = claim()
    a = authorization(c)
    a["authorized"] = False
    out = authorize_claim(
        c,
        current_mission_semantics_sha256=MISSION,
        policy=policy(),
        authorization=a,
        authorization_git_blob_sha=AUTH_BLOB,
        verification=verification(c),
    )
    assert out["pass"] is False
    assert "CLAIM_NOT_AUTHORIZED" in out["errors"]


def test_target_predicate_swap_breaks_exact_authorization():
    c = claim()
    a = authorization(c)
    a["target_predicate_sha256"] = "9" * 64
    out = authorize_claim(
        c,
        current_mission_semantics_sha256=MISSION,
        policy=policy(),
        authorization=a,
        authorization_git_blob_sha=AUTH_BLOB,
        verification=verification(c),
    )
    assert "AUTHORIZATION_CLAIM_MISMATCH:target_predicate_sha256" in out["errors"]


def test_verification_must_bind_exact_authorization_blob():
    c = claim()
    v = verification(c)
    v["subject_git_blob_sha"] = "b" * 40
    out = authorize_claim(
        c,
        current_mission_semantics_sha256=MISSION,
        policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        verification=v,
    )
    assert "AUTHORIZATION_VERIFICATION_SUBJECT_MISMATCH" in out["errors"]


def test_independent_verifier_must_be_distinct():
    c = claim()
    out = authorize_claim(
        c,
        current_mission_semantics_sha256=MISSION,
        policy=policy(),
        authorization=authorization(c),
        authorization_git_blob_sha=AUTH_BLOB,
        verification=verification(c, independent_id=AUTHORITY),
    )
    assert "INDEPENDENT_VERIFIER_NOT_DISTINCT" in out["errors"]
