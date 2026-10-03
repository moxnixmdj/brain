from canonical.runtime import retrieval_live_event_ledger_v2 as ledger
from canonical.runtime import global_retrieval_controller_v3 as c

events=[
 {"episode_id":"e1","task_class":"RUST_PACKAGE","source_id":"CRATES","upstream_group":"CRATES_API","action_id":"e1:c","sequence":1,"status":"SUCCESS","candidate_ids":["crates:serde"],"verified_sufficient_candidate_ids":["crates:serde"],"independent_receipt":"r","latency_seconds":0.2,"request_count":1},
 {"episode_id":"e1","task_class":"RUST_PACKAGE","source_id":"GITHUB","upstream_group":"GITHUB_API","action_id":"e1:g","sequence":2,"status":"SUCCESS","candidate_ids":["github:serde-rs/serde"],"verified_sufficient_candidate_ids":["github:serde-rs/serde"],"independent_receipt":"r","latency_seconds":0.8,"request_count":1},
 {"episode_id":"e2","task_class":"MODEL_HUB","source_id":"HUGGINGFACE","upstream_group":"HF_API","action_id":"e2:h","sequence":1,"status":"SUCCESS","candidate_ids":["hf:google-bert/bert-base-uncased"],"verified_sufficient_candidate_ids":["hf:google-bert/bert-base-uncased"],"independent_receipt":"r","latency_seconds":0.1,"request_count":1},
 {"episode_id":"e2","task_class":"MODEL_HUB","source_id":"GITHUB","upstream_group":"GITHUB_API","action_id":"e2:g","sequence":2,"status":"SUCCESS","candidate_ids":[],"verified_sufficient_candidate_ids":[],"latency_seconds":0.7,"request_count":1},
]
cal=ledger.aggregate(events)
assert cal["event_count"]==4
assert cal["episode_count"]==2
assert cal["task_class_count"]==2
assert cal["task_class_source_stats"]["RUST_PACKAGE"]["CRATES"]["sufficient_witness_actions"]==1
assert cal["task_class_source_stats"]["MODEL_HUB"]["HUGGINGFACE"]["sufficient_witness_actions"]==1

actions=[
 {"action_id":"a-crates","source_id":"CRATES","upstream_group":"CRATES_API","task_class":"RUST_PACKAGE"},
 {"action_id":"a-github","source_id":"GITHUB","upstream_group":"GITHUB_API","task_class":"RUST_PACKAGE"},
]
ranked=c.rank_actions_contextual(actions,live_calibration=cal,default_task_class="RUST_PACKAGE")
assert ranked[0]["source_id"]=="CRATES"
assert ranked[0]["retrieval_priority_v3"]["calibration_basis"]=="TASK_CLASS_MEASURED"

model_actions=[
 {"action_id":"m-hf","source_id":"HUGGINGFACE","upstream_group":"HF_API","task_class":"MODEL_HUB"},
 {"action_id":"m-github","source_id":"GITHUB","upstream_group":"GITHUB_API","task_class":"MODEL_HUB"},
]
ranked=c.rank_actions_contextual(model_actions,live_calibration=cal,default_task_class="MODEL_HUB")
assert ranked[0]["source_id"]=="HUGGINGFACE"

cold=[{"action_id":"x","source_id":"UNKNOWN","upstream_group":"X","task_class":"NEW_CLASS"}]
ranked=c.rank_actions_contextual(cold,live_calibration=cal,default_task_class="NEW_CLASS")
assert ranked[0]["retrieval_priority_v3"]["calibration_basis"]=="JEFFREYS_COLD_START"

# Global fallback is allowed only when the task class lacks measured source data.
fallback=[{"action_id":"x","source_id":"CRATES","upstream_group":"CRATES_API","task_class":"NEW_CLASS"}]
ranked=c.rank_actions_contextual(fallback,live_calibration=cal,default_task_class="NEW_CLASS")
assert ranked[0]["retrieval_priority_v3"]["calibration_basis"]=="GLOBAL_FALLBACK_MEASURED"

try:
 ledger.aggregate([
  {"episode_id":"bad","task_class":"A","source_id":"S1","action_id":"a","status":"SUCCESS"},
  {"episode_id":"bad","task_class":"B","source_id":"S2","action_id":"b","status":"SUCCESS"},
 ])
 raise AssertionError("mixed task class episode accepted")
except ValueError as e:
 assert "EPISODE_TASK_CLASS_MISMATCH" in str(e)

print("test_retrieval_contextual_calibration_v10: PASS")
