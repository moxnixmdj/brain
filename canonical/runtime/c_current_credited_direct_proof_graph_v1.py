from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path

from canonical.runtime.c_edge_local_promotion_gate_v1 import verify_credited_proof_graph

ROOT=Path(__file__).resolve().parents[2]
S={
"matrix":("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json","cf736088c1ff460283f9b62d873b8e0710374e79"),
"symbolic":("canonical/capabilities/obsolescence/EXACT_SYMBOLIC_COMPUTATION_V1_ADJUDICATION.json","a691d49ef377fa216bbbeff70183112d65445463"),
"continuity":("canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json","2d912cf8df64bd806fffb6a1070d95644d005470"),
"delegation":("canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","d04f2a8c5594d261158835db1cae3822411b6b23"),
"recovery":("canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json","981c8ac9b66ee7fccf5b531525849e29df9be483"),
"tool":("canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","913d171b3c855000d322e183b142b3200eeaf0a9"),
}
EXPECTED={
"EXACT_SYMBOLIC_COMPUTATION",
"LONG_HORIZON_MEMORY_AND_CONTINUITY",
"SUBAGENT_DELEGATION_AND_COORDINATION",
"SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
"TOOL_DISCOVERY_SELECTION_AND_LEARNING",
}

def blob(rel):
    cp=subprocess.run(["git","-C",str(ROOT),"rev-parse",f"HEAD:{rel}"],text=True,capture_output=True,check=False)
    return cp.stdout.strip() if cp.returncode==0 else ""

def load(k):return json.loads((ROOT/S[k][0]).read_text(encoding="utf-8"))

def derive_rows():
    errors=[]
    for k,(p,h) in S.items():
        got=blob(p)
        if got!=h: errors.append(f"DRIFT:{k}:{got or 'MISSING'}")
    if errors:return None,errors
    matrix=load("matrix")
    accepted=set(matrix["postwave_acceptance_summary"]["calibrated_families"])
    if accepted!=EXPECTED:errors.append("ACCEPTED_FAMILY_SET_DRIFT")

    symbolic=load("symbolic"); continuity=load("continuity")
    delegation=load("delegation"); recovery=load("recovery"); tool=load("tool")

    checks={
      "EXACT_SYMBOLIC_COMPUTATION":(
        symbolic["decision"]["obsolescence_status"]=="OBSOLETE_VERIFIED"
        and symbolic["producer_execution"]["exact_correctness"]==1
        and symbolic["independent_adjudication"]["all_pass"] is True
        and symbolic["frontier_bar"]["basis"]=="THEORETICAL_CEILING"
      ),
      "LONG_HORIZON_MEMORY_AND_CONTINUITY":(
        continuity["status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER"
        and continuity["frontier_bar"]["basis"]=="OBJECTIVE_BEHAVIORAL_CEILING"
        and continuity["independent_adjudication"]["all_checks_pass"] is True
        and continuity["ownership_tests"]["ownership_package_test"]=="PASS"
      ),
      "SUBAGENT_DELEGATION_AND_COORDINATION":(
        delegation["public_runner"]["conclusion"]=="success"
        and delegation["verified_result"]["closure_mode"]=="ABSOLUTE_DOMINANCE"
        and delegation["verified_result"]["scope_completeness_basis"]=="UNIVERSAL_FORMAL_SCOPE_PROOF"
      ),
      "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":(
        recovery["public_runner"]["conclusion"]=="success"
        and recovery["verified"]["scope_complete"] is True
        and recovery["verified"]["objective_ceiling_or_floor"] is True
        and recovery["verified"]["exact_opus_case_level_access_required"] is False
      ),
      "TOOL_DISCOVERY_SELECTION_AND_LEARNING":(
        tool["independent_runner"]["conclusion"]=="success"
        and tool["verified"]["scope_complete"] is True
        and tool["verified"]["objective_ceiling"] is True
        and tool["verified"]["proof_kind"]=="ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS"
      ),
    }
    for k,v in checks.items():
        if not v:errors.append("DIRECT_PROOF_BINDING_FAILED:"+k)
    if errors:return None,errors
    mode={
      "EXACT_SYMBOLIC_COMPUTATION":"THEORETICAL_CEILING",
      "LONG_HORIZON_MEMORY_AND_CONTINUITY":"OBJECTIVE_CEILING",
      "SUBAGENT_DELEGATION_AND_COORDINATION":"ABSOLUTE_DOMINANCE",
      "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":"ABSOLUTE_DOMINANCE",
      "TOOL_DISCOVERY_SELECTION_AND_LEARNING":"ABSOLUTE_DOMINANCE",
    }
    rows=[{
      "route_id":family,
      "proof_kind":"DIRECT",
      "direct_mode":mode[family],
      "direct_scope_complete_verified":True,
      "direct_independent_verified":True,
      "parent_route_id":None,
      "transform_certificate":None,
    } for family in sorted(EXPECTED)]
    return rows,[]

def verify_current():
    rows,errors=derive_rows()
    if errors:
        return {"status":"FAIL_CLOSED","pass":False,"errors":errors,"terminal_credit_delta":0}
    graph=verify_credited_proof_graph(rows)
    ok=(graph["direct_root_count"]==5 and graph["transport_edge_count"]==0)
    return {
      "schema":"PROJECT_BRAIN_C_CURRENT_CREDITED_DIRECT_PROOF_GRAPH_V1",
      "status":"PASS__5_DIRECT_CREDITED_ROOTS__ZERO_TRANSPORT_EDGES__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":[] if ok else ["CURRENT_GRAPH_COUNT_DRIFT"],
      "accepted_family_count":5,
      "direct_root_count":graph["direct_root_count"],
      "transport_edge_count":graph["transport_edge_count"],
      "current_C_transport_certificates_required":graph["transport_edge_count"],
      "future_transport_promotion_requires_local_C_certificate":True,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=verify_current();print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
