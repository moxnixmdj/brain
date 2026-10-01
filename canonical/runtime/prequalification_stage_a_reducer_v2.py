"""Generic deterministic Stage-A pre-exposure admission reducer for TB4 V5.

Reads only generic/pre-exposure Brain evidence. It MUST NOT read the task
instruction, solution, hidden verifier, task-specific hints, or execute the task.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

REF="452bf305c6daa62fc59061d22133a7cbc7c1572e"
BAR=0.664

def load(root: Path, rel: str) -> dict[str,Any]:
    return json.loads((root/rel).read_text(encoding="utf-8"))

def evaluate(root: Path, *, task: str, rank: int, ledger_path: str) -> dict[str,Any]:
    failures=[]
    t=load(root,"canonical/capabilities/opus55/TB4_V5_TARGET_VERSION_LOCK_V1.json")
    c=load(root,ledger_path)
    e=load(root,"canonical/capabilities/opus55/GENERIC_EXECUTION_SURFACE_CERTIFICATE_20261001_V1.json")
    a=load(root,"canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json")
    r=load(root,"canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json")
    s=load(root,"canonical/capabilities/opus55/TB4_V5_STAGE1_STATISTICAL_PROMOTION_PLAN_V1.json")
    d=load(root,"canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V1.json")
    p=load(root,"canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json")

    if not (str(t.get("status","")).startswith("FROZEN_") and t.get("benchmark_ref")==REF and t.get("stage1_target_success_fraction")==BAR and t.get("target_model")=="Claude Opus 5.5"):
        failures.append("TARGET_VERSION_LOCK")
    search=c.get("prior_exposure_search")
    search_clean=isinstance(search,dict) and all(v==0 for v in search.values())
    if not (
        c.get("task")==task and c.get("rank")==rank and c.get("benchmark_ref")==REF
        and c.get("state")=="UNEXPOSED__STAGE_A_PRE_EXPOSURE"
        and c.get("instruction_read") is False
        and c.get("hidden_verifier_read") is False
        and c.get("task_specific_hints_read") is False
        and c.get("task_specific_web_or_repo_search") is False
        and c.get("task_command_executed") is False
        and c.get("clean_for_stage_b_exposure") is True
        and not c.get("disqualifying_exposure_events")
        and search_clean
    ):
        failures.append("QUALIFICATION_CONTAMINATION_LEDGER")
    if e.get("status")!="STAGE_A_GENERIC_SURFACE_PASS__TASK_SPECIFIC_SURFACE_UNCLAIMED":
        failures.append("GENERAL_EXECUTION_SURFACE_CERTIFICATE")
    ar=a.get("runner",{})
    if not (
        ar.get("source_exact_match") is True
        and ar.get("tests_run",0)>0
        and ar.get("tests_passed")==ar.get("tests_run")
        and str(a.get("heldout_selection",{}).get("result","")).startswith("BLOCKED_TERMINAL_SUBMISSION_AS_REQUIRED")
    ):
        failures.append("INDEPENDENT_ACCEPTANCE_MECHANISM")
    rr=r.get("runner",{})
    if not (
        str(r.get("status","")).startswith("INDEPENDENT_VERIFICATION_PASS")
        and rr.get("exact_source_match") is True
        and rr.get("conclusion")=="success"
        and r.get("donor_runtime_required") is False
        and "SEEDED_REQUIREMENT_MUTATION_SUITE_HAS_ZERO_SURVIVORS_ON_VERIFICATION_CORPUS" in r.get("independently_verified_behaviors",[])
    ):
        failures.append("REQUIREMENT_GRAPH_AND_MUTATION_MECHANISM")
    if not (
        str(s.get("status","")).startswith("FROZEN_")
        and s.get("benchmark_ref")==REF
        and s.get("target_success_fraction")==BAR
        and s.get("replay") is False
        and s.get("cherry_picking") is False
    ):
        failures.append("STATISTICAL_PROMOTION_PLAN")
    if not (
        str(d.get("status","")).startswith("ACTIVE_GENERIC_PROTOCOL")
        and d.get("fail_closed") is True
        and d.get("pass_rule")=="BEHAVIOR_PRESERVED_AND_UNDECLARED_DEPENDENCY_COUNT_ZERO"
    ):
        failures.append("DONOR_DELETION_DEPENDENCY_PROTOCOL")
    required=set(p.get("staged_admission",{}).get("stage_a_pre_exposure",{}).get("required",[]))
    expected={
      "TARGET_VERSION_LOCK","QUALIFICATION_CONTAMINATION_LEDGER_CREATED_WITH_PRE_EXPOSURE_IDENTITY",
      "GENERAL_EXECUTION_SURFACE_CERTIFICATE","INDEPENDENT_ACCEPTANCE_MECHANISM_VERIFIED",
      "REQUIREMENT_GRAPH_AND_MUTATION_MECHANISM_VERIFIED",
      "STATISTICAL_PROMOTION_PLAN_FROZEN_IF_BENCHMARK_SCORE_WILL_BE_USED",
      "GENERIC_DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_AVAILABLE",
      "NO_TASK_SPECIFIC_SEARCH_OR_HINT_ACCESS"
    }
    if not expected <= required:
        failures.append("STAGE_A_POLICY_INCOMPLETE")
    return {
      "schema":"PROJECT_BRAIN_TB4_STAGE_A_ADMISSION_VERDICT_V2",
      "task":task,"rank":rank,
      "pass":not failures,
      "authorization":"STAGE_B_INSTRUCTION_EXPOSURE_ONLY" if not failures else "NONE",
      "task_execution_authorized":False,
      "failed_predicates":sorted(set(failures)),
      "rule":"STAGE_A_PASS_AUTHORIZES_ONLY_OFFICIAL_INSTRUCTION_EXPOSURE__NOT_TASK_EXECUTION"
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("repo_root",type=Path)
    ap.add_argument("--task",required=True)
    ap.add_argument("--rank",required=True,type=int)
    ap.add_argument("--ledger",required=True)
    args=ap.parse_args()
    out=evaluate(args.repo_root,task=args.task,rank=args.rank,ledger_path=args.ledger)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__": raise SystemExit(main())
