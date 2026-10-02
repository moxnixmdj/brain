"""Route-specific reconciliation for deleting delegation's weaker exact-Opus comparator.

This combines the independently verified objective-dimension specification with the
independently verified frozen T2 delegation binding. It never runs terminal cases
and never grants execution, promotion, capability, or family credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.objective_oracle_dominance_compiler import compile_dominance

SCHEMA="PROJECT_BRAIN_DELEGATION_OBJECTIVE_DOMINANCE_RECONCILIATION_V1"
LIVE_INPUT="canonical/governance/OBJECTIVE_ORACLE_DOMINANCE_LIVE_INPUT_V1.json"
BINDING="canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json"
BINDING_RECEIPT="canonical/verification/DELEGATION_T2_OBJECTIVE_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
BEHAVIOR="TASK_TO_DELEGATION_GRAPH_001"

def _read(root:Path,rel:str)->dict[str,Any]:
    obj=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return obj

def _git_blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _blob_matches(path:Path, expected:Any)->bool:
    return isinstance(expected,str) and bool(expected) and path.exists() and _git_blob_sha(path)==expected

def reconcile(root:Path)->dict[str,Any]:
    errors=[]
    try:
        live=_read(root,LIVE_INPUT)
        binding=_read(root,BINDING)
        receipt=_read(root,BINDING_RECEIPT)
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "errors":["INPUT_READ_FAILURE:"+type(exc).__name__],
            "comparator_deletion_admissible":False,
            "execution_authority":False,"promotion_authority":False,
            "capability_credit_delta":0,"family_credit_delta":0,
        }

    compiled=compile_dominance(live)
    if compiled.get("pass") is not True:
        errors.append("OBJECTIVE_COMPILER_FAIL_CLOSED")
        row={}
    else:
        matches=[x for x in compiled.get("contracts",[]) if isinstance(x,dict) and x.get("behavior_id")==BEHAVIOR]
        if len(matches)!=1:
            errors.append("DELEGATION_OBJECTIVE_ROW_COUNT_INVALID")
            row={}
        else:
            row=matches[0]

    if row:
        if row.get("objective_spec_complete") is not True:
            errors.append("OBJECTIVE_SPEC_INCOMPLETE")
        if row.get("stronger_direct_behavioral_route_structurally_available") is not True:
            errors.append("STRONGER_DIRECT_ROUTE_NOT_STRUCTURALLY_AVAILABLE")
        if not row.get("weaker_comparator_dependency"):
            errors.append("WEAKER_COMPARATOR_DEPENDENCY_MISSING")

    if binding.get("behavior_id")!=BEHAVIOR:
        errors.append("BINDING_BEHAVIOR_MISMATCH")
    if binding.get("proof_mode")!="T2_MULTIPLEXED_DIRECT_OBJECTIVE_DELEGATION_GATE":
        errors.append("BINDING_PROOF_MODE_INVALID")
    if binding.get("prewave_admissible") is not True:
        errors.append("CURRENT_BINDING_NOT_PREWAVE_ADMISSIBLE")
    if binding.get("independent_verification") != BINDING_RECEIPT:
        errors.append("CURRENT_BINDING_VERIFICATION_POINTER_INVALID")

    required=set(row.get("covered_dimensions") or [])
    declared=set(binding.get("objective_dimensions") or [])
    if not required or declared!=required:
        errors.append("OBJECTIVE_DIMENSION_BINDING_MISMATCH")

    gates=binding.get("route_gates")
    if not isinstance(gates,Mapping):
        errors.append("BINDING_ROUTE_GATES_INVALID")
        gates={}
    for key in (
        "candidate_package_frozen","executable_evaluator_bound",
        "population_or_source_pool_frozen","information_boundary_frozen",
        "post_freeze_selector_frozen","terminal_parent_binding_frozen",
    ):
        if gates.get(key) is not True:
            errors.append("BINDING_GATE_OPEN:"+key)

    if row and row.get("weaker_comparator_deletion_authorized_now") is not True:
        errors.append("OBJECTIVE_COMPILER_HAS_NOT_AUTHORIZED_COMPARATOR_DELETION")
    live_rows=live.get("contracts") if isinstance(live.get("contracts"),list) else []
    live_row=next((x for x in live_rows if isinstance(x,dict) and x.get("behavior_id")==BEHAVIOR),{})
    if live_row.get("route_gate_evidence") != BINDING_RECEIPT:
        errors.append("LIVE_INPUT_ROUTE_GATE_EVIDENCE_INVALID")

    if receipt.get("behavior_id")!=BEHAVIOR:
        errors.append("RECEIPT_BEHAVIOR_MISMATCH")
    if not str(receipt.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("INDEPENDENT_RECEIPT_NOT_PASS")
    if receipt.get("workflow_conclusion")!="success":
        errors.append("INDEPENDENT_WORKFLOW_NOT_SUCCESS")
    if receipt.get("terminal_results_observed")!=0 or receipt.get("fresh_terminal_evidence_consumed")!=0:
        errors.append("RECEIPT_CONSUMED_TERMINAL_EVIDENCE")

    exact=receipt.get("exact_brain_blobs")
    if not isinstance(exact,Mapping):
        errors.append("RECEIPT_EXACT_BLOBS_INVALID")
    else:
        # The public receipt binds the pre-promotion source manifest. The live
        # manifest may differ only by independently-derived verification metadata;
        # that before/after delta is verified by the route-specific public capsule.
        if exact.get(BINDING)!="65cf321cb1d08c06a236cd4d818dfdec3eb77c95":
            errors.append("VERIFIED_SOURCE_BINDING_BLOB_INVALID")
        for rel in (
            "canonical/runtime/delegation_whole_scope_candidate_v2.py",
            "canonical/runtime/delegation_whole_scope_proof_v2.py",
            "canonical/runtime/delegation_structural_variety_proof_v3.py",
        ):
            expected=exact.get(rel)
            if not _blob_matches(root/rel, expected):
                errors.append("OPERATIVE_BLOB_NOT_COVERED_BY_RECEIPT:"+rel)

    comparator_deletion=not errors
    return {
        "schema":SCHEMA,
        "status":"DELEGATION_DIRECT_OBJECTIVE_ROUTE_VERIFIED_READY_FOR_PROMOTION_LAW" if comparator_deletion else "FAIL_CLOSED",
        "pass":comparator_deletion,
        "behavior_id":BEHAVIOR,
        "objective_spec_complete":bool(row.get("objective_spec_complete")) if row else False,
        "bound_objective_dimensions":sorted(declared),
        "weaker_comparator_dependency":row.get("weaker_comparator_dependency") if row else None,
        "comparator_deletion_admissible":comparator_deletion,
        "prewave_route_ready_for_promotion_law":comparator_deletion,
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "errors":sorted(set(errors)),
        "rule":"DELETE_WEAKER_COMPARATOR_ONLY_AFTER_COMPLETE_OBJECTIVE_SPEC_PLUS_EXACT_INDEPENDENTLY_VERIFIED_FROZEN_BINDING__NO_TERMINAL_CREDIT",
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("repo_root",type=Path); a=ap.parse_args()
    out=reconcile(a.repo_root)
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
