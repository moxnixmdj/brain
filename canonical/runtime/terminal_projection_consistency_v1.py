"""Receipt-derived fail-closed consistency reducer for current Project Brain truth.

No capability, ownership, execution, or promotion credit is created here.
The reducer derives the currently admissible strict acceptance projection from
independent receipts and checks every live projection against it.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
PATHS={
 "authority":"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
 "closure":"canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
 "matrix":"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
 "atomic_bindings":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
 "p1_restoration":"canonical/verification/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "delegation_acceptance":"canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "recovery_acceptance":"canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json",
 "recovery_integrator":"canonical/verification/RECOVERY_ACCEPTANCE_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}
RECOVERY={
 "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
 "RECOVERY_TERMINAL_NONINFERIOR",
 "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
}

def _load(rel:str)->dict[str,Any]:
    v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(rel+":NOT_OBJECT")
    return v

def _git_blob_sha(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    h=hashlib.sha1(); h.update(f"blob {len(data)}\0".encode()); h.update(data)
    return h.hexdigest()

def evaluate_documents(
    authority:Mapping[str,Any], closure:Mapping[str,Any], matrix:Mapping[str,Any],
    atomic:Mapping[str,Any], p1:Mapping[str,Any], delegation:Mapping[str,Any],
    recovery:Mapping[str,Any], integrator:Mapping[str,Any],
    actual_blob_shas:Mapping[str,str]|None=None,
)->dict[str,Any]:
    errors:list[str]=[]
    def req(cond:bool,code:str)->None:
        if not cond: errors.append(code)

    # P1 current whole-scope restoration. Historical quarantine remains evidence,
    # never the current behavioral-state authority.
    pv=p1.get("verified") if isinstance(p1.get("verified"),Mapping) else {}
    req(str(p1.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"P1_RESTORATION_NOT_INDEPENDENT_PASS")
    req(pv.get("whole_p1_contract_restored") is True,"P1_WHOLE_SCOPE_NOT_RESTORED")
    req(pv.get("whole_scope_contract_pass_count")==12,"P1_CONTRACT_COUNT_NOT_12")
    req(pv.get("whole_scope_quarantined_contract_count")==0,"P1_CONTRACT_QUARANTINE_NONZERO")
    req(pv.get("provisional_behavioral_family_pass_count")==19,"P1_BEHAVIORAL_COUNT_NOT_19")
    req(pv.get("p1_quarantined_behavioral_family_count")==0,"P1_BEHAVIORAL_QUARANTINE_NONZERO")
    req(pv.get("restoration_new_reality_units_consumed")==0,"P1_RESTORATION_USED_FRESH_REALITY")

    # Delegation established the third accepted family while preserving the first two.
    dv=delegation.get("verified_result") if isinstance(delegation.get("verified_result"),Mapping) else {}
    req(str(delegation.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"DELEGATION_ACCEPTANCE_NOT_INDEPENDENT_PASS")
    req(delegation.get("new_reality_units_consumed")==0 and delegation.get("terminal_results_replayed")==0,
        "DELEGATION_USED_FORBIDDEN_REALITY_OR_REPLAY")
    base=set(dv.get("preserved_closed_families") or [])
    delegation_new=set(dv.get("newly_closed_families") or [])
    req(base=={"EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY"},"DELEGATION_BASE_CLOSED_SET_DRIFT")
    req(delegation_new=={"SUBAGENT_DELEGATION_AND_COORDINATION"},"DELEGATION_NEW_CLOSED_SET_DRIFT")

    # Recovery hardened proof and the separately verified atomic integrator.
    rv=recovery.get("verified") if isinstance(recovery.get("verified"),Mapping) else {}
    iv=integrator.get("verified_result") if isinstance(integrator.get("verified_result"),Mapping) else {}
    req(str(recovery.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"RECOVERY_PROOF_NOT_INDEPENDENT_PASS")
    req(rv.get("scope_complete") is True and rv.get("objective_ceiling_or_floor") is True,"RECOVERY_SCOPE_OR_BOUND_NOT_PROVED")
    req(rv.get("historical_relation_observed_bound_used_as_proof") is False,"RECOVERY_HISTORICAL_BOUND_REUSE")
    req(rv.get("historical_narrow_terminal_run_used_as_proof") is False,"RECOVERY_NARROW_RUN_REUSE")
    req(rv.get("quarantined_public_recovery_run_used_as_proof") is False,"RECOVERY_QUARANTINED_RUN_REUSE")
    req(set(rv.get("predicates") or [])==RECOVERY,"RECOVERY_PROOF_PREDICATE_SET_DRIFT")
    req(str(integrator.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"RECOVERY_INTEGRATOR_NOT_INDEPENDENT_PASS")
    req(iv.get("recovery_only_delta") is True,"RECOVERY_INTEGRATOR_NOT_EXCLUSIVE")
    req(iv.get("historical_bound_reuse_falsification_pass") is True,"RECOVERY_INTEGRATOR_HARDENING_NOT_VERIFIED")
    req(set(iv.get("newly_closed_families") or [])=={"SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"},"RECOVERY_INTEGRATOR_FAMILY_SET_DRIFT")
    req(set(iv.get("newly_proved_predicates") or [])==RECOVERY,"RECOVERY_INTEGRATOR_PREDICATE_SET_DRIFT")
    req(integrator.get("new_reality_units_consumed")==0 and integrator.get("terminal_results_replayed")==0,
        "RECOVERY_INTEGRATOR_USED_FORBIDDEN_REALITY_OR_REPLAY")

    before=iv.get("before") if isinstance(iv.get("before"),Mapping) else {}
    after=iv.get("after") if isinstance(iv.get("after"),Mapping) else {}
    req(before=={"proved_atomic":8,"unresolved_atomic":30,"accepted_families":3,"open_families":16},
        "RECOVERY_INTEGRATOR_BEFORE_STATE_DRIFT")
    req(after=={"proved_atomic":11,"unresolved_atomic":27,"accepted_families":4,"open_families":15},
        "RECOVERY_INTEGRATOR_AFTER_STATE_DRIFT")

    accepted=base|delegation_new|set(iv.get("newly_closed_families") or [])
    closed=int(after.get("accepted_families",-1)); opened=int(after.get("open_families",-1))
    proved=int(after.get("proved_atomic",-1)); unresolved=int(after.get("unresolved_atomic",-1))
    req(len(accepted)==closed and closed+opened==19,"CURRENT_ACCEPTANCE_FAMILY_ARITHMETIC")
    req(proved+unresolved==38,"CURRENT_ATOMIC_ARITHMETIC")

    sat=atomic.get("saturation") if isinstance(atomic.get("saturation"),Mapping) else {}
    req((sat.get("proved_predicate_count"),sat.get("unresolved_predicate_count"))==(proved,unresolved),
        "ATOMIC_LEDGER_COUNTS_INVALID")
    claims=atomic.get("claims") if isinstance(atomic.get("claims"),list) else []
    by_id={x.get("predicate_id"):x for x in claims if isinstance(x,Mapping) and isinstance(x.get("predicate_id"),str)}
    dclaim=by_id.get("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
    req(isinstance(dclaim,Mapping) and dclaim.get("state")=="PROVED" and dclaim.get("scope_complete") is True,
        "DELEGATION_ATOMIC_PROOF_MISSING")
    for pid in RECOVERY:
        row=by_id.get(pid)
        req(isinstance(row,Mapping) and row.get("state")=="PROVED" and row.get("scope_complete") is True,
            "RECOVERY_ATOMIC_PROOF_MISSING:"+pid)
        if isinstance(row,Mapping):
            req(row.get("source_path")==PATHS["recovery_integrator"],"RECOVERY_ATOMIC_SOURCE_PATH_MISMATCH:"+pid)
            if actual_blob_shas is not None:
                req(row.get("source_sha")==actual_blob_shas.get(PATHS["recovery_integrator"]),
                    "RECOVERY_ATOMIC_SOURCE_BLOB_MISMATCH:"+pid)

    truth=authority.get("truth") if isinstance(authority.get("truth"),Mapping) else {}
    req(truth.get("contracts")=="12/12_WHOLE_SCOPE_PASS__P1_SCOPE_RESTORED_BY_INDEPENDENT_ZERO_REALITY_UNIVERSAL_PROOF",
        "AUTHORITY_CONTRACT_WORLD_NOT_CURRENT")
    req(truth.get("behavioral_families")=="19/19_PROVISIONAL_BEHAVIORAL_PASS__P1_SCOPE_QUARANTINE_CLEARED__STRICT_OPUS55_ACCEPTANCE_SEPARATE",
        "AUTHORITY_BEHAVIORAL_WORLD_NOT_CURRENT")
    req(truth.get("opus55_acceptance")==f"{closed}/19_PASS__{opened}/19_OPEN","AUTHORITY_ACCEPTANCE_MISMATCH")
    req(truth.get("achieved") is False,"AUTHORITY_TERMINAL_MUST_REMAIN_FALSE")
    af=authority.get("atomic_acceptance_frontier") if isinstance(authority.get("atomic_acceptance_frontier"),Mapping) else {}
    req((af.get("proved"),af.get("unresolved"),af.get("total"))==(proved,unresolved,38),"AUTHORITY_ATOMIC_FRONTIER_MISMATCH")
    req(af.get("authorized_acceptance_case_actions")==[],"AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT")
    if actual_blob_shas is not None:
        req(af.get("source_git_blob_sha")==actual_blob_shas.get(PATHS["atomic_bindings"]),
            "AUTHORITY_ATOMIC_LEDGER_BLOB_MISMATCH")

    cs=closure.get("opus55_acceptance_summary") if isinstance(closure.get("opus55_acceptance_summary"),Mapping) else {}
    req((cs.get("calibrated_family_count"),cs.get("pending_family_count"))==(closed,opened),"CLOSURE_ACCEPTANCE_COUNTS_MISMATCH")
    req(set(cs.get("calibrated_families") or [])==accepted,"CLOSURE_ACCEPTED_FAMILY_SET_MISMATCH")
    ca=cs.get("atomic_predicates") if isinstance(cs.get("atomic_predicates"),Mapping) else {}
    req((ca.get("proved"),ca.get("unresolved"),ca.get("total"))==(proved,unresolved,38),"CLOSURE_ATOMIC_COUNTS_MISMATCH")
    req(closure.get("behavioral_pass_family_count")==19 and closure.get("behavioral_quarantined_family_count")==0,
        "CLOSURE_P1_RESTORATION_NOT_PROJECTED")
    crows=closure.get("families") if isinstance(closure.get("families"),list) else []
    for fam in ("SUBAGENT_DELEGATION_AND_COORDINATION","SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"):
        row=next((x for x in crows if isinstance(x,Mapping) and x.get("id")==fam),None)
        req(isinstance(row,Mapping) and row.get("opus55_acceptance_state")=="PASS" and row.get("opus55_acceptance_calibrated") is True,
            "CLOSURE_ACCEPTANCE_NOT_PASS:"+fam)

    ms=matrix.get("postwave_acceptance_summary") if isinstance(matrix.get("postwave_acceptance_summary"),Mapping) else {}
    req((ms.get("calibrated_family_count"),ms.get("pending_acceptance_family_count"))==(closed,opened),"MATRIX_ACCEPTANCE_COUNTS_MISMATCH")
    req(set(ms.get("calibrated_families") or [])==accepted,"MATRIX_ACCEPTED_FAMILY_SET_MISMATCH")
    ma=ms.get("atomic_acceptance") if isinstance(ms.get("atomic_acceptance"),Mapping) else {}
    req((ma.get("proved"),ma.get("unresolved"),ma.get("total"))==(proved,unresolved,38),"MATRIX_ATOMIC_COUNTS_MISMATCH")
    req(ms.get("verified_owned_family_count")==2,"MATRIX_OWNERSHIP_COUNT_INFLATED")
    mrows=matrix.get("rows") if isinstance(matrix.get("rows"),list) else []
    for fam in ("SUBAGENT_DELEGATION_AND_COORDINATION","SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"):
        row=next((x for x in mrows if isinstance(x,Mapping) and x.get("family")==fam),None)
        req(isinstance(row,Mapping) and str(row.get("postwave_opus55_acceptance_status","")).startswith("PASS_"),
            "MATRIX_ACCEPTANCE_NOT_PASS:"+fam)
        if isinstance(row,Mapping):
            req(str(row.get("postwave_ownership_credit","")).startswith("ZERO"),
                "MATRIX_OWNERSHIP_OVERCLAIM:"+fam)

    sources=authority.get("sources") if isinstance(authority.get("sources"),Mapping) else {}
    for key in ("residual_plan","acceptance_residual_proof_kernel_v2"):
        row=sources.get(key)
        req(isinstance(row,Mapping) and any(t in str(row.get("status","")) for t in ("HISTORICAL","SUPERSEDED")),
            "STALE_PLANNING_SOURCE_NOT_DEMOTED:"+key)

    if actual_blob_shas is not None:
        pointer_expectations={
          "terminal_closure_manifest":PATHS["closure"],
          "ownership_matrix":PATHS["matrix"],
          "acceptance_predicate_evidence_bindings_reconciled":PATHS["atomic_bindings"],
        }
        for key,rel in pointer_expectations.items():
            row=sources.get(key)
            req(isinstance(row,Mapping),"AUTHORITY_SOURCE_MISSING:"+key)
            if isinstance(row,Mapping):
                req(row.get("path")==rel,"AUTHORITY_SOURCE_PATH_MISMATCH:"+key)
                req(row.get("git_blob_sha")==actual_blob_shas.get(rel),"AUTHORITY_SOURCE_BLOB_MISMATCH:"+key)

    unique=sorted(set(errors))
    return {
      "schema":"PROJECT_BRAIN_TERMINAL_PROJECTION_CONSISTENCY_VERDICT_V4",
      "status":"PASS" if not unique else "FAIL_CLOSED","pass":not unique,"errors":unique,
      "acceptance_closed_families":closed,"acceptance_open_families":opened,
      "accepted_families":sorted(accepted),"atomic_predicates_proved":proved,
      "atomic_predicates_unresolved":unresolved,"terminal_goal_achieved":False,
      "p1_whole_scope_restored":True,"verified_owned_family_count":2,
      "capability_credit_delta":0,"family_credit_delta":0,
      "promotion_authority":False,"execution_authority":False,
      "rule":"LIVE_COUNTS_DERIVED_FROM_CURRENT_INDEPENDENT_RECEIPTS__ACCEPTANCE_DOES_NOT_SELF_PROMOTE_OWNERSHIP",
    }

def evaluate_live()->dict[str,Any]:
    docs={k:_load(v) for k,v in PATHS.items()}
    shas={v:_git_blob_sha(v) for v in PATHS.values()}
    return evaluate_documents(
      docs["authority"],docs["closure"],docs["matrix"],docs["atomic_bindings"],
      docs["p1_restoration"],docs["delegation_acceptance"],docs["recovery_acceptance"],
      docs["recovery_integrator"],shas,
    )

def main()->int:
    out=evaluate_live(); print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__": raise SystemExit(main())
