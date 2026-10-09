import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
RED=ROOT/"canonical/governance/CODING_V5_WAL_SINGLETON_FINITE_CELL_REDUCTION_20261009_V1.json"

def test_v5_constructive_frontier():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    r=json.loads(RED.read_text(encoding="utf-8"))
    live=a["live_truth"]
    assert live["coding_v5_terminal_soundness_implies_constructive_all_members_adequacy"] is False
    assert live["coding_v5_completion_contract_alone_sufficient_for_formal_all_members_certificate"] is False
    assert live["coding_v5_formal_all_members_additional_constructive_liveness_premise_required"] is True
    assert live["coding_v5_wal_singleton_preexecution_cell_defined"] is True
    assert live["coding_v5_wal_singleton_cell_membership_complete"] is True
    assert live["coding_v5_wal_singleton_exact_v5_success_bound"] is True
    assert live["coding_v5_wal_singleton_target_relevance_to_cursorbench_proved"] is False
    assert r["deduction"]["finite_cell_completeness_for_this_exact_singleton"] is True
    assert r["deduction"]["target_relevance_to_cursorbench_ge_57_8_proved"] is False
    assert live["coding_v5_positive_adequacy_certificate_ready"] is False
    assert a["coding_v5_soundness_liveness_singleton_reconciliation_20261009_v1"]["terminal_credit_delta"]==0

if __name__=="__main__":
    test_v5_constructive_frontier()
    print("PASS 1/1")
