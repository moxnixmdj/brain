from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path

from canonical.runtime.coverage_claim_scope_guard_v1 import validate_claim
from canonical.runtime.coverage_root_certificate_registry_guard_v1 import validate as validate_registry

ROOT = Path(__file__).resolve().parents[2]
CLAIM_PATH = ROOT / "canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_R3_PROMOTION_SAFETY_20261010_V1.json"
REGISTRY_PATH = ROOT / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"
MISSION_PATH = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
MISSION_AUTHORITY_PATH = ROOT / "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def test_active_r3_promotion_safety_claim_is_exact_and_zero_credit():
    claim = json.loads(CLAIM_PATH.read_text(encoding="utf-8"))
    checked = validate_claim(claim, current_mission_blob_sha=_git_blob_sha(MISSION_PATH))
    assert checked["pass"], checked
    assert checked["claim_id"] == "e1c519109c4b2c46a9225686fc2c5c5490564d1cc62d5c6ff3c6c436bfca4314"
    assert checked["global_mission_completion_derivable"] is False
    assert checked["terminal_credit_delta"] == 0


def test_registry_accepts_frozen_claim_but_keeps_all_roots_open():
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    mission = json.loads(MISSION_PATH.read_text(encoding="utf-8"))
    checked = validate_registry(
        registry,
        current_mission_pointer=mission,
        current_mission_authority_blob_sha=_git_blob_sha(MISSION_AUTHORITY_PATH),
        current_mission_pointer_blob_sha=_git_blob_sha(MISSION_PATH),
    )
    assert checked["pass"], checked
    assert checked["proved_root_ids"] == []
    assert sorted(checked["open_root_ids"]) == sorted([
        "CC_R1_REALITY_CONTAINMENT_V1",
        "CC_R2_MISSION_SOUNDNESS_V1",
        "CC_R3_TERMINAL_CLOSURE_V1",
    ])
    assert checked["r4_proof_closure"] is False
    assert checked["terminal_credit_delta"] == 0
    assert registry["active_claim"]["claim_id"] == "e1c519109c4b2c46a9225686fc2c5c5490564d1cc62d5c6ff3c6c436bfca4314"
