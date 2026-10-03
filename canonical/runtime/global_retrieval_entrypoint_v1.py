#!/usr/bin/env python3
"""Single mechanically authorized entrypoint for Brain retrieval planning."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v1 as controller

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V1"

def compile_authorized_plan(
 *,
 root:Path,
 query_actions:Sequence[Mapping[str,Any]],
 sources:Sequence[Mapping[str,Any]],
 source_stats:Mapping[str,Mapping[str,Any]]|None=None,
 state:Mapping[str,Any]|None=None,
)->dict[str,Any]:
 gate=guard.evaluate_repository(root)
 if gate.get("pass") is not True:
  return {
   "schema":SCHEMA,"status":"FAIL_CLOSED__GLOBAL_RETRIEVAL_AUTHORITY_INVALID",
   "authority_gate":gate,"plan":None,
   "execution_authority":False,"promotion_authority":False,
   "acceptance_credit_delta":0,"family_credit_delta":0,
   "capability_credit_delta":0,"ownership_credit_delta":0,
  }
 plan=controller.compile_global_plan(
  query_actions=query_actions,sources=sources,source_stats=source_stats or {},
  state=state or controller.new_state(),
 )
 return {
  "schema":SCHEMA,
  "status":"PASS__AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILED",
  "authority_gate":gate,
  "plan":plan,
  "execution_authority":False,"promotion_authority":False,
  "acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
  "incremental_spend_usd":0,
  "hard_rules":[
   "NO_PLAN_COMPILATION_IF_CURRENT_GLOBAL_RETRIEVAL_AUTHORITY_FAILS",
   "PLAN_ACTIONS_REMAIN_CANDIDATE_DISCOVERY_ONLY",
   "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
  ],
 }

def main()->int:
 root=Path(__file__).resolve().parents[2]
 out=compile_authorized_plan(root=root,query_actions=[],sources=[])
 print(json.dumps(out,indent=2,sort_keys=True))
 return 0 if out.get("status","").startswith("PASS") else 1
if __name__=="__main__":raise SystemExit(main())
