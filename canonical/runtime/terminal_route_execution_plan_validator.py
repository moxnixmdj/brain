"""Fail-closed validator for the route-specific terminal execution plan.

This validates only prelaunch structure and exact blob bindings. It must never
derive a post-freeze seed, generate a terminal case, or grant launch/capability
authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TERMINAL_ROUTE_EXECUTION_PLAN_V1"
VERDICT="PROJECT_BRAIN_TERMINAL_ROUTE_EXECUTION_PLAN_VALIDATION_V1"
EXPECTED_PARENTS={"T0","T1","T2","T3"}
EXPECTED_DIRECT={
    "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001":128,
    "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001":2000,
    "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001":150,
    "TASK_TO_DELEGATION_GRAPH_001":132,
    "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":180,
    "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001":180,
}
EXPECTED_MULTIPLEX={
    "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
    "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
    "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
    "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
    "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001",
    "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
}


def _blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def _binding_rows(row:Mapping[str,Any]):
    for key,value in row.items():
        if isinstance(value,Mapping) and isinstance(value.get("path"),str) and isinstance(value.get("blob_sha"),str):
            yield key,value


def validate(root:Path, plan:Mapping[str,Any])->dict[str,Any]:
    errors:list[str]=[]
    if not isinstance(plan,Mapping) or plan.get("schema")!=SCHEMA:
        return _fail("SCHEMA_INVALID")
    if plan.get("terminal_case_generation_allowed") is not False:
        errors.append("TERMINAL_CASE_GENERATION_MUST_REMAIN_DISABLED")
    if plan.get("launch_authority") is not False:
        errors.append("PLAN_MUST_NOT_SELF_AUTHORIZE_LAUNCH")

    kernel=plan.get("selection_kernel")
    if not isinstance(kernel,Mapping):
        errors.append("SELECTION_KERNEL_INVALID")
    else:
        path=kernel.get("path"); expected=kernel.get("blob_sha")
        if not isinstance(path,str) or not isinstance(expected,str):
            errors.append("SELECTION_KERNEL_BINDING_INVALID")
        else:
            p=root/path
            if not p.exists() or _blob_sha(p)!=expected:
                errors.append("SELECTION_KERNEL_BLOB_MISMATCH")

    direct=plan.get("direct_populations")
    multiplex=plan.get("multiplex_instrumentation")
    if not isinstance(direct,list):
        errors.append("DIRECT_POPULATIONS_INVALID"); direct=[]
    if not isinstance(multiplex,list):
        errors.append("MULTIPLEX_INSTRUMENTATION_INVALID"); multiplex=[]

    seen:set[str]=set()
    direct_ids:set[str]=set()
    multiplex_ids:set[str]=set()
    parents_seen:set[str]=set()

    for row in direct:
        if not isinstance(row,Mapping):
            errors.append("DIRECT_ROW_INVALID"); continue
        bid=row.get("behavior_id")
        if not isinstance(bid,str) or not bid:
            errors.append("DIRECT_BEHAVIOR_ID_INVALID"); continue
        if bid in seen:
            errors.append("DUPLICATE_BEHAVIOR:"+bid)
        seen.add(bid); direct_ids.add(bid)
        if bid not in EXPECTED_DIRECT:
            errors.append("UNEXPECTED_DIRECT_BEHAVIOR:"+bid)
        elif row.get("sample_count")!=EXPECTED_DIRECT[bid]:
            errors.append("DIRECT_SAMPLE_COUNT_MISMATCH:"+bid)
        parents=row.get("parents")
        if not isinstance(parents,list) or not parents or any(x not in EXPECTED_PARENTS for x in parents):
            errors.append("DIRECT_PARENTS_INVALID:"+bid)
        else:
            parents_seen.update(parents)
        for key,binding in _binding_rows(row):
            p=root/binding["path"]
            if not p.exists():
                errors.append(f"BINDING_PATH_MISSING:{bid}:{key}")
            elif _blob_sha(p)!=binding["blob_sha"]:
                errors.append(f"BINDING_BLOB_MISMATCH:{bid}:{key}")

    for row in multiplex:
        if not isinstance(row,Mapping):
            errors.append("MULTIPLEX_ROW_INVALID"); continue
        bid=row.get("behavior_id")
        if not isinstance(bid,str) or not bid:
            errors.append("MULTIPLEX_BEHAVIOR_ID_INVALID"); continue
        if bid in seen:
            errors.append("DUPLICATE_BEHAVIOR:"+bid)
        seen.add(bid); multiplex_ids.add(bid)
        if bid not in EXPECTED_MULTIPLEX:
            errors.append("UNEXPECTED_MULTIPLEX_BEHAVIOR:"+bid)
        parents=row.get("parents")
        if not isinstance(parents,list) or not parents or any(x not in EXPECTED_PARENTS for x in parents):
            errors.append("MULTIPLEX_PARENTS_INVALID:"+bid)
        else:
            parents_seen.update(parents)
        if "sample_count" in row:
            errors.append("MULTIPLEX_STANDALONE_SAMPLE_COUNT_FORBIDDEN:"+bid)
        binding=row.get("binding")
        if not isinstance(binding,Mapping):
            errors.append("MULTIPLEX_BINDING_INVALID:"+bid)
        else:
            p=root/str(binding.get("path",""))
            expected=binding.get("blob_sha")
            if not p.exists():
                errors.append("MULTIPLEX_BINDING_PATH_MISSING:"+bid)
            elif not isinstance(expected,str) or _blob_sha(p)!=expected:
                errors.append("MULTIPLEX_BINDING_BLOB_MISMATCH:"+bid)

    if direct_ids!=set(EXPECTED_DIRECT):
        errors.append("DIRECT_SET_MISMATCH")
    if multiplex_ids!=EXPECTED_MULTIPLEX:
        errors.append("MULTIPLEX_SET_MISMATCH")
    if len(seen)!=12:
        errors.append(f"TOTAL_CONTRACT_COUNT_MISMATCH:{len(seen)}")
    if parents_seen!=EXPECTED_PARENTS:
        errors.append("PARENT_PORTFOLIO_COVERAGE_MISMATCH")
    counts=plan.get("counts")
    if not isinstance(counts,Mapping) or counts.get("direct_population_contracts")!=6 or counts.get("multiplex_instrumentation_contracts")!=6 or counts.get("total_contracts")!=12:
        errors.append("DECLARED_COUNTS_INVALID")

    if errors:
        return _fail(*errors,validated_contract_count=len(seen))
    return {
        "schema":VERDICT,
        "status":"PASS__EXACT_12_CONTRACT_TWO_LAYER_EXECUTION_GRAPH_FROZEN__ZERO_TERMINAL_CASES_GENERATED",
        "pass":True,
        "validated_contract_count":12,
        "direct_population_count":6,
        "multiplex_instrumentation_count":6,
        "parent_portfolios":sorted(parents_seen),
        "terminal_case_generation_performed":False,
        "launch_authority":False,
        "promotion_authority":False,
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "errors":[],
    }


def _fail(*errors:str,**extra:Any)->dict[str,Any]:
    out={
        "schema":VERDICT,
        "status":"FAIL_CLOSED",
        "pass":False,
        "launch_authority":False,
        "promotion_authority":False,
        "terminal_case_generation_performed":False,
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "errors":sorted(set(errors)),
    }
    out.update(extra)
    return out


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("plan",type=Path)
    args=ap.parse_args()
    data=json.loads(args.plan.read_text(encoding="utf-8"))
    out=validate(args.root,data)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1


if __name__=="__main__":
    raise SystemExit(main())
