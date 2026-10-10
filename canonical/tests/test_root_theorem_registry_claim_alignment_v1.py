from canonical.runtime import root_theorem_falsifier_v1 as rt


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


def authority(**overrides):
    value = {
        "status": "PASS_CANONICAL_ROOT_CERTIFICATE_AUTHORITY",
        "authorized": True,
        "active_claim": {
            "claim_id": "a" * 64,
            "scope_sha256": "b" * 64,
            "semantics_sha256": "c" * 64,
            "epoch": "E1",
        },
        "canonical_generation": "GEN1",
        "terminal_credit": 0,
    }
    value.update(overrides)
    return value


def root_data(**overrides):
    b = binding()
    value = {
        "R1": True,
        "R2": True,
        "R3": True,
        "R4": True,
        "proof_chain_trustworthy": True,
        "expected_binding": b,
        "root_proofs": {
            root: {"status": "PROVED", "binding": dict(b)}
            for root in ("R1", "R2", "R3")
        },
    }
    value.update(overrides)
    return value


def test_exact_registry_claim_alignment_passes():
    out = rt.evaluate_registry_claim_alignment(
        {"expected_binding": binding()},
        authority(),
    )
    assert out["status"] == "PASS_REGISTRY_CLAIM_ALIGNMENT"
    assert out["aligned"] is True


def test_registry_claim_id_splice_fails():
    out = rt.evaluate_registry_claim_alignment(
        {"expected_binding": binding(claim_id="d" * 64)},
        authority(),
    )
    assert out["status"] == "R4_REGISTRY_CLAIM_MISMATCH"
    assert out["aligned"] is False
    assert "claim_id:claim_id" in out["mismatches"]


def test_registry_scope_splice_fails():
    out = rt.evaluate_registry_claim_alignment(
        {"expected_binding": binding(scope_sha256="d" * 64)},
        authority(),
    )
    assert out["status"] == "R4_REGISTRY_CLAIM_MISMATCH"
    assert "scope_sha256:scope_sha256" in out["mismatches"]


def test_registry_semantics_splice_fails():
    out = rt.evaluate_registry_claim_alignment(
        {"expected_binding": binding(semantics_sha256="d" * 64)},
        authority(),
    )
    assert out["status"] == "R4_REGISTRY_CLAIM_MISMATCH"
    assert "semantics_sha256:semantics_sha256" in out["mismatches"]


def test_registry_epoch_splice_fails():
    out = rt.evaluate_registry_claim_alignment(
        {"expected_binding": binding(epoch_id="E2")},
        authority(),
    )
    assert out["status"] == "R4_REGISTRY_CLAIM_MISMATCH"
    assert "epoch_id:epoch" in out["mismatches"]


def test_current_generation_splice_fails():
    out = rt.evaluate_registry_claim_alignment(
        {"expected_binding": binding(canonical_generation="GEN0")},
        authority(),
    )
    assert out["status"] == "R4_REGISTRY_CLAIM_MISMATCH"
    assert "canonical_generation" in out["mismatches"]


def test_registry_open_cannot_align():
    out = rt.evaluate_registry_claim_alignment(
        {"expected_binding": binding()},
        authority(authorized=False),
    )
    assert out["status"] == "R4_CANONICAL_REGISTRY_NOT_AUTHORIZED"
    assert out["aligned"] is False


def test_r4_rejects_locally_coherent_other_claim(monkeypatch):
    monkeypatch.setattr(
        rt,
        "evaluate_canonical_registry_authority",
        lambda: authority(),
    )
    data = root_data()
    wrong = binding(claim_id="d" * 64)
    data["expected_binding"] = wrong
    data["root_proofs"] = {
        root: {"status": "PROVED", "binding": dict(wrong)}
        for root in ("R1", "R2", "R3")
    }
    out = rt.evaluate_root_closure(data)
    assert out["status"] == "ROOT_NOT_CLOSED"
    assert out["failed_roots"] == ["R4"]


def test_registry_guard_receives_current_mission_pointer_blob(monkeypatch):
    captured = {}

    def fake_validate(registry, **kwargs):
        captured.update(kwargs)
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["SYNTHETIC_STOP"],
            "r4_proof_closure": False,
        }

    monkeypatch.setattr(rt, "validate_root_registry", fake_validate)
    out = rt.evaluate_canonical_registry_authority()
    assert out["authorized"] is False
    assert captured["current_mission_pointer_blob_sha"] == rt._git_blob_sha(rt.MISSION_PATH)


def test_current_open_registry_reports_current_generation():
    out = rt.evaluate_canonical_registry_authority()
    assert out["status"] == "R4_CANONICAL_ROOT_CERTIFICATES_OPEN"
    assert out["authorized"] is False
    assert isinstance(out["canonical_generation"], str)
    assert out["canonical_generation"]
    assert out["mission_pointer_blob_sha"] == rt._git_blob_sha(rt.MISSION_PATH)
