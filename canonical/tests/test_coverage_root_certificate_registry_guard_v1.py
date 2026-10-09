from copy import deepcopy
import json
from pathlib import Path

from canonical.runtime.coverage_root_certificate_registry_guard_v1 import (
    CERTIFICATE_ROOT_IDS,
    validate,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"
MISSION_POINTER = json.loads((ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json").read_text(encoding="utf-8"))\nMISSION_AUTHORITY_BLOB_SHA = "13c470645b037bbb46245c687dd35197b420d51a"\n

def load():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_current_registry_is_valid_and_all_three_certificates_open():
    out = validate(load(), current_mission_pointer=MISSION_POINTER, current_mission_authority_blob_sha=MISSION_AUTHORITY_BLOB_SHA)
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
