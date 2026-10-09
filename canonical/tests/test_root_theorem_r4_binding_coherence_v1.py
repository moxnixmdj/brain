from canonical.runtime.root_theorem_falsifier_v1 import (
    evaluate_binding_coherence,
    evaluate_root_closure,
)


def binding(**overrides):
    value = {
        "claim_id": "a" * 64,
        "scope_sha256": "b" * 64,
        "semantics_sha256": "c" * 64,
        "carrier_schema_id": "CARRIER_V1",
        "mission_id": "MISSION_V1",
        "epoch_id": "E1",
        "canonical_generation": "GEN1",
    }
    value.update(overrides)
    return value


def proofs(value):
    return {
        root: {"status": "PROVED", "binding": dict(value)}
        for root in ("R1", "R2", "R3")
    }


def test_exact_binding_coherence_passes():
    b = binding()
    out = evaluate_binding_coherence({
        "root_proofs": proofs(b),
        "expected_binding": b,
    })
    assert out["status"] == "PASS_EXACT_BINDING_COHERENCE"
    assert out["coherent"] is True


def test_missing_binding_is_unknown_fail_closed():
    out = evaluate_binding_coherence({})
    assert out["status"] == "UNKNOWN_FAIL_CLOSED"
    assert out["coherent"] is None


def test_carrier_mismatch_is_r4_failure():
    b = binding()
    p = proofs(b)
    p["R3"]["binding"]["carrier_schema_id"] = "OTHER"
    out = evaluate_binding_coherence({"root_proofs": p, "expected_binding": b})
    assert out["status"] == "R4_BINDING_MISMATCH"
    assert out["coherent"] is False


def test_epoch_mismatch_is_r4_failure():
    b = binding()
    p = proofs(b)
    p["R2"]["binding"]["epoch_id"] = "E0"
    out = evaluate_binding_coherence({"root_proofs": p, "expected_binding": b})
    assert out["status"] == "R4_BINDING_MISMATCH"


def test_stale_generation_is_r4_failure():
    b = binding()
    out = evaluate_binding_coherence({
        "root_proofs": proofs(b),
        "expected_binding": binding(canonical_generation="GEN2"),
    })
    assert out["status"] == "R4_STALE_OR_FOREIGN_BINDING"


def test_invalid_content_address_is_r4_failure():
    b = binding(claim_id="not-a-sha")
    out = evaluate_binding_coherence({
        "root_proofs": proofs(b),
        "expected_binding": b,
    })
    assert out["status"] == "UNKNOWN_FAIL_CLOSED" or out["status"] == "R4_BINDING_INVALID"


def test_locally_true_roots_with_mismatch_fail_only_r4():
    b = binding()
    p = proofs(b)
    p["R1"]["binding"]["scope_sha256"] = "d" * 64
    out = evaluate_root_closure({
        "R1": True,
        "R2": True,
        "R3": True,
        "R4": True,
        "root_proofs": p,
        "expected_binding": b,
    })
    assert out["status"] == "ROOT_NOT_CLOSED"
    assert out["failed_roots"] == ["R4"]
    assert out["terminal_credit"] == 0


def test_cross_binding_local_truth_does_not_imply_global_truth():
    r = True
    p_r1 = True
    p_r3 = False
    g_r3 = False
    g_r2 = False
    a = False
    r1 = (not r) or p_r1
    r3 = (not p_r3) or g_r3
    r2 = (not g_r2) or a
    global_conclusion = (not r) or a
    assert r1 and r2 and r3
    assert global_conclusion is False
