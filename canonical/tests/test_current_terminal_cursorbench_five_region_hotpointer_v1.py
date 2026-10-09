import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
V4=ROOT/"canonical/governance/CODING_SHARED_SPECIFICATION_COVERAGE_ONLY_SUCCESSOR_20261009_V4.json"
COMP=ROOT/"canonical/governance/CURSORBENCH_FIVE_REGION_COMPLEMENT_NONIDENTIFIABILITY_20261009_V1.json"
VER=ROOT/"canonical/verification/CURSORBENCH_FIVE_REGION_COMPLEMENT_NONIDENTIFIABILITY_INDEPENDENT_VERIFICATION_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_hotpointer_reconciles_five_region_frontier_without_target_membership_credit():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    src=a["authoritative_sources"]["cursorbench_five_region_frontier_20261009_v1"]
    assert blob(V4)==src["projection"]["git_blob_sha"]
    assert blob(COMP)==src["complement"]["git_blob_sha"]
    assert blob(VER)==src["independent_verification"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["cursorbench_current_constructive_region_union_count"]==5
    assert live["cursorbench_current_constructive_region_union_distinct_condition_atom_count"]==34
    assert live["cursorbench_five_region_complement_nonidentifiability_proved"] is True
    assert live["cursorbench_current_static_evidence_identifies_five_region_complement_emptiness"] is False
    assert live["cursorbench_actual_five_region_complement_empty_claimed"] is False
    assert live["cursorbench_actual_five_region_complement_nonempty_claimed"] is False
    assert live["cursorbench_five_region_private_membership_proved"] is False
    assert live["cursorbench_five_region_whole_positive_cover_proved"] is False
    rec=a["cursorbench_five_region_hotpointer_reconciliation_20261009_v1"]
    assert rec["prior_constructive_region_count"]==3
    assert rec["current_constructive_region_count"]==5
    assert rec["prior_distinct_condition_atom_count"]==18
    assert rec["current_distinct_condition_atom_count"]==34
    assert rec["private_cursorbench_membership_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
