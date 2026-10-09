from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from canonical.runtime.coverage_claim_root_certificate_registry_guard_v1 import (
    OPEN,
    PROVED,
    ROOT_IDS,
    canonical_claim_binding,
    validate,
)
from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/COVERAGE_COMPLETENESS_CLAIM_ROOT_CERTIFICATE_REGISTRY_V1.json"
MISSION = "52b98f8019938fa7d8164e6a47e359ffb0faeb6a"
CLAIM_SCOPE = "df3f64759dd1bbf230a40de0695ef514f270f677"


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def make_claim(
    *,
    scope: str = "1" * 64,
    semantics: str = "3" * 64,
    epoch: str = "OPUS_5_5_CHECKPOINT_V1",
    authority_id: str = "CHECKPOINT_AGGREGATOR_TEST_AUTHORITY",
) -> dict:
    claim = {
        "claim_kind": "CHECKPOINT_ACCEPTANCE",
        "mission_blob_sha": MISSION,
        "scope_sha256": scope,
        "target_predicate_sha256": "2" * 64,
        "semantics_sha256": semantics,
        "epoch": epoch,
        "authority_id": authority_id,
        "terminal_credit_delta": 0,
    }
    claim["claim_id"] = compute_claim_id(claim)
    return claim


def open_instance(claim: dict) -> dict:
    return {
        "claim": claim,
        "certificate_slots": [
            {
                "claim_id": claim["claim_id"],
                "root_id": root_id,
                "status": OPEN,
                "certificate": None,
                "independent_verification": None,
            }
            for root_id in ROOT_IDS
        ],
        "proved_root_certificates": 0,
        "open_root_certificates": 3,
        "r4_claim_proof_closure": False,
    }


def proof_payload(claim: dict, root_id: str, suffix: str) -> dict:
    return {
        "root_id": root_id,
        "mission_blob_sha": MISSION,
        "claim_binding": canonical_claim_binding(claim),
        "path": f"canonical/proofs/{suffix}.json",
        "git_blob_sha": (suffix[0] if suffix else "a") * 40,
    }


def register(doc: dict, instance: dict) -> None:
    doc["claim_instances"] = [instance]
    doc["registered_claim_count"] = 1
    doc["currently_open_root_certificates"] = instance["open_root_certificates"]
    doc["currently_proved_root_certificates"] = instance["proved_root_certificates"]
    doc["claim_proof_closure_count"] = 1 if instance["r4_claim_proof_closure"] else 0


def check(doc: dict) -> dict:
    return validate(
        doc,
        current_mission_blob_sha=MISSION,
        current_claim_scope_blob_sha=CLAIM_SCOPE,
    )


def test_empty_current_registry_is_open_not_vacuously_closed():
    out = check(load_registry())
    assert out["pass"] is True, out
    assert out["registered_claim_count"] == 0
    assert out["claim_proof_closure_count"] == 0
    assert out["checkpoint_completion"] is False
    assert out["global_root_closure"] is False
    assert out["global_open_ended_mission_completion"] is False


def test_one_frozen_claim_with_three_open_roots_is_valid():
    doc = load_registry()
    instance = open_instance(make_claim())
    register(doc, instance)
    out = check(doc)
    assert out["pass"] is True, out
    assert out["open_root_certificate_count"] == 3
    assert out["proved_root_certificate_count"] == 0


def test_missing_claim_binding_on_proved_certificate_fails_closed():
    doc = load_registry()
    claim = make_claim()
    instance = open_instance(claim)
    slot = instance["certificate_slots"][0]
    slot["status"] = PROVED
    slot["certificate"] = proof_payload(claim, ROOT_IDS[0], "a_cert")
    slot["certificate"].pop("claim_binding")
    slot["independent_verification"] = proof_payload(claim, ROOT_IDS[0], "b_verify")
    instance["proved_root_certificates"] = 1
    instance["open_root_certificates"] = 2
    register(doc, instance)
    out = check(doc)
    assert out["pass"] is False
    assert any("CERTIFICATE_CLAIM_BINDING_MISMATCH" in e for e in out["errors"])


def test_cross_claim_scope_substitution_fails_closed():
    doc = load_registry()
    claim_a = make_claim()
    claim_b = make_claim(scope="4" * 64)
    instance = open_instance(claim_b)
    slot = instance["certificate_slots"][0]
    slot["status"] = PROVED
    slot["certificate"] = proof_payload(claim_a, ROOT_IDS[0], "a_cert")
    slot["independent_verification"] = proof_payload(claim_b, ROOT_IDS[0], "b_verify")
    instance["proved_root_certificates"] = 1
    instance["open_root_certificates"] = 2
    register(doc, instance)
    out = check(doc)
    assert out["pass"] is False
    assert any("CERTIFICATE_CLAIM_BINDING_MISMATCH" in e for e in out["errors"])


def test_same_scope_different_semantics_substitution_fails_closed():
    doc = load_registry()
    claim_a = make_claim()
    claim_b = make_claim(semantics="5" * 64)
    instance = open_instance(claim_b)
    slot = instance["certificate_slots"][1]
    slot["status"] = PROVED
    slot["certificate"] = proof_payload(claim_a, ROOT_IDS[1], "c_cert")
    slot["independent_verification"] = proof_payload(claim_b, ROOT_IDS[1], "d_verify")
    instance["proved_root_certificates"] = 1
    instance["open_root_certificates"] = 2
    register(doc, instance)
    out = check(doc)
    assert out["pass"] is False
    assert any("CERTIFICATE_CLAIM_BINDING_MISMATCH" in e for e in out["errors"])


def test_stale_epoch_substitution_fails_closed():
    doc = load_registry()
    old_claim = make_claim(epoch="EPOCH_OLD")
    current_claim = make_claim(epoch="EPOCH_CURRENT")
    instance = open_instance(current_claim)
    slot = instance["certificate_slots"][2]
    slot["status"] = PROVED
    slot["certificate"] = proof_payload(old_claim, ROOT_IDS[2], "e_cert")
    slot["independent_verification"] = proof_payload(current_claim, ROOT_IDS[2], "f_verify")
    instance["proved_root_certificates"] = 1
    instance["open_root_certificates"] = 2
    register(doc, instance)
    out = check(doc)
    assert out["pass"] is False
    assert any("CERTIFICATE_CLAIM_BINDING_MISMATCH" in e for e in out["errors"])


def test_authority_id_substitution_fails_closed():
    doc = load_registry()
    wrong = make_claim(authority_id="OTHER_AUTHORITY")
    current = make_claim(authority_id="CURRENT_AUTHORITY")
    instance = open_instance(current)
    slot = instance["certificate_slots"][0]
    slot["status"] = PROVED
    slot["certificate"] = proof_payload(wrong, ROOT_IDS[0], "g_cert")
    slot["independent_verification"] = proof_payload(current, ROOT_IDS[0], "h_verify")
    instance["proved_root_certificates"] = 1
    instance["open_root_certificates"] = 2
    register(doc, instance)
    out = check(doc)
    assert out["pass"] is False
    assert any("CERTIFICATE_CLAIM_BINDING_MISMATCH" in e for e in out["errors"])


def test_all_three_roots_can_close_only_that_claim():
    doc = load_registry()
    claim = make_claim()
    instance = open_instance(claim)
    for i, root_id in enumerate(ROOT_IDS):
        slot = instance["certificate_slots"][i]
        slot["status"] = PROVED
        slot["certificate"] = proof_payload(claim, root_id, f"{chr(97+i)}_cert")
        slot["independent_verification"] = proof_payload(claim, root_id, f"{chr(100+i)}_verify")
    instance["proved_root_certificates"] = 3
    instance["open_root_certificates"] = 0
    instance["r4_claim_proof_closure"] = True
    register(doc, instance)
    out = check(doc)
    assert out["pass"] is True, out
    assert out["claim_proof_closure_count"] == 1
    assert out["closed_claim_ids"] == [claim["claim_id"]]
    assert out["checkpoint_completion"] is False
    assert out["global_root_closure"] is False
    assert out["global_open_ended_mission_completion"] is False


def test_certificate_cannot_self_verify():
    doc = load_registry()
    claim = make_claim()
    instance = open_instance(claim)
    slot = instance["certificate_slots"][0]
    payload = proof_payload(claim, ROOT_IDS[0], "z_same")
    slot["status"] = PROVED
    slot["certificate"] = deepcopy(payload)
    slot["independent_verification"] = deepcopy(payload)
    instance["proved_root_certificates"] = 1
    instance["open_root_certificates"] = 2
    register(doc, instance)
    out = check(doc)
    assert out["pass"] is False
    assert any("VERIFICATION_NOT_INDEPENDENT" in e for e in out["errors"])


def test_global_or_checkpoint_completion_flags_are_forbidden():
    for key in (
        "checkpoint_completion",
        "global_root_closure",
        "global_open_ended_mission_completion",
    ):
        doc = load_registry()
        doc[key] = True
        out = check(doc)
        assert out["pass"] is False
        assert key.upper() + "_FORBIDDEN" in out["errors"]
