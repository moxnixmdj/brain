from pathlib import Path
from canonical.runtime import retrieval_route_strategy_calibration_v2 as cal
from canonical.runtime import global_retrieval_controller_v3 as c
from canonical.runtime import global_retrieval_entrypoint_v3 as e

ROOT=Path(__file__).resolve().parents[2]
live=cal.calibrate_repository(ROOT)

actions=[
 {"action_id":"g_raw","source_id":"GITHUB_REPOSITORY_SEARCH","provider_route":"GITHUB_REPOSITORY_SEARCH","strategy_id":"RAW_BEHAVIOR_V1","query":"x"},
 {"action_id":"g_anchor","source_id":"GITHUB_REPOSITORY_SEARCH","provider_route":"GITHUB_REPOSITORY_SEARCH","strategy_id":"ANCHOR_COMPRESSED_V2","query":"x"},
 {"action_id":"hf_raw","source_id":"HUGGINGFACE_MODEL_SEARCH","provider_route":"HUGGINGFACE_MODEL_SEARCH","strategy_id":"RAW_BEHAVIOR_V1","query":"x"},
 {"action_id":"hf_enum","source_id":"HUGGINGFACE_MODEL_PIPELINE_ENUM","provider_route":"HUGGINGFACE_MODEL_PIPELINE_ENUM","strategy_id":"PROVIDER_NATIVE_ENUM_V2","query":"x"},
]
ranked=c.rank_actions(actions,calibration=live)
order=[x["action_id"] for x in ranked]
assert order.index("g_anchor") < order.index("g_raw"), order
assert order.index("hf_enum") < order.index("hf_raw"), order
assert all("retrieval_priority_v3" in x for x in ranked)

plan=e.compile_authorized_plan(root=ROOT,query_actions=actions,sources=[])
assert plan["status"]=="PASS__AUTHORIZED_ROUTE_STRATEGY_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED",plan
assert plan["plan"]["provider_only_calibration_forbidden"] is True
assert plan["route_strategy_calibration"]["best_known_strategy_union"]["hit_case_count"]==13
assert plan["route_strategy_calibration"]["best_known_strategy_union"]["hit_rate"]==1.0
assert plan["route_strategy_calibration"]["best_known_strategy_union"]["miss_case_ids"]==[]
assert plan["execution_authority"] is False
assert plan["promotion_authority"] is False

print("test_global_retrieval_controller_v3: PASS",order)
