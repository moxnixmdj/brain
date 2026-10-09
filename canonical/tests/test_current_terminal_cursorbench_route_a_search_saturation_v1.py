import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
SAT=ROOT/"canonical/governance/CURSORBENCH_ROUTE_A_PUBLIC_OWNER_SEARCH_SATURATION_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_bounded_owner_search_saturation_routes_without_credit_or_nonexistence_claim():
    a=json.loads(AUTH.read_text(encoding="utf-8"))
    s=json.loads(SAT.read_text(encoding="utf-8"))
    ref=a["authoritative_sources"]["cursorbench_route_a_public_owner_search_saturation_20261009_v1"]
    assert blob(SAT)==ref["git_blob_sha"]
    assert len(s["exact_remaining_route_a_objects"])==2
    assert s["bounded_search"]["claim_scope"].startswith("ONLY_THE_LISTED")
    assert "NO_GLOBAL_CLAIM_THE_SCORER_SEMANTICS_DO_NOT_EXIST_ANYWHERE" in s["hard_nonclaims"]
    live=a["live_truth"]
    assert live["cursorbench_route_a_current_public_owner_search_saturated"] is True
    assert live["cursorbench_route_a_current_static_public_source_state"]=="DORMANT_UNTIL_SOURCE_DELTA"
    assert live["cursorbench_current_active_lane"]=="ROUTE_B_SCOPE_COMPLETE_STRONGER_PROOF"
    assert live["cursorbench_threshold_lower_bound_route_remaining_blocker_count"]==2
    assert live["cursorbench_remaining_typed_acceptance_mechanism_gap_count"]==0
    assert live["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
    rec=a["cursorbench_route_a_public_owner_search_saturation_reconciliation_20261009_v1"]
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
