"""Brain-owned Retrieval V6 controller."""
from __future__ import annotations
from typing import Any,Mapping,Sequence
from canonical.runtime.evidence_omniretrieval_planner_v2 import ProofObligation,compile_channels
from canonical.runtime.retrieval_monotonic_candidate_ledger_v1 import empty_ledger,ingest
from canonical.runtime.retrieval_conditional_novelty_scheduler_v1 import rank_actions
SCHEMA="PROJECT_BRAIN_RETRIEVAL_OPEN_WORLD_CONTROLLER_V6"
def compile_plan(obligation:ProofObligation,actions:Sequence[Mapping[str,Any]])->dict[str,Any]:
 channels=compile_channels(obligation)
 if channels.get("status")!="COMPILED":
  return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":channels.get("reason") or "OMNIRETRIEVAL_PLAN_NOT_COMPILED","execution_authority":False,"promotion_authority":False,"acceptance_credit_delta":0}
 ranked=rank_actions(actions,{}) if actions else {"actions":[],"selected_action_id":None}
 return {"schema":SCHEMA,"status":"COMPILED__OPEN_WORLD_RECALL_HARDENED","obligation_id":obligation.obligation_id,"omniretrieval":channels,"candidate_ledger":empty_ledger(),"ranked_actions":ranked,"complete":False,"nonexistence_claim_authorized":False,"incremental_spend_usd":0,"acceptance_credit_delta":0,"execution_authority":False,"promotion_authority":False,"hard_rules":["EXTERNAL_SEARCH_ENGINES_ARE_CANDIDATE_GENERATORS_NOT_AUTHORITY","MONOTONIC_CANDIDATE_RETENTION","QUERYLESS_ENUMERATION_FOR_DECLARED_FINITE_ENUMERABLE_SCOPES","CONDITIONAL_NOVELTY_OUTRANKS_RAW_SOURCE_POPULARITY","NO_OPEN_WORLD_MISS_TO_NONEXISTENCE_INFERENCE"]}
def ingest_candidates(plan:Mapping[str,Any],candidates:Sequence[Mapping[str,Any]],*,epoch_id:str)->dict[str,Any]:
 if plan.get("schema")!=SCHEMA or not str(plan.get("status") or "").startswith("COMPILED"):raise ValueError("V6_COMPILED_PLAN_REQUIRED")
 out=dict(plan);out["candidate_ledger"]=ingest(plan["candidate_ledger"],candidates,epoch_id=epoch_id);return out
def rerank(plan:Mapping[str,Any],actions:Sequence[Mapping[str,Any]],observations:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
 out=dict(plan);out["ranked_actions"]=rank_actions(actions,observations);return out
