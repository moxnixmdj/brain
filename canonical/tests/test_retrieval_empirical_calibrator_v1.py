from canonical.runtime import retrieval_empirical_calibrator_v1 as c
from canonical.runtime import global_retrieval_controller_v1 as g

obs=[
 {"action_id":"a1","source_id":"engine_a","upstream_group":"web","latency_seconds":1.0,"request_count":1,"failed":False,"candidate_ids":["x","y"],"verified_sufficient_candidate_ids":[]},
 {"action_id":"a2","source_id":"engine_b","upstream_group":"web","latency_seconds":1.1,"request_count":1,"failed":False,"candidate_ids":["x","y"],"verified_sufficient_candidate_ids":[]},
 {"action_id":"a3","source_id":"registry","upstream_group":"registry","latency_seconds":0.2,"request_count":1,"failed":False,"candidate_ids":["z"],"verified_sufficient_candidate_ids":["z"]},
 {"action_id":"a4","source_id":"flaky","upstream_group":"other","latency_seconds":2.0,"request_count":2,"failed":True,"candidate_ids":["ghost"],"verified_sufficient_candidate_ids":[]},
]
out=c.calibrate(obs)
assert out["status"]=="CALIBRATED"
assert out["uses_empirical_conditional_novelty"] is True
assert out["uses_fixed_source_quality_constants"] is False
assert out["unique_candidate_count"]==3
s=out["source_stats"]
assert s["registry"]["sufficient_witness_actions"]==1
assert s["engine_b"]["conditional_novel_candidate_fraction"]==0.0
assert s["flaky"]["failures"]==1
pairs={(x["source_a"],x["source_b"]):x["jaccard_candidate_overlap"] for x in out["pairwise_source_overlap"]}
assert pairs[("engine_a","engine_b")]==1.0

stats=c.controller_stats(out)
actions=[
 {"action_id":"qa","source_id":"engine_a","upstream_group":"web"},
 {"action_id":"qr","source_id":"registry","upstream_group":"registry"},
 {"action_id":"qf","source_id":"flaky","upstream_group":"other"},
]
ranked=g.rank_actions(actions,stats,consumed_upstream_groups=["web"])
assert ranked[0]["source_id"]=="registry", ranked
assert ranked[-1]["source_id"] in {"engine_a","flaky"}
print("test_retrieval_empirical_calibrator_v1: PASS")
