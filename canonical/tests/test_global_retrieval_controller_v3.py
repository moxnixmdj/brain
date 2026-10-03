from pathlib import Path
from canonical.runtime import retrieval_live_event_ledger_v1 as ledger
from canonical.runtime import retrieval_live_provider_calibration_v1 as labeled
from canonical.runtime import global_retrieval_controller_v3 as v3
from canonical.runtime import global_retrieval_entrypoint_v3 as entry

ROOT=Path(__file__).resolve().parents[2]
live=ledger.aggregate(ledger.load_jsonl(ROOT/"canonical/state/retrieval_live_events_v1.jsonl"))
lab=labeled.calibrate_repository(ROOT)

actions=[
 {"action_id":"full","source_id":"GITHUB_CODE_SURFACE","upstream_group":"GITHUB_PUBLIC_INDEX_AND_API","provider_route":"GITHUB_CODE_SEARCH","query_family":"BEHAVIORAL_FULL"},
 {"action_id":"anchor","source_id":"GITHUB_CODE_SURFACE","upstream_group":"GITHUB_PUBLIC_INDEX_AND_API","provider_route":"GITHUB_CODE_SEARCH","query_family":"TECHNICAL_ANCHOR_COMPRESSED"},
 {"action_id":"web","source_id":"WEB_SEARCH","upstream_group":"WEB_INDEX","provider_route":"WEB_SEARCH_GITHUB_DOMAIN","query_family":"DIRECT_BEHAVIORAL_Q1"},
 {"action_id":"new","source_id":"NEW_ROUTE","upstream_group":"INDEPENDENT_NEW_INDEX","provider_route":"NEW_ROUTE","query_family":"NEW_FAMILY"},
]
ranked=v3.rank_actions_dual_empirical(
 actions,
 source_stats=live["source_stats"],
 labeled_stats=lab["route_query_family_stats"],
)
by={x["action_id"]:x for x in ranked}
assert by["full"]["retrieval_priority_v3"]["labeled_recovery_trials"]==26
assert by["anchor"]["retrieval_priority_v3"]["labeled_recovery_trials"]==13
assert by["web"]["retrieval_priority_v3"]["labeled_recovery_trials"]==13
assert by["new"]["retrieval_priority_v3"]["labeled_recovery_trials"]==0
assert by["full"]["retrieval_priority_v3"]["hard_disable"] is False
assert by["anchor"]["retrieval_priority_v3"]["hard_disable"] is False
assert by["new"]["retrieval_priority_v3"]["cold_start_prior"]=="JEFFREYS_BETA_0_5_0_5"

scores={x["action_id"]:x["retrieval_priority_v3"]["dual_empirical_score"] for x in ranked}
assert scores["new"] > scores["web"] > scores["anchor"] > scores["full"], scores

plan=v3.compile_global_plan(
 query_actions=actions,
 sources=[
  {"source_id":"GITHUB_CODE_SURFACE","upstream_group":"GITHUB_PUBLIC_INDEX_AND_API","bounded_scope":False},
  {"source_id":"WEB_SEARCH","upstream_group":"WEB_INDEX","bounded_scope":False},
  {"source_id":"NEW_ROUTE","upstream_group":"INDEPENDENT_NEW_INDEX","bounded_scope":False},
 ],
 live_calibration=live,
 labeled_calibration=lab,
)
assert plan["status"]=="COMPILED_DUAL_EMPIRICALLY_CALIBRATED_GLOBAL_RETRIEVAL_PLAN"
assert plan["labeled_route_query_family_count"]>=4
assert plan["open_world_nonexistence_claim_authorized"] is False
assert plan["fixed_correlation_multiplier_used"] is False
assert plan["fixed_source_independence_multiplier_used"] is False

ep=entry.compile_authorized_plan(root=ROOT,query_actions=actions,sources=[])
assert ep["status"]=="PASS__AUTHORIZED_DUAL_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED"
assert ep["authority_gate"]["pass"] is True
assert ep["labeled_provider_calibration"]["live_provider_calibration_complete"] is False
assert ep["execution_authority"] is False
assert ep["promotion_authority"] is False

print("test_global_retrieval_controller_v3: PASS")
