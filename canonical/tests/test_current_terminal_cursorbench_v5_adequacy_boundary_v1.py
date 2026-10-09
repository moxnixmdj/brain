import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC = ROOT / "canonical/governance/CURSORBENCH_V5_POLICY_VERSION_BOUNDARY_RECONCILIATION_20261009_V1.json"
VERIFY = ROOT / "canonical/verification/CURSORBENCH_V5_POLICY_VERSION_BOUNDARY_INDEPENDENT_VERIFICATION_20261009_V1.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def test_current_terminal_authority_binds_cursorbench_v5_version_truth_only():
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    rec = json.loads(REC.read_text(encoding="utf-8"))
    verify = json.loads(VERIFY.read_text(encoding="utf-8"))

    src = auth["authoritative_sources"]["cursorbench_v5_policy_version_boundary_20261009_v1"]
    assert git_blob_sha(REC) == src["git_blob_sha"] == "90e3a91b650579a900a5a93bec4bcaa586fdf785"
    assert git_blob_sha(VERIFY) == src["independent_verification"]["git_blob_sha"] == "81dd440f5d5afdfe60a4194d882189abc88f1ecd"
    assert verify["result"]["tests_passed"] == 1
    assert verify["result"]["tests_failed"] == 0

    live = auth["live_truth"]
    assert live["cursorbench_scope_completeness_proved"] is True
    assert live["cursorbench_positive_adequacy_cover_closed"] is False
    assert live["cursorbench_dominance_closed"] is False
    assert live["cursorbench_v5_common_policy_branch_state"] == "UNREFUTED_BY_BOUND_HISTORICAL_FAILURE_RECEIPTS__UNPROVED"
    assert live["cursorbench_bound_historical_failures_are_exact_v5_counterexamples"] is False
    assert live["cursorbench_exact_v5_positive_task_count"] == 1
    assert live["cursorbench_absence_of_bound_v5_failure_is_adequacy_proof"] is False
    assert live["cursorbench_one_v5_pass_is_scope_complete_adequacy_proof"] is False
    assert live["cursorbench_selector_work_authorized_now"] is False
    assert live["cursorbench_next_proof_object"] == "CURSORBENCH_V5_TARGET_RELEVANT_POLICY_ADEQUACY_REGION_V1"

    assert rec["deduction"]["exact_v5_whole_cursorbench_adequacy_proved"] is False
    assert rec["accounting"]["acceptance_credit_delta"] == 0
    assert rec["accounting"]["terminal_credit_delta"] == 0
    assert auth["pointer_revision"] == 70
