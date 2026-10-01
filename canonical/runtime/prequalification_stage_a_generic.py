"""Generic fail-closed Stage-A pre-exposure admission for TB4 tasks.

Only generic/pre-exposure evidence is admissible. The official task instruction,
solution, verifier, task-specific hints, and task commands must remain untouched.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

REF="452bf305c6daa62fc59061d22133a7cbc7c1572e"
BAR=0.664

def load(root: Path, rel: str) -> dict[str,Any]:
    return json.loads((root/rel).read_text(encoding="utf-8"))

def evaluate(root: Path, ledger_rel: str, task: str, rank: int, identity_sha256: str) -> dict[str,Any]:
    failures=[]
    t=load(root,"canonical/capabilities/opus55/TB4_V5_TARGET_VERSION_LOCK_V1.json")
    c=load(root,ledger_rel)
    e=load(root,"canonical/capabilities/opus55/GENERIC_EXECUTION_SURFACE_CERTIFICATE_20261001_V1.json")
    a=load(root,"canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json")
    r=load(root,"canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json")
    s=load(root,"canonical/capabilities/opus55/TB4_V5_STAGE1_STATISTICAL_PROMOTION_PLAN_V1.json")
    d=load(root,"canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V1.json")
    p=load(root,"canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json")
    l=load(root,"canonical/governance/PER_ACTION_CANONICAL_LEASE_REVALIDATION_VERIFICATION_20261001_V1.json")
    b=load(root,"canonical/governance/RUNNER_TOTAL_STAGE_C_BUDGET_GUARD_VERIFICATION_20261001_V1.json")

    if not (str(t.get("status","")).startswith("FROZEN") and t.get("benchmark_ref")==REF and t.get("stage1_target_success_fraction")==BAR and t.get("target_model")=="Claude Opus 5.5"):
        failures.append("TARGET_VERSION_LOCK")
    if not (
        c.get("task")==task and c.get("rank")==rank and
        c.get("task_identity_sha256")==identity_sha256 and
        c.get("benchmark_ref")==REF and
        c.get("state")=="UNEXPOSED__STAGE_A_PRE_EXPOSURE" and
        c.get("instruction_read") is False and
        c.get("hidden_verifier_read") is False and
        c.get("task_specific_hints_read") is False and
        c.get("task_specific_web_or_repo_search") is False and
        c.get("task_command_executed") is False and
        c.get("clean_for_stage_b_exposure") is True and
        not c.get("disqualifying_exposure_events")
    ):
        failures.append("QUALIFICATION_CONTAMINATION_LEDGER")
    exposure=c.get("prior_exposure_search",{})
    expected_hit_fields=(
        "brain_code_hits","runner_code_hits",
        "brain_branch_hits","runner_branch_hits",
        "brain_commit_hits","runner_commit_hits",
        "brain_pr_hits","runner_pr_hits"
    )
    if exposure.get("search_complete") is not True:
        failures.append("PRIOR_EXPOSURE_SEARCH_INCOMPLETE")
    missing=[k for k in expected_hit_fields if k not in exposure]
    if missing:
        failures.append("PRIOR_EXPOSURE_SEARCH_FIELDS_MISSING")
    if any(exposure.get(k) != 0 for k in expected_hit_fields):
        failures.append("PRIOR_EXPOSURE_SEARCH_NOT_CLEAN")
    if e.get("status")!="STAGE_A_GENERIC_SURFACE_PASS__TASK_SPECIFIC_SURFACE_UNCLAIMED":
        failures.append("GENERAL_EXECUTION_SURFACE_CERTIFICATE")
    ar=a.get("runner",{})
    if not (
        ar.get("source_exact_match") is True and ar.get("tests_run",0)>0 and
        ar.get("tests_passed")==ar.get("tests_run") and
        str(a.get("heldout_selection",{}).get("result","")).startswith("BLOCKED_TERMINAL_SUBMISSION_AS_REQUIRED")
    ):
        failures.append("INDEPENDENT_ACCEPTANCE_MECHANISM")
    rr=r.get("runner",{})
    if not (
        str(r.get("status","")).startswith("INDEPENDENT_VERIFICATION_PASS") and
        rr.get("exact_source_match") is True and rr.get("conclusion")=="success" and
        r.get("donor_runtime_required") is False and
        "SEEDED_REQUIREMENT_MUTATION_SUITE_HAS_ZERO_SURVIVORS_ON_VERIFICATION_CORPUS" in r.get("independently_verified_behaviors",[])
    ):
        failures.append("REQUIREMENT_GRAPH_AND_MUTATION_MECHANISM")
    if not (
        str(s.get("status","")).startswith("FROZEN") and
        s.get("benchmark_ref")==REF and s.get("target_success_fraction")==BAR and
        s.get("replay") is False and s.get("cherry_picking") is False
    ):
        failures.append("STATISTICAL_PROMOTION_PLAN")
    if not (
        str(d.get("status","")).startswith("ACTIVE_GENERIC_PROTOCOL") and
        d.get("fail_closed") is True and
        d.get("pass_rule")=="BEHAVIOR_PRESERVED_AND_UNDECLARED_DEPENDENCY_COUNT_ZERO"
    ):
        failures.append("DONOR_DELETION_DEPENDENCY_PROTOCOL")
    if not (
        l.get("status")=="VERIFIED_AND_MERGED__RANK15_REVOCATION_ESCAPE_CLASS_BLOCKED" and
        l.get("runner",{}).get("verification_tests_failed")==0 and
        l.get("runner",{}).get("verification_tests_passed",0)>0
    ):
        failures.append("PER_ACTION_CANONICAL_LEASE_REVALIDATION")
    bv=b.get("independent_verification",[])
    verified_workflows={x.get("workflow") for x in bv if isinstance(x,dict) and x.get("conclusion")=="success"}
    behaviors=set(b.get("repair",{}).get("behavior",[]))
    required_budget_behaviors={
      "EVERY_ACCEPTED_BUILDER_BURST_CONSUMES_ONE_EXECUTION_UNIT_BEFORE_ANY_TASK_COMMAND_RUNS",
      "BUILDER_BURST_REJECTED_WHEN_EXECUTION_COUNT_USED_GTE_EXECUTION_COUNT_ALLOWED",
      "TERMINAL_VERIFIER_UNIT_CONSUMED_BEFORE_HIDDEN_VERIFIER_INVOCATION",
      "TERMINAL_SUBMISSION_REJECTED_WHEN_TERMINAL_COUNT_USED_GTE_TERMINAL_VERIFIER_COUNT_ALLOWED"
    }
    if not (
        str(b.get("status","")).startswith("INDEPENDENT_PASS__MERGED") and
        b.get("repair",{}).get("merge_commit") and
        required_budget_behaviors <= behaviors and
        {"Verify independent acceptance gate","Stage lease promotion regression","Execution Guard Regression"} <= verified_workflows
    ):
        failures.append("TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD")
    required=set(p.get("staged_admission",{}).get("stage_a_pre_exposure",{}).get("required",[]))
    expected={
      "TARGET_VERSION_LOCK","QUALIFICATION_CONTAMINATION_LEDGER_CREATED_WITH_PRE_EXPOSURE_IDENTITY",
      "COMPLETE_8_SURFACE_PRIOR_EXPOSURE_SEARCH_INCLUDING_BRAIN_PRS",
      "GENERAL_EXECUTION_SURFACE_CERTIFICATE","INDEPENDENT_ACCEPTANCE_MECHANISM_VERIFIED",
      "REQUIREMENT_GRAPH_AND_MUTATION_MECHANISM_VERIFIED",
      "STATISTICAL_PROMOTION_PLAN_FROZEN_IF_BENCHMARK_SCORE_WILL_BE_USED",
      "GENERIC_DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_AVAILABLE",
      "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD_VERIFIED",
      "NO_TASK_SPECIFIC_SEARCH_OR_HINT_ACCESS"
    }
    if not expected <= required:
        failures.append("STAGE_A_POLICY_INCOMPLETE")
    failures=sorted(set(failures))
    return {
      "schema":"PROJECT_BRAIN_TB4_STAGE_A_ADMISSION_VERDICT_V2",
      "task":task,"rank":rank,"task_identity_sha256":identity_sha256,
      "pass":not failures,
      "authorization":"STAGE_B_INSTRUCTION_EXPOSURE_ONLY" if not failures else "NONE",
      "task_execution_authorized":False,
      "failed_predicates":failures,
      "rule":"STAGE_A_PASS_AUTHORIZES_ONLY_ONE_OFFICIAL_INSTRUCTION_EXPOSURE__NOT_TASK_EXECUTION"
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("repo_root",type=Path)
    ap.add_argument("--ledger",required=True)
    ap.add_argument("--task",required=True)
    ap.add_argument("--rank",required=True,type=int)
    ap.add_argument("--identity-sha256",required=True)
    args=ap.parse_args()
    out=evaluate(args.repo_root,args.ledger,args.task,args.rank,args.identity_sha256)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
