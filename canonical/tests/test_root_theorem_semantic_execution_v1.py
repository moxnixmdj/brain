from canonical.runtime import root_theorem_falsifier_v1 as rt


def claim():
    return {
        "claim_id": "a" * 64,
        "scope_sha256": "b" * 64,
        "semantics_sha256": "c" * 64,
    }


def slot(root_id="CC_R1_REALITY_CONTAINMENT_V1"):
    return {
        "root_id": root_id,
        "status": "PROVED_CURRENT",
        "certificate": {"path": "cert.json", "git_blob_sha": "a" * 40},
        "semantic_verifier": {"path": "verify.py", "git_blob_sha": "b" * 40},
        "independent_verification": {"path": "receipt.json", "git_blob_sha": "c" * 40},
    }


def registry(*slots):
    return {
        "active_claim": claim() if slots else None,
        "certificate_slots": list(slots),
    }


def test_zero_proved_slots_are_vacuously_semantic_pass():
    out = rt.execute_semantic_root_verifiers(registry())
    assert out["pass"] is True
    assert out["status"] == "PASS_NO_PROVED_ROOTS_TO_SEMANTICALLY_VERIFY"
    assert out["results"] == []


def test_each_proved_slot_runs_existing_semantic_validator(monkeypatch):
    seen = []

    def fake_validate(root, proved_slot, active_claim):
        seen.append((root, proved_slot["root_id"], active_claim["claim_id"]))
        return {
            "pass": True,
            "status": "PASS__EXECUTABLE_SEMANTIC_ROOT_CERTIFICATE_VERIFICATION",
            "errors": [],
        }

    monkeypatch.setattr(rt, "validate_semantic_root_slot", fake_validate)
    out = rt.execute_semantic_root_verifiers(
        registry(
            slot("CC_R1_REALITY_CONTAINMENT_V1"),
            slot("CC_R2_MISSION_SOUNDNESS_V1"),
            slot("CC_R3_TERMINAL_CLOSURE_V1"),
        )
    )
    assert out["pass"] is True
    assert out["status"] == "PASS_EXECUTABLE_SEMANTIC_ROOT_VERIFICATION"
    assert [row[1] for row in seen] == [
        "CC_R1_REALITY_CONTAINMENT_V1",
        "CC_R2_MISSION_SOUNDNESS_V1",
        "CC_R3_TERMINAL_CLOSURE_V1",
    ]


def test_semantically_rejected_certificate_blocks_r4_semantic_authority(monkeypatch):
    def fake_validate(root, proved_slot, active_claim):
        if proved_slot["root_id"] == "CC_R2_MISSION_SOUNDNESS_V1":
            return {"pass": False, "status": "FAIL_CLOSED", "errors": ["SEMANTIC_FALSE"]}
        return {
            "pass": True,
            "status": "PASS__EXECUTABLE_SEMANTIC_ROOT_CERTIFICATE_VERIFICATION",
            "errors": [],
        }

    monkeypatch.setattr(rt, "validate_semantic_root_slot", fake_validate)
    out = rt.execute_semantic_root_verifiers(
        registry(
            slot("CC_R1_REALITY_CONTAINMENT_V1"),
            slot("CC_R2_MISSION_SOUNDNESS_V1"),
            slot("CC_R3_TERMINAL_CLOSURE_V1"),
        )
    )
    assert out["pass"] is False
    assert out["status"] == "R4_SEMANTIC_ROOT_VERIFICATION_FAILED"
    failed = [row for row in out["results"] if row["pass"] is False]
    assert failed == [{
        "root_id": "CC_R2_MISSION_SOUNDNESS_V1",
        "pass": False,
        "status": "FAIL_CLOSED",
        "errors": ["SEMANTIC_FALSE"],
    }]


def test_proved_slot_without_active_claim_fails_closed():
    out = rt.execute_semantic_root_verifiers({
        "active_claim": None,
        "certificate_slots": [slot()],
    })
    assert out["pass"] is False
    assert out["status"] == "R4_SEMANTIC_ACTIVE_CLAIM_MISSING"


def test_current_open_registry_still_reports_open_not_semantic_error():
    out = rt.evaluate_canonical_registry_authority()
    assert out["authorized"] is False
    assert out["status"] == "R4_CANONICAL_ROOT_CERTIFICATES_OPEN"
