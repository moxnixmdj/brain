#!/usr/bin/env python3
"""Authorized context-conditioned empirical retrieval entrypoint V3."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping,Sequence
from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v3 as controller
from canonical.runtime import retrieval_live_event_ledger_v2 as ledger
from canonical.runtime import global_retrieval_controller_v1 as state_base
SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V3"

def compile_authorized_plan(*,root:Path,query_actions:Sequence[Mapping[str,Any]],sources:Sequence[Mapping[str,Any]],task_class:str,state:Mapping[str,Any]|None=None,live_events:Sequence[Mapping[str,Any]]|None=None)->dict[str,Any]:
 gate=guard.evaluate_repository(root)
 if gate.get("pass") is not True:
  return {"schema":SCHEMA,"status":"FAIL_CLOSED__GLOBAL_RETRIEVAL_AUTHORITY_INVALID","authority_gate":gate,"plan":None,"execution_authority":False,"promotion_authority":False,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
 if live_events is None:
  live_events=ledger.load_jsonl(root/"canonical/state/retrieval_live_events_v2.jsonl")
 calibrated=ledger.aggregate(live_events)
 plan=controller.compile_global_plan(query_actions=query_actions,sources=sources,live_calibration=calibrated,state=state or state_base.new_state(),task_class=task_class)
 return {"schema":SCHEMA,"status":"PASS__AUTHORIZED_CONTEXT_CONDITIONED_EMPIRICAL_RETRIEVAL_PLAN_COMPILED","authority_gate":gate,
  "live_calibration":{"event_count":calibrated["event_count"],"episode_count":calibrated["episode_count"],"task_class_count":calibrated["task_class_count"],"source_stats":calibrated["source_stats"],"task_class_source_stats":calibrated["task_class_source_stats"]},
  "plan":plan,"execution_authority":False,"promotion_authority":False,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"incremental_spend_usd":0,
  "hard_rules":["AUTHORITY_GUARD_MUST_PASS_BEFORE_PLAN_COMPILATION","TASK_CLASS_CONDITIONED_LIVE_EVENTS_CALIBRATE_ROUTING","FINITE_ARENAS_ARE_NOT_USED_AS_LIVE_PROVIDER_ORACLES","OPEN_WORLD_MISS_REMAINS_UNKNOWN"]}
if __name__=="__main__":
 root=Path(__file__).resolve().parents[2]
 print(json.dumps(compile_authorized_plan(root=root,query_actions=[],sources=[],task_class="UNCLASSIFIED"),indent=2,sort_keys=True))
