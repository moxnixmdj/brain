from pathlib import Path
from canonical.runtime import retrieval_live_event_ledger_v3 as ledger
from canonical.runtime import global_retrieval_controller_v3 as controller
from canonical.runtime import global_retrieval_entrypoint_v4 as entry
from canonical.runtime import retrieval_live_provider_epoch_v3 as epoch

ROOT=Path(__file__).resolve().parents[2]
events=[
 {"episode_id":"same","task_class":"PKG","source_id":"A","upstream_group":"A_API","action_id":"a","sequence":1,"status":"SUCCESS","candidate_ids":["a:x"],"candidate_entities":{"a:x":"entity:x"},"verified_sufficient_candidate_ids":["a:x"],"independent_receipt":"r","latency_seconds":0.2,"request_count":1},
 {"episode_id":"same","task_class":"PKG","source_id":"B","upstream_group":"B_API","action_id":"b","sequence":2,"status":"SUCCESS","candidate_ids":["b:x"],"candidate_entities":{"b:x":"entity:x"},"verified_sufficient_candidate_ids":["b:x"],"independent_receipt":"r","latency_seconds":0.3,"request_count":1},
 {"episode_id":"new","task_class":"MODEL","source_id":"B","upstream_group":"B_API","action_id":"c","sequence":1,"status":"SUCCESS","candidate_ids":["b:y"],"candidate_entities":{},"verified_sufficient_candidate_ids":[],"latency_seconds":0.3,"request_count":1},
]
cal=ledger.aggregate(events)
same=[x for x in cal["events"] if x["episode_id"]=="same"]
assert same[0]["novel_candidate_action"] is True
assert same[1]["novel_candidate_action"] is False
pair=next(x for x in cal["pairwise_candidate_overlap"] if {x["source_a"],x["source_b"]}=={"A","B"})
assert pair["candidate_entity_jaccard"]==1.0
assert cal["task_class_source_stats"]["PKG"]["B"]["novel_candidate_actions"]==0

actions=[
 {"action_id":"pa","source_id":"A","upstream_group":"A_API","task_class":"PKG"},
 {"action_id":"pb","source_id":"B","upstream_group":"B_API","task_class":"PKG"},
]
ranked=controller.rank_actions_contextual(actions,live_calibration=cal,default_task_class="PKG")
assert all(x["retrieval_priority_v3"]["calibration_basis"]=="TASK_CLASS_MEASURED" for x in ranked)

out=entry.compile_authorized_plan(root=ROOT,query_actions=actions,sources=[],task_class="PKG",live_events=events)
assert out["status"].startswith("PASS__AUTHORIZED_ENTITY_RESOLVED")
assert out["live_calibration"]["event_count"]==3

# Corrected live runner must never use title-only scholarly sufficiency.
assert all("target_title" not in x for x in epoch.EPISODES)
att=next(x for x in epoch.EPISODES if x["episode_id"]=="V10_ATTENTION")
res=next(x for x in epoch.EPISODES if x["episode_id"]=="V10_RESNET")
assert att["targets"]["OPENALEX"]=={"openalex:w2626778328"}
assert res["targets"]["CROSSREF"]=={"doi:10.1109/cvpr.2016.90"}
assert res["entities"]["openalex:w2194775991"]==res["entities"]["doi:10.1109/cvpr.2016.90"]

try:
 ledger.aggregate([
  {"episode_id":"bad","task_class":"A","source_id":"X","action_id":"1","status":"SUCCESS"},
  {"episode_id":"bad","task_class":"B","source_id":"Y","action_id":"2","status":"SUCCESS"},
 ])
 raise AssertionError("mixed task classes accepted")
except ValueError as e:
 assert "EPISODE_TASK_CLASS_MISMATCH" in str(e)

print("test_retrieval_entity_resolved_contextual_v10: PASS")
