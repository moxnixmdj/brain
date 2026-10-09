import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
CUT=ROOT/"canonical/governance/CURSORBENCH_PREVERIFIER_INFORMATION_BOUNDARY_MINCUT_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_information_boundary_bundle_is_reduced_without_atom_credit():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    c=json.loads(CUT.read_text(encoding="utf-8"))
    ref=a["authoritative_sources"]["cursorbench_preverifier_information_boundary_mincut_20261009_v1"]
    assert blob(CUT)==ref["git_blob_sha"]
    d=c["deduction"]
    assert d["published_family_protocol_supports_post_rollout_grading_boundary"] is True
    assert d["post_4_0_current_production_harness_context_bound"] is True
    assert d["current_4_0_benchmark_to_same_information_boundary_continuity_explicitly_bound"] is False
    assert d["no_hidden_verifier_atom_truth_proved"] is False
    assert d["external_protocol_unknown_count"]==1
    assert d["per_model_internal_audit_is_not_an_external_benchmark_fact"] is True
    live=a["live_truth"]
    assert live["cursorbench_preverifier_information_boundary_external_protocol_unknown_count"]==1
    assert live["cursorbench_preverifier_information_boundary_per_model_internal_audit_required"] is True
    assert live["cursorbench_no_hidden_verifier_access_atom_truth_proved"] is False
    assert live["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
    rec=a["cursorbench_preverifier_information_boundary_mincut_reconciliation_20261009_v1"]
    assert rec["atom_truth_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
