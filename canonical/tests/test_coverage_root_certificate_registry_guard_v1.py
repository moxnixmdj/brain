from copy import deepcopy
import json
from pathlib import Path

from canonical.runtime.coverage_root_certificate_registry_guard_v1 import (
    CERTIFICATE_ROOT_IDS,
    validate,
)
from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"
MISSION_POINTER = json.loads((ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json").read_text(encoding="utf-8"))
MISSION_AUTHORITY_BLOB_SHA = "13c470645b037bbb46245c687dd35197b420d51a"
MISSION_POINTER_BLOB_SHA = "7ad5f82d8434966781bf97c725d482e10133fc7c"


def active_claim(**overrides):
    claim = {
        "claim_kind": "CHECKPOINT_ACCEPTANCE",
        "mission_blob_sha": MISSION_POINTER_BLOB_SHA,
        "scope_sha256": "1" * 64,
        "target_predicate_sha256": "2" * 64,
        "semantics_sha256": "3" * 64,
        "epoch": "2026-10-09",
        "authority_id": "PROJECT_BRAIN_CURRENT_MISSION_OBJECTIVE",
        "terminal_credit_delta": 0,
    }
    claim.update(overrides)
    claim["claim_id"] = compute_claim_id(claim)
    return claim


def proved_slot(root_id, claim, *, claim_override=None, verify_claim_id=None):
    binding = dict(claim if claim_override is None else claim_override)
    return {
        "root_id": root_id,
        "status": "PROVED_CURRENT",
        "certificate": {
            "root_id": root_id,
            "mission_authority_blob_sha": MISSION_AUTHORITY_BLOB_SHA,
            "path": f"{root_id}.json",
            "git_blob_sha": "abc",
            "claim_binding": binding,
        },
        "independent_verification": {
            "path": f"{root_id}.verify.json",
            "git_blob_sha": "def",
            "claim_id": claim["claim_id"] if verify_claim_id is None else verify_claim_id,
        },
    }


def load():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_current_registry_is_valid_and_all_three_certificates_open():
    out = validate(load(), current_mission_pointer=MISSION_POINTER, current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA, current_mission_pointer_blob_sha=MISSION_POINTER_BLOB_SHA)
    assert out["pass"] is True, out
    assert out["open_root_ids"] == list(CERTIFICATE_ROOT_IDS)
    assert out["proved_root_ids"] == []
    assert out["r4_proof_closure"] is False
    assert out["terminal_credit_delta"] == 0


def test_short_alias_cannot_replace_canonical_root_id():
    doc = load()
    doc["certificate_slots"][1]["root_id"] = "R2"
    out = validate(doc, current_mission_pointer=MISSION_POINTER, current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA)
    assert out["pass"] is False
    assert "INVALID_CERTIFICATE_ROOT_ID:R2" in out["errors"]


def test_unrelated_r3_label_cannot_close_cc_r3():
    doc = load()
    doc["certificate_slots"][2] = {
        "root_id": "R3_ZERO_RESIDUAL_TERMINAL_TRUTH_RECONCILIATION",
        "status": "PROVED_CURRENT",
        "certificate": {},
        "independent_verification": {},
    }
    out = validate(doc, current_mission_pointer=MISSION_POINTER, current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA)
    assert out["pass"] is False


def test_proved_slot_without_content_addressed_certificate_fails():
    doc = load()
    doc["certificate_slots"][0] = {
        "root_id": "CC_R1_REALITY_CONTAINMENT_V1",
        "status": "PROVED_CURRENT",
        "certificate": None,
        "independent_verification": None,
    }
    doc["currently_proved_root_certificates"] = 1
    doc["currently_open_root_certificates"] = 2
    out = validate(doc, current_mission_pointer=MISSION_POINTER, current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA)
    assert "PROVED_SLOT_CERTIFICATE_MISSING:CC_R1_REALITY_CONTAINMENT_V1" in out["errors"]
    assert "PROVED_SLOT_INDEPENDENT_VERIFICATION_MISSING:CC_R1_REALITY_CONTAINMENT_V1" in out["errors"]


def test_proved_slot_bound_to_stale_mission_fails():
    doc = load()
    doc["certificate_slots"][0] = {
        "root_id": "CC_R1_REALITY_CONTAINMENT_V1",
        "status": "PROVED_CURRENT",
        "certificate": {
            "root_id": "CC_R1_REALITY_CONTAINMENT_V1",
            "mission_authority_blob_sha": "stale",
            "path": "x.json",
            "git_blob_sha": "abc",
        },
        "independent_verification": {"path": "v.json", "git_blob_sha": "def"},
    }
    doc["currently_proved_root_certificates"] = 1
    doc["currently_open_root_certificates"] = 2
    out = validate(doc, current_mission_pointer=MISSION_POINTER, current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA)
    assert "PROVED_SLOT_MISSION_AUTHORITY_DRIFT:CC_R1_REALITY_CONTAINMENT_V1" in out["errors"]


def test_open_slot_cannot_smuggle_certificate_payload():
    doc = load()
    doc["certificate_slots"][0]["certificate"] = {"path": "fake"}
    out = validate(doc, current_mission_pointer=MISSION_POINTER, current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA)
    assert "OPEN_SLOT_HAS_AUTHORITY_PAYLOAD:CC_R1_REALITY_CONTAINMENT_V1" in out["errors"]


def test_terminal_credit_is_always_forbidden():
    doc = load()
    doc["accounting"]["terminal_credit_delta"] = 1
    out = validate(doc, current_mission_pointer=MISSION_POINTER, current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA)
    assert "UNAUTHORIZED_TERMINAL_CREDIT" in out["errors"]


def test_current_registry_has_no_active_claim_and_cannot_close_any_slot():
    doc = load()
    assert doc["active_claim"] is None
    doc["certificate_slots"][2] = proved_slot("CC_R3_TERMINAL_CLOSURE_V1", active_claim())
    doc["currently_proved_root_certificates"] = 1
    doc["currently_open_root_certificates"] = 2
    out = validate(
        doc,
        current_mission_pointer=MISSION_POINTER,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA,
        current_mission_pointer_blob_sha=MISSION_POINTER_BLOB_SHA,
    )
    assert "PROVED_SLOT_WITHOUT_ACTIVE_CLAIM:CC_R3_TERMINAL_CLOSURE_V1" in out["errors"]


def test_exact_active_claim_allows_claim_bound_proved_slot_without_closing_r4():
    doc = load()
    claim = active_claim()
    doc["active_claim"] = claim
    doc["certificate_slots"][2] = proved_slot("CC_R3_TERMINAL_CLOSURE_V1", claim)
    doc["currently_proved_root_certificates"] = 1
    doc["currently_open_root_certificates"] = 2
    out = validate(
        doc,
        current_mission_pointer=MISSION_POINTER,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA,
        current_mission_pointer_blob_sha=MISSION_POINTER_BLOB_SHA,
    )
    assert out["pass"] is True, out
    assert out["proved_root_ids"] == ["CC_R3_TERMINAL_CLOSURE_V1"]
    assert out["r4_proof_closure"] is False


def test_wrong_claim_certificate_cannot_fill_cc_r3():
    doc = load()
    claim = active_claim()
    wrong = active_claim(scope_sha256="4" * 64)
    doc["active_claim"] = claim
    doc["certificate_slots"][2] = proved_slot(
        "CC_R3_TERMINAL_CLOSURE_V1",
        claim,
        claim_override=wrong,
    )
    doc["currently_proved_root_certificates"] = 1
    doc["currently_open_root_certificates"] = 2
    out = validate(
        doc,
        current_mission_pointer=MISSION_POINTER,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA,
        current_mission_pointer_blob_sha=MISSION_POINTER_BLOB_SHA,
    )
    assert any(
        e.startswith("PROVED_SLOT_CLAIM_BINDING_MISMATCH:CC_R3_TERMINAL_CLOSURE_V1")
        for e in out["errors"]
    )


def test_verification_for_other_claim_cannot_fill_slot():
    doc = load()
    claim = active_claim()
    wrong = active_claim(scope_sha256="4" * 64)
    doc["active_claim"] = claim
    doc["certificate_slots"][2] = proved_slot(
        "CC_R3_TERMINAL_CLOSURE_V1",
        claim,
        verify_claim_id=wrong["claim_id"],
    )
    doc["currently_proved_root_certificates"] = 1
    doc["currently_open_root_certificates"] = 2
    out = validate(
        doc,
        current_mission_pointer=MISSION_POINTER,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA,
        current_mission_pointer_blob_sha=MISSION_POINTER_BLOB_SHA,
    )
    assert "PROVED_SLOT_VERIFICATION_CLAIM_MISMATCH:CC_R3_TERMINAL_CLOSURE_V1" in out["errors"]


def test_active_claim_stale_mission_pointer_is_rejected():
    doc = load()
    claim = active_claim(mission_blob_sha="f" * 40)
    doc["active_claim"] = claim
    out = validate(
        doc,
        current_mission_pointer=MISSION_POINTER,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA,
        current_mission_pointer_blob_sha=MISSION_POINTER_BLOB_SHA,
    )
    assert "ACTIVE_CLAIM_MISSION_BINDING_STALE" in out["errors"]


def test_active_claim_missing_current_mission_pointer_blob_fails_closed():
    doc = load()
    doc["active_claim"] = active_claim()
    out = validate(
        doc,
        current_mission_pointer=MISSION_POINTER,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA,
    )
    assert "CURRENT_MISSION_POINTER_BLOB_REQUIRED_FOR_ACTIVE_CLAIM" in out["errors"]


def test_malformed_active_claim_with_proved_slot_fails_closed_without_exception():
    doc = load()
    doc["active_claim"] = "not-an-object"
    doc["certificate_slots"][2] = proved_slot("CC_R3_TERMINAL_CLOSURE_V1", active_claim())
    doc["currently_proved_root_certificates"] = 1
    doc["currently_open_root_certificates"] = 2
    out = validate(
        doc,
        current_mission_pointer=MISSION_POINTER,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA,
        current_mission_pointer_blob_sha=MISSION_POINTER_BLOB_SHA,
    )
    assert out["pass"] is False
    assert "ACTIVE_CLAIM_NOT_OBJECT" in out["errors"]
