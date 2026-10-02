"""One-shot executor for the frozen global replacement terminal proof population."""
from __future__ import annotations

import argparse, hashlib, json, tempfile
from pathlib import Path
from typing import Any

from canonical.runtime import contract_native_proof_suites as c_suite
from canonical.runtime import contract_native_brain_candidate as c_candidate
from canonical.runtime import remaining_behavior_proof_suites as r_suite
from canonical.runtime import remaining_behavior_brain_candidate as r_candidate
from canonical.runtime import terminal_prequalification_reducer as prequal

SCHEMA="PROJECT_BRAIN_GLOBAL_TERMINAL_REPLACEMENT_WAVE_RESULT_V1"
PREFIX=b"PROJECT_BRAIN_TERMINAL_V1\0"
DIFFICULTIES=(1,2,3,4,5)
CONTRACTS=tuple(sorted(set(c_suite.CONTRACTS)|set(r_suite.CONTRACTS)))
REQUIRED_ACTIVE_CONTRACTS=tuple(sorted((
    "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
    "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
    "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001",
    "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
    "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
    "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
    "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001",
    "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
    "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
    "TASK_TO_DELEGATION_GRAPH_001",
    "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
    "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
)))


def contract_coverage()->dict[str,Any]:
    implemented=set(CONTRACTS)
    required=set(REQUIRED_ACTIVE_CONTRACTS)
    return {
        "required_count":len(required),
        "implemented_count":len(implemented),
        "missing":sorted(required-implemented),
        "unexpected":sorted(implemented-required),
        "pass":implemented==required,
    }


def derive_seed(candidate_package_commitment:str,post_freeze_beacon:str,case_id:str)->int:
    if not all(isinstance(x,str) and x for x in (candidate_package_commitment,post_freeze_beacon,case_id)):
        raise ValueError("NONEMPTY_STRING_BINDINGS_REQUIRED")
    raw=PREFIX+candidate_package_commitment.encode()+b"\0"+post_freeze_beacon.encode()+b"\0"+case_id.encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big",signed=False)


def execute(
    *,
    candidate_package_commitment:str,
    post_freeze_beacon:str,
    slots_per_obligation:int=12,
    repo_root:Path,
    work_root:Path|None=None,
)->dict[str,Any]:
    if not isinstance(slots_per_obligation,int) or isinstance(slots_per_obligation,bool) or slots_per_obligation<1:
        raise ValueError("SLOTS_INVALID")
    if slots_per_obligation!=12:
        raise ValueError("TERMINAL_PROTOCOL_REQUIRES_EXACTLY_12_SLOTS")
    coverage=contract_coverage()
    if not coverage["pass"]:
        raise ValueError(
            "TERMINAL_CONTRACT_COVERAGE_INCOMPLETE:"
            f"missing={','.join(coverage['missing'])}:"
            f"unexpected={','.join(coverage['unexpected'])}"
        )
    authorization=prequal.evaluate(repo_root)
    if authorization.get("pass") is not True or authorization.get("execution_authority") is not True:
        failed=",".join(authorization.get("failed_predicates") or [])
        raise ValueError("TERMINAL_PREQUALIFICATION_NOT_AUTHORIZED:"+failed)
    if authorization.get("authorization")!="T0_T1_T2_T3_PARALLEL_TERMINAL_WAVE":
        raise ValueError("TERMINAL_PREQUALIFICATION_AUTHORIZATION_MISMATCH")
    root=work_root or Path(tempfile.mkdtemp(prefix="brain-terminal-wave-"))
    root.mkdir(parents=True,exist_ok=True)
    behaviors={}
    total=0
    failures=0

    for contract in CONTRACTS:
        rows=[]
        for slot in range(slots_per_obligation):
            case_id=f"{contract}::slot::{slot:02d}"
            seed=derive_seed(candidate_package_commitment,post_freeze_beacon,case_id)
            difficulty=DIFFICULTIES[slot%len(DIFFICULTIES)]
            if contract in c_suite.CONTRACTS:
                case=c_suite.generate_case(contract,seed,difficulty)
                public=c_suite.public_task(case)
                candidate=c_candidate.solve(public)
                verdict=c_suite.score_case(case,candidate)
            else:
                case=r_suite.generate_case(contract,seed,difficulty)
                public=r_suite.public_task(case)
                case_dir=root/contract/f"{slot:02d}"
                case_dir.mkdir(parents=True,exist_ok=True)
                candidate=r_candidate.solve(public,workdir=case_dir)
                artifact_bytes=None
                if contract=="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001" and candidate.get("status")=="PASS":
                    artifact_bytes=Path(candidate["output_path"]).read_bytes()
                verdict=r_suite.score_case(case,candidate,artifact_bytes=artifact_bytes)
            passed=verdict.get("pass") is True
            total+=1
            failures+=0 if passed else 1
            rows.append({
                "case_id":case_id,
                "seed":seed,
                "difficulty":difficulty,
                "pass":passed,
                "failure_reason":None if passed else str(verdict.get("reason") or verdict.get("reasons") or "UNKNOWN"),
            })
        behavior_pass=all(x["pass"] for x in rows)
        behaviors[contract]={
            "case_count":len(rows),
            "pass_count":sum(1 for x in rows if x["pass"]),
            "pass":behavior_pass,
            "cases":rows,
        }

    all_pass=all(v["pass"] for v in behaviors.values()) and len(behaviors)==len(REQUIRED_ACTIVE_CONTRACTS)
    return {
        "schema":SCHEMA,
        "status":"PASS" if all_pass else "FAIL",
        "candidate_package_commitment":candidate_package_commitment,
        "post_freeze_beacon":post_freeze_beacon,
        "unique_behavioral_obligation_count":len(behaviors),
        "total_case_count":total,
        "total_failures":failures,
        "all_active_behavioral_contracts_pass":all_pass,
        "behaviors":behaviors,
        "rule":"12_OF_12_CASES_PER_BEHAVIOR__12_OF_12_ACTIVE_BEHAVIORS__NO_REPLACEMENT__NO_REPLAY_FOR_TUNING",
        "capability_credit_delta":"DEFER_TO_TERMINAL_REDUCER",
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate-package-commitment",required=True)
    ap.add_argument("--post-freeze-beacon",required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--repo-root",type=Path,required=True)
    ap.add_argument("--work-root",type=Path)
    args=ap.parse_args()
    out=execute(candidate_package_commitment=args.candidate_package_commitment,post_freeze_beacon=args.post_freeze_beacon,repo_root=args.repo_root,work_root=args.work_root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k!="behaviors"},sort_keys=True))
    return 0 if out["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
