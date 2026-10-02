"""One-shot executor for the frozen global replacement terminal proof population."""
from __future__ import annotations

import argparse, hashlib, json, tempfile
from pathlib import Path
from typing import Any

ACTIVE_REGISTRY=Path("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
ACTIVE_BASIS=Path("canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json")

from canonical.runtime import contract_native_proof_suites as c_suite
from canonical.runtime import contract_native_brain_candidate as c_candidate
from canonical.runtime import remaining_behavior_proof_suites as r_suite
from canonical.runtime import remaining_behavior_brain_candidate as r_candidate

SCHEMA="PROJECT_BRAIN_GLOBAL_TERMINAL_REPLACEMENT_WAVE_RESULT_V1"
PREFIX=b"PROJECT_BRAIN_TERMINAL_V1\0"
DIFFICULTIES=(1,2,3,4,5)
CONTRACTS=tuple(sorted(set(c_suite.CONTRACTS)|set(r_suite.CONTRACTS)))


def _preflight_active_basis()->tuple[str,...]:
    registry=json.loads(ACTIVE_REGISTRY.read_text(encoding="utf-8"))
    basis=json.loads(ACTIVE_BASIS.read_text(encoding="utf-8"))
    active=tuple(sorted(
        row["behavior_id"] for row in registry.get("active_contracted_residuals",[])
        if isinstance(row,dict) and isinstance(row.get("behavior_id"),str)
    ))
    if len(active)!=len(registry.get("active_contracted_residuals",[])) or len(active)!=len(set(active)):
        raise ValueError("ACTIVE_CONTRACT_REGISTRY_INVALID")
    rows=basis.get("contracts",[])
    by_id={row.get("behavior_id"):row for row in rows if isinstance(row,dict) and isinstance(row.get("behavior_id"),str)}
    if set(by_id)!=set(active):
        raise ValueError("ACTIVE_TERMINAL_PROOF_BASIS_COVERAGE_MISMATCH")
    not_ready=sorted(
        bid for bid,row in by_id.items()
        if row.get("proof_state")!="TERMINAL_ROUTE_FROZEN_ADMISSIBLE"
    )
    if not_ready:
        raise ValueError("TERMINAL_ROUTES_NOT_ADMISSIBLE:"+",".join(not_ready))
    if set(CONTRACTS)!=set(active):
        missing=sorted(set(active)-set(CONTRACTS))
        extra=sorted(set(CONTRACTS)-set(active))
        raise ValueError("EXECUTOR_CONTRACT_SET_MISMATCH:missing="+",".join(missing)+";extra="+",".join(extra))
    return active


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
    work_root:Path|None=None,
)->dict[str,Any]:
    if not isinstance(slots_per_obligation,int) or isinstance(slots_per_obligation,bool) or slots_per_obligation<1:
        raise ValueError("SLOTS_INVALID")
    if slots_per_obligation!=12:
        raise ValueError("TERMINAL_PROTOCOL_REQUIRES_EXACTLY_12_SLOTS")
    active_contracts=_preflight_active_basis()
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

    all_pass=all(v["pass"] for v in behaviors.values()) and len(behaviors)==len(active_contracts)==12
    return {
        "schema":SCHEMA,
        "status":"PASS" if all_pass else "FAIL",
        "candidate_package_commitment":candidate_package_commitment,
        "post_freeze_beacon":post_freeze_beacon,
        "unique_behavioral_obligation_count":len(behaviors),
        "total_case_count":total,
        "total_failures":failures,
        "all_twelve_behavioral_contracts_pass":all_pass,
        "behaviors":behaviors,
        "rule":"12_OF_12_CASES_PER_ACTIVE_CONTRACT__12_OF_12_ACTIVE_CONTRACTS__NO_REPLACEMENT__NO_REPLAY_FOR_TUNING",
        "capability_credit_delta":"DEFER_TO_TERMINAL_REDUCER",
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate-package-commitment",required=True)
    ap.add_argument("--post-freeze-beacon",required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--work-root",type=Path)
    args=ap.parse_args()
    out=execute(candidate_package_commitment=args.candidate_package_commitment,post_freeze_beacon=args.post_freeze_beacon,work_root=args.work_root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k!="behaviors"},sort_keys=True))
    return 0 if out["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
