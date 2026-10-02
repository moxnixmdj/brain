"""Fail-closed verifier for the frozen T3 research-control multiplex prewave binding.

This verifies only prewave structure, exact prerequisite receipts, information
separation, scope accounting, and zero-cost carrier readiness. It does not open
terminal cases, execute HLE or Terminal-Bench, or grant capability/family credit.
"""
from __future__ import annotations
import json
from pathlib import Path

BINDING="canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json"
HLE="canonical/verification/HLE_STRICT_LOWER_BOUND_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
RESEARCH="canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
SCOPE="canonical/governance/T3_UNKNOWN_DOMAIN_SCOPE_AUDIT_V1.json"
HARBOR="canonical/verification/HARBOR_ZERO_COST_TERMINAL_CARRIER_PREFLIGHT_20261002_V1.json"

def _load(root:Path, rel:str)->dict:
    return json.loads((root/rel).read_text(encoding="utf-8"))

def evaluate(root:Path)->dict:
    errors=[]
    try:
        b=_load(root,BINDING)
        h=_load(root,HLE)
        r=_load(root,RESEARCH)
        s=_load(root,SCOPE)
        c=_load(root,HARBOR)
    except Exception as exc:
        return {"schema":"PROJECT_BRAIN_T3_RESEARCH_CONTROL_PREWAVE_VERDICT_V1","pass":False,"errors":["UNREADABLE:"+type(exc).__name__],"execution_authority":False}

    if b.get("behavior_id")!="ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001":
        errors.append("BEHAVIOR_ID")
    if b.get("proof_mode")!="PUBLIC_FIXED_BAR_MULTIPLEX_PLUS_DIRECT_BEHAVIOR_INSTRUMENTATION":
        errors.append("PROOF_MODE")
    if b.get("portfolio")!="T3":
        errors.append("PORTFOLIO")

    if h.get("workflow_conclusion")!="success" or "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(h.get("status","")):
        errors.append("HLE_SCORER_NOT_INDEPENDENT_PASS")
    if r.get("workflow_conclusion")!="success" or "INDEPENDENT_PASS" not in str(r.get("status","")):
        errors.append("RESEARCH_CONTROL_NOT_INDEPENDENT_PASS")
    grid=r.get("fresh_grid") or {}
    if grid.get("cases")!=2048 or grid.get("passed")!=2048 or grid.get("failed")!=0:
        errors.append("RESEARCH_GRID")
    if (s.get("coverage") or {}).get("unbound_contracts")!=[]:
        errors.append("UNKNOWN_DOMAIN_UNBOUND_CONTRACTS")
    cov=s.get("coverage") or {}
    if cov.get("required_contract_count")!=cov.get("bound_contract_count") or cov.get("scope_audit_frozen") is not True:
        errors.append("UNKNOWN_DOMAIN_SCOPE")
    if "INDEPENDENT_PASS" not in str(c.get("status","")):
        errors.append("HARBOR_CARRIER_NOT_INDEPENDENT_PASS")
    if c.get("incremental_spend_usd")!=0:
        errors.append("HARBOR_NONZERO_SPEND")

    visible=set((b.get("information_boundary") or {}).get("candidate_visible") or [])
    hidden=set((b.get("information_boundary") or {}).get("hidden_from_candidate") or [])
    if visible & hidden:
        errors.append("INFORMATION_BOUNDARY_OVERLAP")
    ib=b.get("information_boundary") or {}
    if ib.get("candidate_receives_reference_answer") is not False:
        errors.append("REFERENCE_ANSWER_VISIBLE")
    if ib.get("candidate_receives_hidden_oracle") is not False:
        errors.append("HIDDEN_ORACLE_VISIBLE")

    direct=b.get("direct_behavior_instrumentation") or {}
    if len(direct.get("required_observables") or [])<7:
        errors.append("DIRECT_OBSERVABLES_INCOMPLETE")
    for rel in (direct.get("candidate"),direct.get("preflight_population")):
        if not isinstance(rel,str) or not (root/rel).is_file():
            errors.append("DIRECT_DEPENDENCY_MISSING:"+str(rel))

    surfaces={x.get("id"):x for x in b.get("public_surfaces") or [] if isinstance(x,dict)}
    if set(surfaces)!={"HLE_WITH_TOOLS","TERMINAL_BENCH_SCIENCE_0_1"}:
        errors.append("PUBLIC_SURFACES")
    if (surfaces.get("HLE_WITH_TOOLS") or {}).get("target_percent")!=67.7:
        errors.append("HLE_TARGET")
    if (surfaces.get("TERMINAL_BENCH_SCIENCE_0_1") or {}).get("target_percent")!=58.7:
        errors.append("TB_SCIENCE_TARGET")
    if (surfaces.get("HLE_WITH_TOOLS") or {}).get("paid_judge_required") is not False:
        errors.append("PAID_JUDGE_REQUIRED")

    for k,v in (b.get("contamination") or {}).items():
        if v is not False:
            errors.append("CONTAMINATION:"+k)
    if b.get("execution_authority") is not False or b.get("terminal_results_observed")!=0:
        errors.append("PREWAVE_OVERCLAIM")
    if b.get("incremental_spend_usd")!=0 or b.get("capability_credit_delta")!=0 or b.get("family_credit_delta")!=0:
        errors.append("CREDIT_OR_SPEND")

    return {
        "schema":"PROJECT_BRAIN_T3_RESEARCH_CONTROL_PREWAVE_VERDICT_V1",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "execution_authority":False,
        "terminal_results_observed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "incremental_spend_usd":0,
    }
