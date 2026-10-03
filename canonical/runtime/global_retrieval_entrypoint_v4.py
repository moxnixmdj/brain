#!/usr/bin/env python3
"""Authorized entity-resolved contextual empirical retrieval entrypoint V4."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping,Sequence
from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v3 as controller
from canonical.runtime import retrieval_live_event_ledger_v3 as ledger
from canonical.runtime import global_retrieval_controller_v1 as state_base
SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V4"
def compile_authorized_plan(*,root:Path,query_actions:Sequence[Mapping[str,Any]],sources:Sequence[Mapping[str,Any]],task_class:str,state:Mapping[str,Any]|None=None,live_events:Sequence[Mapping[str,Any]]|None=None)->dict[str,Any]:
 gate=guard.evaluate_repository(root)
 if gate.get("pass") is not True:
  return {"schema":SCHEMA,"status":"FAIL_CLOSED__GLOBAL_RETRIEVAL_AUTHORITY_INVALID","authority_gate":gate,"plan":None,"execution_authority":False,"promotion_authority":False,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
 if live_events is None:live_events=ledger.load_jsonl(root/"canonical/state/retrieval_live_events_v3.jsonl")
 cal=ledger.aggregate(live_events)
 plan=controller.compile_global_plan(query_actions=query_actions,sources=sources,live_calibration=cal,state=state or state_base.new_state(),task_class=task_class)
 return {"schema":SCHEMA,"status":"PASS__AUTHORIZED_ENTITY_RESOLVED_CONTEXTUAL_EMPIRICAL_RETRIEVAL_PLAN_COMPILED","authority_gate":gate,
  "live_calibration":{"event_count":cal["event_count"],"episode_count":cal["episode_count"],"task_class_count":cal["task_class_count"],"source_stats":cal["source_stats"],"task_class_source_stats":cal["task_class_source_stats"],"pairwise_candidate_overlap":cal["pairwise_candidate_overlap"]},
  "plan":plan,"execution_authority":False,"promotion_authority":False,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"incremental_spend_usd":0,
  "hard_rules":["AUTHORITY_GUARD_MUST_PASS_BEFORE_PLAN_COMPILATION","ENTITY_RESOLVED_LIVE_EVENTS_CALIBRATE_NOVELTY_AND_SOURCE_OVERLAP","TASK_CLASS_CONDITIONED_EVENTS_CALIBRATE_ROUTING","UNMAPPED_CANDIDATES_REMAIN_SOURCE_SCOPED","FINITE_ARENAS_ARE_NOT_LIVE_PROVIDER_ORACLES","OPEN_WORLD_MISS_REMAINS_UNKNOWN"]}
if __name__=="__main__":
 root=Path(__file__).resolve().parents[2]
 print(json.dumps(compile_authorized_plan(root=root,query_actions=[],sources=[],task_class="UNCLASSIFIED"),indent=2,sort_keys=True))
