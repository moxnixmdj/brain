import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
CUT=ROOT/"canonical/governance/CURSORBENCH_SOURCE_COVERAGE_MINCUT_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_source_coverage_mincut_preserves_semantic_unknowns_and_zero_credit():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    c=json.loads(CUT.read_text(encoding="utf-8"))
    ref=a["authoritative_sources"]["cursorbench_source_coverage_mincut_20261009_v1"]
    assert blob(CUT)==ref["git_blob_sha"]
    d=c["deduction"]
    assert d["source_coverage_bundle_semantic_proof_object_count"]==2
    assert d["per_context_source_boundary_audit_count"]==1
    assert d["source_contract_structural_coverage_mechanism_available"] is True
    assert d["current_real_source_coverage_receipt_exists"] is False
    assert d["typed_semantics_atom_truth_proved"] is False
    assert d["failure_mode_completeness_atom_truth_proved"] is False
    assert len(d["remaining_semantic_objects"])==2
    live=a["live_truth"]
    assert live["cursorbench_source_coverage_semantic_proof_object_count"]==2
    assert live["cursorbench_source_coverage_per_context_source_boundary_audit_count"]==1
    assert live["cursorbench_source_coverage_real_receipt_bound"] is False
    assert live["cursorbench_typed_semantics_atom_truth_proved"] is False
    assert live["cursorbench_failure_mode_completeness_atom_truth_proved"] is False
    assert live["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
    rec=a["cursorbench_source_coverage_mincut_reconciliation_20261009_v1"]
    assert rec["atom_truth_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
