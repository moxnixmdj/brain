"""P3 real-context admission v7.

Preserves every V6 positive route unchanged. If V6 fails closed and a
decision_dependency_contract is present, tries the independently verified exact
complete dependency-graph relevance cell. No authority escalation.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime.p3_real_context_v3_admission_v6 import evaluate as evaluate_v6
from canonical.runtime.p3_exact_dependency_relevance_cell_v1 import evaluate as evaluate_dependency

SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V7"

def _fail(reason:str)->dict[str,Any]:
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "p3_contract_cell_authorized":False,"source_authorization_verified":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0}

def evaluate(payload:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(payload,Mapping): return _fail("PAYLOAD_MAPPING_REQUIRED")
    prior=evaluate_v6(payload)
    if prior.get("pass") is True:
        out=dict(prior);out["schema"]=SCHEMA;out["v6_preserved_positive_route"]=True
        return out
    if isinstance(payload.get("decision_dependency_contract"),Mapping):
        root=Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
        dep=evaluate_dependency(payload,repo_root=root)
        if dep.get("pass") is True:
            if (
              dep.get("p3_contract_cell_authorized") is not True
              or dep.get("source_authorization_verified") is not False
              or dep.get("policy_adequacy_authority") is not False
              or dep.get("db_admission_authority") is not False
              or dep.get("u_subtraction_authority") is not False
              or dep.get("terminal_authority") is not False
              or dep.get("terminal_credit_delta") != 0
            ):
                return _fail("DEPENDENCY_RELEVANCE_AUTHORITY_BOUNDARY_INVALID")
            out=dict(dep);out["schema"]=SCHEMA
            out["status"]="PASS__P3_REAL_CONTEXT_EXACT_DEPENDENCY_RELEVANCE_FAST_PATH"
            out["route"]="EXACT_COMPLETE_DECISION_DEPENDENCY_RELEVANCE_CELL_V1"
            out["v6_preserved_positive_route"]=False
            return out
    out=dict(prior);out["schema"]=SCHEMA
    out["v6_preserved_positive_route"]=False
    out["dependency_relevance_fast_path_pass"]=False
    return out

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {},repo_root=root)
