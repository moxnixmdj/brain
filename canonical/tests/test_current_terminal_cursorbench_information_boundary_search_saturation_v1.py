import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
SAT=ROOT/"canonical/governance/CURSORBENCH_4_0_INFORMATION_BOUNDARY_PUBLIC_SEARCH_SATURATION_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_boundary_search_saturation_preserves_open_fact_and_zero_credit():
    a=json.loads(AUTH.read_text())
    s=json.loads(SAT.read_text())
    ref=a["authoritative_sources"]["cursorbench_4_0_information_boundary_public_search_saturation_20261009_v1"]
    assert blob(SAT)==ref["git_blob_sha"]
    assert s["observed"]["explicit_current_4_0_boundary_continuity_bound"] is False
    live=a["live_truth"]
    assert live["cursorbench_preverifier_information_boundary_public_search_saturated"] is True
    assert live["cursorbench_preverifier_information_boundary_external_protocol_unknown_count"]==1
    assert live["cursorbench_preverifier_information_boundary_owner_fact_state"]=="OPEN_DORMANT_UNTIL_OWNER_SOURCE_DELTA"
    assert live["cursorbench_public_exact_4_0_task_member_found"] is False
    rec=a["cursorbench_information_boundary_public_search_saturation_reconciliation_20261009_v1"]
    assert rec["atom_truth_delta"]==0
    assert rec["cursorbench_membership_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
