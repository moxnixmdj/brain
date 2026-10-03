from pathlib import Path
from canonical.runtime import retrieval_live_provider_calibration_v1 as c

ROOT=Path(__file__).resolve().parents[2]
out=c.calibrate_repository(ROOT)
stats=out["route_query_family_stats"]

full=stats["GITHUB_CODE_SEARCH::BEHAVIORAL_FULL"]
assert full["transport_success_count"]==26
assert full["transport_failure_count"]==0
assert full["recall_trial_count"]==26
assert full["hit_at_10_count"]==0
assert full["hit_at_10_rate"]==0.0
assert abs(full["mean_latency_ms"]-4182.5)<1e-9
assert abs(full["median_latency_ms"]-1595.5)<1e-9

anchor=stats["GITHUB_CODE_SEARCH::TECHNICAL_ANCHOR_COMPRESSED"]
assert anchor["transport_success_count"]==13
assert anchor["recall_trial_count"]==13
assert anchor["hit_at_10_count"]==0
assert anchor["hit_at_10_rate"]==0.0
assert abs(anchor["mean_latency_ms"]-7835.923076923077)<1e-9
assert anchor["median_latency_ms"]==9403.0

web=stats["WEB_SEARCH_GITHUB_DOMAIN::DIRECT_BEHAVIORAL_Q1"]
assert web["transport_success_count"]==13
assert web["recall_trial_count"]==13
assert web["hit_at_10_count"]==2
assert abs(web["hit_at_10_rate"]-(2/13))<1e-12
assert web["mean_latency_ms"] is None
assert web["independently_reproducible_provider_truth"] is False

repo=stats["GITHUB_REPOSITORY_SEARCH_VIA_FETCH::BEHAVIORAL_FULL"]
assert repo["transport_success_count"]==0
assert repo["transport_failure_count"]==8
assert repo["recall_trial_count"]==0
assert repo["hit_at_10_rate"] is None

recs={x["route_query_family"]:x for x in out["routing_recommendations"]}
assert recs["GITHUB_CODE_SEARCH::BEHAVIORAL_FULL"]["action"]=="DEMOTE_AS_PRIMARY_UNKNOWN_IDENTITY_DISCOVERY_ROUTE"
assert recs["GITHUB_CODE_SEARCH::TECHNICAL_ANCHOR_COMPRESSED"]["action"]=="DEMOTE_AS_PRIMARY_UNKNOWN_IDENTITY_DISCOVERY_ROUTE"
assert recs["WEB_SEARCH_GITHUB_DOMAIN::DIRECT_BEHAVIORAL_Q1"]["action"]=="RETAIN_AS_CANDIDATE_GENERATOR"
assert recs["GITHUB_REPOSITORY_SEARCH_VIA_FETCH::BEHAVIORAL_FULL"]["action"]=="MARK_TRANSPORT_UNAVAILABLE_FOR_THIS_INTERFACE"

# Transport failure cannot poison recall.
toy=c.calibrate([
 {"case_id":"a","provider_route":"r","query_family":"q","transport_status":"SUCCESS","hit_at_10":True,"latency_ms":1,"observation_authority":"X"},
 {"case_id":"b","provider_route":"r","query_family":"q","transport_status":"FAILED","hit_at_10":False,"latency_ms":2,"observation_authority":"X"},
])
s=toy["route_query_family_stats"]["r::q"]
assert s["recall_trial_count"]==1 and s["hit_at_10_rate"]==1.0
assert s["transport_failure_count"]==1
assert s["nonexistence_claim_authorized"] is False

assert out["live_provider_calibration_complete"] is False
assert out["open_world_completeness_claim"] is False
print("test_retrieval_live_provider_calibration_v1: PASS")
