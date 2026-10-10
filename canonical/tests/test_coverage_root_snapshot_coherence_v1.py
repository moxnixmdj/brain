import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEOREM = ROOT / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json"
REGISTRY = ROOT / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"
MISSION = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
CURRENT = ROOT / "canonical/governance/CURRENT_COVERAGE_COMPLETENESS_ROOT_CERTIFICATES.json"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_root_theorem_snapshot_matches_live_registry_and_mission():
    theorem = load(THEOREM)
    registry = load(REGISTRY)
    current = load(CURRENT)

    assert theorem["mission_objective_binding"]["git_blob_sha"] == git_blob_sha(MISSION)
    authority = theorem["r4_canonical_certificate_authority"]
    assert authority["registry_git_blob_sha"] == git_blob_sha(REGISTRY)
    assert authority["current_proved"] == registry["currently_proved_root_certificates"]
    assert authority["current_open"] == registry["currently_open_root_certificates"]
    assert authority["current_r4_proof_closure"] is registry["r4_proof_closure"]
    assert authority["active_claim_id"] == registry["active_claim"]["claim_id"]

    assert current["registry"]["git_blob_sha"] == git_blob_sha(REGISTRY)
    assert current["claim_scope"]["mission_pointer_blob_sha"] == git_blob_sha(MISSION)
    assert current["proved"] == registry["currently_proved_root_certificates"]
    assert current["open"] == registry["currently_open_root_certificates"]
    assert current["r4_proof_closure"] is registry["r4_proof_closure"]
    assert current["active_claim"]["claim_id"] == registry["active_claim"]["claim_id"]


def test_property_scoped_closure_does_not_inflate_global_terminal_credit():
    theorem = load(THEOREM)
    registry = load(REGISTRY)
    current = load(CURRENT)

    assert theorem["theorem"]["current_terminal_success_asserted"] is False
    assert theorem["accounting"]["terminal_credit_delta"] == 0
    assert registry["accounting"]["terminal_credit_delta"] == 0
    assert current["terminal_credit_delta"] == 0
    assert "NO_GLOBAL_OPEN_ENDED_MISSION_COMPLETION" in current["scope_nonclaims"]
