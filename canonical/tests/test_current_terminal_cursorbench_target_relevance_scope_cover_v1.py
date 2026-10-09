import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
RED=ROOT/"canonical/governance/CURSORBENCH_TARGET_RELEVANCE_SCOPE_COVER_REDUCTION_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_non_target_singletons_cannot_be_promoted_by_analogy():
    a=json.loads(AUTH.read_text())
    r=json.loads(RED.read_text())
    ref=a["authoritative_sources"]["cursorbench_target_relevance_scope_cover_reduction_20261009_v1"]
    assert blob(RED)==ref["git_blob_sha"]
    assert r["deduction"]["wal_direct_cursorbench_finite_cell_transfer_rejected"] is True
    assert r["deduction"]["react_direct_cursorbench_finite_cell_transfer_rejected"] is True
    live=a["live_truth"]
    assert live["cursorbench_target_relevance_canonical_mechanism"]=="PROOF_CARRYING_SCOPE_COVER_V1"
    assert live["cursorbench_wal_direct_target_transfer_rejected"] is True
    assert live["cursorbench_react_lead_form_direct_target_transfer_rejected"] is True
    assert live["cursorbench_non_target_singleton_behavioral_analogy_sufficient_for_target_relevance"] is False
    assert live["cursorbench_target_relevance_requires_target_intersection_or_proved_scope_inclusion"] is True
    rec=a["cursorbench_target_relevance_scope_cover_reconciliation_20261009_v1"]
    assert rec["wal_target_coverage_delta"]==0
    assert rec["react_target_coverage_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
