import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "canonical/governance/CURSORBENCH_V5_POLICY_VERSION_BOUNDARY_RECONCILIATION_20261009_V1.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def load(path: str):
    p = ROOT / path
    return json.loads(p.read_text(encoding="utf-8")), git_blob_sha(p)

def test_cursorbench_v5_version_boundary_is_exact_and_fail_closed():
    rec = json.loads(REC.read_text(encoding="utf-8"))
    assert rec["target_predicate"] == "CODING_CURSORBENCH_GE_57_8"
    assert rec["active_policy_version"] == "V5_COMPLETION_CONTRACT"
    assert rec["scope_state"].startswith("CLOSED_")

    current_cut, current_cut_sha = load(rec["sources"]["current_cursorbench_cut"]["path"])
    assert current_cut_sha == rec["sources"]["current_cursorbench_cut"]["git_blob_sha"]
    assert current_cut["cursorbench_4_0"]["scope_completeness"] == "CLOSED"
    assert current_cut["cursorbench_4_0"]["acceptance"] == "OPEN"

    policy, policy_sha = load(rec["sources"]["current_policy"]["path"])
    assert policy_sha == rec["sources"]["current_policy"]["git_blob_sha"]
    assert policy["capability_candidate_id"] == "ADVANCED_AGENTIC_SOFTWARE_ENGINEERING_MINI_SWE_SUPERPOWERS_V1"
    assert policy["evaluation"]["next_required_action"].startswith("EVALUATE_ADDITIONAL_DISTINCT_FRESH_TERMINAL_BENCH_4_TASKS")

    protocol, protocol_sha = load(rec["sources"]["evaluation_protocol"]["path"])
    assert protocol_sha == rec["sources"]["evaluation_protocol"]["git_blob_sha"]
    assert protocol["stage_1_progress"]["current_v5_verified_fresh_passes"] == 1
    assert protocol["stage_1_progress"]["benchmark_comparable_score_established"] is False

    for row in rec["sources"]["historical_failures"]:
        doc, sha = load(row["path"])
        assert sha == row["git_blob_sha"]
        assert row["exact_v5_identity_bound"] is False
        assert "FAIL" in str(doc.get("status") or doc.get("verdict") or "")

    wal_ref = rec["sources"]["exact_v5_positive_receipt"]
    wal, wal_sha = load(wal_ref["path"])
    assert wal_sha == wal_ref["git_blob_sha"]
    assert wal_ref["exact_v5_identity_bound"] is True
    assert wal["configured_route"] == wal_ref["configured_route"]
    assert "V5_COMPLETION_CONTRACT" in wal["configured_route"]
    assert wal["independent_verifier"]["reward"] == 1

    scope, scope_sha = load(rec["sources"]["scope_receipt"]["path"])
    assert scope_sha == rec["sources"]["scope_receipt"]["git_blob_sha"]
    assert scope["scope_complete"] is True
    assert scope["positive_adequacy_cover_closed"] is False

    d = rec["deduction"]
    assert d["historical_failure_receipts_falsify_exact_current_v5_common_policy"] is False
    assert d["exact_v5_positive_evidence_exists"] is True
    assert d["exact_v5_whole_cursorbench_adequacy_proved"] is False
    assert d["absence_of_bound_v5_failure_is_adequacy_proof"] is False
    assert d["one_v5_pass_is_scope_complete_adequacy_proof"] is False
    assert d["selector_work_authorized_now"] is False
    assert rec["accounting"]["acceptance_credit_delta"] == 0
    assert rec["accounting"]["terminal_credit_delta"] == 0
