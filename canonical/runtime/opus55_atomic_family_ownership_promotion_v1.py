"""Fail-closed verifier for the atomic Opus55 2/19 -> 4/19 ownership activation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.terminal_projection_consistency_v1 import evaluate_live as evaluate_projection

ROOT=Path(__file__).resolve().parents[2]

PATHS={
    "transaction":"canonical/governance/OPUS55_ATOMIC_FAMILY_OWNERSHIP_PROMOTION_V1.json",
    "matrix":"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
    "closure":"canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
    "authority":"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "eligibility":"canonical/verification/OPUS55_FAMILY_OWNERSHIP_PROMOTION_ELIGIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "tool_package":"canonical/capabilities/opus55/OPUS55_TOOL_DISCOVERY_SELECTION_AND_LEARNING_V1.json",
    "delegation_package":"canonical/capabilities/opus55/OPUS55_SUBAGENT_DELEGATION_AND_COORDINATION_V1.json",
}
PROMOTED={"TOOL_DISCOVERY_SELECTION_AND_LEARNING","SUBAGENT_DELEGATION_AND_COORDINATION"}
OWNED={"EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY",*PROMOTED}

def load(rel:str)->dict[str,Any]:
    d=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(d,dict): raise ValueError(rel)
    return d

def evaluate_documents(
    transaction:Mapping[str,Any],
    matrix:Mapping[str,Any],
    closure:Mapping[str,Any],
    authority:Mapping[str,Any],
    eligibility:Mapping[str,Any],
    tool_package:Mapping[str,Any],
    delegation_package:Mapping[str,Any],
    projection:Mapping[str,Any],
)->dict[str,Any]:
    e:list[str]=[]

    if projection.get("pass") is not True:
        e.append("PROJECTION_FIREWALL_NOT_PASS")
    if projection.get("verified_owned_families") != 4:
        e.append("PROJECTION_OWNERSHIP_NOT_4")

    if transaction.get("from_state") != {
        "verified_owned_families":2,
        "acceptance_calibrated_families":4,
        "acceptance_pending_families":15,
    }:
        e.append("TRANSACTION_FROM_STATE_MISMATCH")
    to=transaction.get("to_state")
    if not isinstance(to,Mapping):
        e.append("TRANSACTION_TO_STATE_MISSING"); to={}
    if to.get("verified_owned_families") != 4 or to.get("acceptance_calibrated_families") != 4 or to.get("acceptance_pending_families") != 15:
        e.append("TRANSACTION_TO_STATE_MISMATCH")
    if to.get("terminal_goal_achieved") is not False:
        e.append("TRANSACTION_FALSE_TERMINAL_CLOSURE")
    if set(transaction.get("promoted_families") or []) != PROMOTED:
        e.append("TRANSACTION_PROMOTED_SET_MISMATCH")
    if transaction.get("new_reality_units") != 0 or transaction.get("terminal_cases_replayed") != 0 or transaction.get("incremental_spend_usd") != 0:
        e.append("TRANSACTION_NOT_ZERO_REALITY")
    if transaction.get("promotion_authority") is not False:
        e.append("CANDIDATE_TRANSACTION_MUST_NOT_SELF_AUTHORIZE")

    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(eligibility.get("status","")):
        e.append("ELIGIBILITY_NOT_INDEPENDENT_PASS")
    pv=eligibility.get("public_verifier")
    if not isinstance(pv,Mapping) or pv.get("conclusion") != "success" or pv.get("workflow_run_id") != 37014840799 or pv.get("workflow_job_id") != 110863060515:
        e.append("ELIGIBILITY_PUBLIC_VERIFIER_MISMATCH")
    er=eligibility.get("result")
    if not isinstance(er,Mapping): e.append("ELIGIBILITY_RESULT_MISSING"); er={}
    if er.get("eligible_family_count") != 2 or set(er.get("eligible_families") or []) != PROMOTED:
        e.append("ELIGIBILITY_FAMILY_SET_MISMATCH")
    if er.get("current_strict_owned_families") != 2 or er.get("projected_strict_owned_families_after_atomic_promotion") != 4:
        e.append("ELIGIBILITY_TRANSITION_MISMATCH")
    if er.get("terminal_goal_achieved") is not False:
        e.append("ELIGIBILITY_FALSE_TERMINAL_CLOSURE")

    ms=matrix.get("summary")
    if not isinstance(ms,Mapping): e.append("MATRIX_SUMMARY_MISSING"); ms={}
    if set(ms.get("verified_owned_equal_or_better_capabilities") or []) != OWNED:
        e.append("MATRIX_OWNED_SET_MISMATCH")
    pas=matrix.get("postwave_acceptance_summary")
    if not isinstance(pas,Mapping): e.append("MATRIX_ACCEPTANCE_SUMMARY_MISSING"); pas={}
    if (pas.get("calibrated_family_count"),pas.get("verified_owned_family_count"),pas.get("pending_acceptance_family_count")) != (4,4,15):
        e.append("MATRIX_COUNTS_MISMATCH")
    rows=matrix.get("rows")
    if not isinstance(rows,list): e.append("MATRIX_ROWS_MISSING"); rows=[]
    by={r.get("family"):r for r in rows if isinstance(r,Mapping)}
    for fam in PROMOTED:
        r=by.get(fam)
        if not isinstance(r,Mapping):
            e.append(f"MATRIX_ROW_MISSING:{fam}"); continue
        if r.get("status") != "VERIFIED_OWNED_EQUAL_OR_BETTER":
            e.append(f"MATRIX_ROW_NOT_OWNED:{fam}")
        if r.get("postwave_ownership_credit") != "VERIFIED_OWNED_EQUAL_OR_BETTER__INDEPENDENT_FAMILY_LOCAL_PROMOTION":
            e.append(f"MATRIX_ROW_CREDIT_MISMATCH:{fam}")
        if r.get("ownership_promotion_evidence") != PATHS["eligibility"]:
            e.append(f"MATRIX_ROW_EVIDENCE_MISMATCH:{fam}")

    fam_key=next((k for k,v in closure.items() if isinstance(v,list) and any(isinstance(x,Mapping) and x.get("id") in PROMOTED for x in v)),None)
    if fam_key is None:
        e.append("CLOSURE_FAMILY_ARRAY_MISSING"); cf={}
    else:
        cf={x.get("id"):x for x in closure[fam_key] if isinstance(x,Mapping)}
    for fam in PROMOTED:
        r=cf.get(fam)
        if not isinstance(r,Mapping):
            e.append(f"CLOSURE_ROW_MISSING:{fam}"); continue
        if r.get("closure_state") != "PASS" or r.get("ownership_status") != "VERIFIED_OWNED_EQUAL_OR_BETTER":
            e.append(f"CLOSURE_ROW_NOT_OWNED:{fam}")
        if r.get("unresolved") != [] or r.get("opus55_acceptance_state") != "PASS" or r.get("opus55_acceptance_calibrated") is not True:
            e.append(f"CLOSURE_ROW_ACCEPTANCE_MISMATCH:{fam}")
        if r.get("ownership_promotion_evidence") != PATHS["eligibility"]:
            e.append(f"CLOSURE_ROW_EVIDENCE_MISMATCH:{fam}")
    cp=closure.get("family_local_ownership_promotion")
    if not isinstance(cp,Mapping): e.append("CLOSURE_PROMOTION_BLOCK_MISSING"); cp={}
    if cp.get("verified_owned_family_count") != 4 or set(cp.get("promoted_families") or []) != PROMOTED or cp.get("remaining_unowned_family_count") != 15:
        e.append("CLOSURE_PROMOTION_BLOCK_MISMATCH")
    if cp.get("terminal_goal_achieved") is not False:
        e.append("CLOSURE_FALSE_TERMINAL_CLOSURE")

    truth=authority.get("truth")
    if not isinstance(truth,Mapping): e.append("AUTHORITY_TRUTH_MISSING"); truth={}
    if truth.get("verified_owned") != "4/19_VERIFIED_OWNED__15/19_NOT_YET_OWNED":
        e.append("AUTHORITY_OWNERSHIP_MISMATCH")
    if truth.get("opus55_acceptance") != "4/19_PASS__15/19_OPEN":
        e.append("AUTHORITY_ACCEPTANCE_MISMATCH")
    if truth.get("achieved") is not False:
        e.append("AUTHORITY_FALSE_TERMINAL_CLOSURE")

    for pkg,fam,route_sha,witness_sha,cases in (
        (tool_package,"TOOL_DISCOVERY_SELECTION_AND_LEARNING","64c02edd568d95ec5ed54b7b8122183ce5b82e17","60a7c1139cad315d977bf5ed97e708cc5ec3fcc7","180_OF_180"),
        (delegation_package,"SUBAGENT_DELEGATION_AND_COORDINATION","f1a93ee66d90093de61dc17c6ebf2e24073df522","cb3b7c4b6c4e1f2a0471c6b6be72c4ca9ebddc80","132_OF_132"),
    ):
        if pkg.get("family") != fam or pkg.get("status") != "VERIFIED_OWNED_EQUAL_OR_BETTER":
            e.append(f"PACKAGE_IDENTITY_MISMATCH:{fam}")
        route=pkg.get("operative_route")
        acc=pkg.get("acceptance")
        gp=pkg.get("global_postconditions")
        if not isinstance(route,Mapping) or route.get("git_blob_sha") != route_sha or route.get("brain_owned") is not True or route.get("opaque_target_provider_required") is not False:
            e.append(f"PACKAGE_ROUTE_MISMATCH:{fam}")
        if not isinstance(acc,Mapping) or acc.get("git_blob_sha") != witness_sha or acc.get("full_protocol") is not True or acc.get("scope_relation") != "PROVEN_STRONGER" or acc.get("brain_lower_bound") != 1 or acc.get("theoretical_upper_bound") != 1 or acc.get("terminal_population") != cases or acc.get("independent") is not True or acc.get("contamination_clean") is not True:
            e.append(f"PACKAGE_ACCEPTANCE_MISMATCH:{fam}")
        if not isinstance(gp,Mapping) or gp.get("donor_dependent_required_behaviors") != 0 or gp.get("unresolved_verifier_mutations") != 0 or gp.get("unresolved_composition_failures") != 0 or gp.get("donor_deletion_cleanroom_pass") is not True:
            e.append(f"PACKAGE_GLOBAL_POSTCONDITIONS_MISMATCH:{fam}")
        if pkg.get("incremental_spend_usd") != 0:
            e.append(f"PACKAGE_SPEND_NONZERO:{fam}")

    e=sorted(set(e))
    return {
        "schema":"PROJECT_BRAIN_OPUS55_ATOMIC_FAMILY_OWNERSHIP_PROMOTION_VERDICT_V1",
        "status":"PASS__ATOMIC_OWNERSHIP_2_TO_4__ZERO_REALITY__TERMINAL_FALSE" if not e else "FAIL_CLOSED",
        "pass":not e,
        "errors":e,
        "verified_owned_before":2,
        "verified_owned_after":4 if not e else 2,
        "promoted_families":sorted(PROMOTED) if not e else [],
        "acceptance_calibrated_families":4,
        "acceptance_pending_families":15,
        "remaining_unowned_families":15,
        "terminal_goal_achieved":False,
        "new_reality_units":0,
        "terminal_cases_replayed":0,
        "incremental_spend_usd":0,
        "promotion_authority":False,
        "rule":"THIS_VERIFIER_PROVES_THE_ATOMIC_TRANSACTION__FINAL_AUTHORITY_COMES_ONLY_FROM_INDEPENDENT_EXACT_BLOB_VERIFICATION_PLUS_ATOMIC_MAIN_ACTIVATION",
    }

def evaluate_live()->dict[str,Any]:
    d={k:load(v) for k,v in PATHS.items()}
    p=evaluate_projection()
    return evaluate_documents(d["transaction"],d["matrix"],d["closure"],d["authority"],d["eligibility"],d["tool_package"],d["delegation_package"],p)

def main()->int:
    out=evaluate_live()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
