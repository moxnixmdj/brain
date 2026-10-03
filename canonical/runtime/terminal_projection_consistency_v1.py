"""Receipt-derived fail-closed consistency reducer for Project Brain.

This checker grants no capability, family, execution, or promotion credit.
It derives the live acceptance state from current independently verified receipts,
then checks that authority/closure/matrix projections agree. Historical reconciliation
snapshots are evidence, not live counters.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
PATHS = {
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "closure": "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
    "matrix": "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
    "atomic_bindings": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "p1_propagation": "canonical/verification/TERMINAL_SCOPE_QUARANTINE_PROPAGATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "delegation_acceptance": "canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}
EXPECTED_P1_QUARANTINED = {
    "ADVANCED_AGENTIC_CODING","AGENTIC_SCIENTIFIC_RESEARCH","BUSINESS_WORKFLOW_AUTOMATION",
    "COMPLEX_MULTI_TOOL_AGENCY","COMPUTER_AND_BROWSER_USE","INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "MULTI_CAPABILITY_COMPOSITION","SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
}

def _load(rel: str) -> dict[str, Any]:
    value=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(rel+":NOT_OBJECT")
    return value

def _git_blob_sha(rel: str) -> str:
    data=(ROOT/rel).read_bytes()
    h=hashlib.sha1(); h.update(f"blob {len(data)}\0".encode()); h.update(data)
    return h.hexdigest()

def evaluate_documents(authority: Mapping[str,Any], closure: Mapping[str,Any], matrix: Mapping[str,Any],
                       atomic: Mapping[str,Any], p1: Mapping[str,Any], delegation: Mapping[str,Any],
                       actual_blob_shas: Mapping[str,str]|None=None) -> dict[str,Any]:
    errors:list[str]=[]
    vr=delegation.get("verified_result")
    if not isinstance(vr,Mapping):
        errors.append("DELEGATION_VERIFIED_RESULT_MISSING"); vr={}
    if not str(delegation.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DELEGATION_ACCEPTANCE_NOT_INDEPENDENT_PASS")
    closed=vr.get("closed_family_count"); opened=vr.get("open_family_count"); total=vr.get("family_count")
    accepted=set(vr.get("preserved_closed_families") or []) | set(vr.get("newly_closed_families") or [])
    if (closed,opened,total)!=(3,16,19) or len(accepted)!=3:
        errors.append("DELEGATION_ACCEPTANCE_RECEIPT_COUNTS_INVALID")
    if delegation.get("new_reality_units_consumed")!=0 or delegation.get("terminal_results_replayed")!=0:
        errors.append("DELEGATION_ACCEPTANCE_USED_FORBIDDEN_REALITY_OR_REPLAY")

    sat=atomic.get("saturation")
    if not isinstance(sat,Mapping): errors.append("ATOMIC_SATURATION_MISSING"); sat={}
    proved=sat.get("proved_predicate_count"); unresolved=sat.get("unresolved_predicate_count")
    if (proved,unresolved)!=(8,30): errors.append("ATOMIC_LEDGER_COUNTS_INVALID")
    claims=atomic.get("claims") if isinstance(atomic.get("claims"),list) else []
    dclaim=next((x for x in claims if isinstance(x,Mapping) and x.get("predicate_id")=="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"),None)
    if not isinstance(dclaim,Mapping) or dclaim.get("state")!="PROVED" or dclaim.get("scope_complete") is not True:
        errors.append("DELEGATION_ATOMIC_PROOF_MISSING")

    if set(p1.get("quarantined_families") or [])!=EXPECTED_P1_QUARANTINED:
        errors.append("P1_QUARANTINED_FAMILY_SET_MISMATCH")
    if len(p1.get("unaffected_behavioral_families") or [])!=11:
        errors.append("P1_UNAFFECTED_FAMILY_COUNT_NOT_11")

    truth=authority.get("truth") if isinstance(authority.get("truth"),Mapping) else {}
    if truth.get("opus55_acceptance")!=f"{closed}/19_PASS__{opened}/19_OPEN":
        errors.append("AUTHORITY_ACCEPTANCE_MISMATCH")
    if truth.get("achieved") is not False: errors.append("AUTHORITY_TERMINAL_MUST_REMAIN_FALSE")
    af=authority.get("atomic_acceptance_frontier") if isinstance(authority.get("atomic_acceptance_frontier"),Mapping) else {}
    if (af.get("proved"),af.get("unresolved"),af.get("total"))!=(proved,unresolved,38):
        errors.append("AUTHORITY_ATOMIC_FRONTIER_MISMATCH")
    if af.get("authorized_acceptance_case_actions")!=[]:
        errors.append("AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT")

    cs=closure.get("opus55_acceptance_summary") if isinstance(closure.get("opus55_acceptance_summary"),Mapping) else {}
    if (cs.get("calibrated_family_count"),cs.get("pending_family_count"))!=(closed,opened):
        errors.append("CLOSURE_ACCEPTANCE_COUNTS_MISMATCH")
    if set(cs.get("calibrated_families") or [])!=accepted:
        errors.append("CLOSURE_ACCEPTED_FAMILY_SET_MISMATCH")
    ca=cs.get("atomic_predicates") if isinstance(cs.get("atomic_predicates"),Mapping) else {}
    if (ca.get("proved"),ca.get("unresolved"),ca.get("total"))!=(proved,unresolved,38):
        errors.append("CLOSURE_ATOMIC_COUNTS_MISMATCH")
    crows=closure.get("families") if isinstance(closure.get("families"),list) else []
    cr=next((x for x in crows if isinstance(x,Mapping) and x.get("id")=="SUBAGENT_DELEGATION_AND_COORDINATION"),None)
    if not isinstance(cr,Mapping) or cr.get("opus55_acceptance_state")!="PASS" or cr.get("opus55_acceptance_calibrated") is not True:
        errors.append("CLOSURE_DELEGATION_ACCEPTANCE_NOT_PASS")

    ms=matrix.get("postwave_acceptance_summary") if isinstance(matrix.get("postwave_acceptance_summary"),Mapping) else {}
    if (ms.get("calibrated_family_count"),ms.get("pending_acceptance_family_count"))!=(closed,opened):
        errors.append("MATRIX_ACCEPTANCE_COUNTS_MISMATCH")
    if set(ms.get("calibrated_families") or [])!=accepted:
        errors.append("MATRIX_ACCEPTED_FAMILY_SET_MISMATCH")
    ma=ms.get("atomic_acceptance") if isinstance(ms.get("atomic_acceptance"),Mapping) else {}
    if (ma.get("proved"),ma.get("unresolved"),ma.get("total"))!=(proved,unresolved,38):
        errors.append("MATRIX_ATOMIC_COUNTS_MISMATCH")
    mrows=matrix.get("rows") if isinstance(matrix.get("rows"),list) else []
    mr=next((x for x in mrows if isinstance(x,Mapping) and x.get("family")=="SUBAGENT_DELEGATION_AND_COORDINATION"),None)
    if not isinstance(mr,Mapping) or not str(mr.get("postwave_opus55_acceptance_status","")).startswith("PASS_"):
        errors.append("MATRIX_DELEGATION_ACCEPTANCE_NOT_PASS")
    if isinstance(mr,Mapping) and mr.get("postwave_ownership_credit")!="ZERO_DIRECT_CREDIT__PROMOTION_AUTHORITY_FALSE":
        errors.append("MATRIX_DELEGATION_OWNERSHIP_OVERCLAIM")

    sources=authority.get("sources") if isinstance(authority.get("sources"),Mapping) else {}
    for key in ("residual_plan","acceptance_residual_proof_kernel_v2"):
        row=sources.get(key)
        if not isinstance(row,Mapping) or not any(t in str(row.get("status","")) for t in ("HISTORICAL","SUPERSEDED")):
            errors.append("STALE_PLANNING_SOURCE_NOT_DEMOTED:"+key)

    if actual_blob_shas is not None:
        pointer_expectations={
            "terminal_closure_manifest":PATHS["closure"],
            "ownership_matrix":PATHS["matrix"],
            "acceptance_predicate_evidence_bindings_reconciled":PATHS["atomic_bindings"],
            "p1_scope_quarantine_propagation":PATHS["p1_propagation"],
            "delegation_acceptance_reduction":PATHS["delegation_acceptance"],
        }
        for key,rel in pointer_expectations.items():
            row=sources.get(key)
            if not isinstance(row,Mapping):
                errors.append("AUTHORITY_SOURCE_MISSING:"+key); continue
            if row.get("path")!=rel: errors.append("AUTHORITY_SOURCE_PATH_MISMATCH:"+key)
            if row.get("git_blob_sha")!=actual_blob_shas.get(rel):
                errors.append("AUTHORITY_SOURCE_BLOB_MISMATCH:"+key)

    unique=sorted(set(errors))
    return {
        "schema":"PROJECT_BRAIN_TERMINAL_PROJECTION_CONSISTENCY_VERDICT_V3",
        "status":"PASS" if not unique else "FAIL_CLOSED","pass":not unique,"errors":unique,
        "acceptance_closed_families":closed,"acceptance_open_families":opened,
        "accepted_families":sorted(accepted),"atomic_predicates_proved":proved,
        "atomic_predicates_unresolved":unresolved,"terminal_goal_achieved":False,
        "capability_credit_delta":0,"family_credit_delta":0,
        "promotion_authority":False,"execution_authority":False,
        "rule":"LIVE_COUNTS_DERIVED_FROM_CURRENT_INDEPENDENT_RECEIPTS__STALE_HISTORY_CANNOT_OVERRIDE_CURRENT_PROOF_STATE",
    }

def evaluate_live()->dict[str,Any]:
    docs={k:_load(v) for k,v in PATHS.items()}
    shas={v:_git_blob_sha(v) for v in PATHS.values()}
    return evaluate_documents(docs["authority"],docs["closure"],docs["matrix"],docs["atomic_bindings"],
                              docs["p1_propagation"],docs["delegation_acceptance"],shas)

def main()->int:
    out=evaluate_live(); print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__": raise SystemExit(main())
