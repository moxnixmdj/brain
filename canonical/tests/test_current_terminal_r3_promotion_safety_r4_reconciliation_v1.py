import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TERM=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REG=ROOT/"canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"
PTR=ROOT/"canonical/governance/CURRENT_COVERAGE_COMPLETENESS_ROOT_CERTIFICATES.json"
CLAIM=ROOT/"canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_R3_PROMOTION_SAFETY_20261010_V1.json"
MISSION=ROOT/"canonical/governance/CURRENT_MISSION_OBJECTIVE.json"

def blob(p):
    d=p.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(d)).encode("ascii")+b"\0"+d)
    return h.hexdigest()

def test_terminal_projection_binds_bounded_r4_without_global_credit():
    t=json.loads(TERM.read_text(encoding="utf-8"))
    r=json.loads(REG.read_text(encoding="utf-8"))
    src=t["authoritative_sources"]["current_claim_scoped_coverage_root_closure_20261010_v1"]
    assert blob(REG)==src["registry"]["git_blob_sha"]
    assert blob(PTR)==src["current_pointer"]["git_blob_sha"]
    assert blob(CLAIM)==src["active_claim"]["git_blob_sha"]
    assert blob(MISSION)==src["mission_pointer"]["git_blob_sha"]
    live=t["live_truth"]
    assert r["currently_proved_root_certificates"]==3
    assert r["currently_open_root_certificates"]==0
    assert r["r4_proof_closure"] is True
    assert live["coverage_claim_scoped_proved_root_count"]==3
    assert live["coverage_claim_scoped_open_root_count"]==0
    assert live["coverage_claim_scoped_r4_proof_closure"] is True
    assert live["r3_promotion_safety_property_root_chain_closed"] is True
    assert live["r3_promotion_safety_property_global_mission_completion"] is False
    assert live["r3_promotion_safety_property_opus_checkpoint_completion"] is False
    assert live["current_U_empty_proved"] is False
    assert live["independent_open_acceptance_obligations"]==13
    rec=t["r3_promotion_safety_claim_scoped_r4_reconciliation_20261010_v1"]
    assert rec["global_mission_completion"] is False
    assert rec["opus_checkpoint_completion"] is False
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
