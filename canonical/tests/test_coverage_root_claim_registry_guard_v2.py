import json
from hashlib import sha1
from pathlib import Path
from tempfile import TemporaryDirectory

from canonical.runtime.coverage_root_claim_registry_guard_v2 import (
    ROOT_IDS,
    find_exact_claim,
    validate,
)

ROOT = Path(__file__).resolve().parents[2]
MISSION_POINTER = json.loads(
    (ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json").read_text(encoding="utf-8")
)
MISSION_AUTHORITY_SHA = "13c470645b037bbb46245c687dd35197b420d51a"


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


def open_claim(b):
    return {
        "binding": dict(b),
        "certificate_slots": [
            {
                "root_id": root,
                "status": "OPEN_NO_CLAIM_CERTIFICATE_BOUND",
                "certificate": None,
                "independent_verification": None,
            }
            for root in ROOT_IDS
        ],
        "r4_proof_closure": False,
    }


def registry(claims):
    return {
        "schema": "PROJECT_BRAIN_COVERAGE_COMPLETENESS_CLAIM_CERTIFICATE_REGISTRY_V2",
        "namespace": "PROJECT_BRAIN_COVERAGE_COMPLETENESS_ROOTS_V1",
        "mission_binding": {
            "pointer_path": "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
            "authority_path": "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json",
            "authority_git_blob_sha": MISSION_AUTHORITY_SHA,
            "real_objective": MISSION_POINTER["real_objective"],
        },
        "claims": claims,
        "global_mission_completion_derivable": False,
        "accounting": {"terminal_credit_delta": 0},
    }


def check(doc, repo_root=None):
    return validate(
        doc,
        current_mission_pointer=MISSION_POINTER,
        current_mission_authority_blob_sha=MISSION_AUTHORITY_SHA,
        repo_root=repo_root,
    )


def git_blob_sha(path):
    payload = Path(path).read_bytes()
    return sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def test_empty_current_shape_is_valid_and_closes_nothing():
    out = check(registry([]))
    assert out["pass"] is True
    assert out["registered_claim_count"] == 0
    assert out["closed_claim_count"] == 0
    assert out["global_mission_completion_derivable"] is False


def test_open_claim_validates_but_r4_remains_open():
    b = binding()
    out = check(registry([open_claim(b)]))
    assert out["pass"] is True
    assert out["claims"][0]["r4_proof_closure"] is False
    assert find_exact_claim(out, b)["binding"] == b


def test_exact_claim_lookup_rejects_cross_claim_binding():
    b1 = binding()
    b2 = binding(claim_id="d" * 64)
    out = check(registry([open_claim(b1)]))
    assert find_exact_claim(out, b2) is None


def test_same_claim_id_cannot_appear_with_different_scope():
    b1 = binding()
    b2 = binding(scope_sha256="d" * 64)
    out = check(registry([open_claim(b1), open_claim(b2)]))
    assert out["pass"] is False
    assert any(x.startswith("DUPLICATE_CLAIM_ID:") for x in out["errors"])


def test_global_mission_completion_authority_is_forbidden():
    doc = registry([])
    doc["global_mission_completion_derivable"] = True
    out = check(doc)
    assert out["pass"] is False
    assert "GLOBAL_MISSION_COMPLETION_AUTHORITY_ENABLED" in out["errors"]


def test_closed_claim_requires_exact_content_addressed_files():
    b = binding()
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        slots = []
        for i, root_id in enumerate(ROOT_IDS):
            cert = root / f"cert{i}.json"
            verify = root / f"verify{i}.json"
            cert.write_text("{}", encoding="utf-8")
            verify.write_text("{}", encoding="utf-8")
            common = {
                "root_id": root_id,
                "claim_id": b["claim_id"],
                "mission_authority_blob_sha": MISSION_AUTHORITY_SHA,
            }
            slots.append({
                "root_id": root_id,
                "status": "PROVED_CURRENT",
                "certificate": {
                    **common,
                    "path": cert.name,
                    "git_blob_sha": git_blob_sha(cert),
                },
                "independent_verification": {
                    **common,
                    "path": verify.name,
                    "git_blob_sha": git_blob_sha(verify),
                },
            })
        doc = registry([{
            "binding": b,
            "certificate_slots": slots,
            "r4_proof_closure": True,
        }])
        out = check(doc, repo_root=root)
        assert out["pass"] is True
        assert out["closed_claim_count"] == 1
        assert find_exact_claim(out, b)["r4_proof_closure"] is True


def test_tampered_certificate_bytes_fail_closed():
    b = binding()
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        cert = root / "cert.json"
        verify = root / "verify.json"
        cert.write_text("{}", encoding="utf-8")
        verify.write_text("{}", encoding="utf-8")
        bad_sha = "0" * 40
        slots = []
        for root_id in ROOT_IDS:
            common = {
                "root_id": root_id,
                "claim_id": b["claim_id"],
                "mission_authority_blob_sha": MISSION_AUTHORITY_SHA,
            }
            slots.append({
                "root_id": root_id,
                "status": "PROVED_CURRENT",
                "certificate": {**common, "path": cert.name, "git_blob_sha": bad_sha},
                "independent_verification": {
                    **common,
                    "path": verify.name,
                    "git_blob_sha": git_blob_sha(verify),
                },
            })
        out = check(registry([{
            "binding": b,
            "certificate_slots": slots,
            "r4_proof_closure": True,
        }]), repo_root=root)
        assert out["pass"] is False
        assert any("CONTENT_ADDRESS_MISMATCH" in x for x in out["errors"])
