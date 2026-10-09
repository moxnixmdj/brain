import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "canonical/evidence/CURSORBENCH_4_0_OWNER_AND_RESULT_ARTIFACT_AUTHORITY_EVIDENCE_20261009_V1.json"
R = ROOT / "canonical/governance/CURSORBENCH_4_0_OWNER_MEMBERSHIP_AND_RESULT_ARTIFACT_REDUCTION_20261009_V1.json"

def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()

def test_owner_authority_reduction_localizes_without_overclaiming():
    e = json.loads(E.read_text())
    r = json.loads(R.read_text())
    assert e["deduction"]["concrete_cursor_4_0_result_artifact_family_exists"] is True
    assert e["deduction"]["artifact_publicly_retrieved_by_brain"] is False
    assert e["deduction"]["route_a_threshold_lower_bound_ready"] is False
    assert e["deduction"]["five_region_target_membership_closed"] is False
    assert r["stable_basis"]["owner_and_result_artifact_evidence"]["path"] == str(E.relative_to(ROOT))
    assert r["route_a_reduction"]["direct_cursor_result_artifact_family_exists"] is True
    assert r["route_a_reduction"]["result_artifact_publicly_retrieved"] is False
    assert r["route_a_reduction"]["remaining_scoring_object_count"] == 2
    assert len(r["route_a_reduction"]["remaining_scoring_objects"]) == 2
    assert r["route_a_reduction"]["threshold_lower_bound_ready"] is False
    assert len(r["five_existing_regions"]) == 5
    assert all(
        row["public_target_membership_entailment"] is False
        for row in r["five_existing_regions"].values()
    )
    assert r["membership_reduction"]["public_owner_category_evidence_proves_region_nonmembership"] is False
    assert r["membership_reduction"]["private_cursorbench_membership_delta"] == 0
    assert r["accounting"]["acceptance_credit_delta"] == 0
    assert r["accounting"]["terminal_credit_delta"] == 0
    assert r["scheduling_authority"] is True
    assert r["promotion_authority"] is False
    assert r["terminal_authority"] is False
